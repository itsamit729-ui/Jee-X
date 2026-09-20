# Official JEE syllabi — 2026

Verified on 20 September 2026 from the official examination websites. These are **2026 editions**, not a claim that the 2027 syllabi have been released or remain unchanged.

| Exam | Official source | PDF pages | Subject start pages (1-based) |
|---|---|---|---|
| JEE Main 2026 | [NTA syllabus PDF](https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2025/10/202510311323551056.pdf), linked from [JEE Main](https://jeemain.nta.nic.in/) | 17 | Mathematics 1; Physics 3; Chemistry 7 |
| JEE Advanced 2026 | [Official syllabus PDF](https://jeeadv.ac.in/documents/jee-advanced-2026-syllabus.pdf), [official site](https://jeeadv.ac.in/) | 16 | Chemistry 1; Mathematics 9; Physics 13 |

JeeX's engineering scope is JEE Main Paper 1 (B.E./B.Tech.) and the Physics/Chemistry/Mathematics syllabus for Advanced. NTA's full PDF also contains Paper 2A (B.Arch.) and Paper 2B (B.Planning). The Advanced document explicitly says the 2026 syllabus is unchanged from 2025.

## App access

Open `/syllabus`; no login is required. Signed-in users can use the **Syllabus** navigation item. The page opens the complete, authoritative PDF rather than substituting a shortened topic summary.

The machine-readable source registry is [`frontend/src/data/officialSyllabi.json`](../../frontend/src/data/officialSyllabi.json). It holds exam IDs, years, publisher names, verified URLs, page counts, and subject-page references. These source references are separate from the existing practice question catalog; no existing question links, chapter IDs or student progress are changed.

## Optional local PDF copies

Direct PDF downloads were unavailable in the implementation environment. **PDF binaries are not bundled in this release.** To download unmodified copies into this repository from your own machine, run from the repository root:

```bash
python backend/scripts/download_official_syllabi.py
```

The standard-library script downloads to `docs/syllabus/2026/`, checks the PDF signature, and records URL, download time, byte count and SHA-256 in `downloads.json`. It writes each PDF atomically and will not overwrite an existing file unless `--overwrite` is provided. Review the PDFs against the source registry before committing them. The app continues to link to the official originals.

## Updating the year

Follow each authority's official syllabus link, confirm the year **inside the PDF**, and update the source registry, page shortcuts, README and app edition label together. Check all three subject start pages. Retain earlier source metadata in version control. Do not infer Main coverage from Advanced or silently reuse 2026 as 2027. The original PDFs and official corrigenda take precedence over any app taxonomy.
