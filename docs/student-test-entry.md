# Student practice and mock entry

The shared instructions screen enables Begin test when a nonempty paper is
loaded and the student acknowledges the instructions. There is no minimum
reading delay. The solving timer starts in the existing entry handler.
Instructions use the shared light surface and text tokens.

Screens using the shared fullscreen guard (subject practice, archived papers,
full mocks, the free diagnostic and the legacy mock interface) count actual
fullscreen-to-windowed transitions. Three exits show Resume test and Submit &
exit test. The fourth calls the existing submission flow automatically and
keeps the guard closed to further solving. A failed server submission keeps
answers in the current session and offers Retry submission. In-flight
submission is guarded against duplicate requests in the subject/mock flow.
MHT-CET submits saved answers, preserving its existing Save & Next semantics.

Duplicate standard/WebKit events are counted once. Unsupported or denied
fullscreen requests do not count as exits. This is a browser-side attempt
policy, not server-enforced proctoring; it does not count tab changes that
leave fullscreen intact. Classroom assignments and rated contests retain their
existing separate start/save flows.

Validation: npm --prefix frontend test; npm --prefix frontend run build.
Optional browser integration: from frontend, run
`node scripts/verify-student-fullscreen.mjs` with Playwright installed. Managed
installations can set PLAYWRIGHT_MODULE and CHROMIUM_EXECUTABLE. The browser
harness simulates fullscreen transitions to test React lifecycle and denial
handling; native browser/OS fullscreen behavior still needs device testing.
