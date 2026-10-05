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

Personal-key post metrics from the most recent seven submissions are supplied to
the caption generator when available. This is basic feedback, not a complete
growth optimizer. This version creates carousels only; reels, automated comment
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
