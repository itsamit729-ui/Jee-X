# Jee Edge Auth0 login design

The current React app redirects to Auth0 Universal Login. The hosted page in the screenshot is controlled by Auth0; changing React CSS cannot restyle its form.

`preview.jpg` shows the intended desktop composition. The form in the preview is illustrative; Auth0 renders the real form and may position it differently on different screen sizes.

## Ready now: branded Universal Login theme

The files `frontend/public/auth/jee-edge-mark.svg` and `frontend/public/auth/jee-edge-login-background.jpg` can be served by the frontend at `/auth/jee-edge-mark.svg` and `/auth/jee-edge-login-background.jpg` after its next deployment. The editable SVG background is included alongside the JPEG. For example, if your frontend is `https://jee-x-1.onrender.com`, the logo URL is `https://jee-x-1.onrender.com/auth/jee-edge-mark.svg`. Check that each asset URL opens before entering it into Auth0.

In Auth0 Dashboard, open **Branding → Universal Login → Customization Options**. Keep **New Universal Login** enabled. Set the following in the no-code editor, preview login, signup, and password reset, then **Save and Publish**:

| Setting | Value |
| --- | --- |
| Primary button | `#BA431F` |
| Primary button label | `#FFFFFF` |
| Links and focused components | `#963318` |
| Header and filled input text | `#202126` |
| Body text | `#5F6069` |
| Input labels | `#71727C` |
| Widget background | `#FFFFFF` |
| Input background | `#FFFFFF` |
| Input border | `#CBCBD3` |
| Page background image | Full HTTPS URL to `jee-edge-login-background.jpg` |
| Widget position | Right |
| Logo | Full HTTPS URL to `jee-edge-mark.svg` |
| Corners | Rounded, moderate radius |

This layout gives the page a distinct Jee Edge side panel while leaving the authentication form fully managed by Auth0. On narrow screens, check Auth0's preview to confirm that the form remains legible when the background crops. Replace the generated tenant name in the subtitle in **Branding → Universal Login → Advanced Options → Custom Text** (login prompt), and set the application display name to **Jee Edge** if it still shows `JeeX`.

## Full page template

`jee-edge-universal-login.html` is a responsive, two-column template that retains Auth0's `{%- auth0:head -%}` and `{%- auth0:widget -%}` tags. Auth0 continues to render and handle the sign-in, signup, MFA, and password reset widget. Theme colors above still style that widget. The template is ready to submit using the Auth0 Management API; it has **not** been applied to your tenant.

1. Configure and verify an Auth0 custom domain, such as `login.your-domain.example`. Auth0's current guide says the Free plan includes one custom domain but requires a credit card for verification; check what your tenant currently offers. The custom page template requires a configured custom domain.
2. Before switching traffic, update the frontend `VITE_AUTH0_DOMAIN` and backend `AUTH0_DOMAIN` together to the verified custom hostname. The backend validates both JWKS and the issuer against `AUTH0_DOMAIN` (`backend/app/auth.py`). Switching the hostname can invalidate existing browser sessions. If you use Auth0's development social login keys, configure your own provider keys for the custom domain.
3. Get a short-lived Auth0 Management API token scoped to update branding templates. Back up any existing template using `GET /api/v2/branding/templates/universal-login` before replacing it.
4. Send this HTML as the `text/html` request body to `PUT https://YOUR_TENANT_DOMAIN/api/v2/branding/templates/universal-login`. Auth0's [API reference](https://auth0.com/docs/api/management/v2/branding/put-universal-login) documents both the endpoint and `text/html` body. Keep the token in an environment variable and out of Git.
5. Test email/password, social sign-in if enabled, signup, password reset, and mobile layout on the custom domain before exposing it to all users.

The full page template is intentionally not connected to React: adding the markup in your app would not replace the hosted Auth0 page.
