# Image questions

Three adapted Physics / Current Electricity questions are included in
`generated/questions/physics/current-electricity-images.json` (refs PHY-CUR-IMG-001–003).
They are single-correct practice questions, not previous-year JEE questions.

## Source and attribution

OpenStax, *College Physics*, section 21.1, Examples 21.1–21.3, as distributed by
BCcampus under CC BY 4.0: https://pressbooks.bccampus.ca/collegephysics/chapter/resistors-in-series-and-parallel/
License: https://creativecommons.org/licenses/by/4.0/
Wording was shortened into MCQs, distractors added, and diagrams redrawn as local SVGs.
Source and license appear in the preview, SVG metadata and question JSON.
Answers: 0.600 A; 0.804 Ω; 1.61 A (A, B, C).

## Preview and deployment

After the frontend deploys, open `/image-questions`. This public practice preview
works without database import and does not record marks, rewards or ratings.
Only these three practice answers are included in its client bundle.

To add the questions to the live question bank, deploy the frontend assets and
backend changes, then run from the repository root in the backend environment:

```sh
python backend/scripts/import_image_questions.py
```

The command uses the existing DATABASE_URL and importer, upserts by ref, and can
be rerun without duplicates. No schema migration is needed. A Git push does not
run this command automatically. The records are marked published; subject tests
under Physics → Current Electricity can select them randomly after import.
Existing attempts and ranked contest snapshots are not rewritten.

## UI and API

The optional `assets` array (url, alt_text) is returned in subject and daily
question responses. Ranked contests already snapshot these fields. All three
screens now share QuestionAssets: question text → responsive diagram → options.
Expand opens a native modal (Escape closes it); failed images show the description
and a Retry button. Older questions with no assets render as before.

Local image URLs start with `/question-images/` and resolve on the frontend host.
External HTTP(S) assets remain supported. SVGs are served as images, never injected
as HTML. The separate generated full-mock question set is unchanged.

## Verification

Validated all three answer keys, image XML, question metadata, Pydantic asset
serialization (including legacy empty-asset defaults), Python compilation, and
JavaScript/JSX parsing. A production frontend build and browser interaction test
were not run: dependency downloads were unavailable and no browser executable
was installed. Live database import and deployment have not been performed.
