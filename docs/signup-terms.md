# Signup terms and privacy notice — 11 October 2026

The user-facing documents live at `/terms` and `/privacy` (source: `frontend/src/pages/Legal.jsx`). Both are accessible without signing in and have a Print / save as PDF action. Signup links open in a new tab so entered form values remain intact.

## Acceptance flow

Email signup requires the current document version, age band and explicit unchecked acceptance. Under-18 signup additionally requires a declaration made by the parent/legal guardian, not simply a student claiming permission. The backend rejects missing, outdated or declined acceptance and under-18 submissions without that declaration.

New Google accounts receive a pending acceptance record and must finish `/signup/terms` before using onboarding or protected study APIs. Authentication, sign-out and acceptance remain available. Google supplies the account email and subject identifier before this terms step. Existing accounts remain usable; historical acceptance is not fabricated. Explicitly connecting Google does not change an account's acceptance.

`auth_terms` stores account ID, version, age band, accepting role and UTC acceptance time. `guardian_declaration` means a declaration only, never verified identity. Repeated acceptance does not overwrite the original record. Startup creates this additive table through existing SQLAlchemy metadata; no existing question or account columns are altered. Existing table-creation privileges are required. Existing accounts are left unaffected. Future material revisions need a versioned re-acceptance migration; changing the page alone does not implement that workflow.

## Owner information still needed

The public account/privacy contact is `admin@jeeedge.in`, as supplied by the owner. `VITE_SUPPORT_EMAIL` can override it at build time. Founder names are intentionally not published at the owner’s request. The legal operator identity remains unresolved; `Jee Edge team` is not represented as an incorporated entity. If later supplied, set `VITE_LEGAL_OPERATOR_NAME` to the actual legal operator and rebuild. They are public, not secrets. No operator identity or email has been invented. The operator section is omitted until supplied; the legal notice still needs owner completion and review. The operator must actually handle correction, deletion, withdrawal and complaints before publishing the corresponding contact wording. Retention/deletion policy and backups also need operational review; no automated deletion period is promised by these documents.

## Important limits for a minors-focused service

This is a plain-language terms implementation, not legal clearance or a verified-parental-consent system. A checkbox and age-band declaration cannot verify an adult's identity or guardianship. Google verification proves control of the Google identity, not age or parental authority. Obtain India-qualified legal review of the documents and actual data practices. Add a suitable verified-parent flow before processing children's data where required; the current Google callback already processes minimal account data before the acceptance page.

Existing student profiles and rated-contest history remain public. The notice deliberately describes that reality. Optional activity visibility is separate. Review privacy-by-default and public rankings for children, as well as behavioural tracking, recommendations, service providers, retention, contact/rights handling and any advertising before describing the whole service as suitable or legally compliant for minors.

Sources reviewed:
- Indian Contract Act 1872, section 11 (capacity): https://www.indiacode.nic.in/bitstream/123456789/2187/2/A187209.pdf
- Final Digital Personal Data Protection Rules 2025, rules 1 and 10: https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf

The final rules have phased commencement; rules 3, 5–16, 22 and 23 commence eighteen months after publication, not all on publication day. Review the Act's separate commencement notifications and any later amendments with counsel. No educational exemption is assumed.
