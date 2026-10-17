# Student test and results fixes — 18 October 2026

## Test screens

The shared SubjectTest practice/mock route uses TestSession instead of the site
header and narrow page card. Question codes remain in stored data but are not
shown during solving. Subject navigation, question count, timer and actions are
separate from the question-content scroll area. The palette stays beside the
question on desktop and opens as a panel on smaller screens. It no longer pushes
the question below a full-paper grid. Content resets to the top on question change.

Practice shows elapsed session time and visible/focused question time. Timed mocks
retain their deadline and automatic submission. Fullscreen exit policy and the
existing server grader remain in use. Multiple-correct options can be toggled
independently. MHT-CET keeps Save & Next, section locks and saved-answer grading,
with a viewport layout and a mobile question palette. Exceptionally long questions
still need vertical content scrolling; navigation/actions remain available.

JEE shift-paper construction groups Physics, Chemistry and Mathematics and puts
MCQs before numericals inside each subject. Saved TestQuestion positions define
the displayed, graded and reviewed order. Source reconstruction does not establish
original official question order within a section. Existing attempts are unchanged.

Math fragments no longer create horizontal sliders. Oversized formula groups are
fitted to the containing width after layout/font loading and on resize. Diagrams
retain the expand control. Mobile/device layout needs browser verification; build
and server-rendered tests do not establish the final appearance on every device.

## Result and dashboard flow

Successful SubjectTest submission navigates directly to the existing protected
/results/:attemptId?tab=questions route. Question-wise review lists every question,
answers, outcomes and available solutions. Show all questions & solutions opens
all disclosures; closed rows otherwise keep expensive maths/diagrams deferred.

The dashboard now includes submitted server-graded chapter practice, baselines and
full mocks as well as legacy attempts, scoped to the student. Incomplete attempts
and classroom assignments stay out of this personal-test summary. Fresh reads on
entry/focus and submission cache invalidation avoid an old progress snapshot.

JEE percentile, rank and college prediction is one combined automatic request.
The private in-memory result is reused for five minutes across view changes and
cleared on account changes and mutations. It is never persisted in browser storage.
Insufficient reference evidence still produces no estimate. MHT-CET retains its
actual/assumed-percentile CAP comparison: there is no calibrated MHT marks-to-
percentile reference curve in this repository, so it does not invent one.

## Selection, search and plans

Chapter selection has a searchable, keyboard-accessible panel with an All chapters
choice, counts and no-match state. Navigation, chapter and weekly-topic search use
normalized, token-based matching with subject abbreviations and reordered terms.
Weekly plans offer previous/next-week navigation, scheduled minutes and topic/
subject search instead of nested later-week disclosures. Full-mock return links
using ?mock=1 reopen the full-mock builder.
