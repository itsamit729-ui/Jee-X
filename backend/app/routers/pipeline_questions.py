"""Admin-only, explicit publication; never runs during startup."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers.admin_dashboard import _require_admin
from app.services import pipeline_dataset as source,pipeline_question_import as importer,mht_dataset

router=APIRouter(prefix='/api/admin/pipeline-questions',tags=['admin'],dependencies=[Depends(_require_admin)])


def load(year,exam='jee_main'):
    dataset=mht_dataset if exam=='mht_cet' else source
    if year not in dataset.YEARS:raise HTTPException(404,'No reviewed export for this year')
    try:return dataset.dataset(year)
    except (OSError,ValueError,KeyError,TypeError):raise HTTPException(503,'Pipeline export is unavailable or invalid on this deployment.') from None


@router.get('')
def index(response:Response,db:Session=Depends(get_db),exam:Literal['jee_main','mht_cet']='jee_main'):
    response.headers['Cache-Control']='no-store'
    return {'years':[{**source.summary(load(year,exam)),'progress':importer.progress(db,load(year,exam))} for year in (mht_dataset.YEARS if exam=='mht_cet' else source.YEARS)]}


@router.get('/{year}')
def preview(year:int,response:Response,db:Session=Depends(get_db),exam:Literal['jee_main','mht_cet']='jee_main'):
    response.headers['Cache-Control']='no-store'
    data=load(year,exam)
    return {**source.summary(data),'database':importer.plan(db,data),'progress':importer.progress(db,data)}


@router.get('/{year}/progress')
def progress(year:int,response:Response,db:Session=Depends(get_db),exam:Literal['jee_main','mht_cet']='jee_main'):
    response.headers['Cache-Control']='no-store'
    return importer.progress(db,load(year,exam))


class Publish(BaseModel):
    expected_digest:str=Field(pattern=r'^[0-9a-f]{64}$')
    offset:int=Field(default=0,ge=0)
    limit:int=Field(default=25,ge=1,le=50)


@router.post('/{year}/publish')
def publish(year:int,body:Publish,response:Response,db:Session=Depends(get_db),exam:Literal['jee_main','mht_cet']='jee_main'):
    response.headers['Cache-Control']='no-store'
    data=load(year,exam)
    if body.expected_digest!=data['digest']:raise HTTPException(409,'Export changed. Review the current dataset before publishing.')
    if body.offset>len(data['questions']):raise HTTPException(422,'Offset exceeds the eligible question count')
    try:return importer.publish_next(db,data,body.offset,body.limit)
    except ValueError as error:raise HTTPException(409,str(error)) from None
    except IntegrityError:raise HTTPException(409,'Concurrent import or content conflict. Refresh the preview; no changes from this batch were committed.') from None
