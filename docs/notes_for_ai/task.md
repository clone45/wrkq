Okay, let's tackle this. There are two related issues here:

1.  **Root Cause:** The actual error `Slogger.exception() got an unexpected keyword argument 'level'` happening inside the database layer (`db_access.py` or the underlying `job_tracker` code it calls).
2.  **Symptom/Goal:** The pipeline continues processing the next URL even after this critical database error occurs, whereas you want it to stop.

Let's address both.

**Issue 1: Fixing the `Slogger.exception()` Error**

This error means that somewhere in the code called by `DatabaseInterface.store_job` (likely within the `CompanyRepo.find_or_create` method or the `JobRepo.add` method it uses), there's a call to `logger.exception` (or a wrapper named `Slogger.exception`) that is incorrectly passing a `level` argument.

*   **Standard Logging:** The built-in `logging.exception()` method automatically logs the message at the `ERROR` level and includes the exception traceback. It does *not* accept a `level` keyword argument.

*   **Locating the Error:** Examine `tools/fetch/db_access.py`. Look inside the `_initialize_db`, `store_job`, `_find_existing_job`, `_create_job_model`, and especially any code related to calling `self._company_repo.find_or_create(...)` and `self._job_repo.add(...)`. The actual faulty call might be inside the `job_tracker.db.repos` files themselves if `db_access.py` is just calling them directly.

*   **The Fix:** Find the line making the call like `logger.exception("Some message", ..., level=logging.ERROR)` or similar. **Remove the `level=...` argument**. The call should look like:
    ```python
    # Example of the incorrect call (likely inside job_tracker repo code):
    # logger.exception(f"Database error creating company '{company_name}': {str(company_err)}", level=logging.ERROR) # INCORRECT

    # Corrected call:
    logger.exception(f"Database error creating company '{company_name}': {str(company_err)}") # CORRECT
    ```
    *Self-Correction within `db_access.py`*: I notice your `db_access.py` *does* re-raise critical errors using `raise RuntimeError(...)`. This is good! It means the error *should* be propagating up. The issue is how it's handled *after* it propagates. Let's focus on Issue 2.

**Issue 2: Making the Pipeline Stop on Critical Storage Errors**

The trace shows the error *is* caught by the `try...except` block around the storage section within the URL loop in `JobPipeline.run`. However, after catching it, logging it, and updating failure counts, the `except` block finishes, and the loop continues.

*   **Locating the Handling Block:** In `tools/search/pipeline.py`, find the `run` method and specifically the `try...except Exception as e:` block that wraps the call to `self.db_interface.store_jobs_batch(...)`. It looks like this:

    ```python
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
                        # <<<<<<< PROBLEM: Execution continues after this block >>>>>>>>
    ```

*   **The Fix:** To make the pipeline stop, you need to re-raise the exception after you've logged it and handled the progress bar within this `except` block. This will cause the exception to propagate out of the `run` method and be caught by the top-level handler in `store_jobs.py`, which will then exit the script.

*   **Code Modification:** Add `raise` at the end of that specific `except` block:

    ```python
                    except Exception as e:
                        logger.error(f"Critical error storing jobs for URL {url}: {e}")
                        logger.debug(traceback.format_exc())
                        all_errors.append(f"Critical Store error for {url}: {e}")
                        # Count these jobs as failures
                        total_failure_count += len(filtered_jobs_from_url) # Or adjust based on actual failure point

                        if self.progress:
                            self.progress.update(
                                status_message=f"Error storing jobs for URL {i+1}: {str(e)[:50]}..."
                            )

                        # Re-raise the exception to stop the pipeline
                        raise # <<<<<<< ADD THIS LINE >>>>>>>>
    ```

**Summary of Changes:**

1.  **(Recommended but likely in `job_tracker` code):** Find the `logger.exception(...)` call in the database repository code (`CompanyRepo` or `JobRepo`) that is causing the `TypeError: Slogger.exception() got an unexpected keyword argument 'level'` and remove the `level=...` argument.
2.  **(Required for stopping):** In `tools/search/pipeline.py`, inside the `run` method, locate the `except Exception as e:` block that handles errors from `self.db_interface.store_jobs_batch` and add the line `raise` at the very end of that block.

Making the change in `pipeline.py` will ensure that *any* exception escaping `store_jobs_batch` (including the one you're seeing now, or any future critical database errors) will halt the entire script execution immediately after being logged for the specific URL.Thanks