from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.deps import get_current_db_user
from app.services.college_insights import for_program, catalog_profile

router = APIRouter(prefix='/api/colleges', tags=['college-insights'])


@router.get('/insight')
def college_insight(institute: str = Query(min_length=1, max_length=255),
                    program: str = Query(min_length=1, max_length=255),
                    user=Depends(get_current_db_user), db: Session = Depends(get_db)):
    result = (db.query(models.PredictorInstitute, models.CollegeInsight)
              .outerjoin(models.CollegeInsight, models.CollegeInsight.institute_id == models.PredictorInstitute.id)
              .filter(models.PredictorInstitute.name == institute).first())
    if not result:
        raise HTTPException(404, 'This college is not in the reference catalog yet.')
    college, insight = result
    exists = db.query(models.PredictorProgram.id).filter_by(institute_id=college.id, name=program).first()
    if not exists:
        raise HTTPException(404, 'This branch is not listed for this college.')
    return for_program(insight.content if insight else catalog_profile(college.name), program)
