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

The default target is **up to 12 items/day (8 carousels, 4 animated Reels)**.
Twelve evenly spaced windows run from 07:00 to 23:00 (80 minutes per window);
the first cron invocation within each window creates one item. Publication is
scheduled about five minutes later. Later invocations reconcile delivery or
retry safe pre-submission failures. Missed windows are skipped, not backfilled.
Existing same-day legacy submissions count against the daily target during
migration. One rendering claim at a time, unique per-slot ownership, three
attempts per slot, and durable pre-submit fencing remain in place.

Optional lower settings: SOCIAL_DAILY_TARGET=1..12, SOCIAL_REELS_PER_DAY=0..min(4,target).
Code clamps older 30/10 environment values to 12/4.
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
12 x 3 + 2 = about 38 calls/day, or about 1140/30 days. Retries, extra accounts,
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
variants and topic ordering change with the date. Both Reels and eight-slide
carousels use them, now with authored reasoning and transfer problems. No copied exam papers, unsupported PYQ labels or website/bio
invitations. Captions teach the topic without repeated engagement requests or hashtag blocks.

Groq gpt-oss-120b drafts three hooks and a caption, then reviews the packaging and
selects a hook. It cannot edit the stored mathematical rule, condition or solution.
Typical editorial use is two calls per item, about 24/day at the maximum target;
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

The current bank has 60 topics. Eighteen have dedicated diagrams; remaining
concepts use an animated worked proof. The daily plan prefers supported diagrams
for the four Reel positions. Frozen lesson snapshots are preserved on retries.

Groq writes and reviews the hook and caption; it does not generate geometry,
executable code or arbitrary external media. Visual direction is deterministic.
A full 12-item day uses at most 24 editorial calls before any retries, plus up to
12 TTS requests when all clips are uncached. Commenting is independent. Local
samples use authored hooks and do not establish live provider availability.

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
vary by concept and by Render hardware; the 12-item daily target is conditional.

`social/test_storyboard.py` checks all concepts and story variants for layout,
actual motion inside the diagram, safe AI fallback, and daily topic diversity.

### Optional free-tier English narration

Reels now use the existing `GROQ_API_KEY` for Orpheus (`canopylabs/orpheus-v1-english`,
`troy`). Enabled by default; `SOCIAL_TTS_ENABLED=false` disables speech. Keep the
Groq organization on its Free plan: application quotas cannot prevent provider
billing if someone upgrades the account. No second key or paid-provider fallback.
Comments are independent and their configuration is unchanged.

Three short narration segments open, explain and reinforce each lesson. WAV audio
is validated, aligned to scene boundaries, and mixed over quieter licensed music.
A sentence that cannot fit at at most 1.3x speed is omitted, never truncated.
The opening uses the reviewed editorial hook; explanatory speech is authored.
No additional script-generation call is required. Narration is synthetic English speech.

Separate durable `groq_tts` budgets: 8 calls/1,000 reserved tokens per minute and
90 calls/3,200 reserved tokens per rolling 24 hours. UTF-8 input bytes plus 32
are conservatively reserved per request (not measured provider token usage).
429 cooldown affects speech only. `/api/social/status` reports these counters.
Requests have a 15-second timeout and 1 MiB response cap. Quota, access, network,
or invalid-audio failures fall back to captions/animation/music without blocking
publication. No guarantee of narration on every Reel or automatic quota upgrades.

Private `social_speech` database cache (created at startup) reuses successful clips
across retries/restarts for 7 days; failed/uncertain attempts back off
for 30 minutes before a later generation may try again within the same free-tier budgets. Cache storage is capped at 32 MiB. Audio is
not exposed through public media routes. Existing account-wide consumption is
not visible to this worker. Verify the first deployed Reel in Buffer; a local
render test does not establish live Groq model access.


## Quality-focused 12/day rollout

The daily plan selects **4 Physics, 4 Chemistry and 4 Maths topics**, 12 distinct
concepts, with no topic repeated on consecutive days in the new schedule. Four
supported concepts become Reels; eight become carousels. Existing frozen lesson
snapshots are preserved on retry, so rollout-day legacy content may differ.
Old same-day submissions count toward the 12-item cap; the worker does not try to
catch up or send another 12 after deployment. Existing Buffer queue entries are
not edited, deleted or unscheduled by a deployment: inspect those separately.

Six-card carousels teach a rule, explain why, state conditions and mistakes,
show a worked example, then ask and solve a second reasoning/boundary-case
question. Supported concepts have a visual diagram. Reels now explain why the
animation works during the reveal and end with conditions rather than repeated
follow requests. Authored extension questions include changed constraints,
limiting-reagent leftovers, tangent lines and when integral symmetry is invalid.
These are original exercises, not claimed PYQs or a comprehensive Advanced course.

Groq must produce a topic-specific teaching caption and pass a separate strict
review (clarity, educational value, hook specificity and payoff >=4/5). These scores are editorial filters,
not proof of accuracy. The fallback is a complete authored explanation, never
generic marketing copy. No routine hashtag blocks, tag requests, follow/save
requests, website/bio links or guaranteed-score claims are appended. Required
music-license credits and the duplicate-detection marker remain intact.

Captions too similar (>=0.82 normalized sequence similarity) to current/prior-day
captions in returned Buffer history are held before rendering/submission; numbers,
tracking dates and music credits are ignored in that check. It can conservatively
skip a useful post and does not evaluate Instagram's private spam classifier.

Any returned Buffer error/failed/notSent status stops new submissions for 24 hours.
Inspect Instagram and the existing Buffer post; a stale Buffer error can also
cause this hold. The hold is visible as `publishing_hold` on `/api/social/status`.
If the failed entry remains after expiry, generation holds again; resolve it in
Buffer after verifying actual Instagram publication. This never retries that post
and does not pause entries already in Buffer. Confirmed restrictions need account
review, not caption rotation. No workflow can guarantee spam-free publication.

Default trigger windows (IST): 07:00 C, 08:20 C, 09:40 R, 11:00 C, 12:20 C,
13:40 R, 15:00 C, 16:20 C, 17:40 R, 19:00 C, 20:20 C, 21:40 R.
Publication is requested five minutes after generation completes; delays, holds
and missed windows can reduce the actual count. Existing ten-minute cron remains.


### Speech WAV compatibility and retry recovery

Speech validation accepts PCM WAVs with `0xffffffff` streaming length markers.
It walks RIFF chunks (including metadata), bounds reads by actual response bytes,
checks complete sample frames, measures real duration, and writes a canonical WAV
with correct lengths before caching/mixing. Ordinary truncated WAVs, non-PCM data,
partial frames, invalid rates/channels, and clips outside 0.1–20 seconds remain
rejected. The 1 MiB request cap, 15-second request timeout, 1.3x maximum playback
speed, separate speech quotas and music fallback remain unchanged.

Successful audio stays cached for 7 days. Failed/uncertain attempts use a 30-minute
backoff with a database-locked claim; existing empty cache rows become eligible
without manual deletion or a schema migration. There is no same-call retry loop,
no extra key or paid fallback. Already queued or published MP4s are not regenerated.

Logs now include a stage (cache_lookup/provider_request/audio_validation/cache_write),
a controlled reason code and numeric audio metrics. A successful streamed clip
shows `streaming_header: True`, its measured seconds, then `TTS generated`; a Reel
shows `narration_clips` and `voice_and_music`. No raw exception text, credentials,
provider body, or audio payload is logged. Header compatibility is regression-tested
with streamed WAV fixtures; production access and voice quality require a live run.


### Publish one narrated test Reel manually

`POST /api/social/test-reel` with the existing `Authorization: Bearer
<SOCIAL_TRIGGER_SECRET>` header and no request body. It works outside 07:00–23:00
and requires TTS enabled. It reserves slot `s99`, at most one submitted manual
Reel per IST date. Explicitly invoking this endpoint permits one extra test after
the regular daily allowance; ordinary cron never selects s99 and keeps its 12 cap.
Earlier manual submissions count toward the day's ordinary allowance.

The same locks, provider budgets, publishing hold, queue check, caption check,
media verification and durable submission fence apply. The test chooses an
animated topic not already saved today. All three narration scenes
must validate and fit their scene windows; otherwise it fails BEFORE rendering
or Buffer submission, with an error on `/api/social/status`. Failed tests back off
for 30 minutes before a manual retry and have at most three pre-submit attempts.
Repeated calls for an already submitted test return its status, never another copy.

Use a separate one-off cron-job.org test (or temporarily change the existing test
URL then restore `/api/social/trigger`). Do NOT schedule `/test-reel` as recurring.
A 202 response means accepted, not published. Inspect the `s99` job in
`GET /api/social/status` and the `JeeEdge Reel` logs. A successful test is scheduled
in Buffer about five minutes after generation. No secrets or new services needed.

### Content bank v2 (October 2026)

The live slot worker uses 60 distinct authored lessons (20 per subject): the
original 30 calculated families plus 30 in `knowledge.json`. The 12-post plan
rotates through all 60 topics over five days without repeating one inside that
cycle, with four posts per subject daily. The cap remains eight carousels and
four Reels. Already saved job snapshots and submitted Buffer posts are preserved.

The additional bank includes optics, magnetic work, photoelectric emission,
capacitor energy, electrochemistry, weak-acid approximations, buffers, organic
reaction conditions, coordination charge counting, conditional probability,
telescoping sums, determinants, limits and integration tricks. Each contains an
original worked example, reasoning, applicability limits and a transfer problem
with an answer. These are authored teaching examples, not quoted PYQs. Topic
scope was checked against NTA's published 2026 Paper 1 syllabus:
https://jeemain.nta.nic.in/document/syllabus-2026/
This is a bounded local knowledge bank, not automatic web ingestion or a claim
of complete syllabus coverage. New material must receive equation and layout
review before being admitted; the AI cannot rewrite the answer key.

Visual styling is selected deterministically; the old cosmetic storyboard AI
request is removed. Groq proposes three specific hooks and the caption. A separate teacher review
uses medium reasoning, up to 1024 completion tokens, and gates clarity,
educational value, hook specificity and delivered payoff at 4/5. This is an AI
quality check, not external subject-expert certification. Quota/validation
failures fall back to the concrete authored hook and teaching caption.

The selected hook now reaches both the first frame and narration. The Reel
reveals at 4 seconds, explains through 17 seconds, works the example through
23 seconds, then reinforces conditions through 28 seconds. Eighteen topics have
specific diagram animations; other topics use a labelled animated worked proof,
never an unrelated physical simulation. The apex in the vertical-throw reveal
is now actually at the highest point. Six-slide carousels lead with a challenge,
then the worked answer, reason, conditions, transfer question and explained answer.

Narration now has three scenes: opening, explanation and worked-example/mistake
check. All three are required by the manual narrated test; ordinary production
retains the existing logged music fallback on TTS failure. Successful clips
produce short on-screen phrase captions distributed across the measured clip
length; these are approximate phrase timings, not forced-aligned word timings.
All existing TTS budgets, 1.3x speed cap, speech cache and free-provider limits
remain in force. `JeeEdge content` logs report the bank, topic, format, editorial
source and hook length so fallback usage is visible alongside TTS clip counts.

A new release cannot demonstrate account growth by itself. Reach, watch time,
saves, shares and profile-to-follow conversion must be assessed from actual
Instagram Insights. This change does not fetch Insights or claim to optimise
from performance data it cannot observe. Spam flags and follower gains cannot
be guaranteed by a content generator; repetition checks and the existing
publishing holds remain active.

### Editorial variety and original comics (October 8)

New daily lesson snapshots carry `art_direction` and `design_version: 3`.
Each media kind rotates independently through notebook, comic (`casefile` in
code), poster and comparison. At the 12/day setting this gives **two comic
carousels and one comic Reel daily**, plus six other carousels and three other
Reels. No extra publication slots are added. A comic replaces a normal item.
The four Reel slots use all four directions; each carousel direction appears
twice. Smaller schedules use the same bounded rotation. Frozen snapshots retain
their metadata; older ones use a deterministic lesson-ID fallback.

These are different compositions, fonts and reading sequences, not colour-only
variants. Notebook carousels have five slides, comic and poster four, and
comparison six. Comic covers use original drawn characters and an authored
brain-versus-question exchange. `humor.json` covers every one of the 60 lessons.
The apparent wrong answer is explicitly a fictional character's misconception;
the punchline corrects it and the following cards supply the worked answer and
conditions. No scraped image macros, celebrity footage, invented student results,
personal anecdotes or extra media licences are involved.

Captions no longer have to begin with the topic name or end in a stock question.
Each direction has a different caption brief and length range; authored fallbacks
follow those same distinct structures. Groq still drafts and teacher-reviews
facts, specificity and payoff. Four recent caption excerpts provide repetition
context. The existing publication similarity check, credits and marker remain.

Comic Reels spend 0–4 seconds on the confident thought, 4–9 on the punchline,
then show the verified diagram and working. Their four authored voice scenes
speak those lines in order. Ordinary Reels retain three scenes. If any comic
voice scene fails validation/timing, all comic voice is omitted: do not publish
a spoken misconception without its spoken correction. The manual test still
requires every requested voice scene; regular production retains music and
complete on-screen teaching on a provider failure. No extra LLM/script calls,
new keys, paid services, enabled comments or quota increases are needed.

Published and already queued assets are not rewritten by deployment. The new
formats apply when a fresh slot is generated. Local previews with music only
are labelled as such and are not evidence of live TTS or Instagram delivery.
