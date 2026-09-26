from datetime import datetime, date
from fastapi import APIRouter, Depends
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.deps import get_current_db_user
from app.services import roadmap

router = APIRouter(prefix='/api/roadmap', tags=['roadmap'])


class RoadmapSettings(BaseModel):
    model_config = {'extra': 'forbid'}
    goal_type: Literal['marks', 'colleges'] = 'marks'
    target_marks: int | None = Field(default=150, ge=1, le=300)
    college_choices: list[int] = Field(default_factory=list, max_length=3)

    @model_validator(mode='after')
    def valid_goal(self):
        if self.goal_type == 'marks':
            if self.target_marks is None or self.college_choices:
                raise ValueError('Enter target marks or choose colleges, not both.')
        else:
            if not self.college_choices or len(set(self.college_choices)) != len(self.college_choices):
                raise ValueError('Choose one to three different college and branch combinations.')
            if self.target_marks is not None:
                raise ValueError('College goals must not include a marks target.')
        return self


@router.get('/colleges')
def college_options(q: str = '', user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    query = db.query(models.PredictorProgram.id, models.PredictorProgram.name.label('program'),
                     models.PredictorInstitute.name.label('institute')).join(models.PredictorInstitute)
    term = q.strip()[:100]
    if term:
        escaped = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.filter(or_(models.PredictorProgram.name.ilike(f'%{escaped}%', escape='\\'),
                                 models.PredictorInstitute.name.ilike(f'%{escaped}%', escape='\\')))
    return [dict(r._mapping) for r in query.order_by(models.PredictorInstitute.name, models.PredictorProgram.name).limit(40)]


@router.get('')
def get_roadmap(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    return roadmap.build_view(db, user.id, db.get(models.StudentRoadmap, user.id))


@router.put('')
def save_roadmap(body: RoadmapSettings, user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    # Serialize concurrent saves for this student, including the first insert.
    db.query(models.User).filter_by(id=user.id).with_for_update().first()
    record = db.query(models.StudentRoadmap).filter_by(user_id=user.id).with_for_update().first()
    now = datetime.utcnow()
    rows = roadmap.evidence(db, user.id)
    settings = roadmap.resolve_settings(db, user.id, body.model_dump(mode='json'), rows, now, validate=True)
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
