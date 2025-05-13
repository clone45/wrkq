# Battle Plan: Add Applied Status Column to Jobs Table

**Date:** April 28, 2025
**Author:** AI Assistant

## Problem Statement

Currently, the application lacks a visual indicator in the jobs table to show which jobs have been applied to. This information exists in the applications table but is not immediately visible in the main job listing. The goal is to add a new column as the first column in the job table that displays a checkmark (using ASCII characters) to indicate whether the job has been applied to.

## Approach Overview

We'll add a new virtual column to the jobs table UI that shows the application status without modifying the database schema. Since the applications table already stores this information with a relationship to jobs, we'll enhance the job loading logic to include application data for each job. This approach keeps the database structure intact while improving the user interface.

Key technical decisions:
1. Add an "Applied" column as the first column in the JobTable widget
2. Modify the `load_jobs()` method to fetch application status for each job
3. Use the existing ApplicationService.by_job_id() method to check application status
4. Display "✓" (checkmark) for jobs with applications, and an empty cell for jobs without

## Implementation Steps

1. **Modify JobsScreen.on_mount() Method**
   - Update the `table.add_columns()` call in `/mnt/c/code/wrkq/job_tracker/ui/screens/jobs_screen.py`
   - Add "Applied" as the first column in the table

2. **Enhance job data loading**
   - Modify the `load_jobs()` method in JobsScreen to check application status for each job
   - Create a helper method to efficiently check application status for all loaded jobs
   - Update the table row data to include the application status indicator
   - Ensure that the application check is only performed when the ApplicationService is available

3. **Update Table Row Creation**
   - Modify the table row creation in `load_jobs()` to include the application status indicator
   - Use a checkmark (✓) for jobs that have been applied to
   - Use an empty string for jobs that haven't been applied to

4. **Handle Edge Cases**
   - Ensure the implementation works when ApplicationService is not available
   - Maintain backward compatibility with existing code
   - Ensure correct cursor positioning after adding the new column

## Potential Challenges

- **Performance Impact**: Checking application status for each job could be inefficient if done individually. To mitigate this, we can batch fetch application status for all jobs in the current page in a single query.

- **Visual Consistency**: Different terminals might render Unicode characters differently. As a fallback, we should use ASCII alternatives (like 'X' or '*') if Unicode characters cause display issues.

- **State Management**: We need to ensure the applied status updates properly when a job is marked as applied through the job actions modal. The current code already reloads the job list after marking a job as applied, which should capture the updated state.

- **Null Safety**: We need to handle cases where the application service might not be available or when application data retrieval fails, to prevent application crashes.

- **UI Layout**: Adding a new first column might affect the layout of other columns. We should ensure the table continues to display properly with reasonable column widths after this change.