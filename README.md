# GODMODE Backend

FastAPI backend for authentication, tier-based prediction access, Director Mode, and Stripe Payment Link fulfillment.

## Access model

| Mode | Authentication | Entitlement |
|---|---|---|
| Basic | Public | None |
| God | Bearer access token | `has_god_mode` or Director user |
| Universe | Bearer access token | `has_universe_mode` or Director user |
| Director | Director bearer token | Valid `DIRECTOR_PIN` exchange |

A signup request can express an intended tier, but **never grants a paid entitlement**. Paid access is granted only after a verified Stripe webhook or a separately authenticated administrative operation.

## Core endpoints

| Method and path | Purpose |
|---|---|
| `GET /health` | Service health check |
| `GET /basic/predict?state=NY&game=P3` | Public basic prediction |
| `POST /auth/signup` | Create a free account |
| `POST /auth/login` | Return access and refresh tokens |
| `POST /auth/refresh` | Exchange a refresh token for a new access token |
| `GET /auth/me` | Return the current server-authoritative profile and entitlements |
| `POST /director/access` | Exchange the configured Director PIN for a short-lived Director token |
| `POST /director/3175` | Run the Director engine with a JSON `history` array |
| `GET /god/predict` | Entitlement-protected God prediction |
| `GET /universe/predict` | Entitlement-protected Universe prediction |
| `POST /billing/checkout` | Return the configured authenticated Stripe Payment Link for `god` or `universe` |
| `POST /billing/webhook` | Verify and fulfill supported Stripe events |

Interactive API documentation is available at `/docs`.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Load `.env` with your preferred process manager or export the variables in your shell. The SQLite fallback is suitable only for local development.

## Production deployment on Render

Use the command in `Procfile` and configure all production variables below. Attach a persistent PostgreSQL database; the default SQLite file is ephemeral on Render.

| Variable | Requirement |
|---|---|
| `SECRET_KEY` | Required; long random JWT signing secret |
| `ADMIN_KEY` | Required for administrative routes; distinct from `SECRET_KEY` |
| `DIRECTOR_PIN` | Required to enable Director PIN exchange |
| `DATABASE_URL` | Required in production; PostgreSQL connection URL |
| `CORS_ORIGINS` | Comma-separated exact frontend origins |
| `STRIPE_PAYMENT_LINK_GOD` | God-tier Stripe Payment Link |
| `STRIPE_PAYMENT_LINK_UNIVERSE` | Universe-tier Stripe Payment Link |
| `STRIPE_WEBHOOK_SECRET` | Stripe endpoint signing secret (`whsec_...`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional; defaults to 60 |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Optional; defaults to 43,200 |
| `EXPOSE_RESET_TOKEN` | Keep `false` in production |

### Stripe setup

1. Create the God and Universe Payment Links in Stripe.
2. Configure the two `STRIPE_PAYMENT_LINK_*` variables with those URLs.
3. Add a Stripe webhook endpoint pointing to `https://<backend-host>/billing/webhook`.
4. Subscribe the endpoint to `checkout.session.completed`.
5. Store that endpoint's signing secret as `STRIPE_WEBHOOK_SECRET`.
6. Ensure each Checkout Session supplies the authenticated customer email and tier metadata used by the backend. The checkout endpoint appends a `client_reference_id` and prefilled email to the configured Payment Link.

The webhook verifies Stripe's signature, ignores unpaid sessions, validates the requested tier, and records the processed event before upgrading the account so retries are idempotent.

## Testing

```bash
python -m pytest -q
```

The regression suite covers signup entitlements, login and refresh-token types, CORS, prediction request parsing, Director authorization, administrative controls, and Stripe fulfillment.

## Security actions required after deployment

A Firebase service-account credential was previously tracked in the repository. Deleting the file from the latest commit does not invalidate the leaked key or erase Git history. **Revoke/rotate that key in Google Cloud/Firebase immediately**, remove it from repository history if the project will remain public, and rotate any other secret that was committed or exposed in deployment logs.

Do not put Stripe secrets, admin keys, Director PINs, JWT keys, reset tokens, database files, or service-account JSON in Git. The included `.gitignore` and `.env.example` are intended to prevent recurrence.
