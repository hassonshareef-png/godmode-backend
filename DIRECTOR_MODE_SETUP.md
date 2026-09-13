# DIRECTOR MODE SETUP (REMOVED SENSITIVE CONTENT)

This file previously contained sensitive credentials (username, email, password, PIN). Those values have been removed from the repository for security reasons.

Do NOT store credentials or secrets in the repository. Instead, follow the steps below to configure your deployment securely.

Required environment variables (set these in your hosting provider's secret manager):

- OWNER_USERNAME
- OWNER_EMAIL
- OWNER_PASSWORD  # set a strong password in secret manager
- DIRECTOR_PIN
- SECRET_KEY
- ADMIN_KEY
- DATABASE_URL
- CORS_ORIGINS

Recommended steps after removing secrets from the repo:

1. Immediately rotate any credentials that were exposed.
2. If this repo was public, assume credentials were compromised and revoke/regenerate them.
3. Use a secrets manager (Render/Heroku/AWS Secrets Manager/Vault) to store secrets in production.
4. Do not commit secrets to source control. Use `.env.example` for documentation only (no real values).

If you need help purging secrets from git history, see SECRETS_ROTATION.md in this branch for commands and guidance.
