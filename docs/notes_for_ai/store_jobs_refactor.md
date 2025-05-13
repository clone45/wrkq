Okay, here is a detailed implementation plan designed to be understood and executed by an LLM. It breaks down the refactoring of `tools/search/store_jobs.py` into specific, actionable steps based on the previously discussed modular structure.

**Goal:** Refactor the monolithic script `tools/search/store_jobs.py` into a modular structure within the `tools` directory, separating concerns like argument parsing, configuration, searching, fetching details, filtering, database interaction, reporting, and orchestration. The script's core functionality must be preserved.

**Target Directory Structure:**

```
tools/
├── common/             # Existing: common utilities
│   ├── config.py
│   ├── utils.py
│   ├── progress_display.py
│   └── __init__.py
├── fetch/              # Existing: Focus on getting data & DB
│   ├── db_access.py      # Existing: DatabaseInterface
│   ├── details.py        # New/Renamed: For fetch_job_details
│   └── __init__.py       # (Cleanup potential redundant files later)
├── search/             # Existing: Focus on finding jobs & orchestration
│   ├── cli.py            # New: Argument parsing
│   ├── config_loader.py  # New: Filter/workflow loading
│   ├── filter.py         # New: Job filtering logic
│   ├── reporting.py      # New: Report generation, stats
│   ├── search.py         # Existing: Primary search_jobs function
│   ├── pipeline.py       # New: Orchestration logic
│   ├── store_jobs.py     # Existing: Becomes thin ENTRY POINT
│   └── __init__.py
```

**Implementation Plan:**

**Phase 1: Create New Files and Move Core Functions**

1.  **Create New Files:**
    *   In `tools/search/`, create the following empty Python files:
        *   `cli.py`
        *   `config_loader.py`
        *   `filter.py`
        *   `reporting.py`
        *   `pipeline.py`
    *   In `tools/fetch/`, create the file:
        *   `details.py`

2.  **Move Argument Parsing (`tools/search/cli.py`):**
    *   Locate the `parse_args()` function in the original `tools/search/store_jobs.py`.
    *   Move the entire `parse_args()` function definition into `tools/search/cli.py`.
    *   Ensure necessary imports (`argparse`, `os`, constants from `tools.common.config`) are present or added at the top of `cli.py`. Use relative imports for accessing `common` (e.g., `from ..common.config import ...`).

3.  **Move Configuration Loading (`tools/search/config_loader.py`):**
    *   Locate the functions `load_filter_config()`, `load_workflows()`, and `get_workflow_by_name()` in the original `tools/search/store_jobs.py`.
    *   Move these three function definitions into `tools/search/config_loader.py`.
    *   Ensure necessary imports (`os`, `json`, `logging`, potentially `typing`) are present or added at the top of `config_loader.py`.
    *   Define a `logger` instance within this module if needed (e.g., `logger = logging.getLogger(__name__)`).

4.  **Move Filtering Logic (`tools/search/filter.py`):**
    *   Locate the functions `compile_regex_patterns()` and `apply_filters()` in the original `tools/search/store_jobs.py`.
    *   Move these two function definitions into `tools/search/filter.py`.
    *   Ensure necessary imports (`os`, `re`, `logging`, `typing`, `json` if `load_filter_config` was called directly inside, `tools.common.progress_display`) are present or added at the top of `filter.py`.
    *   Update the `apply_filters` function: It should now *receive* the loaded filter configurations as arguments instead of loading them itself (the loading will be done by the pipeline using `config_loader`). It should also accept the `progress` object or a callback function. Modify its signature accordingly.
    *   Define a `logger` instance within this module.

5.  **Move Reporting Logic (`tools/search/reporting.py`):**
    *   Locate the functions `print_job_stats()` and `print_sample_jobs()` in the original `tools/search/store_jobs.py`.
    *   Move these two function definitions into `tools/search/reporting.py`.
    *   Locate the code block within `main()` responsible for writing the `storage_report_{datetime}.txt` file (starting around `report_path = os.path.join...`). Create a new function in `reporting.py`, perhaps named `write_storage_report(args, storage_results, output_dir, ...)`, and move this report-writing logic into it. Pass necessary data (like `args`, counts, elapsed time, errors) as arguments.
    *   Ensure necessary imports (`os`, `datetime`, `typing`) are present or added at the top of `reporting.py`.

6.  **Consolidate Job Searching (`tools/search/search.py`):**
    *   Ensure the definitive `search_jobs()` function (which takes a search URL and returns a list of basic job dictionaries) resides in `tools/search/search.py`.
    *   *Crucially*, check if variations of `search_jobs` exist in other files (like `tools/fetch/search_jobs.py` or `tools/fetch/search.py`). If they perform the *same task*, remove the duplicates and ensure all callers use the one in `tools/search/search.py`. If they perform a *different* task, rename them appropriately.
    *   Ensure necessary imports are present in `tools/search/search.py`.

7.  **Move Job Detail Fetching (`tools/fetch/details.py`):**
    *   Locate the `fetch_job_details()` function in the original `tools/search/store_jobs.py` (it might currently be imported from `tools.search.search`).
    *   Move the *definition* of `fetch_job_details()` into `tools/fetch/details.py`.
    *   Ensure necessary imports (`os`, `datetime`, `logging`, `typing`, constants, potentially selenium/requests if used directly) are present or added at the top of `details.py`. Use relative imports to access `common` (e.g., `from ..common.config import ...`).
    *   Define a `logger` instance within this module.

**Phase 2: Create the Pipeline Orchestrator**

8.  **Implement the Pipeline (`tools/search/pipeline.py`):**
    *   Create a class named `JobPipeline` (or similar) in `tools/search/pipeline.py`.
    *   **`__init__` Method:**
        *   The constructor `__init__(self, args, progress=None)` should accept the parsed `args` object and the optional `progress` display object.
        *   Store `args` and `progress` as instance attributes (e.g., `self.args`, `self.progress`).
        *   Define instance attributes to hold state, like `self.config = {}`, `self.db_interface = None`, `self.storage_results = {}`.
        *   Import necessary modules using relative imports: `from . import cli, config_loader, filter, reporting, search`, `from ..fetch import details, db_access`, `from ..common import utils, progress_display`.
    *   **Helper Methods (Internal):**
        *   Create private helper methods like `_load_configuration()`, `_determine_urls()`, `_initialize_db()`, `_update_progress(self, **kwargs)`, `_db_progress_callback(...)`.
        *   `_load_configuration`: Call functions from `config_loader` to load workflows/filters based on `self.args` and store them in `self.config`.
        *   `_determine_urls`: Implement the logic from the original `main()` to decide whether to use `args.url` or load URLs from a workflow in `self.config`. Return the list of URLs.
        *   `_initialize_db`: If not `self.args.dry_run`, instantiate `db_access.DatabaseInterface` and store it in `self.db_interface`. Include error handling for DB connection issues.
        *   `_update_progress`: A wrapper to safely call `self.progress.update(**kwargs)` if `self.progress` is not None.
        *   `_db_progress_callback`: Adapt the `job_progress_callback` logic from the original `main()` to be a method that uses `self._update_progress`.
    *   **`run()` Method:**
        *   This method contains the main orchestration logic, previously in `main()`.
        *   Call `self._load_configuration()`.
        *   Call `urls_to_process = self._determine_urls()`. Handle the case of no URLs.
        *   Call `self._initialize_db()`.
        *   Initialize `all_jobs = []`.
        *   **Loop through `urls_to_process`:**
            *   Update progress using `self._update_progress`.
            *   Call `search.search_jobs(...)` for the current URL.
            *   Call `details.fetch_job_details(...)` using the result from `search_jobs`. Pass necessary config from `self.config` and `self.args`.
            *   Handle potential `max_age_hours` filtering (logic from `process_single_url`) *here* within the loop if desired per-URL, or after collecting all jobs if global.
            *   Extend `all_jobs` with the detailed jobs found for this URL.
            *   Include error handling (`try...except`) for processing each URL, logging errors but continuing if possible.
            *   Update progress.
        *   **After the loop:**
            *   Update progress. Handle the case where `all_jobs` is empty.
            *   Call `filtered_jobs = filter.apply_filters(all_jobs, self.config['filters_dir'], self._update_progress)`. Store the result (maybe back into `all_jobs` or a new variable).
            *   Handle the case where `filtered_jobs` is empty.
            *   **Database Storage:**
                *   Check if `not self.args.dry_run` and `filtered_jobs` is not empty.
                *   If true, call `self.db_interface.store_jobs_batch(filtered_jobs, ..., progress_callback=self._db_progress_callback)`.
                *   Store the returned counts and errors in `self.storage_results`.
                *   Handle potential exceptions during DB storage.
                *   If `self.args.dry_run`, log this and populate `self.storage_results` accordingly.
            *   **Reporting:**
                *   Call `reporting.write_storage_report(self.args, self.storage_results, ...)` passing necessary data.
                *   If `not self.progress`, call `reporting.print_job_stats(filtered_jobs)` and `reporting.print_sample_jobs(filtered_jobs)`.
            *   Update progress with a final completion message.
            *   Return an appropriate exit code (e.g., 0 for success).

**Phase 3: Update Entry Point and Finalize**

9.  **Refactor Entry Point (`tools/search/store_jobs.py`):**
    *   Remove *all* function definitions (`parse_args`, `load_filter_config`, etc.) that were moved.
    *   Keep the initial `#!/usr/bin/env python3` and docstring.
    *   Keep necessary top-level imports: `os`, `sys`, `datetime`, `logging`.
    *   **Update Imports:** Import the necessary components using relative paths:
        *   `from ..common.utils import setup_path, setup_logging`
        *   `from ..common.progress_display import ProgressDisplay, ProgressStyle`
        *   `from .cli import parse_args`
        *   `from .pipeline import JobPipeline`
    *   Keep the `setup_path()` call.
    *   Remove the global `logger` and `progress` initializations at the top level.
    *   **Modify `main()` function:**
        *   Keep `args = parse_args()`.
        *   Keep the `setup_logging` call, assigning the result to a `logger` variable.
        *   Keep the `ProgressDisplay` initialization logic, assigning the result to a `progress` variable.
        *   **Remove** almost all the remaining logic (URL determination, looping, filtering, DB storage, report writing) - this is now in `JobPipeline.run()`.
        *   Instantiate the pipeline: `pipeline = JobPipeline(args, progress)`
        *   Execute the pipeline: `exit_code = pipeline.run()`
        *   Return the `exit_code`.
    *   **Modify `if __name__ == "__main__":` block:**
        *   Wrap the call to `main()` in a `try...except KeyboardInterrupt...except Exception...` block, similar to the original script's end, to handle top-level errors gracefully.
        *   Use the `logger` defined within `main`.
        *   If using `progress`, ensure `progress.finalize()` is called appropriately in `except` blocks.
        *   Call `sys.exit(main())` or `sys.exit(exit_code)` based on the `main` function's return.

10. **Review and Test:**
    *   Thoroughly review all modified and new files for correct imports (especially relative vs. absolute).
    *   Ensure all necessary arguments are passed between functions/methods.
    *   Check that logging is consistent.
    *   Run the `tools/search/store_jobs.py` script with various arguments (`--url`, `--workflow`, `--dry-run`, `--no-progress`) to ensure functionality remains the same. Check log files and database entries (if not dry-running).

This detailed plan should provide the LLM with clear instructions to perform the refactoring task. Remember to provide the original `store_jobs.py` code alongside this plan.