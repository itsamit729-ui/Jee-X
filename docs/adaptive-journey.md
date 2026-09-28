# Adaptive goal journey

Roadmap and Recommendations share `/api/roadmap/journey`. The full roadmap embeds the same object. It shows the student's marks or college goal, observed assessment baseline/range, seven evidence-based milestones, priority chapters, and recent plan revisions. Recommendations reserve support slots for priority chapters while retaining revision and exploration. Each question records the milestone and its role alongside its existing recommendation reason.

## Evidence rules

These are conservative initial product heuristics, not a validated forecast model:

- Skill evidence uses first-exposure correct/wrong answers from the recent 500 submitted response records, within 45 days. Repeated answers cannot manufacture mastery. Skips do not count as correct/wrong evidence.
- Foundations require 8 fresh answers with at least 70% accuracy over 2 distinct days, in at least one chapter per subject. This is a starter checkpoint, not full-syllabus mastery.
- Application requires 12 fresh questions at internal difficulty 4+, 70% accuracy, 3 chapters and 2 days.
- Fluency requires 12 correct timed answers over 3 chapters and 2 days, with median active time no more than 1.3 times the question's expected time. It is a pacing indicator, not exam-time measurement.
- Retention requires the foundation sample and at least 4 fresh questions 3+ days later at 75% accuracy, in one chapter per subject.
- Exam evidence uses the existing server-scored, fresh, balanced 75-question roadmap assessments only. Legacy client-reported summaries cannot create score readiness. Three assessments on separate days within 45 days establish an observed score range, not a future forecast.
- A marks goal requires all three recent assessment scores to meet the target. College goals retain their historical category/rank/eligibility benchmarks and are never marked as guaranteed admissions.

## Persistence and updates

The existing `student_roadmaps.plan` JSON stores `journey`, its first-achieved milestone dates and the last eight meaningful revision entries. No schema migration is needed. Goal changes reset the goal-specific achievement while keeping prior skill achievements. Stale or weaker evidence triggers a recheck without erasing first-achieved dates.

Reconciliation occurs when the student opens either plan or starts a practice session. This captures all submission routes without adding work or failure dependencies to grading. It serializes on the student's existing user and roadmap rows; repeated reads do not duplicate revisions. The results page requests a fresh journey after successful submission. No background job or external model call is involved.

The weekly schedule refreshes after three new submitted sessions with question-level responses or seven days. A small individual test updates evidence immediately but does not rebuild the weekly schedule. Previous weekly checkpoints are archived in the existing bounded history. Without a saved goal the journey remains a preview; the student is invited to save a marks target or up to three college/branch choices.

Only operator-configured examination dates are shown. The full milestone sequence remains visible when the exact date is unknown; no exam date or milestone finish date is invented. The next seven days remain actionable and later work stays flexible.

## UX

The full roadmap prioritizes the journey and places detailed weekly schedules, score details and history in expandable sections. Recommendations show a compact goal/current-step panel and preserve the practice builder. After a test, students see evidence changes and a link to the updated roadmap. Subject filters, native accessible disclosure controls, keyboard focus styles and mobile single-column layouts use the existing charcoal/orange palette.


## Interactive journey map and missions

The primary view is now a responsive route map with seven selectable stops. Native buttons expose selection and current-step semantics; an adjacent inspector explains each stop. The map shows learning evidence rather than admission probability. Saved college destinations can be switched to inspect their own historical rank-list benchmarks without mutating the student's goal. Mobile places today's mission before the map; reduced-motion preferences disable arrival animation.

A mission starts up to eight questions in a 15-minute suggested session with one click. Roadmap launches the server-backed session and transfers its response through temporary router state, which is cleared after consumption. Recommendations can start the same mission in place. Explicit subject/chapter selections take precedence over the inferred priority. Full assessments remain a separate, clearly labelled three-hour action. Launch errors stay visible and do not erase the map. The custom practice builder is expandable.

The post-test update appears before the route; optional rank/college references are expandable. A saved starting snapshot records milestone count and foundation chapter IDs on first use of this view. Later views show newly evidenced foundation chapters and the current milestone count against this snapshot. Assessment comparisons show the earliest and latest available server-scored balanced checkpoints (up to six); both dates remain visible and at least two distinct days are needed. They are observed scores from potentially different-difficulty papers, not forecasts or a claim about the student's first-ever assessment. No percentage-to-admission metric is created.
