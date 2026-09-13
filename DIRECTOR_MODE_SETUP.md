# 🎬 DIRECTOR MODE - PRODUCTION LOGIN SETUP

## YOUR DIRECTOR CREDENTIALS

**Username**: `hassonshareef`
**Email**: `hassonshareef@gmail.com`
**Password**: `FATMAN050`
**PIN**: `1234`

---

## 🚀 Deploy to Render - Setup Instructions

### Step 1: Go to Render Dashboard
- Navigate to your `godmode-backend` service
- Click **Environment**

### Step 2: Set These Variables

Copy-paste these EXACTLY (replace YOUR values where marked):

```
OWNER_USERNAME=hassonshareef
OWNER_PASSWORD=FATMAN050
OWNER_EMAIL=hassonshareef@gmail.com
DIRECTOR_PIN=1234
SECRET_KEY=generate-random-32-chars-openssl-rand-hex-16
ADMIN_KEY=your-random-admin-secret-key
DATABASE_URL=postgresql://your-db-connection
CORS_ORIGINS=https://your-frontend.com,http://localhost:3000
```

### Step 3: Click "Deploy" or "Redeploy"
The backend will auto-create your director account at startup.

---

## 🔐 Director Login Options

### Option A: Standard Email/Username Login
```bash
POST /auth/login
Content-Type: application/json

{
  "identifier": "hassonshareef",
  "password": "FATMAN050"
}
```

**Or use email**:
```bash
{
  "identifier": "hassonshareef@gmail.com",
  "password": "FATMAN050"
}
```

### Option B: Quick PIN Access (Fastest)
```bash
POST /director/access
Content-Type: application/json

{
  "pin": "1234"
}
```

---

## 📱 Frontend - Director Login Code

### Using Standard Login
```javascript
async function directorLogin() {
  const response = await fetch('https://godmode-backend.onrender.com/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      identifier: "hassonshareef",  // or use email
      password: "FATMAN050"
    })
  });
  
  const data = await response.json();
  if (response.ok) {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('is_director', 'true');
    console.log("✅ Director Mode Activated!");
  } else {
    console.error("❌ Login failed:", data.detail);
  }
}
```

### Using PIN (Faster)
```javascript
async function quickDirectorLogin() {
  const response = await fetch('https://godmode-backend.onrender.com/director/access', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pin: "1234"
    })
  });
  
  const data = await response.json();
  if (response.ok) {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('is_director', 'true');
    console.log("🎬 Director Mode Activated with PIN!");
  }
}
```

---

## ✅ What Happens on Startup

When the backend deploys to Render with these env vars set:

1. ✅ Creates user account: `hassonshareef@gmail.com`
2. ✅ Sets username: `hassonshareef`
3. ✅ Sets password: `FATMAN050` (hashed securely)
4. ✅ Grants tier: `director`
5. ✅ Unlocks all modes: God Mode, Universe Mode, Director Mode
6. ✅ PIN access enabled: `1234`

---

## 🧪 Test Your Director Login

### Test 1: Login with Email
```bash
curl -X POST https://godmode-backend.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "hassonshareef@gmail.com",
    "password": "FATMAN050"
  }'
```

### Test 2: Login with Username
```bash
curl -X POST https://godmode-backend.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "hassonshareef",
    "password": "FATMAN050"
  }'
```

### Test 3: Quick PIN Access
```bash
curl -X POST https://godmode-backend.onrender.com/director/access \
  -H "Content-Type: application/json" \
  -d '{"pin": "1234"}'
```

### Test 4: Verify Director Status
```bash
# Use token from login/director access above
curl https://godmode-backend.onrender.com/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Expected response:
```json
{
  "id": 1,
  "username": "hassonshareef",
  "email": "hassonshareef@gmail.com",
  "tier": "director",
  "has_god_mode": true,
  "has_universe_mode": true,
  "is_director": true
}
```

---

## 🎯 All Director Endpoints

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/auth/login` | POST | Login with email/username | ❌ No |
| `/auth/logout` | POST | Sign out | ✅ Yes |
| `/auth/me` | GET | Get current user | ✅ Yes |
| `/director/access` | POST | Quick PIN login | ❌ No |
| `/director/3175` | POST | Run 3175 engine | ✅ Yes (Director) |
| `/god/predict` | GET | God mode predictions | ✅ Yes |
| `/universe/predict` | GET | Universe predictions | ✅ Yes |

---

## 🔒 Security Notes

- ✅ Password is hashed with Argon2 (never stored in plain text)
- ✅ PIN is stored in env var (never in database)
- ✅ All communications should be HTTPS
- ✅ Access tokens expire in 60 minutes
- ✅ Refresh tokens last 30 days
- ✅ Rate limiting protects against brute force

---

**YOUR DIRECTOR MODE IS NOW READY TO DEPLOY! 🚀**
