# Category-aware NIT and college matching

## Data provenance and coverage

The repository already contains official-source JoSAA snapshots under `docs/JEE-Predictor-Data/jee-predictor-data`: 2025 round 6 (11,945 source records) and 2026 round 5 (12,936 source records), retrieved September 19, 2026. The official current opening/closing-rank page was checked again during this change and still exposes rounds 1–5. Snapshot retrieval dates and hashes have not been relabelled as a fresh full scrape.

Sources:
- https://josaa.nic.in/or-cr/
- https://josaa.admissions.nic.in/Applicant/SeatAllotmentResult/currentorcr.aspx
- https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx
- https://cdnbbsr.s3waas.gov.in/s313111c20aee51aeb480ecbd988cd8cc9/uploads/2026/06/20260601632081678.pdf

A complete local import of all 11 reference files produced 26,133 rows across reference tables, including 24,880 usable cutoff rows. One source row lacks usable matching fields and is skipped by the existing importer. Repeating the import added/updated zero rows. Included rank lists: CRL, EWS, OBC-NCL, SC, ST and each corresponding PwD list. Source hashes are validated against the existing manifest before writing.

## Database deployment

The database credentials are not present in the development workspace; no direct live-DB write has been claimed. The server now imports bundled reference data using its own configured DATABASE_URL at application startup:

- Docker copies the reference bundle into `/app/predictor-data`. Native repository deployments resolve the docs path. `PREDICTOR_DATA_ROOT` can override it.
- Import runs in a background thread; public health/read requests are not blocked waiting for data.
- A MySQL named lock serializes overlapping workers/deployments. Successful file hashes in `predictor_import_runs` prevent repeat work.
- Each file has its own transaction. A failed/interrupted file rolls back and can be retried on the next restart.
- Existing rows are upserted by natural keys, never truncated or deleted. Institute and program dimensions are preloaded/created in batches.
- `AUTO_IMPORT_PREDICTOR_DATA=false` disables automatic import if the operator prefers the CLI.
- `GET /api/roadmap/data-status` reports worker state and persisted cutoff row counts by year, without exposing configuration or credentials. On a worker that did not acquire the import lock, persisted counts are the cross-worker evidence of completion.

After deployment, verify that the status endpoint includes 2026 with 12,936 rows. Backend startup must be allowed to complete; this source-code push is not itself proof that a hosting rollout has finished. Failed imports log only the exception class to avoid revealing database credentials.

## Matching rules

Students still choose marks or up to three college/branch preferences. A separate admissions section collects category, Class XII **state code of eligibility**, optional female-only/PwD eligibility and optional actual JEE Main rank-list positions.

OPEN seats compare CRL. Reserved seats compare the matching category rank; PwD seats compare the relevant PwD rank. CRL is never converted to category rank. Marks-based scenarios produce CRL only. Missing category rank does not prevent browsing category cutoffs or choosing a category-specific college goal.

The 31 NIT mappings and quota rules are tied to the **2026** reference year (JoSAA clauses 8, 11 and 12). HS/OS is selected from state code of eligibility rather than residence. Explicit exceptions:

- NIT Goa: GO for Goa; HS for Lakshadweep and Dadra and Nagar Haveli and Daman and Diu; OS for other states.
- NIT Srinagar: JK for Jammu and Kashmir; LA for Ladakh; OS otherwise.
- NIT Delhi: Chandigarh also receives HS.
- NIT Puducherry: Andaman and Nicobar Islands also receives HS.

Unknown state, unknown institution-state mappings, and future-year quota rules fail closed for personal matches. Unresolved NIT examples may appear in the **historical cutoff explorer**, explicitly labelled as examples, not eligibility matches. State quotas for non-NIT institutions, foreign/special eligibility routes and CSAB supernumerary allocations are not inferred. AI rows remain available where applicable. The UI is not a full admission-eligibility adjudicator.

College targets retain separate rank lists. An SC closing rank cannot become a CRL target. Current matches may include both OPEN and category pools when the corresponding rank inputs exist. The UI shows quota, category, gender pool, rank list, year and round for every result.

## Verification

Tests cover 31-institute mapping, state and UT exceptions, missing/future-year fail-closed behavior, rank-list separation including PwD, persisted category preferences, invalid state rejection, actual NIT matches and target benchmarks, checksum rejection and import idempotency. The complete bundled dataset was additionally imported twice into a temporary SQLite validation database. Production MySQL execution remains to be verified through the deployed status endpoint.
