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

## Three daily slots on the existing free Render service

POST `https://jee-edge.onrender.com/api/social/trigger` with
`Authorization: Bearer <SOCIAL_TRIGGER_SECRET>`. Keep existing GROQ_API_KEY,
BUFFER_API_KEY and SOCIAL_TRIGGER_SECRET (at least 32 characters). No new paid
service or secret is required. Docker now includes FFmpeg.

Replace the old cron-job.org schedule with `0,10,20 9,14,19 * * *`, timezone
Asia/Kolkata. The first invocation generates, later invocations reconcile Buffer
status or retry a safe pre-submission failure. Do not create additional cron jobs
with the old schedule. Optional warm-up GET /health at `55 8,13,18 * * *`.

| Local slot | Content | Trigger window |
| --- | --- | --- |
| 09:00 | Four-card JPEG carousel | 09:00–13:59 |
| 14:00 | 28-second vertical template Reel | 14:00–18:59 |
| 19:00 | Four-card JPEG carousel | 19:00–23:59 |

Before 09:00 a trigger is idle. Only the current window is eligible: missed
windows are not batch-published. Manual test calls also use the current window.
A successful submission is due about five minutes later. At most one submission
per slot; max three generation attempts. Existing once-daily records consume the
morning slot on the transition day, preserving today's prior publication fence.
New slot/asset/dispatch tables are created by the existing startup create_all;
no old table is altered or dropped. Old PNG media URLs remain functional.

GET /api/social/status with the same header shows the latest 21 slot jobs.
`scheduled` means Buffer accepted the post; `published` means a later status
check observed Buffer status `sent`. `needs_review` means inspect the existing
post in Buffer. Unknown submission responses are never automatically retried.
Later trigger calls reconcile only; they do not republish failed remote posts.

The Reel is 720×1280, 30fps H.264/AAC MP4 with a silent audio track, a countdown,
answer reveal, explanation and CTA. No music, paid voice, or AI video provider.
One FFmpeg thread, 180-second timeout, maximum 8 MiB output; a DB dispatch lock
serializes rendering claims. Server hardware performance must still be measured
on Render. Captions receive only subject/topic, not the problem or its solution;
numeric/equation output is rejected. Reel captions use fixed non-spoiling copy.

Public media supports GET/HEAD and single byte ranges for videos. JPEG/MP4 URLs
are fetched and checked before submission. Media is stored in the existing
MySQL database, with a 96 MiB admission budget. Confirmed-published media is
cleaned after 14 days; unresolved media is retained for recovery. Slots are
blocked when the budget is reached rather than buying storage. Free tier
bandwidth, database space and account quotas still apply; no paid fallback is
configured. Keep SOCIAL_PAUSED=true to suspend new generation/submission.

Tests: `PYTHONPATH=backend:.:social python -m pytest -q backend/tests/test_social_slots.py backend/tests/test_social.py social/test_worker.py`
