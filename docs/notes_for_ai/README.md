# Notes for AI

Welcome, Claude! This directory contains documentation specifically designed to help you understand the codebase and assist with development tasks.

## Purpose

These documents provide context, patterns, and architecture details that may not be immediately apparent from the code itself. They serve as a knowledge base to help you quickly understand the project structure, coding conventions, and architectural decisions.

## Available Documentation

| Document | Description |
|----------|-------------|
| [database_layers.md](database_layers.md) | Explains the database architecture, including models, repositories, and services |
| [database_schema.md](database_schema.md) | Contains the SQLite schema definitions for all database tables |
| [what_is_a_battle_plan.md](what_is_a_battle_plan.md) | Explains the concept of battle plans and how to create them |

## Battle Plans

Before implementing significant features, we create battle plans that outline the implementation approach. These are stored in `/docs/battle_plans/`. When asked to create a feature, you should:

1. Research the existing codebase to understand the context
2. Create a battle plan in `/docs/battle_plans/{feature_name}.md`
3. Only proceed with implementation after the battle plan is reviewed

See [what_is_a_battle_plan.md](what_is_a_battle_plan.md) for detailed guidance on creating effective battle plans.

## Coding Patterns

This application follows several consistent patterns:

1. **Layered Architecture**
   - UI Layer: Textual-based TUI components in `/job_tracker/ui/`
   - Service Layer: Business logic in `/job_tracker/services/`
   - Data Layer: Repository pattern in `/job_tracker/db/repos/`
   - Domain Models: Immutable dataclasses in `/job_tracker/models/`

2. **Repository Pattern**
   - Each entity has a dedicated repository class
   - Repositories handle CRUD operations and return domain models

3. **Dependency Injection**
   - Services and repositories are injected where needed
   - The DI container is defined in `/job_tracker/di.py`

4. **UI Components**
   - Built using the Textual library
   - Follow a widget-based composition pattern
   - Styling is done via TCSS files in `/job_tracker/ui/css/`

## How to Use These Docs

When working on this codebase:

1. Start by understanding the feature request or issue
2. Review relevant documentation in this directory
3. Explore the code structure to locate the components involved
4. Create a battle plan for non-trivial changes
5. Implement the changes following established patterns

Feel free to suggest improvements or additions to this documentation as you work with the codebase. The goal is to make these notes increasingly helpful for AI assistants working on this project.

## Additional Resources

- [CLAUDE.md](../../../CLAUDE.md) - Contains project-wide instructions and commands
- [README.md](../../../README.md) - Main project documentation