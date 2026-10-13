"""Canonical reviewed answers shared by offline scoring and online result import."""
import math
import re
from types import SimpleNamespace
from fastapi import HTTPException
from app import schemas
from app.services.grading import _grade_one


def normalize(question,value):
    value=value.strip()
    if value in ('','invalid'):return value
    if question['type']=='numerical':
        if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',value) or not math.isfinite(float(value)) or abs(float(value))>3.4e38:
            raise HTTPException(422,'Enter a finite numerical answer within ±3.4e38, leave blank, or mark invalid.')
        return value
    allowed={o['label'] for o in question['options']}
    labels=list(value.upper().replace(',','').replace(' ',''))
    if not labels or len(labels)!=len(set(labels)) or not set(labels)<=allowed or (question['type']=='single_correct' and len(labels)!=1):
        raise HTTPException(422,'Choose valid options for this question type; multiple-correct questions accept several choices.')
    return ''.join(sorted(labels))


def draft(question,value):
    return {'question_id':question['question_id'],'option_ids':[o['id'] for o in question['options'] if o['label'] in value] if question['type']!='numerical' and value!='invalid' else [],
        'numeric_answer':float(value) if question['type']=='numerical' and value not in ('','invalid') else None,'time_taken_sec':0,'invalid':value=='invalid'}


def outcome(question,value):
    if value=='invalid':return 'wrong'
    answer=schemas.SubjectTestAnswerIn(**{k:v for k,v in draft(question,value).items() if k!='invalid'})
    q=SimpleNamespace(**{**question,'options':[SimpleNamespace(**o) for o in question['options']]})
    return _grade_one(q,answer)[0]
