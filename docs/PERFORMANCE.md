# Browser performance and recovery

These changes use the existing React/FastAPI deployment and add no services.

- Subject and chapter catalogs: five-minute browser cache in sessionStorage, reused across tab reloads. Storage failures fall back to memory/network.
- Profile, legacy test history, rating summary and wallet: 30-second memory cache. No student data is written to persistent browser storage by this cache.
- Concurrent identical GETs share one request. Consumers receive independent copies.
- Mutations invalidate caches before and after the request; a generation counter prevents an older GET from repopulating an invalidated cache.
- Login/logout/account changes clear private cached data. Session checks, admin data, live tests and daily assignments are not response-cached.
- GETs retry once after a network failure, timeout, or 502/503/504. Requests time out after 30 seconds per attempt. Writes are never automatically retried.
- Dashboard reads run concurrently. Dashboard and profile failures have in-page retry; a failed profile request no longer redirects to onboarding.
- Subject changes ignore superseded chapter responses and disable starting while chapters load.
- Pending diagnostic submissions are coalesced across effect replays within the tab. This is not server-side idempotency and cannot guarantee deduplication after an ambiguous network failure or across tabs.
- FastAPI compresses responses over 1 KB. In the combined deployment, Vite's hashed assets get one-year immutable caching; HTML and unversioned files revalidate. API HTTP responses remain no-store.

## Verification

Run `npm ci`, `npm test` and `npm run build` in `frontend`.
The API tests mock fetch and storage; they cover cache reuse, concurrent reads, expiration, invalidation, account changes, stale in-flight responses, retry/timeout behavior and disabled/corrupt storage.

For deployment verification, visit profile/dashboard repeatedly, save a profile or test, switch subjects quickly, and interrupt/reconnect the network. Confirm fresh data after writes and in-page recovery. Confirm gzip and Cache-Control headers on the combined deployment. Browser visual checks and live latency measurements were not available in the implementation environment.

Deploy frontend and backend from the same commit. These changes reduce repeat requests and transfer size; they do not eliminate hosting cold starts or database latency.

## Server round-trip follow-up

The deployed bundle on `https://jee-edge.onrender.com` was checked and contained the first caching patch. The follow-up addresses work left behind that cache:

- Session, account, student profile and avatar metadata are fetched in one joined SELECT. The loaded objects are held only for the current request; subsequent requests still check revocation, verification, disabled accounts and suspension. Avatar image bytes are excluded from this metadata read.
- `/api/test-attempts/dashboard` returns profile, attempt history and rating together. The dashboard no longer starts a separate rating request after its initial data arrives.
- A list of 30 contests now uses two SELECTs instead of 31, with all of the current student's entries fetched in one query.
- Settlement only locks unfinished, closed contests. Cohort fields are captured before commit to avoid expired-object reloads and holding an extra connection during parallel ranking reads.
- Reward redemption names are loaded with their parent rows instead of one extra read per redemption.
- `Server-Timing: app;dur=...` reports application response preparation time in milliseconds, helping distinguish it from end-to-end network/hosting delay. It is not full browser load time or streaming transfer time.

Regression tests assert one SELECT for authenticated session/profile reads, exclusion of avatar bytes, suspension on the next request, dashboard authentication/onboarding behavior, two SELECTs for 30 contests, and exclusion of finalized contests from settlement.

Unauthenticated probes from the implementation environment took approximately 6 seconds for `/health`, 7.4 seconds for `/api/auth/session`, and 7.6 seconds for `/api/subjects`. These are environment-specific end-to-end observations, not a user-side benchmark or proof of a hosting cold start. No production database credentials or authenticated browser session were available.
