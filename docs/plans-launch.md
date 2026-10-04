# Plans launch

`/pricing` introduces the proposed Free, Student Plus and Teacher plans. Homepage and app navigation link to it. The server owns prices in `backend/app/routers/plans.py`.

- Student Plus: ₹249 for one month, or ₹599 for three months.
- Teacher: proposed ₹999/month for up to 50 active students, following an individually agreed 30-day supported pilot.
- Free practice and existing account/teacher access are unchanged.

## What is live in this change

Authenticated accounts can save, replace or remove their plan preference. Selection survives signup/login through a safe return URL; saving still requires a deliberate click after login. Requests are persisted in `plan_interests` and visible in the existing password-protected admin console, with pagination. The new table is created by the application's existing `Base.metadata.create_all` startup path. No changes to existing tables are needed.

These records are interest only: no subscription, charge, entitlement, teacher-access grant, automatic email, expiry or pilot countdown is created. The UI states that clearly. Supported pilot dates must be agreed separately; the admin list is the operational queue.

## Before accepting payment

Choose and configure a merchant/payment provider. Add server-created orders, verified signed webhooks, idempotent payment processing, subscription entitlements, cancellation/refund handling and displayed purchase terms. Never grant access from a browser success callback or a plan-interest record. Do not change `checkout_available` until checkout and lifecycle handling are implemented and tested. Final tax-inclusive prices and purchase terms must be shown before purchase.

## First launch experiment

Recruit a small student cohort and a few independent teachers. Use the admin interest list to assess demand; it is not revenue. Agree pilot support and dates directly. Evaluate completed practice sessions, return visits, feedback and willingness to pay before expanding acquisition. Referral rewards, paid advertising, marketing messages and automated campaigns are not enabled by this change.
