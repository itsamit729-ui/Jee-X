# Native accounts on Render

Student authentication now uses custom React pages and FastAPI email/password authentication. Auth0 is no longer used by the application. Routes: `/login`, `/signup`, `/verify-email`, `/forgot-password`, `/reset-password`, `/account/security`.

## Fresh accounts — no migration

Everyone signs up, verifies their email, and creates a new student profile. Existing Auth0 accounts, passwords, and progress are not imported or automatically linked, even when the email matches. Old database records remain intact and may still appear in existing public leaderboards and admin analytics. Existing usernames remain reserved. There is no bulk deletion in this release. The legacy `users.auth0_sub` column remains for schema compatibility; new profiles store `local:<account UUID>` there, without using Auth0. Google/social login is not included.

## Render setup

Use the root Dockerfile to serve React and the API from **one Render Web Service**. This avoids dependence on third-party cookies between different `onrender.com` sites. A custom domain is not required for the website. A standalone Python backend or a separate Static Site will not automatically become this combined service just because code was pushed.

1. Create a Render Blueprint from this repository, branch `feature/version-1`, using `render.yaml`; or create a Docker Web Service with repository root as the build context and `./Dockerfile`. Leave Root Directory empty. The image builds React and starts Uvicorn. Health check: `/health`.
2. Keep your existing Aiven MySQL database. Set `DATABASE_URL` with the `mysql+pymysql://` scheme and URL-encoded credentials. Upload Aiven's CA certificate as a Render secret file named `ca.pem`; `DB_SSL_CA=/etc/secrets/ca.pem`. Never add database credentials/certificates to Git.
3. Set `PUBLIC_APP_URL` and `CORS_ORIGINS` to the exact new origin, e.g. `https://jee-edge-example.onrender.com`, without a trailing slash. Remove old localhost origins in production. Redeploy after configuring the assigned URL.
4. Keep `AUTH_COOKIE_SECURE=true`, `AUTH_COOKIE_SAMESITE=lax`. Do not set `VITE_API_URL` for this combined deployment. Both UI and API use the same origin.
5. Configure email below and set a strong `ADMIN_PASSWORD` (existing independent admin authentication is unchanged).
6. Open the new site's `/signup`. Verify an actual email, log in, complete onboarding, save an answer, upload an avatar, log out, and test password reset. Only direct students to the new URL once these live checks pass.
7. After verification, remove obsolete `AUTH0_*`/`VITE_AUTH0_*` environment variables and disable the old Auth0 application if no other service uses it. The older `docs/auth0` files are historical and do not apply to native accounts.

Startup creates four additive tables: `auth_accounts`, `auth_sessions`, `auth_email_tokens`, `auth_rate_limits`. Existing feature migrations still need to have been applied as before. Back up your database before deployment. No student data migration is run.

## Email delivery

Use an HTTPS API, not SMTP. Default: create a Brevo transactional-email account, verify a sender, enable transactional sending, then set `BREVO_API_KEY`, `AUTH_EMAIL_PROVIDER=brevo`, and `AUTH_EMAIL_FROM` to the sender's plain email address. Provider approval, sender/domain authentication, quotas and deliverability rules still apply; hosting on `onrender.com` does not supply an email domain. A domain you control is recommended for production delivery.

Alternatively use `AUTH_EMAIL_PROVIDER=resend`, `RESEND_API_KEY`, and an approved `AUTH_EMAIL_FROM` for Resend. Missing configuration or failed delivery returns a clear temporary error and does not pretend an email was sent. Never place provider keys in `VITE_*` variables.

## Security and operations

- Argon2id password hashes; 15–128 character passwords; bounded concurrent hashing.
- Random seven-day sessions in HttpOnly, Secure, host-only cookies. MySQL stores only session-token hashes, so sessions survive restarts and work across backend replicas sharing the same database.
- Exact origin checks, custom request header, and per-session CSRF tokens for authenticated writes. No student bearer tokens or localStorage credentials.
- Email verification required before login. Verification and reset links expire after 30 minutes and work once; tokens are hashed in MySQL and placed in URL fragments. Password reset revokes all sessions; password change revokes other sessions and rotates the current one.
- Shared database rate limits by IP and normalized email. Only trust Render's proxy headers; the Docker entry point assumes Render is the only public ingress. For other hosting, restrict forwarded-header trust to known proxies.
- Auth expiry displays an in-page login dialog so an active test remains mounted. Exam timers continue. Failed requests are not automatically replayed; students retry saving after login.
- Free Render instances may sleep; this configuration does not eliminate cold starts. Keep an always-on instance when exam reliability requires it. Monitor email quota/errors and DB usage, and maintain tested backups.
- Periodically delete expired rows from `auth_email_tokens` and `auth_sessions`; rate-limit cleanup runs automatically. Never log passwords, session cookies or email tokens.

## Local development and verification

Copy the two `.env.example` files, configure your test MySQL and email provider, run `uvicorn app.main:app --reload` in backend and `npm run dev` in frontend. Vite proxies `/api` to port 8000. Local HTTP uses `AUTH_COOKIE_SECURE=false`; never copy that setting to production.

Install backend requirements plus `pytest httpx`, then run `pytest tests/test_native_auth.py` in backend. Tests use an isolated SQLite database and mocked email; they do not touch Aiven. Run `npm ci && npm run build` in frontend. MySQL row-lock behavior, real email delivery, and Render cookies require the live smoke test above.
