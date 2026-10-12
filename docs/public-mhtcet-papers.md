# Public MHT-CET paper discovery

The combined Docker deployment serves `/mhtcet/papers` and individual paper pages directly from FastAPI. Content, canonical tags, descriptions and previews are present in the initial HTML. Existing React routes remain the signed-in workspace. No question bank is copied into a public static bundle.

The archive uses the existing published-question eligibility rules. Each available year/shift has a deterministic URL containing a readable shift and a short hash to prevent slug collisions. Missing papers return 404. Only three sample questions and their options/assets are rendered, without correctness flags or solutions. The mock creation endpoint continues to require a valid session, accepted terms and CSRF validation.

`/sitemap.xml` is generated from the current catalogue, plus existing public routes, before the SPA fallback. It updates when eligible papers are imported. The sitemap in frontend/public remains a fallback for standalone frontend hosting; full public paper pages require the combined backend deployment.

## Attribution

Share `/mhtcet/papers?utm_source=teacher` or an individual paper URL. Supported sources: teacher, google, youtube, instagram, whatsapp, telegram, direct; other values are grouped as other. Google and YouTube referrers are classified when available. Links preserve the source through paper selection and sign-in.

The admin dashboard's Public paper traffic panel reports the last 30 days: browser-reported views and continue clicks, and server-recorded successful mock starts. These are event counts, not unique people; repeated visits and blocked JavaScript affect them. No email, IP address, device identifier or referrer URL is stored in these counters. They are approximate acquisition metrics, not billing data.

`acquisition_counts` is a new independent aggregate table created by the existing `Base.metadata.create_all` startup. No existing question or account columns change. Mock-start counters are committed with the attempt. Other counters are best-effort browser requests.

## Sign-in

The CTA carries the exact year, shift and source to `/pyq`. Existing auth/terms/onboarding return URLs preserve it. The selected mock is shown prominently after sign-in; the student clicks Start to begin the timer. A 30-minute browser-local paper destination also handles email verification in a new tab on the same browser. Verification on a different device requires returning to the original paper link.

## Build and verification

Vite builds a small second entry for math rendering and attribution. FastAPI reads its production manifest and dependency CSS. All content and navigation work without JavaScript; math enhancement and view/click counters need it.

- `cd frontend && npm test && npm run build`
- Backend: `pytest backend/tests/test_public_papers.py backend/tests/test_mht_cet.py -q`
- After deployment, open `/mhtcet/papers`, preview an available paper, and verify its title/content in View Source. Test sign-in and starting that selected mock. Confirm `/sitemap.xml` contains its canonical URL.
