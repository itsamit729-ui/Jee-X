from datetime import datetime, date
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.deps import get_current_db_user
from app.services import roadmap

router = APIRouter(prefix='/api/roadmap', tags=['roadmap'])


class RoadmapSettings(BaseModel):
    weekly_hours: int = Field(default=5, ge=2, le=60)
    target_marks: int = Field(default=150, ge=1, le=300)
    exam_date: date | None = None
    target_college: str = Field(default='', max_length=120)
    current_crl: int | None = Field(default=None, ge=1, le=3000000)
    target_crl: int | None = Field(default=None, ge=1, le=3000000)

    @field_validator('exam_date')
    @classmethod
    def future_date(cls, value):
        if value and value < date.today():
            raise ValueError('Choose a future exam date.')
        return value


@router.get('')
def get_roadmap(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    return roadmap.build_view(db, user.id, db.get(models.StudentRoadmap, user.id))


@router.put('')
def save_roadmap(body: RoadmapSettings, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    # Serialize concurrent saves for this student, including the first insert.
    db.query(models.User).filter_by(id=user.id).with_for_update().first()
    record = db.query(models.StudentRoadmap).filter_by(user_id=user.id).with_for_update().first()
    now = datetime.utcnow()
    settings = body.model_dump(mode='json')
    rows = roadmap.evidence(db, user.id)
    checkpoints = list(record.checkpoints) if record else []
    if record:
        since = datetime.fromisoformat(record.plan['created_at'])
        checkpoints.append({'date': now.isoformat(), 'tasks': [
            {'title': t['title'], **roadmap.task_progress(t, rows, since)} for t in record.plan['tasks']]})
    plan = roadmap.make_plan(rows, settings, now)
    if not record:
        record = models.StudentRoadmap(user_id=user.id)
        db.add(record)
    record.settings, record.plan, record.checkpoints, record.updated_at = settings, plan, checkpoints[-12:], now
    db.commit()
    return roadmap.build_view(db, user.id, record, now)
