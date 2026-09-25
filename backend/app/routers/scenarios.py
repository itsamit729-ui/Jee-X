"""Authenticated, resumable short exam situations; never affect rating or rewards."""
import math
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_db_user
from app.services import scenarios

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


class ScenarioAnswer(BaseModel):
    option_ids: list[str] = Field(default_factory=list, max_length=4)
    numeric_answer: float | None = None
    marked_for_review: bool = False
    time_spent_sec: int = Field(default=0, ge=0, le=2700)


def _owned_run(db, user_id, run_id):
    run = (db.query(models.ScenarioRun)
           .filter(models.ScenarioRun.id == run_id, models.ScenarioRun.user_id == user_id)
           .with_for_update().populate_existing().first())
    if not run:
        raise HTTPException(404, "Scenario session not found.")
    return run


@router.get("")
def list_scenarios():
    return [dict(preset, exam_minutes=scenarios.EXAM_MINUTES) for preset in scenarios.PRESETS]


@router.post("/{scenario_key}/start", status_code=201)
def start(scenario_key: str, user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    preset = scenarios.get_preset(scenario_key)
    # Serialize starts for this user, including two quick clicks in separate tabs.
    db.query(models.User).filter(models.User.id == user.id).with_for_update().first()
    previous = (db.query(models.ScenarioRun)
                .filter(models.ScenarioRun.user_id == user.id, models.ScenarioRun.scenario_key == scenario_key,
                        models.ScenarioRun.submitted_at.is_(None))
                .order_by(models.ScenarioRun.id.desc()).with_for_update().first())
    now = scenarios.utcnow()
    if previous and previous.deadline_at > now:
        return scenarios.serialize(previous, now)
    if previous:
        scenarios.finish(previous, now)
    questions = scenarios.choose_questions(db, preset["question_count"])
    run = models.ScenarioRun(user_id=user.id, scenario_key=scenario_key,
                             started_at=now, deadline_at=now + timedelta(minutes=preset["duration_minutes"]),
                             questions=questions, answers={})
    db.add(run)
    db.commit()
    db.refresh(run)
    return scenarios.serialize(run, now)


@router.get("/runs/{run_id}")
def get_run(run_id: int, user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    run = _owned_run(db, user.id, run_id)
    now = scenarios.utcnow()
    if run.submitted_at is None and now >= run.deadline_at:
        scenarios.finish(run, now)
        db.commit()
    return scenarios.serialize(run, now)


@router.put("/runs/{run_id}/answers/{question_id}")
def save_answer(run_id: int, question_id: str, body: ScenarioAnswer,
                user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    run = _owned_run(db, user.id, run_id)
    now = scenarios.utcnow()
    if run.submitted_at is not None:
        raise HTTPException(409, "This scenario has ended.")
    if now >= run.deadline_at:
        scenarios.finish(run, now)
        db.commit()
        raise HTTPException(409, "Time is up. Open the session to see your result.")
    question = next((q for q in run.questions if q["id"] == question_id), None)
    if not question:
        raise HTTPException(404, "Question is not part of this session.")
    if question["type"] == "numerical":
        if body.option_ids or (body.numeric_answer is not None and not math.isfinite(body.numeric_answer)):
            raise HTTPException(422, "Enter a finite number or leave this question blank.")
    elif (body.numeric_answer is not None or len(body.option_ids) > 1 or
          len(body.option_ids) != len(set(body.option_ids)) or
          any(option not in {o["id"] for o in question["options"]} for option in body.option_ids)):
        raise HTTPException(422, "Choose one available option or clear your response.")
    elapsed = max(0, (now - run.started_at).total_seconds())
    if body.time_spent_sec > min(scenarios.get_preset(run.scenario_key)["duration_minutes"] * 60, elapsed + 5):
        raise HTTPException(422, "Question time exceeds elapsed session time.")
    answers = dict(run.answers or {})
    answers[question_id] = body.model_dump()
    if sum(answer.get("time_spent_sec", 0) for answer in answers.values()) > elapsed + 5:
        raise HTTPException(422, "Total question time exceeds elapsed session time.")
    run.answers = answers  # reassign JSON so SQLAlchemy persists the change
    db.commit()
    return {"saved": True, "question_id": question_id}


@router.post("/runs/{run_id}/finish")
def finish(run_id: int, user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    run = _owned_run(db, user.id, run_id)
    now = scenarios.utcnow()
    scenarios.finish(run, now)
    db.commit()
    return scenarios.serialize(run, now)
