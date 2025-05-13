# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code Style Guidelines
- Use Python 3.x type annotations for all functions and methods
- Use snake_case for variables, functions, and methods; PascalCase for classes
- Use dataclasses with frozen=True, slots=True for models
- Follow repository pattern for data access layer
- Separate UI, service, and data layers as per architecture.md
- Use triple double-quotes for docstrings
- Handle exceptions with try/except blocks with specific exception types
- Import from `typing`: Dict, List, Optional, etc.
- Import from `__future__` for annotations
