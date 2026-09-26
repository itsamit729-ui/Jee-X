"""Service 4: rank/percentile/college prediction for a submitted test attempt. Works for both
subject-test and legacy (free_diagnostic/mock) attempts since both are rows in `test_attempts` —
see app/services/predictor.py for the estimation pipeline."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.deps import get_current_db_user
from app.services import predictor, admissions

router = APIRouter(prefix="/api/test-attempts", tags=["predictions"])


@router.get("/{attempt_id}/prediction", response_model=schemas.PredictionOut)
def get_prediction(
    attempt_id: int,
    user: models.User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
):
    attempt = (
        db.query(models.TestAttempt)
        .options(joinedload(models.TestAttempt.test).joinedload(models.Test.test_questions))
        .filter(models.TestAttempt.id == attempt_id)
        .first()
    )
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if attempt.submitted_at is None:
        raise HTTPException(status_code=409, detail="This attempt hasn't been submitted yet.")

    prediction = predictor.predict_for_attempt(db, attempt)
    roadmap = db.get(models.StudentRoadmap, user.id)
    profile = {**admissions.DEFAULT, **(roadmap.settings.get('admission', {}) if roadmap else {})}
    colleges = admissions.matches(admissions.cutoff_rows(db, profile),
        admissions.rank_inputs(profile, prediction.rank_low, prediction.rank_high))

    return schemas.PredictionOut(
        attempt_id=attempt.id,
        raw_score=prediction.raw_score,
        raw_max_score=prediction.raw_max_score,
        scaled_marks_300=prediction.scaled_marks_300,
        reference_year=prediction.reference_year,
        percentile=schemas.PercentileBand(
            low=prediction.percentile_low, high=prediction.percentile_high, basis=prediction.percentile_basis
        ),
        rank=schemas.RankBand(low=prediction.rank_low, high=prediction.rank_high, basis=prediction.rank_basis),
        confidence=prediction.confidence,
        disclaimer=prediction.disclaimer,
        colleges=[schemas.CollegeMatchOut(**c) for c in colleges],
    )
