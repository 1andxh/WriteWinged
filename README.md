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
- Google OAuth login
- JWT access/refresh tokens
- Email verification and password reset flows

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
- Redis
- Alembic
- uv (dependency and environment management)

## Local Setup (uv)

1. Create `.env` from `.env.sample` and set required values.
2. Install dependencies:

```bash
uv sync
```

3. Run migrations:

```bash
uv run alembic upgrade head
```

4. Start API:

```bash
uv run uvicorn src:app --host 0.0.0.0 --port 8000 --reload
```

## Useful Commands

```bash
uv run pytest
uv run alembic revision --autogenerate -m "your message"
uv run alembic downgrade -1
```

## Status

In active development.
