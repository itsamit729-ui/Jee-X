# JeeEdge Instagram automation

One original four-card carousel per Indian calendar day. GitHub Actions runs at
18:00 IST, with two retry windows at 19:00 and 20:00. Successful submissions are
not repeated. GitHub schedules can run late; publication is requested 30 minutes
after generation. The workflow must exist on the default branch (`main`), and
checks out `feature/version-1` for the worker. The application is untouched.

## Initial setup

Repository Actions secrets: `BUFFER_API_KEY` (personal) and `GROQ_API_KEY`.
Create the Groq key at https://console.groq.com/keys and save it as an Actions
repository secret. The old Gemini secret is no longer used.
Use a Groq Free-plan account; do not upgrade to the paid Developer plan. The worker does
not create billing accounts, upgrade tiers, or switch to paid providers.
Default model: `openai/gpt-oss-20b`; override using the `GROQ_MODEL` repository
variable if availability changes. Quota failures wait for the next run.

Instagram professional account must be connected to Buffer as `jeeedge`.
The workflow token needs repository contents write access to create the
`jeeedge-social-media` branch. That branch stores public PNGs and submission
records; no secrets or student information are written there.

Open Actions → JeeEdge Instagram → Run workflow (branch main) to test the
connection immediately. Select `preview_only` to generate an artifact without
posting. Normal runs publish without daily approval. Set the repository variable
`SOCIAL_PAUSED=true` to pause all jobs, and pause the Buffer queue separately to
stop posts already queued. Disable this workflow if you no longer want it.

## Content and verification

Six code-calculated original problem families rotate across Physics, Chemistry,
and Maths with reproducible daily parameters. These are foundational warm-ups,
not actual PYQs. Groq writes a short hook and caption; the question, answer,
solution and layout stay deterministic. The worker rejects invalid copy and
overflowing layouts. An AI caption is not a mathematical verification system.
Visual templates use charcoal and orange, with no image-generation credits.

Personal-key post metrics from the most recent seven submissions are saved in
run artifacts when available. They are not sent to Groq. Only the original
practice problem and public caption instructions are sent to the AI provider.
This version does not optimize content based on private performance data. This version creates carousels only; reels, automated comment
and DM replies, paid ads, and guaranteed follower growth are not implemented.

## Failure handling

Preview PNGs and copy are available in each run's artifacts for 14 days. Media
URLs are verified before Buffer submission. The persistent ledger is written
before the non-idempotent createPost mutation. If submission times out, later
runs check recent Buffer posts for the date marker and do not blindly resubmit.
An unresolved ledger entry stops that day's submission for manual inspection;
future days are independent. Do not delete a ledger record without checking
Buffer for a matching post. Publication errors after scheduling need review in
Buffer; a scheduled post is not proof Instagram published it.

GitHub public repositories have free standard Actions runners. Free services
can change quotas, and GitHub may disable inactive scheduled workflows. Monitor
initial runs; occasional reconnection or maintenance may still be necessary.

Local verification: `pip install -r social/requirements.txt` then
`python social/worker.py --offline-preview` and
`python -m unittest discover -s social -p 'test_*.py'`.

## Render + cron-job.org (active scheduler)

The existing Docker backend includes POST `/api/social/trigger` and GET
`/api/social/status`. Both require `Authorization: Bearer <SOCIAL_TRIGGER_SECRET>`.
Set a random secret of at least 32 characters plus GROQ_API_KEY and BUFFER_API_KEY
on the existing Render service. SOCIAL_PAUSED=true disables triggering.
No GitHub token is needed by Render. Only original public problem text goes to Groq.

After Render deploys this commit, configure cron-job.org:
- URL: https://jee-edge.onrender.com/api/social/trigger
- Method: POST; empty body; header Authorization: Bearer <your secret>
- Time zone: Asia/Kolkata; run at 18:00, 18:20 and 18:40 daily.
- Enable failure notifications and save responses for debugging.
- Optional daily warm-up: GET https://jee-edge.onrender.com/health at 17:55.

Trigger returns 202 quickly; this acknowledges the job, not publication. Inspect
GET /api/social/status with the same header, or the next trigger response, for
state. `scheduled` means Buffer accepted the post (due about 5 minutes after
submission); confirm actual Instagram delivery in Buffer. `existing` means a
matching daily marker was already found. `failed` allows up to three total
attempts per day. `running` can be reclaimed after 15 minutes after a restart.
`submitting` or `needs_review` never automatically resubmits: inspect Buffer
before manually repairing the database record. Database ownership fences stop
expired workers from submitting. Jobs use the Asia/Kolkata calendar date.

Media and job status persist in MySQL. Public media URLs contain random IDs;
media for completed/failed jobs is retained at least 60 days. Background work
runs in the existing Render process and can be interrupted by a deployment;
subsequent triggers recover only work that has not reached submission. Free
Render cold starts can exceed cron-job.org's timeout, so the spaced retries
are intentional. GitHub Actions now supports manual previews only and has no
schedule, preventing two independent publishers.

Tests: `PYTHONPATH=backend:. python -m pytest -q backend/tests/test_social.py social/test_worker.py`
