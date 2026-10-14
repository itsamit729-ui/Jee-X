# Jee Edge Instagram automation

## Active setup

The Render app owns scheduling and publishing. The GitHub Action is an offline
preview of that same renderer; it cannot publish and uses no provider secrets.
Deploy `origin/feature/version-1` to apply these changes to newly generated slots.
Frozen lessons, existing media URLs and already submitted Buffer posts keep their
original content. No database migration or additional API key is needed.

- Site: https://jeeedge.in
- Set the Instagram profile website to **https://jeeedge.in/start** once.
- Keep the existing Render cron: `POST /api/social/trigger`, every ten minutes
  between 07:00 and 23:00, Asia/Kolkata, using its existing Bearer secret.
- Required: existing `BUFFER_API_KEY`, `SOCIAL_TRIGGER_SECRET` (at least 32
  characters) and a connected professional Instagram account with automatic
  publishing. `GROQ_API_KEY` is optional: authored captions and music-only Reels
  work without it.
- Public media URLs use `SOCIAL_MEDIA_ORIGIN`, then `RENDER_EXTERNAL_URL`, then
  the original Render origin. An override must be a public HTTPS origin without
  a path. Check it if Buffer cannot fetch a video.
- No video-generation subscription, stock-footage purchase, image-generation
  credits, voice subscription or paid fallback was added.

The profile link opens three real choices: ten free mixed-subject warm-up
questions; public MHT-CET year/shift previews with sign-in for mocks; and signed-in
chapter practice. Reel end cards and captions give this short URL explicitly.
The worker does not change the Instagram profile. It does not assume that a URL
in a Reel caption is clickable. A destination-specific share link can add
`?utm_source=instagram&to=cet` (or `warmup` / `practice`); these reorder the three
choices, never redirect to an arbitrary website.

## Stories and content

New snapshots have `creative_version: 4`. Four Reel formats rotate independently
of the carousel layout; a four-Reel day uses one of each:

| Story | Opening and payoff | Length |
| --- | --- | --- |
| Challenge | Make a call, then check the answer and working | 24 s |
| Answer first | See the result immediately, then learn why | 23 s |
| Mistake check | Question a specific misconception and resolve it | 25 s |
| Visual proof | Connect a concept illustration to the worked example | 27 s |

Hooks concern the actual worked question. Captions vary their entry point and
keep the question, solution and essential condition. Sixty authored lessons
rotate across Physics, Chemistry and Maths. A twelve-item schedule covers the
bank in five days; a four-item schedule covers it in fifteen days. Reels also
balance subjects. Different pacing, compositions, authored motion, diagram
reveals and four original synthesized music beds provide variation without
provider calls. Eleven additional concept drawings cover parallel resistance,
series springs/capacitors, mole fraction, gas ratios, arithmetic pairing,
successive percentages, signed impulse, lens displacement, SN1 rate changes and
the AM-GM minimum. Illustrations are labelled separately
from exact worked examples. No scraped footage or fabricated student results.

Carousels retain four distinct layouts (notebook, original comic, poster and
comparison), with four to six cards, then a practice link on the final card.
The lessons are original teaching examples, not claimed PYQs. The public paper
archive labels its reconstructed papers and available question coverage separately.

Groq still drafts three hooks and a caption, then performs a teacher-style
review: at most two editorial calls per fresh item. Exact mathematical content
and diagrams are authored. AI review is a filter, not proof of correctness.
Provider or validation failure uses the complete authored hook/caption. No extra
AI story-planning request is made. Captions similar to recent lessons are held;
site promotion, credits and tracking markers are excluded from that comparison.

## Sound, speech and rendering

Each new Reel uses locally synthesized rhythm and transition sounds. No runtime
music download or samples are needed. Original-music credit is appended before
the final deduplication marker. Legacy snapshots retain the checked, licensed
Carefree excerpt and its Kevin MacLeod / CC BY 4.0 attribution.

Existing optional Orpheus English narration uses `GROQ_API_KEY`; disable with
`SOCIAL_TTS_ENABLED=false`. Three short authored scenes speak the opening,
reasoning and condition. Measured WAV duration controls alignment and phrase
subtitles; playback speed is capped at 1.3x and speech is never truncated. If any
new-story scene fails, the entire Reel uses the complete visual lesson and music.
Successful clips are cached for seven days within the existing 32 MiB speech
cache; failed attempts back off thirty minutes. There is no paid voice fallback.
Local preview videos intentionally use music only and do not verify live TTS.

Video remains 720×1280, 24 fps source / 30 fps H.264 output, AAC stereo audio.
Essential text avoids the right interaction rail and bottom caption area; speech
has a separate subtitle band. One-thread encoding, the 180-second render ceiling
and 8 MiB output limit remain enforced. Throughput depends on Render hardware.

## Schedule, budgets and recovery

The existing maximum is twelve items/day: eight carousels and four Reels.
`SOCIAL_DAILY_TARGET=1..12` and `SOCIAL_REELS_PER_DAY=0..min(4,target)` lower it.
Change targets between days because allocation depends on them. A four-Reel-only
schedule is possible with both values set to four. The worker skips windows that
never created a job; it does not backfill a burst. An existing interrupted or
failed pre-submission job can recover within two hours, with a ten-minute backoff
and at most three attempts. Each trigger claims at most one job. Default windows (IST): 07:00 C,
08:20 C, 09:40 R, 11:00 C, 12:20 C, 13:40 R, 15:00 C, 16:20 C, 17:40 R,
19:00 C, 20:20 C, 21:40 R. Publication is requested five minutes after generation.

| Existing local rolling budget | Limit |
| --- | --- |
| Buffer | 95 calls / 15 min; 95 / 24 h; 2,850 / 30 days |
| Groq editorial | 28 calls / 7,600 tokens per minute; 950 / 190,000 per day |
| Groq speech | 8 calls / 1,000 reserved tokens per minute; 90 / 3,200 per day |
| Rendering | 1,800 seconds per day |
| New media admission | 64 MiB per day; 1 GiB per 30 days |

These are application budgets, not measured provider-wide allowance or a hard
hosting bill cap. Keep provider accounts on their free plans. Other applications
and website traffic are outside this ledger. Reservations, provider cooldowns,
queue headroom, caption checks, daily caps and a database fence before submission
remain active. Quota failures wait instead of upgrading or rotating keys.

`GET /api/social/status` and `GET /api/social/plan` require the existing Bearer
secret. Status reports actual jobs and local budget counters. Plan shows today's
fresh-slot topics, authored hooks, formats and destinations without spending
quota or creating jobs; frozen or queued slots can differ from this preview.

### Delivery and recovery

`GET /api/social/status` is read-only. A successful status request does **not**
run the publishing workflow. The external cron must use **POST
`/api/social/trigger`**, with `Authorization: Bearer <existing secret>`. The
application does not create or repair the external cron configuration. Status
includes the last valid publishing trigger, next planned windows, job formats,
stages, due times, last delivery checks, and configuration-presence flags; it
never returns credentials. A planned window is not a promise of publication.

Triggers reconcile pending deliveries at most every thirty minutes, including
outside publishing hours. Checks use recent history plus bounded exact-post
lookups, so older accepted jobs can reach a confirmed state. Authenticated
`POST /api/social/reconcile` requests a read-only check with a one-minute
throttle. Neither this endpoint nor status creates or resends a post. Checks
respect the existing Buffer call budget. Paginated history reads are bounded.

`scheduled` means Buffer accepted the post; `published` means Buffer was observed
reporting `sent` for automatic publishing. Drafts, approval-required posts,
notification publishing and unknown results remain distinct attention states.
A timeout after the durable submission fence is `needs_review`, never blindly
resubmitted. Failed delivery is quarantined on that post instead of installing
a global twenty-four-hour hold. Unrelated historical failures do not block fresh
work. Two recent tracked delivery failures stop fresh submissions until the
connection or delivery problem is resolved. Reconciliation can clear that
circuit when it confirms successful delivery.

Legacy global failure holds request an exact read of their flagged post at most
once every thirty minutes. A successful read migrates the result to that post's
state and clears the legacy hold, even if it failed or disappeared. API read
errors preserve the hold. Explicit holds without a post ID are preserved. No
migration path resubmits the old post.

Frozen lessons survive restarts. Prepared media IDs, full captions and format
are checkpointed before the public-media check. A transient fetch failure
reuses those assets on a safe retry instead of rerendering or repeating editorial
requests. Confirmed published media and safely failed pre-submission assets
become eligible for cleanup forty-eight hours after their last job update.
Uncertain submissions retain their media. The 96 MiB active-media ceiling still
applies; status explains storage and admission failures rather than hiding them.
`SOCIAL_PAUSED=true` stops new jobs; pause existing queued posts in Buffer itself.

### Admin controls and manual test

Admin → **Reels & publishing health** shows trigger health, pending deliveries,
preparation stages, errors, saved media, and the last confirmed Reel. **Refresh
status** reads the ledger; **Check Buffer delivery** requests reconciliation.
Neither button publishes anything. If Buffer reports failure but the matching
post is already visible on Instagram, **Already live on Instagram?** lets an
administrator record its public URL after explicitly checking the lesson and
caption. This is labelled `confirmed_published`, distinct from provider-confirmed
publication. It never creates, edits, deletes or resends a remote post.

The optional `POST /api/social/test-reel` publishes one manual test using slot
`s99`, with the same authored/music fallback as production. Add
`?require_voice=true` only when intentionally testing all three voice scenes;
that strict mode stops before submission if narration is unavailable. At most
one submitted test is permitted per IST day, and it can add one test beyond the
ordinary daily cap. This is **not** a preview endpoint and must not be placed on
a recurring schedule. These development checks do not call it against a live
account. Comments remain independently configured; see [COMMENTS.md](COMMENTS.md).

## Preview and verification

Run from the repository root with Pillow and FFmpeg installed:

```sh
python -m social.preview --day 2026-10-12 --count 4 --reels 2
python -m social.preview --day 2026-10-12 --count 4 --reels 4 --output social/output/all-reels
```

`--stills-only` skips video encoding. Outputs include actual MP4s, first-frame
covers, scene PNGs, carousel cards, captions, a contact sheet and a JSON content
plan. The CLI never calls Groq, Buffer or Instagram. Actions → JeeEdge Instagram
preview runs this same path and retains review artifacts for fourteen days.
Keep `preview_only` checked. The old `social/worker.py` publishing CLI is legacy;
use `social.preview` to inspect the active slot renderer.

```sh
PYTHONPATH=backend:. python -m pytest -q social backend/tests/test_social.py backend/tests/test_social_slots.py backend/tests/test_social_recovery.py backend/tests/test_public_papers.py
cd frontend
npm run build
```

Tests protect the full topic rotation, all-format layout fit, immutable answers,
legacy playback/attribution, voice fallback, sound samples, duplicate prevention,
quotas, authenticated planning and the public practice journey. Actual account
reach and watch time must be assessed from Instagram Insights. Admin → Practice
discovery shows aggregate Instagram start-page/paper views and start-button
clicks alongside successful paper mock starts. These do not measure completed
warm-ups, followers, Reel watch time or unique visitors.
