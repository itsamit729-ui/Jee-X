# College information cards

Recommendations in Roadmap and RankPredictor use the same accessible information card. Hover, focus or tap the info button to load it; Enter/ArrowDown moves keyboard focus into the card. Escape, Close and outside clicks dismiss it. Cards show available college context, notable alumni and source links. Available package figures are shown with their year, scope and source. Missing metrics, missing-data messages and empty sections are omitted. Requests are deduplicated and cached in browser memory for ten minutes; there is no live scraping on student requests.

## Sources and coverage

`backend/app/data/college_insights.json` contains reviewed facts and HTTPS source links for each profile, placement record and alumnus. The expanded bundle includes **15 institutes and 37 placement records**, with package coverage for MNNIT Allahabad, NITK Surathkal, NIT Trichy, NIT Rourkela, IIITDM Kancheepuram, NIT Hamirpur, NIT Patna, NIT Calicut, NIT Kurukshetra, NIT Uttarakhand, IIIT Vadodara, IIIT Dharwad, IIIT Sri City, NIT Durgapur and VNIT Nagpur. Coverage can be branch-only, undergraduate-wide or institute-wide; not every branch has its own report. Remaining catalog institutes receive concise catalog profiles. Unavailable details are omitted from the UI.

The September 2026 collection uses official placement pages and institute brochures. Each record retains the source URL, reporting year and relevant snapshot date or historical caveat. NIT Trichy’s available ICE and Mechanical records are historical (2021 and 2021–22); they are not presented as current outcomes. NIT Durgapur’s 2025 homepage supplies the highest package only. IIIT Sri City’s branch averages are separate from its overall maximum. Conflicting reports and ambiguous branch-name aliases were not merged.

Match placements only by exact institute and full JoSAA program title. Never apply B.Tech results to dual degrees, apply one department's results to another, or relabel institute-wide results as branch-specific. Store CTC in INR lakh per annum, preserve report year and scope, and leave unpublished/unverified metrics null. Cards render only positive, finite package metrics. Branch, overall B.Tech, undergraduate and college-wide records are shown separately with explicit scope labels. College-wide totals can include multiple degree levels and are never labelled as a selected branch’s outcomes. Alumni descriptions use stable achievements or dated roles, not assumed current jobs. The API tracks source age for future maintenance; the card shows the source-check date when available.

## Database lifecycle

The `college_insights` table stores one JSON profile per institute, a content hash and update timestamp. Startup creates the table and the existing serialized background reference importer calls `sync_insights` after importing the catalog. Updates are idempotent and only changed records are written. `AUTO_IMPORT_PREDICTOR_DATA=false` disables this automatic step too. No production database credentials are needed by the browser.

After checking a new official source, update the bundle and its `verified_on` date, run the tests, and deploy. A manual sync is available with the deployment's database connection:

```sh
PYTHONPATH=backend python scripts/import_college_insights.py
```

The catalog must already be imported. Run one manual importer at a time. The authenticated GET `/api/colleges/insight` checks that the requested branch belongs to the institute. If startup import is still running, it can serve a catalog fallback. Imported data is retained in the database; no API request downloads external pages.
