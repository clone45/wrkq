# Database Architecture

This document explains the database architecture used in the Job Tracker application.

## Overview

The application uses SQLite for data storage and follows a layered architecture pattern. It previously used MongoDB but has been migrated to SQLite.

## Layer Structure

The database functionality is organized into several layers:

1. **Domain Models** (`/job_tracker/models/`)
   - Pure dataclasses that represent domain entities (Job, Company, Application, etc.)
   - All models implement serialization methods (from_sqlite, to_sqlite)
   - Models use frozen=True and slots=True for immutability and performance

2. **Repositories** (`/job_tracker/db/repos/`)
   - Handle direct database access (CRUD operations)
   - Each entity has its own repository class (JobRepo, CompanyRepo, ApplicationRepo, etc.)
   - Repositories accept and return domain model instances
   - Repositories encapsulate SQL queries and connection management

3. **Business Services** (`/job_tracker/services/`)
   - Implement business logic and use cases
   - Coordinate between multiple repositories when needed
   - Handle validation, relationships, and complex operations
   - Interface with the UI layer

4. **Database Connection** (`/job_tracker/db/connection.py`)
   - Manages the SQLite connection
   - Provides cursor access and transaction support

## Key Database Files

- **Data Storage**: SQLite database file located at `/job_tracker/db/data/job_tracker.db`
- **Connection Manager**: `/job_tracker/db/connection.py`
- **Schema Definition**: See `/docs/notes_for_ai/database_schema.md` for table definitions

## Database Tables

The main tables are:
- `jobs` - Job listings with details
- `companies` - Company information
- `applications` - User's job applications
- `history` - Records of actions taken (applying, hiding, etc.)

## Common Patterns

1. **Repository Pattern**
   - CRUD operations are encapsulated in repository classes
   - Queries return domain models, not raw database rows
   - Each entity has its own dedicated repository

2. **Service Layer**
   - Business logic is handled in service classes
   - Services orchestrate operations across multiple repositories
   - UI interacts with services, not directly with repositories

3. **Dependency Injection**
   - Application uses a lightweight DI container in `job_tracker/di.py`
   - Database connections and repositories are injected into services
   - Services are injected into UI components

## How to Add New Database Features

When adding new database-related features:

1. Define any new model classes in the appropriate file in `/job_tracker/models/`
2. Implement repository methods in the appropriate repo file in `/job_tracker/db/repos/`
3. Add business logic in the appropriate service file in `/job_tracker/services/`
4. If needed, update the schema in `/docs/notes_for_ai/database_schema.md`
5. Modify the DI container in `job_tracker/di.py` to expose the new functionality

Always follow the existing patterns and conventions when extending the database layer.