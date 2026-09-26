# College information cards

Recommendations in Roadmap and RankPredictor use the same accessible information card. Hover, focus or tap the info button to load it; Enter/ArrowDown moves keyboard focus into the card. Escape, Close and outside clicks dismiss it. Cards show available college context, notable alumni and source links. Available package figures are shown with their year, scope and source. Missing metrics, missing-data messages and empty sections are omitted. Requests are deduplicated and cached in browser memory for ten minutes; there is no live scraping on student requests.

## Sources and coverage

`backend/app/data/college_insights.json` now contains **121 institutes and 174 placement records**, covering every IIT and NIT in the 138-institute catalog. `docs/college-salary-coverage.json` audits all 138 institutes and identifies the 17 for which this collection found no usable dated salary statistic. This is source coverage, not proof that unpublished outcomes do not exist. Missing metrics and empty sections stay absent from the student UI.

Sources include 66 downloaded official NIRF institution submissions, institute placement pages and brochures, and attributed reporting from Shiksha, Careers360, College Pravesh, Collegedunia, Indian Express and Times of India. Student reviews, advertisements, estimated packages and parent-campus substitutions are excluded. Secondary sources are labelled by publisher rather than presented as official institute reports. Historical figures retain their actual reporting year. In-progress reports retain snapshot notes where available.

Highest CTC, average CTC and median annual salary remain distinct metrics. NIRF records use the **graduation cohort year**, not the publication year. Four-year UG, five-year UG, architecture, planning, integrated postgraduate and two-year postgraduate cohorts have separate labels. These appear as college context for any selected programme; they are never assigned to its branch. University-wide submissions are explicitly identified, and IISc’s historical UG cohort is noted as predating the first B.Tech graduating class. Postgraduate-only salary context is clearly labelled as postgraduate outcomes.

Branch matches still require an exact institute and full JoSAA program title. B.Tech overall figures are matched only to four-year B.Tech selections; other degrees can still see those reports as explicitly labelled college context. No statistics are copied between campuses or merged across years. The API preserves each cohort’s latest available report. Cards round LPA for readability while the stored values retain precision.

### Reproducing NIRF extraction

`docs/college-salary-nirf-sources.json` records exact institute mappings, source URLs and SHA-256 hashes. With Poppler installed:

```sh
python scripts/collect_nirf_salary_context.py --cache-dir /tmp/nirf-sources --output /tmp/nirf-candidates.json
```

The collector downloads public reports outside student requests, checks hashes and extracts median salary candidates with source rows for review. Changed PDFs fail for manual review. It writes candidates only, not the serving bundle or database. Inspect cohort labels and source tables before merging candidates into `college_insights.json`; NIRF salary is not average CTC. No scheduled scraping is added.

## Database lifecycle

The `college_insights` table stores one JSON profile per institute, a content hash and update timestamp. Startup creates the table and the existing serialized background reference importer calls `sync_insights` after importing the catalog. Updates are idempotent and only changed records are written. `AUTO_IMPORT_PREDICTOR_DATA=false` disables this automatic step too. No production database credentials are needed by the browser.

After checking a new official source, update the bundle and its `verified_on` date, run the tests, and deploy. A manual sync is available with the deployment's database connection:

```sh
PYTHONPATH=backend python scripts/import_college_insights.py
```

The catalog must already be imported. Run one manual importer at a time. The authenticated GET `/api/colleges/insight` checks that the requested branch belongs to the institute. If startup import is still running, it can serve a catalog fallback. Imported data is retained in the database; no API request downloads external pages.
