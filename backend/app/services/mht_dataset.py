"""Pinned MHT-CET reconstructions; keys are source keys, not official keys.

No network or database access. Pending rows are never included. A dataset hash
pins the export, not independent verification of its answers or worked solutions.
"""
import hashlib
import json
import os
from collections import Counter
from functools import lru_cache
from pathlib import Path
from app.services import pipeline_dataset as common
from app.services.pipeline_question_import import norm

YEARS=tuple(range(2020,2027))
SOURCE_COMMIT='25d6976a77141b6d18887b3d330502766a852a74'
DIGESTS={2020: 'f5902a8eb35cb77c1b7bf66935b1e9a70883d3fc62f364586bdae391873b2028', 2021: '8b81cd957d7714dec8730f15ad12019814b7fa3b1632e56d431f2d5e26007e34', 2022: 'd90c4d6fb4c5ef44083ca3a98610f210083b7d92b21ca78c4436a9a4fe6120dd', 2023: '7ce35107bce20a5a5228a6a674bd96f510f735c8acaa2d518ee8d32585fdf131', 2024: '110f338abb6595d10e1876afe6a68d81f2f836729a7ad816ea68ff3fe42a5910', 2025: 'd048ce90927906fd2d7160a12768b370d0a5abc7cb81e437c4f3936729f3854f', 2026: 'c5f8c0b2622bbd360638c559d89c22e7838ff36c4dece00da781a8bb9c7dc25e'}


def load_dataset(year,root=None,public=None):
    if year not in YEARS:raise ValueError('No pinned MHT-CET export for this year')
    root=Path(root or os.getenv('PIPELINE_DATA_ROOT',common.REPO/'datasets'))
    public=Path(public or os.getenv('QUESTION_PUBLIC_ROOT') or os.getenv('FRONTEND_DIST') or common.REPO/'frontend/public')
    folder=root/f'mht-cet-{year}'
    raw=(folder/'questions.jsonl').read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=DIGESTS[year]:raise ValueError('MHT-CET export differs from the pinned source revision')
    rows=[json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    seen=set();stems={};eligible=[];blocked=[]
    for original in rows:
        ref=original.get('ref')
        if ref in seen:raise ValueError('Duplicate reference in MHT-CET export: '+str(ref))
        seen.add(ref)
        try:
            if original.get('type')!='single_correct':raise ValueError('MHT-CET requires single-correct questions')
            # The export contains reconstructed ExamSIDE keys and no checked solutions.
            if original.get('solution_verified') or original.get('solution'):raise ValueError('Worked solutions require a separately reviewed export')
            prepared=common.validate({**original,'answer_source':'examside'},year,public,
                exam='mht_cet',answer_sources={'examside'},image_prefix='/question-images/mht-cet/')
            key=(norm(prepared['stem']),prepared['shift'])
            if key in stems:raise ValueError('Possible duplicate in source export under reference '+stems[key])
            stems[key]=ref
            eligible.append(prepared)
        except (ValueError,KeyError,TypeError,OSError) as error:blocked.append({'ref':ref,'reason':str(error)})
    pending=folder/'pending.jsonl'
    return {'exam':'mht_cet','year':year,'digest':digest,'source_commit':SOURCE_COMMIT,
        'total':len(rows),'eligible':len(eligible),'blocked':blocked,
        'source_pending':sum(bool(line.strip()) for line in pending.read_text().splitlines()) if pending.is_file() else 0,
        'verified_solutions':0,'figures':sum(bool(q['image']) for q in eligible),
        'subjects':dict(Counter(q['subject'] for q in eligible)),'questions':eligible}


@lru_cache(maxsize=7)
def dataset(year):return load_dataset(year)
