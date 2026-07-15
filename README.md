# WriteWinged API

WriteWinged is a collaborative writing backend inspired by software-style workflows: versioning, contributor permissions, and proposal reviews.

## Core Concepts

- Documents are owned by one author.
- Versions are authoritative snapshots of document content.
- Contributors can propose changes but cannot publish directly.
- Proposals behave like pull requests.
- Publishing is explicit, not implicit.

## Features

### Authentication and Users

- Email/password registration and login
- JWT bearer access tokens
- Google OAuth, email verification, and password reset are deferred until after the MVP deploy

### Documents

- Create, rename, lock/unlock, archive/unarchive, soft delete
- Public/private visibility
- Owner-only management controls

### Version Control

- Version creation with transactional locking
- Single draft pointer and publish/unpublish behavior
- State-aware mutability checks

### Collaboration and Proposals

- Add/revoke contributors
- Contributor proposal workflow (open, accept, reject, withdraw)
- Owner-controlled proposal merge into draft version

## Tech Stack

- FastAPI
- SQLAlchemy/SQLModel
- PostgreSQL
- Alembic
- uv (dependency and environment management)

## Status

MVP backend cleanup in progress. Current deployment target is a small FastAPI + PostgreSQL setup.

This project is part of my journey learning backend development with FastAPI. It reflects a deep exploration of backend architecture, domain modeling, and professional engineering practices using FastAPI and SQLAlchemy.
