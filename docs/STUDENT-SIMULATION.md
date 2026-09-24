# Student Behaviour Simulation Guide

This document defines a safe, repeatable way to simulate realistic student behaviour on JEE Edge for QA, product analytics, personalization checks, and admin-dashboard validation.

## Goal

Use dedicated test accounts to behave like real students across the major JEE Edge flows without using production user credentials or committing secrets to Git.

The simulations should help answer questions such as:

- Does onboarding work end to end?
- Do tests submit and score correctly?
- Do daily-question streaks and rewards update?
- Does personalization react to weak/strong topics?
- Do ranking/profile flows behave correctly?
- Does the admin dashboard reflect user activity accurately?
- Are session, navigation, retry, refresh, and error states handled well?

## Security Rules

1. Never commit passwords, Auth0 credentials, access tokens, API keys, or session tokens.
2. Use only dedicated test/student accounts.
3. Store credentials in environment variables or the local test runner's secret store.
4. Do not use a real student's account for automated testing.
5. Prefer staging/test data for destructive or high-volume runs.
6. The admin password must remain server-side as `ADMIN_PASSWORD`.
7. Any automated test artifacts containing personal data should be ignored by Git.

Example local environment variables:

```bash
TEST_STUDENT_EMAIL=test-student@example.com
TEST_STUDENT_PASSWORD=replace-me
TEST_BASE_URL=http://localhost:5173
```

Do not add the real values to the repository.

## Recommended Student Personas

### 1. New Student

Purpose: validate first-time user experience.

Behaviour:

- Visit the landing page.
- Start a free test.
- Sign up/login.
- Complete onboarding.
- Set target exam and target year.
- Open dashboard.
- Take a first subject test.
- Visit profile and public profile.

Expected observations:

- User is created once.
- Onboarding redirects correctly.
- Dashboard is not empty after the first submission.
- Public profile resolves correctly.
- Admin dashboard total/new-user counts increase.

### 2. Weak Physics Student

Purpose: validate adaptive practice and learning signals.

Behaviour:

- Take Physics-heavy tests.
- Deliberately answer several Physics questions incorrectly.
- Answer Chemistry/Mathematics more accurately.
- Repeat chapter/subject practice.
- Open the daily question on later runs.

Expected observations:

- Physics/subtopic mastery should be lower than stronger areas.
- Personalized/daily-question selection should tend toward weaker attempted areas when inventory allows.
- Attempts and question-response records should be visible in analytics.

### 3. Strong Student

Purpose: test high-score and ranking behaviour.

Behaviour:

- Answer most questions correctly.
- Keep response time realistic.
- Submit multiple tests.
- Participate in rated/ranked flows where available.
- Open rankings and public profile.

Expected observations:

- Accuracy remains high.
- Rating/ranking-related data updates where applicable.
- Profile and ranking pages remain stable for high-performing users.

### 4. Daily Streak Student

Purpose: validate daily engagement, streaks, and Edge Coins.

Behaviour:

- Open the daily question.
- Submit it.
- Repeat on separate calendar days using a controlled test environment.
- Check rewards and profile after completion.

Expected observations:

- One daily assignment per user per IST calendar day.
- Current/longest streak updates correctly.
- Edge Coins are awarded according to the existing reward rules.
- Admin dashboard daily assigned/completed metrics update.

### 5. Inconsistent Student

Purpose: test realistic incomplete behaviour.

Behaviour:

- Start a test and leave it unfinished.
- Refresh during a test.
- Navigate away and return.
- Skip questions.
- Submit partially answered tests.
- Log out and sign back in.

Expected observations:

- No duplicate attempts are created unexpectedly.
- In-progress state behaves consistently.
- Skipped answers grade correctly.
- Authentication/session restoration works.

### 6. Returning Student

Purpose: test a user with history.

Behaviour:

- Log in to an existing test account.
- Review dashboard trends.
- Take another subject test.
- Open daily/rewards/rankings/profile.
- Compare previous and current performance.

Expected observations:

- Historical attempts remain intact.
- New attempts append rather than overwrite.
- Dashboard trend data remains chronologically correct.

## Core Test Journeys

### Journey A — First-Time Student

```text
Landing
  -> Free Test
  -> Login / Signup
  -> Onboarding
  -> Dashboard
  -> Subject Test
  -> Submit
  -> Analysis / Dashboard
  -> Profile
```

### Journey B — Regular Practice

```text
Login
  -> Dashboard
  -> Subject Test
  -> Select subject/chapter
  -> Attempt questions
  -> Submit
  -> Review result
  -> Dashboard
```

### Journey C — Daily Engagement

```text
Login
  -> Daily
  -> Attempt daily question
  -> Submit
  -> Streak update
  -> Rewards
```

### Journey D — Competition

```text
Login
  -> Rankings
  -> Ranked test
  -> Submit
  -> Ranking/rating update
  -> Public profile
```

## Behaviour Variations

For better coverage, vary the following:

- Correct vs wrong answers
- Skipped answers
- Fast vs normal response times
- Numerical vs option-based questions
- Physics vs Chemistry vs Mathematics
- New vs returning accounts
- Desktop vs narrow/mobile viewport
- Refresh mid-test
- Back/forward navigation
- Network/API failure and retry
- Session expiry
- Multiple consecutive test attempts

Avoid unrealistically hammering the production API.

## Admin Dashboard Validation

After each simulation run, check `/admin`.

The following metrics should change consistently with the simulated behaviour:

| Student action | Expected admin effect |
|---|---|
| New account completes onboarding | Total users / new users increase |
| Student starts tests | Active-user count increases |
| Student submits tests | Submitted attempts increase |
| Test contains N questions | Questions solved increases according to stored attempt totals |
| Daily question is opened | Daily assigned increases |
| Daily question is submitted | Daily completed and completion rate update |
| New test activity | 14-day activity chart updates |
| Rated flow is used | Rated-user / contest metrics may update |
| Reward activity occurs | Coin-related metrics update |
| Question report is created | Open report count increases |

### Important Analytics Note

The current admin dashboard defines "active" primarily from test-attempt activity. Merely visiting the site without starting a test may not count as an active user.

If product analytics need page-view/session-level DAU in the future, add a dedicated analytics/event model rather than inferring all activity from test attempts.

## Suggested Automated Test Structure

If Playwright is added, a clean structure would be:

```text
frontend/
  tests/
    auth/
      onboarding.spec.js
    practice/
      subject-test.spec.js
      daily-question.spec.js
    profile/
      public-profile.spec.js
    competition/
      ranking.spec.js
    resilience/
      refresh-session.spec.js
    admin/
      analytics.spec.js
```

Example environment setup:

```bash
TEST_BASE_URL=https://your-frontend.example.com
TEST_STUDENT_EMAIL=...
TEST_STUDENT_PASSWORD=...
```

The test runner should read these values at runtime.

## Suggested Automated Scenario

A useful end-to-end smoke scenario:

1. Log in with a dedicated test account.
2. Verify onboarding state.
3. Open Dashboard.
4. Open Subject Test.
5. Select a subject/chapter.
6. Submit a mix of correct, wrong, and skipped answers.
7. Verify the result is persisted.
8. Open Daily Question and submit if not already completed.
9. Open Profile.
10. Log out.
11. Log into the admin dashboard separately.
12. Verify the corresponding analytics changed.

## Test Data Strategy

Use recognizable test usernames such as:

```text
qa_new_student_01
qa_weak_physics_01
qa_strong_student_01
qa_daily_streak_01
qa_returning_01
```

This makes it easier to identify and clean up QA data.

Do not use names or emails belonging to real people.

## Pass Criteria

A simulation run is successful when:

- No unexpected frontend exception occurs.
- No API request fails without a useful user-facing error.
- Test submission is persisted exactly once.
- Scores and accuracy match the submitted answers.
- Dashboard history reflects the attempt.
- Daily activity/streak/reward state is internally consistent.
- Admin metrics move in the expected direction.
- Logout/login and refresh flows do not corrupt state.
- Secrets remain outside source control.

## Future Improvements

Useful additions once the core flow is stable:

- Playwright-based browser automation
- Seedable deterministic question selection for QA
- A staging environment with resettable test data
- Admin filters by date range
- Per-feature funnel metrics
- Event-level analytics for page/session DAU
- Automated admin-metric assertions after simulated runs
- Scheduled synthetic student journeys against staging

## Recommended First Automation

Start with one dedicated test account and automate:

```text
Login -> Dashboard -> Subject Test -> Submit -> Daily Question -> Profile -> Logout
```

Once this is stable, add the weak-student, strong-student, and returning-student personas.
