import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
import json
from datetime import datetime
from app import models
from app.services import admissions
from app.schemas import CollegeMatchOut
from test_roadmap import setup


def test_nit_state_rules_include_ut_exceptions():
    assert len(admissions.NIT_STATES) == 31
    q = admissions.quota_for
    assert q('National Institute of Technology, Tiruchirappalli', 'Tamil Nadu') == 'HS'
    assert q('National Institute of Technology, Tiruchirappalli', 'Maharashtra') == 'OS'
    assert q('National Institute of Technology, Tiruchirappalli', None) is None
    assert q('National Institute of Technology Goa', 'Goa') == 'GO'
    assert q('National Institute of Technology Goa', 'Lakshadweep') == 'HS'
    assert q('National Institute of Technology Goa', 'Delhi') == 'OS'
    assert q('National Institute of Technology, Srinagar', 'Ladakh') == 'LA'
    assert q('National Institute of Technology, Srinagar', 'Jammu and Kashmir') == 'JK'
    assert q('National Institute of Technology Delhi', 'Chandigarh') == 'HS'
    assert q('National Institute of Technology Puducherry', 'Andaman and Nicobar Islands') == 'HS'
    assert q('National Institute of Technology, Tiruchirappalli', 'Tamil Nadu', 2027) is None


def test_category_crl_and_pwd_comparisons_never_mix():
    profile = {**admissions.DEFAULT, 'category': 'SC', 'category_rank': 400, 'pwd': True, 'category_pwd_rank': 20}
    ranks = admissions.rank_inputs(profile, 50000, 55000)
    assert ranks == {'CRL': (50000, 55000), 'SC': (400, 400), 'SC-PwD': (20, 20)}
    base = {'quota_resolved': True, 'is_nit': True, 'program_id': 1, 'gender_pool': 'Gender-Neutral'}
    rows = [{**base, 'rank_list': 'CRL', 'closing_rank': 1000},
            {**base, 'rank_list': 'SC', 'closing_rank': 500},
            {**base, 'rank_list': 'SC-PwD', 'closing_rank': 25}]
    assert {r['rank_list'] for r in admissions.matches(rows, ranks)} == {'SC', 'SC-PwD'}
    assert not admissions.matches(rows, {'CRL': (50000, 55000)})
    assert not admissions.matches([{**rows[1], 'quota_resolved': False}], ranks)


def test_category_goal_and_nit_ui_data(setup):
    client, factory, _ = setup
    name = 'National Institute of Technology, Tiruchirappalli'
    with factory() as db:
        db.add(models.PredictorInstitute(id=99, name=name))
        db.flush()
        db.add(models.PredictorProgram(id=99, institute_id=99, name='Mechanical Engineering'))
        db.flush()
        for quota in ('HS', 'OS'):
            for seat, rank, closing in [('OPEN','CRL',25000), ('SC','SC',1000), ('OBC-NCL','OBC-NCL',4000)]:
                db.add(models.PredictorJosaaCutoff(year=2026,counselling='JoSAA',round=5,institute_id=99,
                    program_id=99,quota=quota,seat_type=seat,rank_list=rank,gender_pool='Gender-Neutral',
                    exam_route='JEE_MAIN_PAPER1',opening_rank=1,closing_rank=closing))
        db.commit()
    payload = {'goal_type':'colleges','college_choices':[99],'target_marks':None,
               'admission':{'category':'SC','state':'Tamil Nadu','category_rank':900}}
    response = client.put('/api/roadmap', json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['settings']['choices'][0]['rank_list'] == 'SC'
    assert data['settings']['target_crl'] is None  # SC cutoff must never become a CRL target
    assert data['current']['rank_inputs'] == {'SC':900}
    assert data['current']['colleges'][0]['quota'] == 'HS'
    assert data['current']['colleges'][0]['rank_list'] == 'SC'
    CollegeMatchOut(**data['current']['colleges'][0])
    assert all(c['seat_type']=='SC' for c in data['cutoff_preview'])
    assert client.put('/api/roadmap',json={**payload,'admission':{'state':'Invalid'}}).status_code == 422
    payload['admission']['state'] = 'Maharashtra'
    assert client.put('/api/roadmap',json=payload).json()['current']['colleges'][0]['quota'] == 'OS'
    payload['admission']['state'] = None
    assert not client.put('/api/roadmap',json=payload).json()['current']['colleges']
    assert client.get('/api/roadmap/data-status').json()['datasets'] == [{'year':2026,'rows':6}]


def test_import_once_checks_hash_and_is_idempotent(setup, tmp_path, monkeypatch):
    import hashlib
    from app import predictor_bootstrap as bootstrap
    from app.predictor_importer import import_josaa
    _, factory, _ = setup
    monkeypatch.setattr(bootstrap, 'FILE_IMPORTERS', {'cutoffs.json': import_josaa})
    (tmp_path/'data').mkdir()
    path=tmp_path/'data/cutoffs.json'
    path.write_text(json.dumps({'metadata':{'year':2026,'round':5,'counselling':'JoSAA'},'records':[
        {'institute':'NIT example','program':'Engineering','quota':'OS','seat_type':'SC',
         'gender_pool':'Gender-Neutral','rank_list':'SC','exam_route':'JEE_MAIN_PAPER1',
         'opening_rank':1,'closing_rank':1000,'opening_is_preparatory':False,'closing_is_preparatory':False,
         'opening_rank_raw':'1','closing_rank_raw':'1000'}]}))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path/'manifest.json').write_text(json.dumps({'files':[{'path':'data/cutoffs.json','sha256':digest}]}))
    with factory() as db:
        assert bootstrap.import_missing(db,tmp_path)['added']==1
        assert bootstrap.import_missing(db,tmp_path)=={'files':0,'added':0,'updated':0}
        path.write_text(path.read_text()+' ')
        import pytest
        with pytest.raises(ValueError,match='checksum'):
            bootstrap.import_missing(db,tmp_path)
