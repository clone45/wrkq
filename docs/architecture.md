# ByteJobs Application Architecture

## Overview

ByteJobs is a terminal-based job tracking application built with Python, using the Textual TUI framework for the user interface and MongoDB for data persistence. The application follows a layered architecture with clear separation of concerns between data access, business logic, and presentation layers.

## Visual Architecture Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                     User Interface Layer                       │
│                                                               │
│  ┌─────────────┐  ┌───────────────────────────┐  ┌─────────┐  │
│  │   Screens   │  │        Widgets            │  │   CSS   │  │
│  │             │  │                           │  │         │  │
│  │ JobsScreen  │  │ JobTable   JobDetails     │  │ *.tcss  │  │
│  │ AddJobScreen│  │ ChatPanel  SearchBar      │  │         │  │
│  │             │  │ Pagination                │  │         │  │
│  └──────┬──────┘  └────────────┬─────────────┘  └─────────┘  │
│         │                      │                             │
│         │         ┌────────────┴─────────────┐               │
│         │         │       Controllers        │               │
│         │         │                          │               │
│         │         │   StatusBarController    │               │
│         │         └────────────┬─────────────┘               │
│         │                      │                             │
│         │         ┌────────────┴─────────────┐               │
│         │         │         Mixins           │               │
│         │         │                          │               │
│         │         │    PaneToggleMixin       │               │
│         │         └────────────┬─────────────┘               │
│         │                      │                             │
└─────────┼──────────────────────┼─────────────────────────────┘
          │                      │
          ▼                      ▼
┌───────────────────────────────────────────────────────────────┐
│                      Service Layer                             │
│                                                               │
│  ┌────────────────┐  ┌───────────────────┐  ┌──────────────┐  │
│  │   JobService   │  │ JobsViewState     │  │ ChatService  │  │
│  │                │  │     Service       │  │ (Placeholder)│  │
│  └────────┬───────┘  └─────────┬─────────┘  └──────────────┘  │
│           │                    │                              │
└───────────┼────────────────────┼──────────────────────────────┘
            │                    │
            ▼                    ▼
┌───────────────────────────────────────────────────────────────┐
│                     Repository Layer                           │
│                                                               │
│   ┌───────────┐    ┌────────────┐    ┌──────────┐             │
│   │  JobRepo  │    │CompanyRepo │    │ UserRepo │             │
│   └─────┬─────┘    └──────┬─────┘    └────┬─────┘             │
│         │                 │                │                  │
│         └─────────────────┼────────────────┘                  │
│                           │                                   │
│                           ▼                                   │
│                  ┌──────────────────┐                         │
│                  │MongoDBConnection │                         │
│                  └──────────────────┘                         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                    Database (MongoDB)                          │
└───────────────────────────────────────────────────────────────┘
```

## Architecture Layers

### 1. Database Layer

**Components: MongoDB Connection and Repositories**

The database layer handles data persistence and retrieval through the following components:

- `MongoDBConnection` (`job_tracker/db/connection.py`): Establishes and manages the connection to MongoDB.
- Repository classes:
  - `JobRepo` (`job_tracker/db/repos/job_repo.py`): Handles CRUD operations for job listings.
  - `CompanyRepo` (`job_tracker/db/repos/company_repo.py`): Manages company data.
  - `UserRepo` (`job_tracker/db/repos/user_repo.py`): Manages user data.

This layer implements the Repository pattern, providing a clean abstraction over the underlying database operations.

#### Example Repository Implementation:

```python
# Key aspects of JobRepo implementation
class JobRepo:
    def __init__(self, db: MongoDBConnection, col_name: str = "jobs"):
        self._col = db.col(col_name)
    
    def list(self, page: int = 1, per_page: int = 10, filters: Dict = None) -> List[Dict]:
        if filters is None:
            filters = {}
        skip = (page - 1) * per_page
        cursor = self._col.find(filters).sort([("_id", DESCENDING)]).skip(skip).limit(per_page)
        return list(cursor)
    
    def by_id(self, job_id: str) -> Optional[Dict]:
        try:
            return self._col.find_one({"_id": ObjectId(job_id)})
        except:
            # Try with string ID if it's not an ObjectId
            return self._col.find_one({"_id": job_id})
```

### 2. Service Layer

**Components: Business Logic Services**

The service layer contains the application's business logic:

- `JobService` (`job_tracker/services/job_service.py`): Handles job-related operations like querying, filtering, and manipulation.
- `JobsViewStateService` (`job_tracker/services/jobs_view_state_service.py`): Manages the UI state for job views, including pagination, search, and selected items.
- `ChatService` (`job_tracker/services/chat_service.py`): Intended to provide chat functionality (appears to be a placeholder for future development).

Services coordinate between the UI and data layers, encapsulating business rules and orchestrating operations that might involve multiple repositories.

#### Example Service Implementation:

```python
# Key aspects of JobService implementation
class JobService:
    def __init__(self, job_repo: JobRepo, company_repo: CompanyRepo, config: Dict[str, Any]):
        self.job_repo = job_repo
        self.company_repo = company_repo
        self.config = config
    
    def get_jobs(self, page: int = 1, per_page: int = 15, search_query: str = "", 
                 show_hidden: bool = False) -> Dict[str, Any]:
        # Build filters
        filters = {}
        if search_query:
            search_regex = {"$regex": search_query, "$options": "i"}
            filters["$or"] = [
                {"company": search_regex}, {"title": search_regex}, {"location": search_regex}
            ]
        if not show_hidden:
            filters["hidden"] = {"$ne": True}
        
        # Fetch data
        jobs_data = self.job_repo.list(page=page, per_page=per_page, filters=filters)
        total_jobs = self.job_repo.count(filters)
        total_pages = max(1, (total_jobs + per_page - 1) // per_page)
        
        return {
            "jobs": jobs_data,
            "total": total_jobs,
            "pages": total_pages
        }
```

### 3. UI Layer

**Components: Screens, Widgets, Controllers, Mixins**

The UI layer provides the terminal user interface using the Textual framework:

- **Screens** (`job_tracker/ui/screens/`):
  - `JobsScreen`: Main screen for displaying job listings.
  - `AddJobScreen`: Form screen for adding new jobs.

- **Widgets** (`job_tracker/ui/widgets/`):
  - `JobTable`: Custom DataTable for displaying job listings.
  - `JobDetails`: Shows detailed information about a selected job.
  - `ChatPanel`: UI component for chat interaction.
  - `Pagination`: Widget for navigating through pages of results.
  - `SearchBar`: Input component for search functionality.

- **Controllers** (`job_tracker/ui/controllers/`):
  - `StatusBarController`: Manages the status bar UI, displaying information about current state.

- **Mixins** (`job_tracker/ui/mixins/`):
  - `PaneToggleMixin`: Provides functionality for toggling panes (detail view, chat panel) in the UI.

- **Other UI Components**:
  - `app.py`: Main application class that orchestrates the UI components.
  - CSS files (`job_tracker/ui/css/`): Define styling for UI components.

#### Example UI Component Implementation:

```python
# Excerpt from PaneToggleMixin showing reactive UI pattern
class PaneToggleMixin:
    def watch_show_detail_pane(self, show: bool) -> None:
        """React to changes in show_detail_pane to show/hide the detail view"""
        detail_widget = self.query_one(JobDetail)
        table_widget = self.query_one("#jobs-table")

        if show:
            detail_widget.remove_class("-hidden")
            detail_widget.display = True
            table_widget.styles.height = "1fr"
            detail_widget.styles.height = "2fr"

            if self.selected_job_id:
                 job = self._get_job_data(self.selected_job_id)
                 detail_widget.update_job(job)
            else:
                 detail_widget.update_job(None)
        else:
            detail_widget.add_class("-hidden")
            detail_widget.display = False
            table_widget.styles.height = "1fr"
            detail_widget.styles.height = None
            detail_widget.update_job(None)
```

### 4. Utility Layer

**Components: Helper Functions**

- `formatters.py` (`job_tracker/utils/formatters.py`): Utility functions for formatting data in the UI.

### 5. Configuration

- `config.py` (`job_tracker/config.py`): Manages application configuration, loading from files and environment variables.

## Detailed Data Flows

### 1. Application Initialization Flow

```
┌─────────┐      ┌────────────────┐      ┌────────────────┐      ┌─────────────┐
│ main.py │ ─────► load_config()  │ ─────► JobTrackerApp  │ ─────► fetch_user  │
└─────────┘      └────────────────┘      └───────┬────────┘      └─────────────┘
                                                  │
                                                  ▼
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│   job_repo,    │ ◄────┤ MongoDBConn    │ ◄────┤  Create DB     │
│ company_repo,  │      └────────────────┘      │  connection    │
│   user_repo    │                               └────────────────┘
└───────┬────────┘
        │
        ▼
┌────────────────┐
│  push_screen   │
│  (JobsScreen)  │
└────────────────┘
```

### 2. Job Search Flow

```
┌─────────────┐     ┌───────────────────┐     ┌────────────────┐
│ User types  │     │ SearchBar emits   │     │ JobsScreen     │
│ search term │────►│ Submitted event   │────►│ updates state  │
└─────────────┘     └───────────────────┘     └───────┬────────┘
                                                      │
                                                      ▼
┌─────────────┐     ┌───────────────────┐     ┌────────────────┐
│ JobTable    │     │ JobRepo executes  │     │ JobService     │
│ updates     │◄────│ MongoDB query     │◄────│ builds filters │
└─────────────┘     └───────────────────┘     └────────────────┘
```

### 3. Add Job Flow

```
┌─────────────┐     ┌───────────────────┐     ┌────────────────┐
│ User clicks │     │ JobTrackerApp     │     │ AddJobScreen   │
│ "Add Job"   │────►│ calls action_add_ │────►│ is displayed   │
└─────────────┘     │ job()             │     └───────┬────────┘
                    └───────────────────┘             │
                                                      ▼
┌─────────────┐     ┌───────────────────┐     ┌────────────────┐
│ Screen is   │     │ Reload callback   │     │ User fills form │
│ dismissed,  │◄────│ triggers load_    │◄────│ and submits    │
│ jobs update │     │ jobs() on JobsScreen    └───────┬────────┘
└─────────────┘     └───────────────────┘             │
                                                      ▼
                    ┌───────────────────┐     ┌────────────────┐
                    │ JobRepo.add()     │◄────│ JobService     │
                    │ saves to MongoDB  │     │ processes data │
                    └───────────────────┘     └────────────────┘
```

### 4. Toggle Detail View Flow

```
┌─────────────┐     ┌───────────────────┐     ┌────────────────┐
│ User presses│     │ action_toggle_    │     │ show_detail_   │
│ "d" key     │────►│ detail() called   │────►│ pane toggled   │
└─────────────┘     └───────────────────┘     └───────┬────────┘
                                                      │
                                                      ▼
                    ┌───────────────────┐     ┌────────────────┐
                    │ JobDetail widget  │◄────│ watch_show_    │
                    │ shown/hidden      │     │ detail_pane()  │
                    └───────────────────┘     │ triggered      │
                                              └────────────────┘
```

## Architectural Patterns

1. **Repository Pattern**: Abstracts data access operations, providing a clean interface to database operations.
2. **Service Layer Pattern**: Encapsulates business logic, coordinating between UI and data layers.
3. **Dependency Injection**: Services and repositories are injected rather than created directly.
4. **Reactive UI Pattern**: Uses Textual's reactive attributes to automatically update the UI when state changes.
5. **Event-Driven Architecture**: Components communicate through events for loosely coupled interaction.

## Potential Fragmentation Issues

1. **Multiple State Management**:
   - State is managed in multiple places (view state service, reactive attributes in screens, etc.)
   - This could lead to inconsistency or duplication of logic.

2. **Mixed Responsibilities**:
   - `JobsScreen` contains both UI logic and some business logic.
   - Some UI components have direct knowledge of data structures.

3. **Incomplete Service Implementation**:
   - `ChatService` appears to be a placeholder, with chat functionality partially implemented directly in the UI.

4. **Hardcoded User**:
   - The application has a hardcoded user email, indicating the user management system might not be fully implemented.

5. **Parallel Inheritance Hierarchies**:
   - Various component types (widgets, services, repositories) have parallel structures that must be kept in sync.

## Refactoring Roadmap

To address the identified fragmentation issues, the following refactoring roadmap is proposed:

### Phase 1: Consolidate State Management

1. **Centralize state management**:
   - Move all application state from reactive attributes in screens to the `JobsViewStateService`
   - Make screens observe the view state service rather than managing state themselves
   - Implement a proper state observation pattern

```python
# Current approach - state in screens:
class JobsScreen(Screen):
    current_page = reactive(1)
    show_hidden = reactive(False)
    
# Proposed approach:
class JobsScreen(Screen):
    def __init__(self, view_state_service):
        self.view_state = view_state_service
        self.view_state.subscribe(self.on_state_changed)
    
    def on_state_changed(self, state):
        # Update UI based on new state
        pass
```

### Phase 2: Separate UI and Business Logic

1. **Move business logic from screens to services**:
   - Extract all business logic from `JobsScreen` into appropriate services
   - Ensure screens only handle UI concerns and delegate to services

2. **Define clear domain models**:
   - Create proper domain models to decouple UI from raw database structures
   - Add mapping logic to convert between domain models and database structures

```python
# Current approach - UI knows database structure:
job_id_str = str(job["_id"])
table.add_row(job_id_str, job.get("company", ""), job.get("title", ""))

# Proposed approach:
job_model = JobModel.from_dict(job)
table.add_row(job_model.id, job_model.company_name, job_model.title)
```

### Phase 3: Complete Service Implementations

1. **Implement proper ChatService**:
   - Move chat functionality from UI to the ChatService
   - Implement proper messaging logic in the service layer

2. **Implement User Management**:
   - Replace hardcoded user with proper authentication/user management
   - Create a UserService to manage user-related operations

```python
# Current approach:
HARDCODED_USER_EMAIL = "clone45@gmail.com"
self.current_user_data = self.user_repo.by_email(HARDCODED_USER_EMAIL)

# Proposed approach:
class AuthService:
    def authenticate(self, credentials):
        # Authentication logic
        pass
    
    def get_current_user(self):
        # Return current user from session
        pass
```

### Phase 4: Improve Code Organization

1. **Refactor parallel hierarchies**:
   - Introduce proper interfaces/abstract classes for repositories and services
   - Ensure consistent patterns across all components
   - Use dependency inversion to make components depend on abstractions

2. **Implement better error handling**:
   - Add consistent error handling throughout the application
   - Create error models and error handling services

## Conclusion

ByteJobs follows a layered architecture with clear separation between data access, business logic, and UI concerns. It uses modern architectural patterns and a component-based UI framework. While there are some potential fragmentation issues where concerns might be mixed, the overall structure provides a solid foundation for maintenance and extension.

The application demonstrates good practices like dependency injection and the repository pattern, but could benefit from more consistent state management and clearer separation of responsibilities between UI components and business logic. The proposed refactoring roadmap outlines specific steps to address these issues and improve the overall architecture.