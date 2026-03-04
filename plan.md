# Render Deploy Failure Plan (DB Connectivity + Startup Reliability)

## Summary
- Deploy failed because app startup attempted PostgreSQL on `127.0.0.1:5432` inside Render.
- Startup check in lifespan raised `ConnectionRefusedError`, causing Gunicorn worker boot failure.
- Local `.env` values could be copied into the image because `.dockerignore` did not exclude `.env`.

## Implemented Changes
1. Deployment config hardening:
- Added `.env` and `.env.*` to `.dockerignore` so local env files are not baked into images.

2. Startup resilience while preserving fail-fast:
- Added bounded retry logic to DB startup check in `src/db/main.py`.
- Retry interval and max wait are configurable.
- If DB never becomes reachable within the timeout, startup still fails (fail-fast preserved).

3. Diagnostics:
- Startup logs sanitized DB host/port target.
- Startup logs warning if DB host is localhost in production-like environments.

4. Configuration surface:
- Added `ENVIRONMENT` (`development` default).
- Added `DB_STARTUP_MAX_WAIT_SECONDS` (`30` default).
- Added `DB_STARTUP_RETRY_INTERVAL_SECONDS` (`2` default).
- Added new env keys to `.env.sample`.

5. Tests:
- Added `tests/test_db_startup.py` covering:
  - success on first attempt
  - transient failure then success
  - timeout failure behavior
  - config defaults and overrides for retry settings

## Required Render Settings
- Set `DATABASE_URL` to managed Postgres URL with async driver:
  - `postgresql+asyncpg://user:pass@host:port/dbname`
- Set `REDIS_URL` to managed Redis endpoint (not localhost).
- Set `ENVIRONMENT=production`.

## Verification Results
- Ran `uv run pytest`.
- Result: `7 passed`.

## Rollout Checklist
1. Update Render environment variables (`DATABASE_URL`, `REDIS_URL`, `ENVIRONMENT`).
2. Redeploy service.
3. Confirm logs show remote DB host and successful startup.
4. Confirm health checks remain green after automatic restart cycle.
