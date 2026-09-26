# Google sign-in setup

The combined Jee Edge Render service supports Google sign-in alongside email and password. The Google button remains hidden until both OAuth settings below are configured. Password accounts keep working. Existing password users can sign in and explicitly connect Google from `/account/security`; matching email alone never links accounts. Legacy Auth0 students are not imported.

## Configure Google

1. In Google Cloud Console, create a project and open **Google Auth platform**. Set up **Branding** and choose **External** under **Audience** if students outside your organization should sign in. Configure the `openid` and `email` scopes. Review Google's publication and domain requirements before inviting students.
2. Under **Clients**, create an **OAuth client ID** with application type **Web application**. Add this exact **Authorized redirect URI**: `https://jee-edge.onrender.com/api/auth/google/callback`. The current flow runs on the server; no JavaScript origin is required by the implementation.
3. Copy the client ID and client secret into the **new `jee-edge` Render service** as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Keep `PUBLIC_APP_URL=https://jee-edge.onrender.com`. Save and deploy. Never put the secret in a `VITE_*` variable or Git.
4. Visit `/login`. The Google button should appear. Sign in with a new Google account and finish onboarding. Also verify that an existing password account must sign in with its password before connecting Google from `/account/security`.

Google can require verification of a domain you control to publish branded OAuth consent screens. If Google does not accept the `onrender.com` address for your OAuth configuration, connect a domain you own to the Render service first, then change `PUBLIC_APP_URL` and the authorized redirect URI to that exact domain and redeploy.

The backend creates `auth_google_identities` on startup. The table stores Google's stable subject ID and the existing Jee Edge account ID. It does not store Google access tokens. Browser sessions remain the same secure HttpOnly cookies used by password login. OAuth state expires after ten minutes.
