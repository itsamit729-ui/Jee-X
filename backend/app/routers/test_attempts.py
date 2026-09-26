from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.deps import get_current_db_user
from app.database import get_db
from app.auth import get_auth_account

router = APIRouter(prefix="/api/test-attempts", tags=["test-attempts"])

# Legacy client-scored flows (FreeTest.jsx, Analysis.jsx) submit a test_type
# string instead of a test_id. Each maps to one canonical `tests` row (created
# lazily) per docs/database-schema.md section 14 ("create one free_diagnostic
# test and point old attempts at it via test_id").
_LEGACY_TEST_DEFS = {
    "free_diagnostic": dict(title="Free diagnostic", kind="free_diagnostic", pattern="jee_main", duration_sec=300),
    "full_mock": dict(title="Full mock", kind="mock", pattern="jee_main", duration_sec=10800),
}


def _get_or_create_legacy_test(db: Session, test_type: str) -> models.Test:
    definition = _LEGACY_TEST_DEFS[test_type]
    test = db.query(models.Test).filter(models.Test.kind == definition["kind"], models.Test.generated_for_user_id.is_(None)).first()
    if test:
        return test
    test = models.Test(**definition, ranked=False)
    db.add(test)
    db.flush()
    return test


def _to_out(attempt: models.TestAttempt) -> schemas.TestAttemptOut:
    test_type = "full_mock" if attempt.test.kind == "mock" else "free_diagnostic"
    return schemas.TestAttemptOut(
        id=attempt.id,
        test_type=test_type,
        score=attempt.score,
        total_questions=attempt.total_questions,
        accuracy=attempt.accuracy,
        avg_time_seconds=attempt.avg_time_seconds,
        subject_breakdown=attempt.subject_breakdown or {},
        created_at=attempt.created_at,
    )


@router.post("", response_model=schemas.TestAttemptOut, status_code=201)
def create_test_attempt(
    body: schemas.TestAttemptIn,
    user: models.User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
):
    test = _get_or_create_legacy_test(db, body.test_type)

    attempt_number = (
        db.query(models.TestAttempt)
        .filter(models.TestAttempt.user_id == user.id, models.TestAttempt.test_id == test.id)
        .count()
        + 1
    )

    attempt = models.TestAttempt(
        user_id=user.id,
        test_id=test.id,
        attempt_number=attempt_number,
        counts_for_rank=False,
        submitted_at=datetime.now(timezone.utc),
        score=body.score,
        total_questions=body.total_questions,
        accuracy=body.accuracy,
        avg_time_seconds=body.avg_time_seconds,
        subject_breakdown={k: v.model_dump() for k, v in body.subject_breakdown.items()},
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return _to_out(attempt)


@router.get("", response_model=list[schemas.TestAttemptOut])
def list_test_attempts(
    user: models.User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
):
    # Scoped to the legacy client-scored flows this endpoint's response shape
    # matches (Dashboard.jsx expects Physics/Chemistry/Mathematics keys and a
    # non-null score). Subject-wise test results are fetched via
    # /api/subject-tests instead — see subject_test_attempts.py.
    attempts = (
        db.query(models.TestAttempt)
        .join(models.Test, models.TestAttempt.test_id == models.Test.id)
        .options(joinedload(models.TestAttempt.test))
        .filter(
            models.TestAttempt.user_id == user.id,
            models.Test.kind.in_(["free_diagnostic", "mock"]),
            models.TestAttempt.submitted_at.isnot(None),
        )
        .order_by(models.TestAttempt.created_at.desc())
        .all()
    )
    return [_to_out(a) for a in attempts]


@router.get('/dashboard')
def dashboard(account: models.AuthAccount = Depends(get_auth_account), db: Session = Depends(get_db)):
    """One authenticated read for the study desk, history and rating summary."""
    from app.routers.users import _user_out
    from app.routers.ranking import _build_me
    user = db.get(models.User, account.user_id) if account.user_id else None
    profile = user.student_profile if user else None
    if not profile:
        return {'onboarded': False, 'profile': None, 'attempts': [], 'rating': None}
    return {
        'onboarded': True,
        'profile': _user_out(user),
        'attempts': list_test_attempts(user, db),
        'rating': _build_me(db, user.id, profile.target_exam, profile.target_year, profile.leaderboard_visibility),
    }
