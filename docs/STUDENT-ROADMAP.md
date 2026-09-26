# Student roadmap

Available at `/roadmap` from the main navigation, mobile menu and dashboard. Uses the existing palette and responsive two-column layout. Recommendation explanations remain attached to practice questions.

## Deployment

Deploy backend and frontend from the same commit. No new service, secret or dependency is required. Operators can configure verified JEE Main dates with `JEE_MAIN_EXAM_DATES`, a JSON object mapping target year strings to ISO dates. Leave it `{}` when an official date is not configured; the UI explicitly uses a rolling 12-week planning horizon instead. Past, malformed or missing dates never become an exam countdown. Existing `Base.metadata.create_all` startup creates the additive `student_roadmaps` table. No existing rows are rewritten. The database account needs the same table-creation permission already used at startup.

## Student flow

1. Choose exactly one goal: target marks, or one to three distinct college-and-branch program IDs from the searchable imported catalog. There are no student inputs for dates, ranks or study hours. The server validates program IDs and rejects duplicate/extra choices. `GET /api/roadmap/colleges?q=...` provides authenticated, bounded search.
   JeeX derives the target year from the student profile, manages verified exam dates centrally, and suggests a weekly pace (five hours initially; 3–15 hours from observed timed practice plus review). This is a suggested pace, not an assertion of available time. Existing saved marks goals remain readable without a migration; old manual timeline/rank fields are ignored.
2. A saved plan contains up to three chapter priorities, each with the evidence behind it, concept review, 15-minute practice and a 15-minute fresh-question check. Small weekly budgets receive fewer priorities; blocks are capped at 90 minutes, leaving remaining time for independent study/full assessment.
3. Practice links preselect the subject and chapter. Fresh distinct answers after plan creation update checkpoints; repeating a previously seen question never counts as fresh. Four correct in the latest five fresh answers is a checkpoint, not a mastery claim.
4. Rebuilding archives the previous checkpoint state (latest 12 reviews retained) and starts another seven-day plan. GET does not create or rewrite a plan. Assessment results and task progress update when the page is revisited; navigation reads use private 30-second memory caching and mutations invalidate it.
5. Goals are chosen by the student, not model-predicted gains. For college goals the lowest historical applicable closing CRL among comparable selected choices becomes the reference target. Each preference retains its own cutoff/year/round; missing or inapplicable data is explicitly shown and is never replaced by a guessed cutoff. The target college list shows the selected comparable choices. The date countdown and marks gap communicate the target; neither task completion nor study hours automatically increases an estimated score/rank.

## Baseline assessment

`POST /api/subject-tests` accepts `assessment: true`. The existing authenticated builder and grader serve 75 fresh, complete questions: 20 single-correct + 5 numerical per subject, from Main-enabled chapters. Selection spreads chapters and difficulty buckets, independently of weakness-based recommendations. Answers are never included in the paper response.

- Three-hour browser timer with automatic submission, +4 correct / -1 incorrect / 0 unanswered for both supported question types.
- All scores are calculated server-side. Batched question/revision/topic-stat reads avoid per-question read roundtrips during grading.
- Missing fresh content for any subject/type returns a recoverable 409; no incomplete or repeated substitute paper is labelled a baseline.
- Only generated roadmap assessments with 75 question responses, correct marking configuration and submission within 3h + 60s delivery tolerance enter the baseline.
- Current score is the median of up to three valid assessments in the last 45 days; up to six historical assessments are displayed.
- Legacy client-scored mock counts and short adaptive tests do not establish roadmap national standing. The predictor now treats stored TestQuestion scores as actual marks, rather than multiplying them by four.
- Existing legacy dashboard summaries exclude these new assessments; the roadmap displays their marks and assessment history separately.

Generated papers are **not psychometrically calibrated** or guaranteed representative of official chapter weightings. The UI says this explicitly. The assessment currently requires keeping the page open; refreshing loses the local answer draft. Timeout freezes answer edits, and failed submission can be retried. Late submissions still produce practice feedback but do not enter the baseline. Server-enforced proctoring and resumable assessment drafts are separate future improvements.

## Evidence and college limits

The rules reuse practice-engine evidence over the latest 500 submitted responses, deduplicating questions, and avoid inferring weakness from too few answers. First-exposure timestamps exclude repeats from checkpoints. No LLM, national rank derived from platform rating, inferred prerequisite graph or invented marks-gain coefficient is used.

College scenarios use the existing imported historical marks/percentile and CRL data. Values outside supported interpolation ranges remain unavailable. College rows include institute, program, reference year, counselling round, quota, seat type and gender pool.

The roadmap deliberately requests **All India / CRL / Gender-Neutral** comparisons only. Institute-state mappings, category rank data and verified eligibility are not available in this schema; HS/OS and category-specific recommendations must not be guessed. The page states these exclusions. Empty results do not imply no admission options. College choices are personal aspirations and guide the displayed historical benchmark; they are not eligibility claims. If none has applicable data, the rank goal stays unavailable. Marks and college modes are mutually exclusive.

Before expanding admission coverage, import verified institute state-of-eligibility mappings and category-specific rank inputs, collect relevant student eligibility details, validate data completeness, and add matching tests. Broader growth forecasts require longitudinal validation against held-out assessments and actual student outcomes.

## Validation

Backend tests cover saved-plan persistence, validation, ownership isolation, balanced paper construction, lack of answer leakage, numerical negative marking, baseline expiry by submission duration, fresh-pool exhaustion, repeat-proof checkpoints and exclusion of unresolved state/category pools. Existing auth, practice, rewards and ranking suites remain applicable. Frontend production build and existing request-cache/timing tests are required.
