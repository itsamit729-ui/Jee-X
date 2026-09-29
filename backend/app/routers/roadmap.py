from datetime import datetime, date
from fastapi import APIRouter, Depends, Query
from typing import Literal
from pydantic import BaseModel, Field, model_validator, field_validator
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.deps import get_current_db_user
from app.services import roadmap, admissions

router = APIRouter(prefix='/api/roadmap', tags=['roadmap'])


class AdmissionsProfile(BaseModel):
    model_config = {'extra': 'forbid'}
    category: Literal['OPEN', 'EWS', 'OBC-NCL', 'SC', 'ST'] = 'OPEN'
    state: str | None = None
    female_pool: bool = False
    pwd: bool = False
    crl: int | None = Field(default=None, ge=1, le=3000000)
    category_rank: int | None = Field(default=None, ge=1, le=3000000)
    crl_pwd: int | None = Field(default=None, ge=1, le=3000000)
    category_pwd_rank: int | None = Field(default=None, ge=1, le=3000000)

    @field_validator('state')
    @classmethod
    def known_state(cls, value):
        if value is not None and value not in admissions.STATES:
            raise ValueError('Choose a valid state code of eligibility.')
        return value


class RoadmapSettings(BaseModel):
    available_hours: int | None = Field(default=None, ge=1, le=40)
    admission: AdmissionsProfile = Field(default_factory=AdmissionsProfile)
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


@router.get('/data-status')
def data_status(db: Session = Depends(get_db)):
    from app.predictor_bootstrap import STATUS
    groups = db.query(models.PredictorJosaaCutoff.year, func.count(models.PredictorJosaaCutoff.id)).group_by(models.PredictorJosaaCutoff.year).all()
    return {'import': dict(STATUS), 'datasets': [{'year': year, 'rows': count} for year, count in groups],
            'source': 'https://josaa.nic.in/or-cr/'}


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
    from app.services.journey import load_journey
    context = {}
    journey = load_journey(db, user.id, context=context)
    return {**roadmap.build_view(db, user.id, db.get(models.StudentRoadmap, user.id), context=context), 'journey': journey}


@router.get('/journey')
def get_journey(user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    from app.services.journey import load_journey
    return load_journey(db, user.id)


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
    if record and record.plan.get('journey'):
        plan['journey'] = record.plan['journey']
    if not record:
        record = models.StudentRoadmap(user_id=user.id)
        db.add(record)
    record.settings, record.plan, record.checkpoints, record.updated_at = settings, plan, checkpoints[-12:], now
    db.commit()
    from app.services.journey import load_journey
    context = {}
    journey = load_journey(db, user.id, now, context=context)
    return {**roadmap.build_view(db, user.id, record, now, context=context), 'journey': journey}


@router.get('/advanced')
def advanced_outlook(
    category: Literal['OPEN', 'EWS', 'OBC-NCL', 'SC', 'ST'] = 'OPEN',
    pwd: bool = False, female_pool: bool = False,
    current_rank: int | None = Query(default=None, ge=1, le=3000000),
    target_rank: int | None = Query(default=None, ge=1, le=3000000),
    user=Depends(get_current_db_user), db: Session = Depends(get_db),
):
    """Advanced ranks only. Never infer an IIT rank from Main marks or topic accuracy."""
    profile = {**admissions.DEFAULT, 'category': category, 'pwd': pwd, 'female_pool': female_pool}
    rows = admissions.cutoff_rows(db, profile, exam_route='JEE_ADVANCED')
    rank_list = ('CRL' if category == 'OPEN' else category) + ('-PwD' if pwd else '')
    reference_list = rank_list.replace('EWS', 'GEN-EWS')
    anchors_model = models.PredictorAdvancedMarksRankAnchor
    year = db.query(func.max(anchors_model.year)).filter(anchors_model.rank_list == reference_list).scalar()
    anchors = db.query(anchors_model).filter_by(year=year, rank_list=reference_list).order_by(anchors_model.rank).all() if year else []
    def outcome(rank):
        matches = admissions.matches(rows, {rank_list: (rank, rank)}, limit=30) if rank else []
        below = [a for a in anchors if a.rank <= rank] if rank else []
        above = [a for a in anchors if a.rank >= rank] if rank else []
        # Show enclosing published anchors, not invented interpolated scores.
        refs = list({a.rank: a for a in ([below[-1], above[0]] if below and above else [])}.values())
        return {'rank': rank, 'colleges': matches, 'score_references': [
            {'year': a.year, 'rank': a.rank, 'marks': a.marks, 'total_marks': a.total_marks} for a in refs]}
    cutoff_model = models.PredictorAdvancedQualifyingCutoff
    cutoff = db.query(cutoff_model).filter_by(rank_list=reference_list).order_by(cutoff_model.year.desc()).first()
    return {'exam': 'JEE_ADVANCED', 'rank_list': rank_list,
        'cutoff_year': rows[0]['reference_year'] if rows else None,
        'cutoff_round': rows[0]['reference_round'] if rows else None,
        'institutes': len({r['institute'] for r in rows}),
        'current': outcome(current_rank), 'target': outcome(target_rank),
        'qualification': {'year': cutoff.year, 'minimum_each_subject': cutoff.minimum_each_subject,
            'minimum_aggregate': cutoff.minimum_aggregate} if cutoff else None,
        'sources': ['https://josaa.nic.in/or-cr/'] + ([f'https://jeeadv.ac.in/reports/{year}.pdf'] if year else [])}
