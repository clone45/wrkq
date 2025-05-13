# Battle Plan: Improved Logging for Company Creation Failures

**Date:** April 28, 2025
**Author:** AI Assistant

## Problem Statement

When a company fails to be created during the job submission process in the `AddJobScreen`, the error handling is minimal. Currently, the application shows a notification to the user with the message "Failed to create company record for '{company_name}'", but the logging is insufficient to diagnose the underlying cause of the failure. 

The issue is in the `action_submit` method of `add_job_screen.py`, where company creation failures are not consistently or thoroughly logged. This makes troubleshooting difficult when users report company creation issues.

## Approach Overview

1. Enhance the error logging in `CompanyRepo.find_or_create()` to capture detailed error information
2. Improve error propagation from the repository layer to the UI layer
3. Add comprehensive error logging in `AddJobScreen.action_submit()`
4. Create consistent error logging patterns throughout the application
5. Use structured logging to include context such as user actions and input data

## Implementation Steps

1. **Upgrade the `simple_logger.py` implementation**
   - Add log levels (DEBUG, INFO, WARNING, ERROR)
   - Add ability to include context data in logs
   - Implement directory creation if logs directory doesn't exist
   - Add method to log exceptions with full traceback

2. **Update the `CompanyRepo.find_or_create()` method**
   - Replace basic print statements with proper error logging
   - Capture different error types (empty name, database errors)
   - Add contextual information about the attempted company creation
   - Structure the logging to distinguish between different failure scenarios

3. **Enhance error handling in `AddJobScreen.action_submit()`**
   - Use structured exception handling for company creation
   - Log detailed information about the context (user inputs, specific error)
   - Separate UI error display from error logging
   - Add error codes or identifiers to help trace issues across logs

4. **Create standard error categories**
   - Define error types: validation errors, database errors, configuration errors
   - Implement standardized logging format for each error type
   - Ensure consistent error reporting across the application

5. **Update exception handling pattern**
   - Catch specific exceptions rather than generic Exception where possible
   - Add contextual data to exception logging
   - Implement proper exception propagation

## Potential Challenges

- **Backwards Compatibility**: Changes to the logger might affect existing log parsing tools or practices. Solution: Ensure the new format is compatible with existing log consumers or provide a migration path.

- **Performance Impact**: More detailed logging could introduce slight performance overhead. Solution: Implement log levels to control verbosity in production vs. development environments.

- **Error Context**: Gathering enough context without over-logging or including sensitive information can be challenging. Solution: Create a structured context object that includes only necessary debugging information.

- **Concurrency Issues**: If multiple users are creating companies simultaneously, logs might become interleaved and difficult to follow. Solution: Include session or request IDs in logs to correlate related entries.

- **Root Cause Identification**: Even with improved logging, some database errors might still require database-level logging. Solution: Ensure SQLite connection errors are properly captured and include database state information where relevant.