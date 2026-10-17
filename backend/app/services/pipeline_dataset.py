"""Validate the pinned JEE Main 2019–2025 exports without contacting a database."""
import hashlib
import json
import math
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from PIL import Image

REPO=Path(__file__).resolve().parents[3]
YEARS=tuple(range(2019,2026))
SOURCES={'examsnet','grafite-jee-mains','pw-jee-main-math','pipeline-two-solves-checked'}
SUBJECTS={'Physics':'PHY','Chemistry':'CHEM','Mathematics':'MATH'}
SOURCE_COMMIT='3c7ec3ec7a0a70e0b62cefdace7ac41d7f3b4a04'
SOURCE_COMMITS={year:SOURCE_COMMIT if year<2024 else 'eb6190d13b1984fd75b26bd2565202bdeefc2c42' for year in YEARS}
DIGESTS={2019:'57c385547793670bd316081eea41204c48faa6da88cc0d2358eeef8ecceaa750',
         2020:'a74b5b75f8a34e257dbd269f33c2016f1c0a68fce5df7d768d01d683cf3d5f74',
         2021:'45c99128733a94065e7f817c15419101caaace7f43bd8912608e8f7c625cdcc3',
         2022:'34e4773da8c6cd40ccc0b0d5e8c6e7be9957a10e9798f0ca1615fa1c827a6351',
         2023:'7e71c84882c2f3288b70110259714a8a245e632fc125521ffdffd11f73c01e24',
         2024:'eeef233e3b1852b136de6341979427c4c73822171a5c546adc005ff4f32da731',
         2025:'b9b492c9f7f1f37c299ff90838404482a1479636d7eae1dd55734665fe9d15b2'}


def narrow(value):
    if isinstance(value,str):
        value=''.join(unicodedata.normalize('NFKC',c) if ord(c)>65535 else c for c in value)
        if any(ord(c)>65535 for c in value):raise ValueError('Unsupported character for a MySQL utf8 database')
        return value
    if isinstance(value,list):return [narrow(v) for v in value]
    if isinstance(value,dict):return {k:narrow(v) for k,v in value.items()}
    return value


def validate(q,year,public):
    if q.get('exam')!='jee_main' or q.get('year')!=year:raise ValueError('Exam/year mismatch')
    subject=SUBJECTS.get(q.get('subject'))
    if not subject or not re.fullmatch(r'PYQ-'+subject+r'-[0-9a-f]{12}',q.get('ref','')):raise ValueError('Invalid subject/reference')
    if not q.get('stem','').strip():raise ValueError('Missing question text')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',q.get('chapter_slug','')) or not q.get('chapter','').strip():raise ValueError('Invalid chapter')
    if q.get('class_level') not in ('11','12'):raise ValueError('Invalid class level')
    match=re.fullmatch(r'(\d{1,2} [A-Z][a-z]{2} \d{4}), Shift ([12])',q.get('shift',''))
    if not match or datetime.strptime(match[1],'%d %b %Y').year!=year:raise ValueError('Invalid year/shift')
    if q.get('answer_source') not in SOURCES:raise ValueError('Answer source not reviewed')
    if type(q.get('difficulty')) is not int or not 1<=q['difficulty']<=10:raise ValueError('Invalid difficulty')
    if type(q.get('expected_time_sec')) is not int or not 1<=q['expected_time_sec']<=3600:raise ValueError('Invalid question duration')
    if type(q.get('solution_verified')) is not bool or q['solution_verified']!=bool(q.get('solution')):raise ValueError('Solution verification flag mismatch')
    if q.get('type')=='single_correct':
        options=q.get('options',[])
        if len(options)!=4 or [o.get('label') for o in options]!=list('ABCD'):raise ValueError('JEE Main requires four A–D options; extra source options need review')
        if any(not o.get('content','').strip() or type(o.get('is_correct')) is not bool for o in options):raise ValueError('Blank/invalid option')
        correct=[o['label'] for o in options if o['is_correct']]
        if len(correct)!=1 or q.get('answer')!=correct[0]:raise ValueError('Missing or inconsistent single-correct key')
        answer=None
    elif q.get('type')=='numerical':
        number=q.get('answer')
        if type(number) not in (int,float) or not math.isfinite(number) or q.get('options'):raise ValueError('Invalid numerical key/options')
        answer={'min':number,'max':number}
    else:raise ValueError('Unsupported exported question type')
    image=q.get('figure')
    if image:
        url=image.get('url','')
        if not url.startswith('/question-images/pyq/'):raise ValueError('Figure must use a bundled question image')
        file=(public/url.lstrip('/')).resolve()
        if not file.is_relative_to(public.resolve()) or not file.is_file():raise ValueError('Figure file missing')
        with Image.open(file) as im:im.verify()
    return narrow({'ref':q['ref'],'subtopic':'general','type':q['type'],'stem':q['stem'],
        'options':q['options'],'answer':answer,'solution':q.get('solution') or '',
        'difficulty':q['difficulty'],'expected_time_sec':q['expected_time_sec'],'source_type':'pyq',
        'exam':'jee_main','year':year,'shift':q['shift'],'status':'published','image':image,
        'subject':subject,'chapter_slug':q['chapter_slug'],'chapter_name':q['chapter'],'class_level':q['class_level'],
        'answer_source':q['answer_source'],'solution_verified':q['solution_verified']})


def load_dataset(year,root=None,public=None):
    if year not in YEARS:raise ValueError('Only the reviewed 2019–2025 exports are supported')
    root=Path(root or os.getenv('PIPELINE_DATA_ROOT',REPO/'datasets'))
    public=Path(public or os.getenv('QUESTION_PUBLIC_ROOT') or os.getenv('FRONTEND_DIST') or REPO/'frontend/public')
    file=root/f'jee-main-{year}'/'questions.jsonl'
    raw=file.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DIGESTS[year]:raise ValueError('Export differs from the reviewed source revision')
    rows=[json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    seen=set();eligible=[];blocked=[]
    for original in rows:
        ref=original.get('ref')
        if ref in seen:raise ValueError('Duplicate reference in source export: '+str(ref))
        seen.add(ref)
        try:eligible.append(validate(original,year,public))
        except (ValueError,KeyError,TypeError,OSError) as error:blocked.append({'ref':ref,'reason':str(error)})
    pending=root/f'jee-main-{year}'/'pending.jsonl'
    pending_count=sum(bool(line.strip()) for line in pending.read_text().splitlines()) if pending.is_file() else 0
    return {'year':year,'digest':hashlib.sha256(raw).hexdigest(),'source_commit':SOURCE_COMMITS[year],
        'total':len(rows),'eligible':len(eligible),'blocked':blocked,'source_pending':pending_count,
        'verified_solutions':sum(bool(q['solution_verified']) for q in eligible),
        'figures':sum(bool(q['image']) for q in eligible),
        'subjects':dict(Counter(q['subject'] for q in eligible)),'questions':eligible}


@lru_cache(maxsize=2)
def dataset(year):return load_dataset(year)


def summary(data):return {k:v for k,v in data.items() if k!='questions'}
