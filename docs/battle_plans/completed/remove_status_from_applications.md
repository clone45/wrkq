# Battle Plan: Remove Status Field from Applications

**Date:** April 28, 2025
**Author:** AI Assistant

## Problem Statement

The applications table is designed to store information about when a user applies to a job. However, the Application model includes a "status" field (with values like "applied", "interview", "rejected", "offer", "accepted") that doesn't conceptually belong in this table. This field should be removed from the Application model to align with the true purpose of the applications table - simply recording when a user applied to a job.

Current issues:
1. The Application model defines a status field that isn't present in the actual database schema
2. This mismatch causes errors when trying to mark a job as applied
3. The concept of tracking application status doesn't align with the purpose of the applications table

## Approach Overview

Remove the status field from the Application model and update all related code that references or uses this field. We won't be adding a status field to the jobs table, as that's a separate concern and isn't required currently.

The primary goal is to simplify the Application model to its core purpose and resolve the mismatch between the model and database schema.

## Implementation Steps

1. **Update the Application model**
   - Remove the status field from the dataclass in `/mnt/c/code/wrkq/job_tracker/models/application.py`
   - Remove status from the to_sqlite() and from_sqlite() methods
   - Remove status from the from_mongo() method if it exists (for backward compatibility)

2. **Update ApplicationService**
   - Modify the add() method in `/mnt/c/code/wrkq/job_tracker/services/application_service.py` to remove the status parameter
   - Remove the update_status() method if it's only used for updating the status field
   - Modify the get_application_stats() method to remove status-based filtering
   - Update any other methods that reference or process the status field

3. **Update ApplicationRepo**
   - Check for any SQL queries in `/mnt/c/code/wrkq/job_tracker/db/repos/application_repo.py` that include the status field and update them
   - Remove any methods specifically designed to update the status field

4. **Update UI components**
   - Find and update any UI components that display or interact with the application status field
   - This includes any status filters, displays, or forms that allow changing application status

5. **Update Job Actions Screen**
   - The _mark_applied_callback in `/mnt/c/code/wrkq/job_tracker/ui/screens/jobs_screen.py` may need updates
   - Remove any status-related parameters when creating applications

## Potential Challenges

- **Data Migration**: If status information is stored in the database for existing applications, we would need a migration plan. However, the logs indicate the status field isn't present in the actual database table, so this isn't a concern.

- **Feature Regression**: Removing the status field might remove functionality to track an application's status. Since we're explicitly choosing not to track this information at this time, this is an intentional change rather than a regression.

- **Code References**: There may be code throughout the application that assumes the status field exists. These references will need to be identified and modified to handle the absence of this field.

- **History Table Integration**: If the history table stores application status changes, the integration would need updating to reflect that status is no longer tracked.

## Implementation Considerations

- Consider renaming the Application model to JobApplication if it's not already named so to better reflect its purpose
- The error handling improvements already made will help identify any issues that arise from this change
- Approach this as a simplification task - removing functionality to better align the model with its core purpose