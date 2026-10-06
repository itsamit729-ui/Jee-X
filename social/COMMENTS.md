# JeeEdge intelligent Instagram comments

## What is implemented

Signed Instagram webhooks persist comments in MySQL. The worker verifies the
comment/media owner, loads the exact saved lesson used for publication, reads a
bounded thread, and asks Groq to draft and independently review a public reply.
The same Groq free-tier ledger is shared with post generation. A saved draft can
resume at the review step if the minute quota runs out. No paid fallback.

Useful questions can receive concise lesson-grounded answers, wrong answers a
hint, and appreciation a brief acknowledgement. Spam/instruction attacks are
skipped. Ambiguous questions, reported errors, unsupported calculations, missing
lesson snapshots and rejected drafts are held for review. AI review reduces risk;
it is not a proof of mathematical correctness. There is no automated deletion,
liking, DM sending, or replying on someone else's posts.

Defaults: at most 6 reply reservations/hour, 30/day, 3/student/day, 1/student/post,
and no further automated answer once JeeEdge has already replied in a thread.
These are conservative operating limits, not claimed Meta quotas. Graph calls
are separately capped at 100/hour and 500/day. Two inbox items per worker run;
webhooks run the worker, and the existing publication cron recovers unfinished
work. No new cron is required. The service holds ambiguous POST outcomes rather
than resending. Expired pre-send leases can resume; stale send fences require
inspection. Provider authorization/rate-limit errors hold work without leaking
raw responses or access tokens into logs.

## One-time activation on the existing Render service

Buffer's publishing token is not a Meta comment-management token. Use **Instagram
API with Instagram Login**, for the @jeeedge professional account. This connector
uses graph.instagram.com, not the Facebook Login token flow.

1. In Meta for Developers create/configure an app with Instagram API with
   Instagram Login. Add @jeeedge as the account/tester and accept the invitation.
   Request `instagram_business_basic` and `instagram_business_manage_comments`.
   Complete the access/review requirements shown by Meta for your app mode and
   account roles. Merely adding an app does not guarantee production access.
2. Generate an Instagram User access token with those permissions and obtain the
   Instagram account ID shown by the API/app setup. Use a long-lived token;
   monitor expiry and refresh/replace it before expiry. Tokens are not refreshed
   automatically by this implementation. Never put credentials in Git or chat.
3. Set these Render environment variables:

| Variable | Value |
| --- | --- |
| `SOCIAL_COMMENTS_ENABLED` | `true` |
| `IG_ACCESS_TOKEN` | Instagram User access token with comment permission |
| `IG_ACCOUNT_ID` | Numeric Instagram professional account ID |
| `IG_APP_SECRET` | Secret for the Meta/Instagram app signing the webhooks |
| `IG_WEBHOOK_VERIFY_TOKEN` | Your own random secret, at least 32 characters |
| `IG_GRAPH_VERSION` | Supported version selected in the Meta app (for example `v26.0`) |

Existing `GROQ_API_KEY` and `SOCIAL_TRIGGER_SECRET` are reused. Deploy this commit.

4. Configure the app's Instagram webhook callback:
   `https://jee-edge.onrender.com/api/social/comments/webhook`
   Enter the exact `IG_WEBHOOK_VERIFY_TOKEN` as the verify token. Subscribe to the
   `comments` field. Complete account-level subscription in the Meta setup flow;
   if using the API, this is `POST /{IG_ACCOUNT_ID}/subscribed_apps` with
   `subscribed_fields=comments` and the same Instagram token. This is an account
   configuration step, not something the worker repeatedly changes.
5. Check authenticated `GET /api/social/comments/status`. It must show enabled
   and an empty `missing_configuration` list. That verifies local configuration,
   not token permissions. Comment from another account on a newly generated
   JeeEdge post, then check the inbox/status and confirm the reply on Instagram.
   Meta's sample webhook verification alone is not an end-to-end comment test.

The existing cron/authentication remain unchanged. New snapshots are saved before
Buffer publication. **Posts created before this deployment have no immutable
snapshot and are held for review**, rather than reconstructing potentially
changed questions from today's code.

## Operations and review

All of these endpoints require `Authorization: Bearer <SOCIAL_TRIGGER_SECRET>`:

- `GET /api/social/comments/status`: configuration, counts, latest 100 records.
- `GET /api/social/comments/inbox?state=review`: up to 50 review items. Use the
  returned `next_before` as the `before` query parameter for the next page.
- `GET /api/social/comments/inbox?state=needs_review`: uncertain send outcomes.
- `POST /api/social/comments/process`: request a bounded inbox run immediately.
- `POST /api/social/comments/{comment_id}/dismiss`: mark a pending/review item
  handled after inspecting/replying manually in Instagram. Does not publish.

Review is an authenticated API inbox; there is no new dashboard UI in this
release. Inspect the actual Instagram thread before handling a `needs_review`
record. Never reset a submission fence to force a second reply.
Set `SOCIAL_COMMENTS_ENABLED=false` to stop sending but keep receiving the inbox;
`SOCIAL_PAUSED=true` also pauses comment sending. Pending items older than two days
are held for review. There is no historical backfill/polling of missed webhooks.

Only public comment text, a small thread excerpt and the authored lesson go to
Groq. Account IDs/usernames are excluded as separate prompt fields; commenters
may still include personal information inside their text. The database stores
comment/author/media IDs for deduplication and rate limits. Comment and reply
bodies are cleared after 30 days during active worker runs; IDs/state remain to
prevent replay. No secrets or comments are stored in the public repository.

## Verification

`PYTHONPATH=backend:.:social python -m pytest -q backend/tests/test_instagram_comments.py social/test_comment_copy.py backend/tests/test_social_slots.py`

Integration tests mock Meta/Groq; they do not prove live app access. Relevant
provider references (checked 2026-10-06):
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/comment-moderation
- https://developers.facebook.com/docs/instagram-platform/webhooks
- https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login
- https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/igcomment.py
- https://console.groq.com/docs/rate-limits
