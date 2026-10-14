# Short-form content review — 14 October 2026

## Evidence and limits

This review used publicly indexed creator pages, video metadata and creators' own
public channel posts. Several direct YouTube requests were throttled; the clips
were not all watchable through the research tools. Counts below are indexed
snapshots, not live analytics or evidence that one technique caused engagement.
Telegram post views must not be reported as YouTube video views. No private
creator retention, saves, click-through or conversion data was available.

| Creator / source | Public signal available | Format lesson, as an inference |
| --- | --- | --- |
| [3Blue1Brown, A short on shorts](https://www.youtube.com/watch?v=TaopSi3Ucfc), published 12 December 2023 | Indexed YouTube snapshot: 815,454 views and 71,000 likes. An older example, not a current trend ranking. Description connects the Short to full visual explanations. | Start with a visual idea worth resolving; make the explanation itself useful. |
| [3Blue1Brown's own production advice](https://www.3blue1brown.com/about/) | The creator explicitly advocates concrete examples before definitions and purposeful animation aligned with narration. | Show the exercise immediately; animate a mathematical relationship, rather than decorating a paragraph. |
| [Eduniti's own public posts](https://t.me/s/edunitimg?before=5840&q=%23eduniti) | One visible Shorts-link post had 36.8K Telegram post views and 56 heart reactions in the retrieved page. This does not establish the Short's YouTube performance. Related indexed posts package specific unexpected questions and compact worked challenges. | Give the student a concrete testable claim and a specific next practice step. |
| [Prateek Jain's own experiment post](https://telegram.me/s/IITJEE_PHYSICS?before=1765) | Indexed public post linking an experiment Short: 7.13K Telegram post views and 20 fire reactions. Again, not YouTube metrics. | A visible experiment followed by an explanation offers a more concrete opening than an abstract formula label. |

These observations support an experiment, not a promise of reach. No scripts,
video clips, creator likenesses, voices or watermarked assets were reused. The
Jee Edge mathematical examples and visual models remain original authored work.

## Why the previous videos felt repetitive

The `advanced_v1` questions had become harder, but the presentation still held
some cards for 14 seconds. The three narration windows covered a hook, a general
explanation and a condition; they did not narrate all three actual deductions.
The same closing promotional sequence appeared after each explanation. Raising
question difficulty did not address those presentation problems.

## Implementation

New advanced snapshots add `story_engine: visual_v1`, while existing immutable
snapshots retain their renderer and timing. New 40-second stories use cuts at
0, 3, 8, 15, 22, 30 and 36 seconds:

- Open with the exact problem's tension; the first frame carries useful content.
- Show an authored model: wedge recoil, rod rotation, opposed springs, a rotating
  hoop, tunnel SHM, crossed-field speed, a complex locus, explicit amount/energy
  comparisons or a structured algebraic deduction.
- Reveal one worked step at a time. Five short speech requests cover the setup,
  three actual deductions and the follow-up question.
- Change a condition, reveal the follow-up answer and keep that answer visible
  through the end. Preserve essential conditions and use a small practice URL.
- Keep the original synthesized audio. Transition cues now follow the new cuts.

Models labelled by physical quantities preserve units and signs. Rod hinge
force is shown as its bottom-position value only at the bottom; the moving wedge
has a geometrically 45-degree incline. Buffer diagrams distinguish initial from
post-neutralisation amounts. Schematic motion is explanatory, not a numerical
simulation of full physical dynamics.

Partial speech still falls back as a complete visual lesson, rather than leaving
only a spoken misconception. The bounded 32 MiB speech cache evicts old completed
clips instead of permanently preventing new narration when it fills. Embedded
MP4 audio is unaffected by cache eviction.

## Capacity

The existing default is four source Reels/day, with a reusable MP4 for each
YouTube mirror. The hard application ceiling is now five; opt in with
`SOCIAL_REELS_PER_DAY=5` for the next day's schedule. Total source posts remain
at most twelve/day, so this substitutes a Reel for a carousel. It is not five
additional source posts and does not double rendering for YouTube.

The 32-day plan test checks distinct lessons, subject balance and the authored
five-Reel speech reservation against the existing 3,200-byte/token local daily
speech budget, including a maximum-length reviewed English hook. This is a
local conservative reservation calculation, not a guarantee about external
account-wide allowances or retry consumption. Existing provider, render,
egress, queue, storage, retry and duplicate-submission guards remain in place.

[Groq's published limits](https://console.groq.com/docs/rate-limits) distinguish
per-minute and per-day limits and apply at organization scope. Their
[Orpheus reference](https://console.groq.com/docs/text-to-speech/orpheus) still
supports this model/voice and caps each input at 200 characters. Account access
and remaining allowances must be checked on the actual provider account; no
paid fallback or budget increase was added.

Admin → Publishing now shows actual embedded voice clips, creative engine,
editorial source, render wall time and MP4 size for newly prepared work, alongside
the existing provider usage ledger. Older jobs say telemetry was not collected.
A configured key does not prove a successful speech request. Audience retention
and account-wide quota usage are not available to this code, and the UI says so.

## Validation

Tests cover all 24 advanced lessons across all four story formats and each
scene boundary, immutable old snapshots, chart arithmetic, narration completion,
source-video reuse for Shorts and speech-cache eviction. Preview MP4s are
rendered using the real 720×1280 H.264/AAC pipeline. Preview audio uses the local
music fallback; live TTS and social delivery need the deployed credentials.
