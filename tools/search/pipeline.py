#!/usr/bin/env python3
"""
Pipeline orchestrator for LinkedIn job search and storage.
Handles the overall flow from search to storage.
"""

# tools\search\pipeline.py

import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Import modules using relative imports
from . import config_loader, filter
from ..common.progress_display import ProgressDisplay
from ..fetch import details, db_access

# Import from search module (current package)
from .search import search_jobs

# Initialize logger
logger = logging.getLogger(__name__)

class JobPipeline:
    """Orchestrates the job search and storage pipeline."""
    
    def __init__(self, args, progress=None):
        """
        Initialize the job search and storage pipeline.
        
        Args:
            args: Command-line arguments
            progress: Optional ProgressDisplay instance for real-time updates
        """
        self.args = args
        self.progress = progress
        self.config = {
            'filters': {},
            'workflows': {}
        }
        self.db_interface = None
        self.storage_results = {
            'success_count': 0,
            'failure_count': 0,
            'updated_count': 0,
            'skipped_count': 0,
            'duplicate_count': 0,
            'errors': []
        }
    
    def _update_progress(self, **kwargs):
        """
        Update the progress display if available.
        
        Args:
            **kwargs: Key-value pairs to update in the progress display
        """
        if self.progress:
            self.progress.update(**kwargs)
    
    def _load_configuration(self):
        """Load filter and workflow configurations."""
        # Load filter configurations
        title_filters_path = os.path.join(self.args.filters_dir, 'title_filters.json')
        company_filters_path = os.path.join(self.args.filters_dir, 'company_filters.json')
        
        self.config['filters'] = {
            'title': config_loader.load_filter_config(title_filters_path),
            'company': config_loader.load_filter_config(company_filters_path)
        }
        
        # Load workflows
        self.config['workflows'] = config_loader.load_workflows(self.args.workflows_file)
        
        logger.info(f"Loaded filter and workflow configurations")
        self._update_progress(status_message="Loaded configurations")
    
    def _determine_urls(self) -> List[str]:
        """
        Determine which URLs to process based on command-line arguments.
        
        Returns:
            List of URLs to process
        """
        urls_to_process = []
        
        # Check if URL mode or workflow mode
        if self.args.url:
            # Single URL mode
            logger.info(f"Single URL mode: {self.args.url}")
            urls_to_process = [self.args.url]
            self.is_workflow_mode = False
            
        else:
            # Workflow mode
            workflow_name = self.args.workflow or 'default'
            logger.info(f"Workflow mode: {workflow_name}")
            
            workflow = config_loader.get_workflow_by_name(self.config['workflows'], workflow_name)
            
            if not workflow:
                error_msg = f"Workflow '{workflow_name}' not found"
                logger.error(error_msg)
                self._update_progress(status_message=f"ERROR: {error_msg}")
                return []
            
            urls_to_process = workflow.get('urls', [])
            
            # Get pages from workflow unless overridden by command line
            if 'pages' in workflow and self.args.pages == 3:  # Default value is 3
                self.args.pages = workflow['pages']
                
            # Add max_age_hours to args if in workflow
            if 'max_age_hours' in workflow:
                self.args.max_age_hours = workflow['max_age_hours']
                logger.info(f"Using max age filter: {self.args.max_age_hours} hours")
            else:
                self.args.max_age_hours = None
                
            self.is_workflow_mode = True
            
        logger.info(f"Will process {len(urls_to_process)} URLs")
        self._update_progress(status_message=f"Will process {len(urls_to_process)} URLs")
        
        return urls_to_process
    
    def _initialize_db(self) -> bool:
        """
        Initialize the database interface.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        if self.args.dry_run:
            logger.info("Dry run mode - database operations will be skipped")
            self._update_progress(status_message="DRY RUN: Database operations will be skipped")
            return True
            
        try:
            logger.info(f"Initializing database interface with DB path: {self.args.db_path}")
            self.db_interface = db_access.DatabaseInterface(self.args.db_path)
            logger.info("Database interface initialized successfully")
            self._update_progress(status_message="Database connection established")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize database connection: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            self._update_progress(status_message=f"DATABASE ERROR: {str(e)[:80]}...")
            return False
    
    def _update_progress_for_url_filter(self, **kwargs):
        """
        Update progress display specifically for URL-level filtering operations.

        Args:
            **kwargs: Key-value pairs to update in the progress display
        """
        if self.progress:
            # Log current state before update
            current_filtered = self.progress.stats.jobs_filtered_out if hasattr(self.progress.stats, 'jobs_filtered_out') else 0
            current_total = self.progress.stats.total_jobs_found if hasattr(self.progress.stats, 'total_jobs_found') else 0
            logger.info(f"Pipeline filter progress - Current state: filtered={current_filtered}, total={current_total}")
            
            # Only update the status message to avoid messing with global counters
            if 'status_message' in kwargs:
                logger.debug(f"Updating status message: {kwargs['status_message']}")
                self.progress.update(status_message=kwargs['status_message'])

            # Only update filter counts if jobs_filtered_out is provided
            if 'jobs_filtered_out' in kwargs:
                new_filtered = current_filtered + kwargs['jobs_filtered_out']
                logger.info(f"Updating filtered count: {current_filtered} -> {new_filtered} "
                           f"(Adding {kwargs['jobs_filtered_out']} newly filtered jobs)")
                
                self.progress.update(
                    jobs_filtered_out=new_filtered,
                    status_message=kwargs.get('status_message', self.progress.stats.status_message)
                )
                
                # Calculate and log remaining jobs
                old_remaining = current_total - current_filtered
                self.progress.stats.calculate_remaining()
                new_remaining = self.progress.stats.jobs_remaining
                logger.info(f"Updated remaining jobs: {old_remaining} -> {new_remaining}")

    def _db_progress_callback(self, job_idx, total_jobs, success_count, error_count):
        """
        Callback function for database operations progress.

        Args:
            job_idx: Current job index (0-based)
            total_jobs: Total number of jobs
            success_count: Number of successful operations
            error_count: Number of failed operations
        """
        if self.progress:
            jobs_processed = job_idx + 1  # Convert from 0-based to count
            percent_done = int((job_idx + 1) / total_jobs * 100) if total_jobs > 0 else 0
            self.progress.update(
                jobs_processed=jobs_processed,
                jobs_inserted=success_count,
                status_message=f"Processed {jobs_processed}/{total_jobs} jobs ({percent_done}%): {success_count} inserted"
            )
    
    def run(self) -> int:
        """
        Run the job search and storage pipeline.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            # Load configurations
            self._load_configuration()

            # Determine URLs to process
            urls_to_process = self._determine_urls()
            if not urls_to_process:
                logger.error("No URLs to process")
                self._update_progress(status_message="Error: No URLs to process")
                return 1

            # Initialize database interface if needed
            if not self.args.dry_run and not self._initialize_db():
                return 1

            # Initialize aggregated statistics
            total_success_count = 0
            total_failure_count = 0
            total_updated_count = 0
            total_skipped_count = 0
            total_duplicate_count = 0
            all_errors = []
            start_time_overall = datetime.now()  # For overall elapsed time
            all_collected_jobs = []  # To store all jobs found before filtering/storing per URL
            successful_urls = 0

            # Process each URL
            self._update_progress(
                total_urls=len(urls_to_process),
                status_message=f"Starting to process {len(urls_to_process)} URLs..."
            )

            for i, url in enumerate(urls_to_process):
                logger.info(f"Processing URL {i+1}/{len(urls_to_process)}: {url}")

                self._update_progress(
                    url_count=i+1,
                    status_message=f"Processing URL {i+1}/{len(urls_to_process)}"
                )

                try:
                    # Search for jobs
                    logger.info(f"Searching URL: {url}")
                    logger.info(f"Will fetch up to {self.args.pages} pages with {self.args.jobs_per_page} jobs per page")

                    self._update_progress(
                        current_url=url,
                        status_message="Searching for jobs..."
                    )

                    start_time = datetime.now()

                    # Call search_jobs function from search module
                    jobs = search_jobs(
                        search_url=url,
                        cookie_file=self.args.cookie_file,
                        output_dir=self.args.output_dir,
                        max_pages=self.args.pages,
                        jobs_per_page=self.args.jobs_per_page,
                        verbose=self.args.verbose
                    )

                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.info(f"Found {len(jobs)} jobs in search results (took {elapsed:.2f} seconds)")

                    if self.progress:
                        self.progress.update(
                            total_jobs_found=self.progress.stats.total_jobs_found + len(jobs),
                            status_message=f"Found {len(jobs)} jobs"
                        )
                        self.progress.stats.calculate_remaining()

                    if not jobs:
                        logger.warning(f"No jobs found for URL: {url}")
                        continue

                    # Fetch detailed job information
                    max_jobs = len(jobs) if self.args.max_jobs is None else min(self.args.max_jobs, len(jobs))
                    logger.info(f"Fetching detailed information for {max_jobs} jobs...")

                    self._update_progress(
                        status_message=f"Fetching details for {max_jobs} jobs..."
                    )

                    try:
                        # Call fetch_job_details from details module
                        detailed_jobs = details.fetch_job_details(
                            jobs=jobs,
                            cookie_file=self.args.cookie_file,
                            output_dir=self.args.output_dir,
                            max_jobs=max_jobs,
                            verbose=self.args.verbose,
                            progress_callback=self._update_progress
                        )

                        jobs = detailed_jobs
                        logger.info(f"Fetched detailed information for {len(detailed_jobs)} jobs")

                    except Exception as e:
                        logger.error(f"Error fetching job details: {e}")
                        logger.debug(traceback.format_exc())
                        logger.warning("Continuing with basic job data")

                        if self.progress:
                            self.progress.update(
                                status_message="Error fetching details, using basic data"
                            )

                    # Apply max age filter if specified in workflow
                    if hasattr(self.args, 'max_age_hours') and self.args.max_age_hours:
                        original_count = len(jobs)
                        from datetime import timedelta
                        max_age = datetime.now() - timedelta(hours=self.args.max_age_hours)

                        if self.progress:
                            self.progress.update(
                                status_message=f"Filtering jobs by age ({self.args.max_age_hours} hours)..."
                            )

                        filtered_jobs = []
                        for job in jobs:
                            # Try to parse the posting date
                            date_str = job.get('posting_date') or job.get('posted_date')
                            if date_str:
                                try:
                                    job_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                    if job_date < max_age:
                                        logger.debug(f"Skipping job posted at {job_date}, older than {self.args.max_age_hours} hours")
                                        continue
                                except (ValueError, TypeError):
                                    # If we can't parse the date, keep the job
                                    pass

                            filtered_jobs.append(job)

                        filtered_out = original_count - len(filtered_jobs)
                        logger.info(f"Age-filtered from {original_count} to {len(filtered_jobs)} jobs (max age: {self.args.max_age_hours} hours)")
                        jobs = filtered_jobs

                        if self.progress:
                            self.progress.update(
                                jobs_filtered_out=self.progress.stats.jobs_filtered_out + filtered_out,
                                status_message=f"Age-filtered: removed {filtered_out} jobs"
                            )
                            self.progress.stats.calculate_remaining()

                    # Add jobs to the collected list (for potential JSON output later)
                    all_collected_jobs.extend(jobs)

                    if not jobs:
                        logger.warning(f"No jobs to filter or store for URL: {url}")
                        continue  # Skip to the next URL if no jobs were found/kept after age filter

                    # --- Apply global filters to jobs from THIS URL ---
                    try:
                        logger.info(f"Applying filters to {len(jobs)} jobs from {url}...")

                        if self.progress:
                            self.progress.update(
                                status_message=f"Filtering {len(jobs)} jobs from URL {i+1}..."
                            )

                        filtered_jobs_from_url = filter.apply_filters(
                            jobs,  # Filter only jobs from the current URL
                            self.args.filters_dir,
                            progress_callback=self._update_progress_for_url_filter,
                            title_filters=self.config['filters']['title'],
                            company_filters=self.config['filters']['company']
                        )
                        logger.info(f"After filtering for URL {url}: {len(filtered_jobs_from_url)} jobs remain")

                        if not filtered_jobs_from_url:
                            logger.warning(f"No jobs remain after filtering for URL: {url}")
                            continue  # Skip to the next URL

                    except Exception as e:
                        logger.error(f"Error applying filters for URL {url}: {e}")
                        logger.debug(traceback.format_exc())
                        all_errors.append(f"Filter error for {url}: {e}")
                        continue  # Skip storing for this URL if filtering failed

                    # --- Store filtered jobs for THIS URL ---
                    if not self.args.dry_run:
                        logger.info(f"Storing {len(filtered_jobs_from_url)} jobs from URL {url}...")
                        self._update_progress(
                            status_message=f"Storing {len(filtered_jobs_from_url)} jobs from URL {i+1}..."
                        )

                        try:
                            # Store jobs for this URL
                            url_start_time = datetime.now()

                            def url_progress_callback(job_idx, total_jobs, success_count, error_count):
                                """Update progress for current URL's storage progress"""
                                if self.progress:
                                    jobs_processed = job_idx + 1  # Convert from 0-based to count
                                    percent_done = int((job_idx + 1) / total_jobs * 100) if total_jobs > 0 else 0
                                    self.progress.update(
                                        jobs_processed=self.progress.stats.jobs_processed + 1,
                                        jobs_inserted=total_success_count + success_count,
                                        status_message=f"URL {i+1}: Processed {jobs_processed}/{total_jobs} jobs ({percent_done}%)"
                                    )

                            # Use the DB interface initialized earlier
                            success_count, failure_count, errors = self.db_interface.store_jobs_batch(
                                filtered_jobs_from_url,  # Store only filtered jobs from this URL
                                update_existing=self.args.update_existing,
                                batch_size=self.args.batch_size,
                                progress_callback=url_progress_callback
                            )

                            # Calculate elapsed time for this URL
                            url_elapsed = (datetime.now() - url_start_time).total_seconds()

                            # Extract counts from errors for this URL
                            url_skipped_count = 0
                            url_duplicate_count = 0
                            url_updated_count = 0

                            for msg in errors:
                                if "already exists" in msg:
                                    if "duplicate job by company and title" in msg:
                                        url_duplicate_count += 1
                                    else:
                                        url_skipped_count += 1
                                elif "updated" in msg:
                                    url_updated_count += 1

                            # Aggregate results
                            total_success_count += success_count
                            total_failure_count += failure_count
                            total_updated_count += url_updated_count
                            total_skipped_count += url_skipped_count
                            total_duplicate_count += url_duplicate_count
                            all_errors.extend([f"Store error ({url}): {e}" for e in errors])  # Prefix errors with URL context

                            logger.info(
                                f"Storage for URL {url} complete: {success_count} new, "
                                f"{url_updated_count} updated, {url_skipped_count} skipped, "
                                f"{url_duplicate_count} duplicates, {failure_count} failed "
                                f"(took {url_elapsed:.2f} seconds)"
                            )

                            # Update progress display
                            if self.progress:
                                self.progress.update(
                                    status_message=f"URL {i+1} storage complete: {success_count} new jobs stored"
                                )

                        except Exception as e:
                            logger.error(f"Critical error storing jobs for URL {url}: {e}")
                            logger.debug(traceback.format_exc())
                            all_errors.append(f"Critical Store error for {url}: {e}")
                            # Count these jobs as failures
                            total_failure_count += len(filtered_jobs_from_url)

                            if self.progress:
                                self.progress.update(
                                    status_message=f"Error storing jobs for URL {i+1}: {str(e)[:50]}..."
                                )

                            # Stop pipeline execution on database errors
                            raise

                    elif filtered_jobs_from_url:  # Handle dry run case
                        logger.info(f"DRY RUN: Would store {len(filtered_jobs_from_url)} jobs from URL {url}")

                        if self.progress:
                            self.progress.update(
                                status_message=f"DRY RUN: Would store {len(filtered_jobs_from_url)} jobs from URL {i+1}"
                            )

                        for job in filtered_jobs_from_url:
                            logger.info(f"DRY RUN: Would store job: {job.get('title')} at {job.get('company')}")

                    successful_urls += 1

                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")
                    logger.debug(traceback.format_exc())
                    all_errors.append(f"URL processing error ({url}): {e}")

                    if self.progress:
                        self.progress.update(
                            status_message=f"Error: {str(e)[:50]}..."
                        )

            # After processing all URLs
            elapsed_overall = (datetime.now() - start_time_overall).total_seconds()
            logger.info(f"Processed {successful_urls}/{len(urls_to_process)} URLs successfully")
            logger.info(f"Found a total of {len(all_collected_jobs)} jobs from all URLs")
            logger.info(f"Storage summary: {total_success_count} new, {total_updated_count} updated, "
                      f"{total_skipped_count} skipped, {total_duplicate_count} duplicates, "
                      f"{total_failure_count} failed")

            if self.progress:
                self.progress.update(
                    status_message=f"Processed {successful_urls}/{len(urls_to_process)} URLs successfully"
                )

            # Check if we found any jobs
            if not all_collected_jobs:
                logger.warning("No jobs found from any URL. Exiting.")
                self._update_progress(status_message="No jobs found")
                return 0

            # Output results to JSON file if requested
            try:
                if self.args.output_json:
                    logger.info(f"Saving all {len(all_collected_jobs)} collected jobs to {self.args.output_json}")
                    with open(self.args.output_json, 'w', encoding='utf-8') as f:
                        import json
                        json.dump(all_collected_jobs, f, indent=2)
                    logger.info(f"Saved all jobs to {self.args.output_json}")
            except Exception as e:
                logger.error(f"Error saving JSON output: {e}")
                logger.debug(traceback.format_exc())

            # Create final storage results for reporting
            final_storage_results = {
                'success_count': total_success_count,
                'failure_count': total_failure_count,
                'updated_count': total_updated_count,
                'skipped_count': total_skipped_count,
                'duplicate_count': total_duplicate_count,
                'errors': all_errors,
                'elapsed': elapsed_overall
            }

            # Write a summary report
            from . import reporting
            report_path = reporting.write_storage_report(
                args=self.args,
                output_dir=self.args.output_dir,
                all_jobs=all_collected_jobs,
                is_workflow_mode=self.is_workflow_mode,
                urls_to_process=urls_to_process,
                successful_urls=successful_urls,
                storage_results=final_storage_results,
                elapsed=elapsed_overall,
                errors=all_errors
            )

            # Print job statistics
            try:
                from . import reporting

                # Only print stats to console if progress display is disabled
                if not self.progress:
                    reporting.print_job_stats(all_collected_jobs)
                    reporting.print_sample_jobs(all_collected_jobs)
                else:
                    # Just log the stats without printing to console
                    reporting.log_job_stats(all_collected_jobs, logger)

            except Exception as e:
                logger.error(f"Error processing job statistics: {e}")
                logger.debug(traceback.format_exc())

            # Finalize progress display
            if self.progress:
                self.progress.update(status_message="Job processing completed successfully")

            logger.info("Job processing completed successfully")
            return 0
            
        except KeyboardInterrupt:
            logger.info("\nOperation interrupted by user. Exiting.")
            
            if self.progress:
                self.progress.update(status_message="Operation interrupted by user")
            
            return 130  # Standard exit code for SIGINT
            
        except Exception as e:
            logger.error(f"Unhandled exception: {e}")
            logger.debug(traceback.format_exc())
            
            if self.progress:
                self.progress.update(status_message=f"Error: {str(e)[:50]}...")
            
            return 1