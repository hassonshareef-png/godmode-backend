# GODMODE Backend

FastAPI backend for user authentication and tier access, designed to run locally with SQLite and in production on Render with PostgreSQL.

## Endpoints

### Health & uptime
- `GET /health` → `{ "status": "ok" }`
- `GET /ping` → `{ "pong": true, "timestamp": "<UTC ISO timestamp>" }`

### Authentication
- `POST /auth/signup`
  - Body: `{ "email": "...", "password": "...", "tier": "god" }`
- `POST /auth/login`
  - Body: `{ "email": "...", "password": "..." }`
  - Returns bearer token
- `GET /auth/me` (requires bearer JWT in `Authorization` header)
  - Returns current user: `{ "id": ..., "email": "...", "tier": "..." }`
- `POST /auth/forgot-password`
  - Body: `{ "email": "..." }`
  - Returns reset token for now. In production this should be emailed.
- `POST /auth/reset-password`
  - Body: `{ "token": "...", "new_password": "..." }`

## Required environment variables

- `SECRET_KEY`
- `DATABASE_URL` (set on Render; local defaults to SQLite if unset)
- `FIREBASE_API_KEY`
- `FIREBASE_AUTH_DOMAIN`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_APP_ID`

Optional Firebase values if used:
- `FIREBASE_STORAGE_BUCKET`
- `FIREBASE_MESSAGING_SENDER_ID`
- `FIREBASE_MEASUREMENT_ID`

## Render keep-alive (free tier)

Use UptimeRobot (or similar) to `GET /ping` every 5 minutes to reduce cold starts/sleep behavior on free tier services.

## Local development

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables (at minimum `SECRET_KEY`).
4. Start server:
   ```bash
   uvicorn app.main:app --reload
   ```
