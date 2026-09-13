# GODMODE Backend - Production Setup Guide

This guide will get your authentication system, director mode, and user sign-in/sign-out working on Render or any production server.

---

## 1. Environment Variables Setup

Copy `.env.example` to your production environment (Render, Heroku, etc.) and fill in all values:

```bash
# Core Security
SECRET_KEY=your-random-32-character-secret-key-here-make-it-long
ADMIN_KEY=another-random-secret-key-for-admin-endpoints
DIRECTOR_PIN=1234  # PIN for director access (minimum 4 digits)

# Database (Render PostgreSQL recommended)
DATABASE_URL=postgresql://user:password@host:5432/godmode

# CORS - Your frontend domain(s), comma-separated
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com,http://localhost:3000

# Stripe Payments (get from Stripe dashboard)
STRIPE_PAYMENT_LINK_GOD=https://buy.stripe.com/your_god_link
STRIPE_PAYMENT_LINK_UNIVERSE=https://buy.stripe.com/your_universe_link
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Token Lifetimes (optional - defaults shown)
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_MINUTES=43200

# DIRECTOR MODE - Owner login (your credentials)
OWNER_USERNAME=your_director_username
OWNER_PASSWORD=YourDirectorPassword123!
OWNER_EMAIL=your_email@example.com

# Development only - NEVER enable in production
EXPOSE_RESET_TOKEN=false
```

---

## 2. Director Mode Setup (You - Admin)

The system auto-creates your director account at startup using these env vars:

```bash
OWNER_USERNAME=hass        # Your login username
OWNER_PASSWORD=Hass1234!   # Your strong password
OWNER_EMAIL=you@example.com
DIRECTOR_PIN=1234          # PIN for quick access
```

**After setting these and deploying**, you can log in two ways:

### Option A: Standard Login
```bash
POST /auth/login
{
  "identifier": "hass",
  "password": "Hass1234!"
}
```

### Option B: PIN-Based Access (Quick)
```bash
POST /director/access
{
  "pin": "1234"
}
```

Both return an `access_token` that unlocks all director features.

---

## 3. User Sign In / Sign Out Flow

### User Registration
```javascript
// Frontend - Signup
const response = await fetch('https://api.yoursite.com/auth/signup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'john_doe',
    email: 'john@example.com',
    password: 'SecurePass123!'
  })
});

const { access_token, refresh_token, username, email } = await response.json();

// Store tokens
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);
```

### User Login
```javascript
// Frontend - Login
const response = await fetch('https://api.yoursite.com/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    identifier: 'john_doe',  // username or email
    password: 'SecurePass123!'
  })
});

const { access_token, refresh_token, tier, has_god_mode } = await response.json();

// Store tokens
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);
```

### Check Who's Logged In
```javascript
// Frontend - Get current user
const response = await fetch('https://api.yoursite.com/auth/me', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});

const user = await response.json();
// { id, username, email, tier, has_god_mode, has_universe_mode, is_director }
```

### User Sign Out
```javascript
// Frontend - Logout (just delete tokens)
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
// User is now logged out - all protected endpoints will reject them
```

### Refresh Expired Token
```javascript
// Frontend - Refresh access token when expired
const response = await fetch('https://api.yoursite.com/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    refresh_token: localStorage.getItem('refresh_token')
  })
});

const { access_token } = await response.json();
localStorage.setItem('access_token', access_token);
```

---

## 4. All Auth Endpoints

| Endpoint | Method | Auth Required | Purpose |
|----------|--------|---------------|---------|
| `/auth/signup` | POST | ❌ No | Create new account |
| `/auth/login` | POST | ❌ No | User login |
| `/auth/me` | GET | ✅ Yes | Get current user |
| `/auth/refresh` | POST | ❌ No | Refresh access token |
| `/auth/forgot-password` | POST | ❌ No | Request password reset |
| `/auth/reset-password` | POST | ❌ No | Complete password reset |
| `/director/access` | POST | ❌ No | Login with PIN |
| `/director/3175` | POST | ✅ Yes (Director) | Director prediction engine |

---

## 5. Testing Your Setup

### Test 1: Health Check
```bash
curl https://api.yoursite.com/health
# {"status": "ok"}
```

### Test 2: Create Account
```bash
curl -X POST https://api.yoursite.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser123",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

### Test 3: Login
```bash
curl -X POST https://api.yoursite.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "testuser123",
    "password": "TestPass123!"
  }'
```

### Test 4: Get Current User
```bash
curl https://api.yoursite.com/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### Test 5: Director PIN Access
```bash
curl -X POST https://api.yoursite.com/director/access \
  -H "Content-Type: application/json" \
  -d '{"pin": "1234"}'
```

---

## 6. Rate Limiting

To prevent abuse, these endpoints have rate limits:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/auth/signup` | 5 attempts | 10 minutes |
| `/auth/login` | 10 attempts | 1 minute |
| `/auth/forgot-password` | 5 attempts | 10 minutes |
| `/auth/reset-password` | 5 attempts | 10 minutes |
| `/auth/refresh` | 20 attempts | 1 minute |

Users hitting limits get: `429 Too Many Requests`

---

## 7. Security Best Practices

✅ **Do:**
- Use strong, random `SECRET_KEY` (32+ chars)
- Set `CORS_ORIGINS` to only your frontend domains
- Rotate `ADMIN_KEY` and `DIRECTOR_PIN` regularly
- Use PostgreSQL in production (not SQLite)
- Enable HTTPS only (`https://` URLs)
- Store tokens in `httpOnly` cookies (not localStorage for sensitive data)

❌ **Don't:**
- Commit `.env` or secrets to git
- Use `SECRET_KEY=test-key` in production
- Set `CORS_ORIGINS=*` (security risk)
- Expose `EXPOSE_RESET_TOKEN=true` in production
- Share `DIRECTOR_PIN` publicly

---

## 8. Deployment Checklist

- [ ] PostgreSQL database created on Render/AWS/etc
- [ ] All env vars copied to production
- [ ] `SECRET_KEY` is 32+ random characters
- [ ] `CORS_ORIGINS` includes your frontend domain(s)
- [ ] `STRIPE_*` vars filled in (or Stripe disabled)
- [ ] `OWNER_USERNAME`, `OWNER_PASSWORD`, `OWNER_EMAIL` set
- [ ] Database migrations run (`Base.metadata.create_all()` runs automatically)
- [ ] Test `/health` endpoint returns `{"status": "ok"}`
- [ ] Test signup/login flow works
- [ ] Test director login with PIN works

---

## 9. Troubleshooting

### "Invalid credentials" on login
- Check username/email is registered: `POST /auth/me` with token
- Check password is correct (password validation: min 8 chars, uppercase, lowercase, digit, special char)

### "Director Mode requires PIN or director access"
- Check `DIRECTOR_PIN` env var is set
- Check `OWNER_USERNAME`, `OWNER_PASSWORD` env vars are set
- Try `/director/access` with PIN first

### CORS errors from frontend
- Add your frontend domain to `CORS_ORIGINS` env var
- Restart the server
- Clear browser cache

### "Too many requests" (429)
- Wait for the rate limit window to expire
- Ask user to wait before retrying

### Token expired
- Use `/auth/refresh` with `refresh_token` to get new `access_token`
- Refresh tokens last 30 days

---

**Your backend is production-ready! 🚀**

Questions? Check the code in `app/main.py` for complete implementation details.
