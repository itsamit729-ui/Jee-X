# JeeEdge Instagram automation

The active system runs on Render; see **Adaptive free-tier capacity** below.
The following initial setup documents the legacy GitHub worker (now preview-only).

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

## Adaptive free-tier capacity (active Render automation)

Deploy the latest feature/version-1 commit, then replace the old cron schedule:

- URL: https://jee-edge.onrender.com/api/social/trigger
- Method: POST; existing Authorization: Bearer <SOCIAL_TRIGGER_SECRET> header
- Cron: `*/10 7-22 * * *`; timezone Asia/Kolkata
- Existing GROQ_API_KEY, BUFFER_API_KEY and SOCIAL_TRIGGER_SECRET remain sufficient.
- No new service, paid fallback, voice subscription or video-generation API.

The default target is **up to 30 items/day (20 carousels, 10 template Reels)**.
Thirty evenly spaced windows run from 07:00 to 23:00 (32 minutes per window);
the first cron invocation within each window creates one item. Publication is
scheduled about five minutes later. Later invocations reconcile delivery or
retry safe pre-submission failures. Missed windows are skipped, not backfilled.
Existing same-day legacy submissions count against the daily target during
migration. One rendering claim at a time, unique per-slot ownership, three
attempts per slot, and durable pre-submit fencing remain in place.

Optional lower settings: SOCIAL_DAILY_TARGET=1..30, SOCIAL_REELS_PER_DAY=0..target.
Change these between days because slot allocation depends on them. SOCIAL_PAUSED=true
stops new work. The system does not create comments, DMs, likes or follows.

### Budgets, not a guarantee about account-wide allowance

| Resource | Local rolling budget |
| --- | --- |
| Buffer | 95 calls/15 min; 95/24 hours; 2850/30 days |
| Groq (all editorial requests combined) | 28 calls + 7600 tokens/min; 950 calls + 190000 tokens/day |
| Rendering | 1800 measured seconds/day; reserve 180 seconds per job first |
| Public social media traffic | Admit new jobs only below 64 MiB/day and 1 GiB/30 days, with an 8 MiB reserve |
| New social asset storage | 96 MiB, independent of other website data |

Quota reservations commit BEFORE HTTP requests, including calls that later fail.
Groq output token allowance and a conservative input-byte estimate are reserved;
reported actual token usage then settles the reservation. Interrupted requests
keep their reservation. Provider 429 responses establish a durable cooldown;
no retry storm, key rotation, paid fallback or quota bypass. Tokens/calls from
before this rollout or other apps are NOT counted locally. The provider still
has final authority. Check provider dashboards for actual remaining capacity.
No unused quota is deliberately burned: more AI calls do not imply better work.

Channel discovery is cached for 24h (two Buffer calls on cache miss). Normally
each item costs one history query, one submission, and one delivery read:
30 x 3 + 2 = about 92 calls/day, or about 2760/30 days. Retries, extra accounts,
slow publication, manual calls or queue backlog reduce achievable output. Queue
checks stop at nine pending entries, leaving one free-plan slot as headroom.
A history page exceeding 100 entries stops safely rather than missing duplicates.

GET /api/social/status (same authorization header) reports targets, jobs and
local usage. scheduled = accepted by Buffer; published = observed Buffer sent;
needs_review = inspect the existing Buffer post, never blindly resubmit it.
Old job/media tables and public PNG URLs remain intact. New social_usage,
social_quota_lock and social_cache tables are registered through startup create_all.

Confirmed-published and safe pre-submit failed assets become eligible for cleanup
after seven days. Ambiguous submissions are retained. Existing media URLs continue
serving even after the traffic admission threshold is reached; otherwise already
queued posts would break. This is NOT a hard cap on Render's total billed bandwidth.
Website traffic, old media, database allowance, other apps and provider billing
settings must still be monitored. Runtime measurements here do not benchmark Render.

### Content and Groq

Thirty authored shortcut families across Physics, Chemistry and Maths include
an applicability condition, common trap, calculated example and solution. Numeric
variants and topic ordering change with the date. Both Reels and six-slide
carousels use them. No copied exam papers, unsupported PYQ labels or website/bio
invitations. Calls to action are save/follow for revision.

Groq gpt-oss-120b drafts three hooks and a caption, then reviews the packaging and
selects a hook. It cannot edit the stored mathematical rule, condition or solution.
Typical editorial use is two calls per item, about 60/day at the maximum target;
there is no reason to consume 950 calls merely to exhaust the free allowance.
Invalid output, quota limits or rejected reviews use authored packaging. Review
by an LLM is not independent proof; authored lessons and numerical checks are
the source of the educational content. No private student or Buffer analytics
are included in prompts.

Reels are locally rendered 28-second 720x1280 H.264/AAC MP4s with licensed music,
a question, shortcut, conditions, worked example and misconception. FFmpeg uses
one thread, with a 180-second overall render budget. JPEG and MP4 URLs support GET/HEAD and
byte ranges; public content is checked before submission.

Validation: `PYTHONPATH=backend:.:social python -m pytest -q backend/tests/test_social_slots.py backend/tests/test_social.py social/test_worker.py social/test_editorial.py`

Quota references checked 2026-10-06:
- https://console.groq.com/docs/rate-limits
- https://support.buffer.com/en-us/articles/troubleshooting-buffers-api-VgBuQXUCDI
- https://render.com/docs/free

## Animated concepts and automatic licensed audio

New Reels include the bundled 28-second excerpt of Carefree by Kevin MacLeod
(CC BY 4.0), mixed at reduced volume with fade-in/out. `social/audio/` contains
the excerpt, its checksum, provenance, and license. Source and license credits
are appended automatically to every Reel caption before the final deduplication
marker; carousel captions are unchanged. No extra secret, paid API, runtime
music download or manual Instagram action is required. Missing or modified
audio fails the job before submission rather than publishing unapproved music.
Existing queued Reels retain their original files. This embeds a soundtrack;
it does not select an Instagram trending-audio entry.

Ten authored concept diagrams: complementary projectiles, vertical throw, circular
motion, travelling waves, kinetic-energy scaling, dilution, first-order half-life,
odd/even integrals, and tangent slope. Illustrative examples are labeled separately
from the generated practice question. Other topics use timed text reveals.
Frames are generated at 12 fps and encoded at 30 fps to limit CPU/storage cost.
Existing 8 MiB media limit and durable render/egress budgets still apply; actual
throughput depends on Render performance. Models preserve mathematical conditions
and are not AI-generated diagrams.

Timeline: 0-6s challenge; 6-16s concept/rule; 16-24s worked answer; 24-28s trap + save/follow.

Verify with:
`PYTHONPATH=backend:.:social python -m pytest -q backend/tests/test_social_slots.py backend/tests/test_social.py social/test_worker.py social/test_editorial.py social/test_reel.py`
The real FFmpeg test checks the encoded audio samples are non-silent.
Deploy this commit on the existing Render service. Cron and posting targets are unchanged.

## Intelligent comments

See [COMMENTS.md](COMMENTS.md) for the implemented Meta webhook + Groq reply worker,
free-tier limits, review inbox and one-time Instagram API connection. It is disabled
until configured; Buffer publishing credentials alone do not enable comments.

## Visual-first Reel renderer (October 7 update)

New Reel slots rotate through 12 dedicated animated concepts, 10 distinct topics
per 10-Reel day. Carousels retain the broader authored lesson pool. Existing saved
lesson snapshots are reused during retries so changing the renderer never changes
the question attached to an already generated job.

Groq makes one additional small structured call per Reel (maximum 512 completion
tokens) to select a supported story format, authored hook, pace, accent and ending.
No executable code, geometry, equations or arbitrary external media come from the
model. Selection validation and deterministic authored fallback keep generation
working when AI output fails or quotas are exhausted. Typical full daily target
now makes 70 editorial/storyboard calls, plus any comment calls, sharing the same
persistent Groq budget. Samples use authored plans; no live Groq access is needed
to preview or test the renderer.

Experiments start on the first frame, occupy a larger central area, and render
at 24 fps (30 fps H.264 output). Story phases are visual prediction/comparison/trap,
result reveal, worked challenge, and a recap with the rule's conditions. Particle
motion, trajectories, tangent slopes and rearranged areas are authored. The
reaction illustration conserves atoms: 3 N2 + 6 H2 produces 4 NH3 + 1 unused N2.
The square transformation preserves the exact (a-b)(a+b) area of the lesson.

Licensed music remains embedded, with original synthesized transition cues added.
Automatic caption attribution is retained. No new service, API key or paid voice/
video generation is required. FFmpeg veryfast encoding, one thread, the 180-second
render ceiling and 8 MiB output ceiling remain enforced. CPU and data use still
vary by concept and by Render hardware; the 30-item daily target is conditional.

`social/test_storyboard.py` checks all concepts and story variants for layout,
actual motion inside the diagram, safe AI fallback, and daily topic diversity.

### Optional free-tier English narration

Reels now use the existing `GROQ_API_KEY` for Orpheus (`canopylabs/orpheus-v1-english`,
`troy`). Enabled by default; `SOCIAL_TTS_ENABLED=false` disables speech. Keep the
Groq organization on its Free plan: application quotas cannot prevent provider
billing if someone upgrades the account. No second key or paid-provider fallback.
Comments are independent and their configuration is unchanged.

Two short authored lines introduce and explain each visual experiment. WAV audio
is validated, aligned to scene boundaries, and mixed over quieter licensed music.
A sentence that cannot fit at at most 1.3x speed is omitted, never truncated.
No extra LLM calls are used for scripts. Narration is synthetic English speech.

Separate durable `groq_tts` budgets: 8 calls/1,000 reserved tokens per minute and
90 calls/3,200 reserved tokens per rolling 24 hours. UTF-8 input bytes plus 32
are conservatively reserved per request (not measured provider token usage).
429 cooldown affects speech only. `/api/social/status` reports these counters.
Requests have a 15-second timeout and 1 MiB response cap. Quota, access, network,
or invalid-audio failures fall back to captions/animation/music without blocking
publication. No guarantee of narration on every Reel or automatic quota upgrades.

Private `social_speech` database cache (created at startup) reuses successful clips
across retries/restarts for 7 days; failed/uncertain attempts are also remembered
for 7 days to avoid spending again. Cache storage is capped at 32 MiB. Audio is
not exposed through public media routes. Existing account-wide consumption is
not visible to this worker. Verify the first deployed Reel in Buffer; a local
render test does not establish live Groq model access.
