# Teacher paper language and conversation state

The AI paper creator remains optional. It uses the published question bank and
produces the saved paper and OMR downloads as soon as the required details are
present. Exam, count, scope and duration are required; marking, difficulty and
sets use the existing defaults. The manual creator is unchanged.

## Editable mappings

`backend/app/services/teacher_paper_mappings.json` contains ordinary term aliases
and chapter aliases. Chapters target a **subject and stable chapter slug**, never
database IDs. Both chapter names and slugs from the current visible, published
bank are also recognized automatically. The file is included in the backend
Docker image; changes take effect after redeployment/restart.

For example:

```json
{"subject":"PHY", "slugs":["laws-of-motion"], "aliases":["nlm", "newton's laws"]}
```

Multiple `slugs` describe alternate names for the same chapter across imports.
If several live chapters match an alias, the teacher is asked to disambiguate.
An alias cannot create a chapter, cross an exam boundary, expose a private
question, or make unpublished questions available. Do not map a narrow subtopic
to a broader chapter: the present selector filters chapters, not subtopics.

Typo matches are suggestions requiring a reply. Unknown topics get a catalog
follow-up, including when another topic in the same request is valid. Missing
required fields are included in the follow-up. No silent fuzzy substitution is
performed.

## Structured follow-ups

The UI sends only the latest reply and the `conversation` returned by the last
successful follow-up response. Textual slots keep exam, count, quotas, scope,
duration, difficulty, marking, sets, type, source, reference and title separate.
An explicit correction replaces its field. Other fields and unfamiliar
constraints are preserved. For example:

1. `Make two JEE Main Physics questions on electrostatcs, no negative marking.`
2. The creator suggests Electrostatics and also asks for the duration.
3. `Electrostatics` fixes the topic; `make it three questions` updates the count.
4. `10 minutes` completes the request and returns the downloads.

An unrelated reply creates nothing and leaves the existing fields intact. Bare
numbers are accepted only when the prior follow-up unambiguously asks for count
or duration; otherwise the teacher is asked to include the unit.

Conversation state is bounded, schema-validated **request data**, not an approved
plan. It carries no database IDs or permissions. The server re-resolves it
against the authenticated teacher's current catalog and validates the final
selection. It does not add a database migration, new secret, or new environment
variable. Older API clients can still submit their conversation as prompt text.

Standard requests, missing-field collection, aliases, typo suggestions and
unrelated input do not require Groq quota. PYQ/source filters and simple requests
for questions from a year also run locally. More complex interpretation still uses
the configured Groq model with the existing token, timeout and rate limits.
This is not a guarantee of arbitrary natural-language support: unsupported
constraints must be clarified rather than silently discarded.

## Regression checks

Add an endpoint conversation to `backend/tests/test_teacher_conversation.py`
when adding a new mapping or correcting a reported failure. The suite disables
the AI key and fails on unexpected provider calls, checks actual selected bank
questions, and verifies paper/OMR completion. Run from the repository root:

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_teacher_conversation.py backend/tests/test_teacher_short_requests.py backend/tests/test_teacher_ai.py -q
```
