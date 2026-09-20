# Public student profiles

Every active student has a public profile automatically, including existing
accounts without saved settings. Visit **Profile → Public profile** to choose
an optional display name/bio and activity visibility. Copy the link or open the
profile; there is no public/private toggle.

- `/u/:username` is accessible without login.
- `/students` finds an exact username; suspended, missing, and nonstudent
  accounts all return the same unavailable response.
- Leaderboard usernames link to profiles. Leaderboard visibility remains a
  separate preference; hiding from the leaderboard does not hide the profile.
- Ratings, peak badges, and history are scoped to the current exam and target year.
  Cohort rank uses the existing active leaderboard rules and competition ties.
- The graph shows the latest 100 finalized rated events. History is paginated in
  groups of 20. There is no contest settlement side effect on public reads.
- Optional activity exposes daily-question dates for 182 days and streaks. It is
  hidden by default. Email, private name, birth date, shipping data, identifiers,
  test answers, and solutions are never included in the public response.
- API responses are non-cacheable. The legacy `enabled` preference is ignored
  for visibility; older clients can still send it, but responses report true.
- Changing username changes the profile URL; old links become unavailable.

## Deployment

Deploy backend and frontend from `feature/version-1`, preferably backend first.
The new `public_profiles` table is registered with the existing startup
`Base.metadata.create_all`. No ALTER TABLE or backfill is needed; absent settings
use a public profile with empty bio/display name and hidden activity. The database account needs CREATE TABLE permission for this initial
deployment (as with the existing startup schema creation).

No new environment variables or packages are required. Keep the existing Render
SPA rewrite `/* → /index.html` so profile links work on refresh, and the frontend
origin in backend CORS settings.

Public reads have a bounded, per-process 60 requests/minute peer-IP limiter.
Configure trusted proxy handling appropriately; do not trust arbitrary forwarded
headers. For multiple workers/instances, replace this with a shared gateway or
Redis-backed limiter. Automated tests use SQLite; production MySQL locking was
not exercised by these tests. Prior security-review findings outside this feature
are not remediated by this change.

## Validation

Run `PYTHONPATH=backend pytest backend/tests` and `npm --prefix frontend run build`.
Privacy tests cover automatic access, legacy disabled records, response field allowlisting, owner-only
settings, unauthenticated access rules, suspended accounts, tied/cohort ranks,
activity opt-in, finalized history pagination, and public rate limits.
