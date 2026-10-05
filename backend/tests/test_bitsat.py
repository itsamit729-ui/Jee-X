import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
from datetime import date
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base, get_db
from app.deps import get_current_db_user
from app.routers.pyqs import router
from app.routers.subject_test_attempts import router as grader
from app.services.question_catalog import candidate_query


def test_bitsat_filters_keys_scoring_and_ownership():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        for uid in (1, 2):
            db.add(models.User(id=uid, auth0_sub=str(uid), username=f'u{uid}', name='Student'))
            db.add(models.StudentProfile(user_id=uid, dob=date(2006,1,1), class_12_year=2027, target_year=2027, target_exam='jee_main'))
        db.add(models.Subject(id=1,code='ENG',name='English Proficiency'))
        db.add(models.Chapter(id=1,subject_id=1,name='Vocabulary',slug='vocabulary',class_level='11',in_main=False,in_advanced=False))
        db.add(models.Subtopic(id=1,chapter_id=1,name='Synonyms',slug='synonyms'))
        db.flush()
        for i in range(1,7):
            db.add(models.Question(id=i,ref=f'BITSAT-{i}',subtopic_id=1,type='single_correct',
                stem='Test fixture',solution='Fixture solution' if i!=6 else '',difficulty=3,expected_time_sec=60,
                source_type='pyq',exam='bitsat',year=2026 if i!=5 else 2025,
                status='published' if i!=4 else 'draft',version=1,content_hash=str(i)))
            db.flush()
            db.add(models.QuestionRevision(question_id=i,version=1,content={}))
            for j in range(4):
                db.add(models.QuestionOption(question_id=i,label='ABCD'[j],content=f'Option {j}',is_correct=j==0,position=j+1))
        db.commit()
        assert candidate_query(db).all() == []
    def database():
        with factory() as db:
            yield db
    active = [1]
    app = FastAPI(); app.include_router(router); app.include_router(grader)
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_db_user] = lambda: models.User(id=active[0])
    with TestClient(app) as client:
        catalog = client.get('/api/pyqs/bitsat').json()
        assert len(catalog['years']) == 5
        english = next(s for s in catalog['years'][0]['subjects'] if s['code']=='ENG')
        assert english['available'] == 3
        assert client.post('/api/pyqs/bitsat/practice',json={'year':2021,'subject_code':'ENG'}).status_code == 422
        assert client.post('/api/pyqs/bitsat/practice',json={'year':2026,'subject_code':'PHY'}).status_code == 404
        response = client.post('/api/pyqs/bitsat/practice',json={'year':2026,'subject_code':'ENG','count':10})
        assert response.status_code == 201, response.text
        test = response.json(); qs = test['questions']
        assert len(qs)==3
        assert all(q['marks_correct']==3 and q['marks_wrong']==1 and 'solution' not in q for q in qs)
        assert all('is_correct' not in o for q in qs for o in q['options'])
        url = f"/api/subject-tests/attempts/{test['attempt_id']}/submit"
        active[0]=2
        assert client.post(url,json={'answers':[]}).status_code==404
        active[0]=1
        response=client.post(url,json={'answers':[
            {'question_id':qs[0]['question_id'],'option_ids':[qs[0]['options'][0]['id']]},
            {'question_id':qs[1]['question_id'],'option_ids':[qs[1]['options'][1]['id']]},
        ]})
        assert response.status_code==200,response.text
        result=response.json()
        assert result['score']==2
        assert [q['marks_awarded'] for q in result['questions']]==[3,-1,0]
        assert client.post(url,json={'answers':[]}).status_code==409


def test_import_validation_rejects_unverified_and_duplicate_questions(tmp_path):
    import importlib.util
    import json
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('validate_bitsat',Path(__file__).resolve().parents[2]/'scripts/validate_bitsat.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    bank=tmp_path/'bank'/'english';bank.mkdir(parents=True)
    q={'ref':'BITSAT-2026-ENG-fixture','subtopic':'synonyms','type':'single_correct','difficulty':3,
       'expected_time_sec':60,'source_type':'pyq','exam':'bitsat','year':2026,'shift':None,
       'status':'draft','stem':'Validation fixture only','solution':'Validation fixture explanation',
       'image':None,'options':[{'label':x,'content':x,'is_correct':x=='A'} for x in 'ABCD'],
       'provenance':{'kind':'memory_based','source':'fixture','locator':'Q1','reuse_basis':'test fixture', 'answer_verified_by':'test'}}
    data={'subject':'ENG','chapter':{'slug':'vocabulary','name':'Vocabulary','class_level':'11','in_main':False,'in_advanced':False},
          'subtopics':[{'slug':'synonyms','name':'Synonyms'}],'questions':[q]}
    path=bank/'vocabulary.json'
    path.write_text(json.dumps(data))
    assert module.validate(tmp_path/'bank',tmp_path)[0]==[]
    # The new files pass through the actual existing importer, including revision history.
    from app.importer import import_chapter_file
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        assert import_chapter_file(db, path)['added'] == 1
        assert import_chapter_file(db, path)['added'] == 0
        assert db.query(models.QuestionRevision).count() == 1
        stored = db.query(models.QuestionRevision).one()
        assert stored.content['provenance']['kind'] == 'memory_based'
        q['solution'] = 'Corrected fixture solution'
        path.write_text(json.dumps(data))
        assert import_chapter_file(db, path)['updated'] == 1
        assert db.query(models.QuestionRevision).count() == 2
    q['provenance']['answer_verified_by']=''
    path.write_text(json.dumps(data))
    assert any('answer review' in e for e in module.validate(tmp_path/'bank',tmp_path)[0])
    q['provenance']['answer_verified_by']='test'
    data['questions'].append(q.copy());path.write_text(json.dumps(data))
    assert any('duplicate ref' in e for e in module.validate(tmp_path/'bank',tmp_path)[0])
