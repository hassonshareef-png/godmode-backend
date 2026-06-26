# GODMODE Backend

FastAPI backend for user authentication and tier access, designed to run locally with SQLite and in production on Render with PostgreSQL.

## Endpoints

### Health & uptime
- `GET /health` → `{ "status": "ok" }`
- `GET /ping` → `{ "pong": true, "timestamp": "<UTC ISO timestamp>" }`

### Authentication
- `POST /auth/signup`
  - Body: `{ "email": "...", "password": "...", "tier": "god" }`
  - Password must be at least 8 characters.
- `POST /auth/login`
  - Body: `{ "email": "...", "password": "..." }`
  - Returns bearer token (valid 60 minutes).
- `GET /auth/me` (requires bearer JWT in `Authorization` header)
  - Returns current user: `{ "id": ..., "email": "...", "tier": "..." }`
- `POST /auth/forgot-password`
  - Body: `{ "email": "..." }`
  - Stores a 15-minute reset token. In production, email this token to the user as a link.
- `POST /auth/reset-password`
  - Body: `{ "token": "...", "new_password": "..." }`

### Stripe
- `POST /stripe/webhook`
  - Receives and verifies Stripe webhook events.
  - On `checkout.session.completed`, upgrades the user's tier based on the `tier` metadata key set on your Stripe Payment Link.
  - Returns `{ "status": "ok" }`.

## Required environment variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Long random string for JWT signing. **Required.** Server will refuse to start without it. |
| `DATABASE_URL` | Set on Render; local defaults to SQLite if unset. |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins (e.g. `https://yourapp.com`). Defaults to `http://localhost:3000`. |
| `STRIPE_SECRET_KEY` | Your Stripe secret key (`sk_live_...` or `sk_test_...`). |
| `STRIPE_WEBHOOK_SECRET` | Signing secret from your Stripe webhook endpoint (`whsec_...`). |
| `OWNER_USERNAME` | Optional owner login username. If set with `OWNER_PASSWORD`, owner account is auto-provisioned as `director`. |
| `OWNER_PASSWORD` | Optional owner login password (set only in secure environment variables, never in code). |
| `OWNER_EMAIL` | Optional owner account email. Defaults to `<OWNER_USERNAME>@owner.local` when omitted. |

Optional Firebase values if used:
- `FIREBASE_API_KEY`
- `FIREBASE_AUTH_DOMAIN`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_APP_ID`
- `FIREBASE_STORAGE_BUCKET`
- `FIREBASE_MESSAGING_SENDER_ID`
- `FIREBASE_MEASUREMENT_ID`

## Stripe Payment Link setup

For each payment link you want to wire to a tier upgrade:

1. Open the link in **Stripe Dashboard → Payment Links**.
2. Click **Edit** → scroll to **Metadata**.
3. Add a key `tier` with the value matching one of: `god`, `universe`, `director`.
4. Save the link.

When a customer pays, Stripe sends a `checkout.session.completed` webhook. The backend matches the customer's email to their account and upgrades their tier automatically.

Register your webhook URL in **Stripe Dashboard → Developers → Webhooks**:
- Endpoint URL: `https://your-render-url.onrender.com/stripe/webhook`
- Events to listen for: `checkout.session.completed`
- Copy the **Signing secret** (`whsec_...`) and set it as `STRIPE_WEBHOOK_SECRET` in Render.

## Owner access setup (director mode)

To configure a private owner login without affecting normal user logins:

1. Set these Render environment variables:
   - `OWNER_USERNAME`
   - `OWNER_PASSWORD`
   - (optional) `OWNER_EMAIL`
2. Restart the service.
3. Log in through `POST /auth/login` using:
   - `email`: your owner username (for example `hass`)
   - `password`: your owner password

When configured, the backend auto-creates/updates this owner account with tier `director`.

## Existing database migration

If you have an existing production database, run this SQL to add the Stripe customer ID column:

```sql
ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR;
```

## Render keep-alive (free tier)

Use UptimeRobot (or similar) to `GET /ping` every 5 minutes to reduce cold starts/sleep behavior on free tier services.

## Local development

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables (at minimum `SECRET_KEY`):
   ```bash
   export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
   ```
4. Start server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Running tests

```bash
python -m unittest discover -q
```
