# GODMODE Backend

FastAPI backend for user authentication, tier-based access control, and prediction engine. Supports Basic Mode (free, public), God Mode (purchase required), Universe Mode (purchase required), and Director Mode (PIN-only, owner access).

## Access Model

| Mode | Access | Login Required | Purchase Required | Features |
|------|--------|---|---|---|
| **Basic** | Public | No | No | Limited predictions, basic features |
| **God** | Authenticated | Yes | Yes | Advanced predictions, full history |
| **Universe** | Authenticated | Yes | Yes | All God features + universe-level analysis |
| **Director** | PIN (8118) | No | No | All modes unlocked, owner-only access |

## Endpoints

### Health & Status
- `GET /health` → `{ "status": "ok" }`
- `GET /ping` → `{ "pong": true, "timestamp": "<UTC ISO timestamp>" }`

### Basic Mode (Public, No Auth Required)
- `GET /basic/features` → Available features for Basic Mode
- `GET /basic/predict?state=NY&game=P3` → Limited predictions

### Authentication
- `POST /auth/signup`
  - Body: `{ "email": "...", "password": "...", "tier": "basic|god|universe" }`
  - Returns: User object with tier and purchase status
  - Note: `tier="basic"` is free; `tier="god"` or `"universe"` marks purchase intent
  
- `POST /auth/login`
  - Body: `{ "email": "...", "password": "..." }`
  - Returns: Bearer token + tier info
  
- `GET /auth/me` (requires bearer JWT)
  - Returns: Current user profile with purchase status
  
- `POST /auth/forgot-password`
  - Body: `{ "email": "..." }`
  - Returns: Reset token (15-min expiry)
  - In production: Email token to user
  
- `POST /auth/reset-password`
  - Body: `{ "token": "...", "new_password": "..." }`
  - Returns: Success message

### God Mode (Login + Purchase Required)
- `GET /god/features` (requires auth)
  - Returns: God Mode features (403 if not purchased)
  
- `GET /god/predict?state=NY&game=P3` (requires auth)
  - Returns: Advanced predictions (403 if not purchased)

### Universe Mode (Login + Purchase Required)
- `GET /universe/features` (requires auth)
  - Returns: Universe Mode features (403 if not purchased)
  
- `GET /universe/predict?state=NY&game=P3` (requires auth)
  - Returns: Universe-level predictions (403 if not purchased)

### Director Mode (PIN-Only, No Login)
- `POST /director/access`
  - Body: `{ "pin": "8118" }`
  - Returns: Director token + all modes unlocked
  - Note: PIN is hardcoded; no login required
  
- `POST /director/3175` (requires director token or PIN)
  - Body: `{ "history": ["123", "456", "789", ...] }`
  - Returns: 3175 engine predictions + alerts

### Admin Endpoints (Requires `ADMIN_KEY`)
- `POST /admin/grant-purchase`
  - Body: `{ "email": "...", "tier": "god|universe", "admin_key": "..." }`
  - Returns: Updated user with purchase granted
  - Use: Triggered by payment processor webhook
  
- `POST /admin/set-director`
  - Body: `{ "email": "...", "admin_key": "..." }`
  - Returns: User marked as director
  - Use: Designate app owner

## Environment Variables

**Required:**
- `SECRET_KEY` — JWT signing key (use strong random value in production)

**Optional:**
- `DATABASE_URL` — Database connection (defaults to SQLite: `sqlite:///./godmode.db`)
  - Supports PostgreSQL: `postgresql://user:password@host/db`
  - Render: Set on deployment dashboard
  
- `DIRECTOR_PIN` — PIN for Director Mode access (defaults to `8118`)
- `ADMIN_KEY` — Key for admin endpoints (defaults to `admin-secret-key`)
- `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, etc. — Firebase config (optional)

## Database Schema

```
users
├── id (Integer, PK)
├── email (String, unique)
├── hashed_password (String)
├── tier (String: basic|god|universe|director)
├── has_god_mode (Boolean)
├── has_universe_mode (Boolean)
├── is_director (Boolean)
└── reset_token (String, nullable)
```

## Password Reset Flow

1. User calls `POST /auth/forgot-password` with email
2. Backend generates 15-minute JWT token
3. **In production:** Email token to user
4. User calls `POST /auth/reset-password` with token + new password
5. Password updated; old credentials no longer work

## Purchase Flow (Payment Integration)

1. User signs up with `tier="god"` or `tier="universe"`
2. Frontend directs to payment processor (Stripe, PayPal, etc.)
3. Payment processor confirms → calls `POST /admin/grant-purchase`
4. Backend marks `has_god_mode=true` or `has_universe_mode=true`
5. User can now access paid features

## Director Mode (Owner Access)

- **No login required**
- **PIN-only:** `8118` (set via `DIRECTOR_PIN` env var)
- **Unlocks all modes:** God, Universe, and Director features
- **Use case:** Owner/admin access without account management

### Access Director Mode:
```bash
curl -X POST http://localhost:8000/director/access \
  -H "Content-Type: application/json" \
  -d '{"pin": "8118"}'
```

Returns:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "mode": "director",
  "unlocked_modes": ["basic", "god", "universe", "director"]
}
```

Use token for Director Mode endpoints:
```bash
curl -X POST http://localhost:8000/director/3175 \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"history": ["123", "456", "789"]}'
```

## Local Development

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   export SECRET_KEY="dev-secret-key"
   export DIRECTOR_PIN="8118"
   export ADMIN_KEY="admin-secret-key"
   ```

4. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

5. API docs available at: `http://localhost:8000/docs`

## Testing

Run the test suite:
```bash
python -m pytest tests/test_auth_endpoints.py -v
```

Or with unittest:
```bash
python -m unittest tests.test_auth_endpoints -v
```

## Production Deployment (Render)

1. Push code to GitHub
2. Create new service on Render
3. Set environment variables:
   - `SECRET_KEY` (strong random value)
   - `DATABASE_URL` (Render PostgreSQL URL)
   - `DIRECTOR_PIN` (your PIN)
   - `ADMIN_KEY` (strong random value)
4. Deploy: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Keep-Alive (Free Tier)

Use UptimeRobot or similar to `GET /ping` every 5 minutes to prevent cold starts.

## Integration Notes

- **Payment Processor:** Call `POST /admin/grant-purchase` on successful payment
- **Email Service:** Implement email delivery for password reset tokens
- **Frontend:** Use bearer tokens from `/auth/login` for authenticated requests
- **CORS:** Currently allows all origins; restrict to frontend URL in production

## License

MIT
