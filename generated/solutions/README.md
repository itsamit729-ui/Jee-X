# Generated solutions (not yet published)

Worked solutions produced by `solution-pipeline/` (Claude Code, Opus 5.5 solver + checker). Nothing here is in the database until `solution-pipeline/pipeline/publish.py --apply` is run; only results with `"verdict": "verified"` are ever published.

| Folder | What | Verdicts |
|---|---|---|
| `pipeline-results/` | First pipeline batches: 25 JEE Main 2026 chemistry questions + 4 earlier test questions | 26 verified, 3 flagged |
| `pipeline-results/preview.html` | All of the above rendered like the app (open in a browser) | |
| `runs/calib-opus/` | Model calibration: 25 mixed questions (9 physics, 8 chemistry, 8 maths; 10 numerical, 10 MCQ, 5 with figures) | 24 verified, 1 flagged |
| `samples/` | Question lists used for the calibration runs | |

Each `<ref>.json` holds the final `solution`, the `verdict`, every attempt (answer, checker verdict and issues, recomputed calculations) and the token use of every Claude call.

Flagged questions (need a person, never published):
- `PYQ-MATH-c040a14493cf` (key_mismatch): the key says 11, the correct answer is 6 (the circle needs $r^2 > 0$).
- `PYQ-CHEM-69229726df9c` (key_mismatch): the source question text is truncated ("goes to 60 ___"); fix or retire the question.
- `PYQ-CHEM-8bb2786269d7` (key_mismatch): counting secondary alcohols in a small, ambiguous structure figure.
