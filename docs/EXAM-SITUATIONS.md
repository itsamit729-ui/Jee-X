# Exam Situations

Six short JEE Main practice sessions sit inside a fictional 180-minute paper:

| Situation | Starts at | Play time | Questions |
| --- | ---: | ---: | ---: |
| The 30-minute trap | 70 min | 20 min | 10 |
| A subject took over | 95 min | 30 min | 12 |
| Too many to revisit | 135 min | 25 min | 10 |
| The last easy marks | 150 min | 30 min | 12 |
| Final answer check | 165 min | 15 min | 8 |
| Recover after a bad hour | 60 min | 45 min | 18 |

The prior answered count and story are fictional context; only the practice
segment has questions, answers, and a score. Time after the segment remains on
the timeline but is never given an invented score. All questions are JEE Main
single-choice or numerical (+4 correct, −1 wrong, 0 skipped). JEE Advanced's
variable marking scheme is not represented by these sessions.

## Launch

Deploy frontend and backend from the same branch. The backend registers
`scenario_runs` with its existing `Base.metadata.create_all` startup call.
The database user must be permitted to create that table. There is no separate
question-bank import step for this feature: the service can always fill a session
from `backend/app/data/scenario_questions.json` (18 original practice items,
6 per subject). Published compatible JEE Main questions from the database are
included in the selection when present. Authenticated students can open
`/scenarios` from the dashboard or top navigation. No existing tests, ratings,
coins, streaks, or mastery records are modified.

The bank fallback is intentionally introductory; review and expand it with
stronger questions before promoting this to a premium timed practice mode.
Question snapshots, including answer keys, are stored privately per session.
A student only receives the stem, options, diagrams, and remaining time until
the session is submitted. The API locks saves to the authenticated owner and
rejects them after the server deadline. Reloading a run ID restores saved
answers and remaining time. Starting the same situation again while it is
active resumes the same run; starting after completion creates a new run.

Backend endpoints: `GET /api/scenarios`, `POST /api/scenarios/{key}/start`,
`GET /api/scenarios/runs/{id}`, `PUT /api/scenarios/runs/{id}/answers/{question_id}`,
and `POST /api/scenarios/runs/{id}/finish`.

## Verification

Run `npm ci && npm run build` in `frontend/`. Backend checks use
`PYTHONPATH=backend DATABASE_URL=mysql+pymysql://test:test@localhost/unused
pytest -q backend/tests` from the repository root with backend development
dependencies installed. Tests use SQLite only; production continues to use MySQL.
The scenario integration test covers start and resume, hidden answers, user
isolation, invalid choices, expiration, idempotent finishing, and replay.
