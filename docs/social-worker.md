# Separate publishing from the student web service

The main website can now forward all `/api/social/*` and `/api/admin/social*`
operations to a standalone publisher. In external mode it does not import the
social renderer, synthesize narration, start publication jobs, reconcile Buffer
posts, or process Instagram comments. Browser Admin sessions are checked on the
main website before requests reach the worker.

The publisher serves media, generates Reels/carousels, prepares Shorts, checks
quotas/delivery and handles comment webhooks. It exposes no student/teacher APIs,
frontend, admin login or predictor import. Its smaller image omits Node, OpenCV,
PDF libraries and the college reference bundle. Existing tables and post IDs are
reused; there is no media migration or change to the content schedule.

## Deploy the publisher first

1. Create a separate Docker web service from `feature/version-1`, using
   **Dockerfile.social**, repository root context, and `/health` as health check.
   Alternatively create a separate Blueprint using **render-social.yaml**.
   Do not replace the existing website with the worker Dockerfile.
2. Use the same `DATABASE_URL` as the current website. Copy its database TLS CA to
   the worker's Secret Files and set `DB_SSL_CA=/etc/secrets/ca.pem` as on the web
   service. The worker initializes only `social_*` tables.
3. Create a new random `SOCIAL_RELAY_SECRET` (at least 32 characters) and store it
   in the worker's environment. This is separate from the cron trigger secret.
   A local generation command is:
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   Do not put secret values in git or frontend environment variables.
4. Copy the current publishing configuration to the worker:
   - Required: `SOCIAL_TRIGGER_SECRET`, `BUFFER_API_KEY`.
   - Keep the existing `SOCIAL_DAILY_TARGET`, `SOCIAL_REELS_PER_DAY`,
     `SOCIAL_PAUSED`, `SOCIAL_TTS_ENABLED`, `SOCIAL_LOCAL_TTS_ENABLED` values.
   - Optional editorial/narration: `GROQ_API_KEY`, `GROQ_MODEL` and any existing
     speech configuration.
   - If comment replies are enabled: `SOCIAL_COMMENTS_ENABLED`, `IG_ACCESS_TOKEN`,
     `IG_ACCOUNT_ID`, `IG_APP_SECRET`, `IG_WEBHOOK_VERIFY_TOKEN`, `IG_GRAPH_VERSION`
     and `GROQ_API_KEY`.
5. Set `SOCIAL_MEDIA_ORIGIN` to the worker's public HTTPS origin, for example
   `https://YOUR-PUBLISHER.onrender.com`. With no explicit override the worker
   uses its own `RENDER_EXTERNAL_URL`. Do not copy the old main-site media origin.
6. Deploy and open the worker's `/health`: it must return `service: publisher`.
   Deploying it does not start a schedule or publish anything by itself.

Do not run two separate cron schedules. Shared checkpoints protect existing slots,
but only one scheduler should control the account.

## Switch the website after the worker is healthy

Add these environment variables on the existing main website:

```text
SOCIAL_EXECUTION_MODE=external
SOCIAL_WORKER_URL=https://YOUR-PUBLISHER.onrender.com
SOCIAL_RELAY_SECRET=<same new secret as the worker>
```

Redeploy the website. Its `/health` must show `social_execution_mode: external`.
Admin publishing controls retain their existing URLs. They use a dedicated relay
credential; browser cookies and Admin session bearer tokens never leave the main
service. Public media streams preserve HEAD/range requests and are not buffered
as complete videos on the main service. New media URLs point straight to the worker.

Update the existing external cron destination to:

```text
POST https://YOUR-PUBLISHER.onrender.com/api/social/trigger
Authorization: Bearer <existing SOCIAL_TRIGGER_SECRET>
```

Keep the existing interval/timezone. Calling the old main-site cron URL also
works via the gateway, but unnecessarily wakes both services. The current Meta
webhook URL also continues to work; it can later point directly at the worker's
`/api/social/comments/webhook` using the existing Meta verification/signature setup.

Verify without generating another post:
- Main `/health` reports external; worker `/health` reports publisher.
- Open Admin social status and check existing Instagram/YouTube IDs and jobs.
- Fetch a known media URL on each origin; test a HEAD and byte-range request.
- Use the read-only `/api/social/status` endpoint with the existing trigger token.
- Let the next normal cron run process its existing slot; do not submit extra
  manual tests while diagnosing a post with an uncertain delivery outcome.

After verification the main website no longer needs Buffer/Groq/Instagram API
credentials. Keep the relay secret on both services. Missing/invalid external
configuration fails closed; there is no automatic fallback to local rendering.
The gateway never retries a timed-out publication request. Check the existing job
on the worker before retrying because it may already have accepted the request.

## Deployment compatibility and rollback

Until the worker URL is configured, the existing embedded publisher continues to
work. This keeps a code deployment from stopping current publishing before the
new service exists. Setting the worker URL selects external mode automatically;
setting `SOCIAL_EXECUTION_MODE=external` explicitly is recommended for clarity.

For rollback, restore any moved provider credentials, set the main site to
`SOCIAL_EXECUTION_MODE=embedded`, and move the single cron back to its old URL.
Allow active jobs to finish before switching. Do not delete shared checkpoints,
media or existing Buffer posts. Disable the worker cron before resuming embedded
publishing. Existing Buffer media URLs on the worker must stay available until
pending deliveries are confirmed.

## Hosting limits and cost

The Blueprint uses a Free service for a trial, not an assumption of unlimited
free capacity. Render gives a workspace **750 shared free instance hours/month**.
Two services kept awake continuously exceed that budget and can cause **all** Free
services to be suspended until reset. Track the workspace's total usage; direct
cron calls to the worker avoid keeping an idle student website awake.

A worker outside that shared allowance, or an appropriately sized paid worker,
is needed if both services must stay online continuously. The separation itself
does not make FFmpeg cheaper or remove the worker's own CPU/RAM limits. Keep one
worker process and the existing render concurrency/quota controls.

Reference: https://render.com/docs/free

## Buffer alternatives

The separation retains Buffer so existing delivery IDs, repairs and reconciliation
continue working. It does not silently replace a provider or recreate queued posts.

For a fully automated replacement, implement independent channel adapters:
- Instagram: Meta's official Instagram Content Publishing API, using the correct
  professional-account login flow and publishing permission. Requires your own
  Meta app/account authorization and token management.
- YouTube: the official Data API's `videos.insert` with channel OAuth consent,
  refresh-token handling and resumable uploads. Track the returned video ID and
  processing status; never count an upload acknowledgement as confirmed public delivery.

Each provider needs its own durable submission checkpoints and ambiguous-outcome
handling. A provider migration must preserve the existing Buffer jobs until they
are delivered or explicitly resolved, rather than submitting the same asset twice.
Native YouTube Studio scheduling is another option for manually uploading videos;
it is not a drop-in API integration for the current automation.

Official documentation (checked 2026-10-16):
- https://developers.facebook.com/documentation/instagram-platform/content-publishing
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login
- https://developers.google.com/youtube/v3/docs/videos/insert
- https://support.google.com/youtube/answer/1270709

### Rendering capacity waits

The `render` ledger is this application's resource guard: 1,800 measured rendering
seconds per rolling 24 hours, with a 180-second reservation per new render. It is
not a Render hosting quota or provider billing report. Dispatch returns
`budget_wait` with `retry_after` calculated from expiring usage and does not use
an attempt while capacity is unavailable. Concurrent budget failures also restore
the claimed attempt. Prepared media can still publish without another rendering
reservation. Keep the cron running; polling rechecks capacity, without resetting
the ledger or increasing the resource limit. A retry time permits another attempt;
it does not guarantee a publishing time.
