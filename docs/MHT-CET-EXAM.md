# MHT CET mock interface and college outlook

The dedicated PCM screen appears only for MHT CET shift mocks. Other exams keep their existing UI.

- 90 minutes Physics/Chemistry, then 90 minutes Mathematics. The first group locks at the boundary.
- Save & Next and Mark for Review & Next commit a choice. Saved review answers count; unsaved choices do not.
- Clear Response removes a saved response. A colour-and-text question palette tracks visited, unanswered, answered and review states.
- Final timeout submits saved answers; failed submissions can be retried. Exiting or reloading currently ends the local session.
- UI timing and locks support unranked practice, not a proctored or server-enforced examination.
- Reconstructed English questions and incomplete papers are labelled; original order and translations are not supplied.

Timing and scoring source: State CET Cell MHT CET 2026 information brochure, section 7.3:
https://cetcell.mahacet.org/wp-content/uploads/2023/12/AGRI_MHT_CET_2026_IB.pdf

## College outlook after mocks

Each submitted MHT CET mock shows raw score and a percentile scenario form. The student enters
an actual or assumed percentile; **no raw-mark-to-percentile conversion is performed**.
The JEE prediction API explicitly rejects MHT CET and BITSAT to avoid using JEE normalization.

Historical reference: official 2025 CAP Round I Maharashtra cutoff document:
https://fe2025.mahacet.org/ViewPublicDocument.aspx?MenuId=2449

`backend/data/mht_cap_2025_r1.json.gz` contains 25,454 regular Stage I G/L cutoff entries
across 362 institutes and 2,133 choice codes. Institute/program maps may contain additional
source headings without eligible extracted rows. Data was extracted on 2026-10-11.
Each row retains institute code, choice code, seat code, percentile, state merit rank and PDF page.
Only ordinary home-to-home, other-to-other and state-level allotments are included.
Minority, special reservations, conversions, later allocation stages and suffixed choice codes are excluded.
Results match the exact category, quota and gender pool chosen. The student must verify eligibility;
meeting a historical cutoff does not imply admission. Empty and partial coverage are stated.

Rebuild with `pdftotext -layout source.pdf source.txt`, then
`python backend/scripts/extract_mht_cutoffs.py source.txt backend/data/mht_cap_2025_r1.json.gz`.
The official document viewer embeds the PDF as base64. The extractor rejects duplicate choice/seat
pairs and invalid percentiles. Tests verify a source anchor, filtering and pagination.

No database migration or question re-import is required for this change.
