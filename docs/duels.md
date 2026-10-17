# 1v1 arena and Exam situations

## Access

Students open **Explore → 1v1 arena**, the sword icon in the header, or
**Challenge** on another student's public profile. Routes: `/duels` and
`/duels/:matchId`. Teachers are redirected to their teaching workspace.

Create a private invitation using an exact student username. Choose JEE Main,
MHT-CET or BITSAT, all PCM subjects or one subject, and one of three formats:
5 questions / 5 minutes, 10 / 15 minutes, or 15 / 25 minutes.

The invite lasts 30 minutes. The opponent accepts or declines; the challenger
can cancel. Both students must ready up within a ten-minute lobby window.
The server schedules a shared five-second countdown and a shared deadline.
No paper is released before that countdown ends. One student cannot ready up
for overlapping active matches. Every match has identical questions, order,
marking and available time for both players.

## Answers, reconnection and results

Published questions with complete answer keys are selected from the requested
exam. Selection balances subjects/difficulty bands and prefers questions neither
student has answered in recorded practice. Questions and keys are snapshotted
at invitation time, so later edits do not change an accepted match.

Answers save automatically, with visible saving/error state and Retry sync.
Submission drains the answer-save queue and retries unsaved responses. Failed
saves block early submission. The server never accepts responses before the
start, after a player's submission, or at/after the deadline. At expiry, only
responses already received by the server count. Refreshing restores saved
answers; responses still unsaved in a disconnected browser cannot be restored.

Reopen the room after a disconnect. The server deadline keeps running. Timeout
settlement occurs on the next authenticated match/inbox request; no background
job or process-local match timer is needed, including after a worker restart.

Only progress counts are visible while playing. Neither player receives scores,
keys, solutions or the other's responses until both submit or the deadline ends.
Surrender ends the match immediately and awards it to the other player. After
submission a player cannot surrender to interrupt their opponent. Equal scores
are draws; latency and client timings never decide a tie. Final review includes
both responses, correct answers and available solutions. Rematch creates a new
invitation requiring acceptance. Matches do not modify contest ratings, coins,
mastery, standard mock history or dashboard test totals.

## Deployment and operations

Deploy the main website/API together. The existing `Base.metadata.create_all`
startup creates `duel_matches` and `duel_players`; no existing columns or data
are migrated. The normal app database account needs CREATE TABLE privileges.
No extra worker, WebSocket server, cron, AI key or external messaging service
is required. No emails/DMs are sent by creating an invitation.

Match progress polls every three seconds while visible. After the initial paper,
polls request only state/progress; final review is fetched once. Lobby lists poll
every ten seconds; the header invitation count polls every thirty seconds. Hidden
tabs pause network polling and focus triggers a refresh. The inbox returns at most
40 matches, prioritizing open ones, with batched player/user queries. Limits:
five open challenges per participant, twenty invitations per challenger per day,
and one open challenge per pair.

Match mutations use database row locks; participant locks use stable user-ID
order. The production engine is MySQL. Isolated lifecycle/access tests use SQLite,
so production MySQL contention and a 500-student load have not been benchmarked.

## Exam situations

`/scenarios` now shows fuller situation briefings before starting: fictional exam
context, decision objective, marking, navigator/review controls, reconnection and
fullscreen rules. The introduction and reading container are centred; question
text and controls remain left aligned. Starting requests fullscreen directly
from the button gesture. Active situations use an exam header without the site
navigation, a visible server-based segment clock and Finish & exit.

Fullscreen initialization no longer cancels entry while a newly mounted page is
loading. Supported browsers that deny entry show a Resume prompt; a failed entry
is not counted as an exit. The fourth actual fullscreen exit submits saved answers.
Unsupported mobile browsers use the viewport; browsers control whether fullscreen
is available. This is a practice aid, not a tamper-proof proctoring system.

## Verification

Backend tests cover participant isolation, private keys/results, frozen snapshots,
exam marking, countdown/expiry, invalid answers, submission idempotence, surrender,
reconnection, overlapping matches, and auth-account/student-ID separation.
Frontend tests cover final review, player identity, server-clock offset,
fullscreen-entry guidance, and uncached authenticated answer requests.
Native two-browser/device fullscreen and visual checks still need a deployment
smoke test; no production load or device-compatibility guarantee is claimed.
