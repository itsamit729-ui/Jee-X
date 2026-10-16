import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
from copy import deepcopy
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base,get_db
from app.routers.admin_dashboard import _require_admin
from app.routers.pipeline_questions import router
from app.services import pipeline_dataset as source,pipeline_question_import as importer


@pytest.fixture
def setup():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,autoflush=False)
    app=FastAPI();app.include_router(router)
    def database():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=database
    yield TestClient(app),app,factory
    engine.dispose()


def sample_data(count=3):
    original=source.dataset(2024)
    return {**original,'questions':deepcopy(original['questions'][:count])}


def test_full_datasets_have_real_assets_and_block_the_three_malformed_records():
    a=source.dataset(2024);b=source.dataset(2025)
    assert (a['total'],a['eligible'],a['source_pending'])==(1684,1683,98)
    assert (b['total'],b['eligible'],b['source_pending'])==(1297,1295,118)
    assert a['verified_solutions']+b['verified_solutions']==1009
    assert a['figures']+b['figures']==301
    assert len({q['ref'] for data in (a,b) for q in data['questions']})==2978
    assert {q['ref'] for data in (a,b) for q in data['blocked']}=={'PYQ-MATH-b25f43af33c6','PYQ-MATH-5e4d39c22d39','PYQ-PHY-8991eda79415'}


def test_import_requires_admin_and_the_reviewed_digest(setup):
    client,app,factory=setup
    data=source.dataset(2024)
    assert client.get('/api/admin/pipeline-questions').status_code==401
    assert client.post('/api/admin/pipeline-questions/2024/publish',json={'expected_digest':data['digest']}).status_code==401
    app.dependency_overrides[_require_admin]=lambda:'verified-admin'
    assert client.post('/api/admin/pipeline-questions/2024/publish',json={'expected_digest':'0'*64}).status_code==409
    assert client.post('/api/admin/pipeline-questions/2024/publish',json={'expected_digest':data['digest'],'limit':51}).status_code==422
    assert client.get('/api/admin/pipeline-questions/2023').status_code==404
    with factory() as db:assert db.query(models.Question).count()==0


def test_preview_is_read_only_and_api_publication_is_bounded_and_repeatable(setup):
    client,app,factory=setup;app.dependency_overrides[_require_admin]=lambda:'verified-admin'
    preview=client.get('/api/admin/pipeline-questions/2024')
    assert preview.status_code==200,preview.text
    assert preview.json()['database']['counts']['add']==1683
    assert 'questions' not in preview.json()
    with factory() as db:assert db.query(models.Question).count()==0
    body={'expected_digest':preview.json()['digest'],'offset':0,'limit':25}
    result=client.post('/api/admin/pipeline-questions/2024/publish',json=body)
    assert result.status_code==200,result.text
    assert result.json()['added']==25 and result.json()['next_offset']==25
    repeated=client.post('/api/admin/pipeline-questions/2024/publish',json=body)
    assert repeated.status_code==200 and repeated.json()['unchanged']==25
    with factory() as db:
        assert db.query(models.Question).count()==25
        assert db.query(models.QuestionRevision).count()==25
        assert db.query(models.ImportRun).count()==1


def test_all_eligible_questions_round_trip_into_current_schema_without_pending_records(setup):
    _,_,factory=setup
    with factory() as db:
        total=0
        for year in source.YEARS:
            data=source.dataset(year)
            for offset in range(0,len(data['questions']),50):
                result=importer.publish_batch(db,data,offset,50)
                assert not result['conflicts'] and not result['skipped']
                total+=result['added']
        assert total==2978 and db.query(models.Question).count()==2978
        assert db.query(models.Question).filter_by(status='published',exam='jee_main').count()==2978
        assert db.query(models.QuestionRevision).count()==2978
        assert db.query(models.Question).filter(models.Question.solution!='').count()==1009
        numerical=db.query(models.Question).filter_by(type='numerical').all()
        assert len(numerical)==858 and all(q.answer_min is not None and q.answer_min==q.answer_max for q in numerical)
        assert db.query(models.Asset).count()==301
        from app.routers.pyqs import catalog
        archive=catalog('jee_main',db)
        assert sum(s['available'] for year in archive['years'] for s in year['subjects'])==2978
        assert {year['year']:len(year['papers']) for year in archive['years'] if year['papers']}=={2024:20,2025:19}
        for year in source.YEARS:
            preview=importer.plan(db,source.dataset(year))
            assert preview['counts']['unchanged']==source.dataset(year)['eligible']
            assert preview['counts']['add']==preview['counts']['update']==preview['counts']['conflict']==0


def test_existing_solutions_clean_figures_taxonomy_and_ids_are_preserved(setup):
    _,_,factory=setup;data=sample_data(1)
    with factory() as db:
        importer.publish_batch(db,data)
        row=db.query(models.Question).one();identity=row.id
        row.solution='Teacher checked solution';row.difficulty=8;row.status='draft'
        row.subtopic.chapter.name='Teacher chapter title';row.subtopic.chapter.position=17
        db.add(models.Asset(question_id=row.id,url='/question-images/clean-replacement.png',alt_text='Clean diagram'))
        db.commit()
        result=importer.publish_batch(db,data)
        assert result['updated']==1
        db.expire_all();row=db.get(models.Question,identity)
        assert row.solution=='Teacher checked solution' and row.difficulty==8
        assert row.assets[0].url=='/question-images/clean-replacement.png'
        assert row.subtopic.chapter.name=='Teacher chapter title' and row.subtopic.chapter.position==17
        assert row.version==2 and row.status=='published'
        assert importer.publish_batch(db,data)['unchanged']==1


def test_answer_disagreement_and_retired_questions_are_held(setup):
    _,_,factory=setup;data=sample_data(2)
    with factory() as db:
        importer.publish_batch(db,data)
        rows=db.query(models.Question).order_by(models.Question.id).all()
        for option in rows[0].options:option.is_correct=option.label=='D'
        incoming=next(o['label'] for o in data['questions'][0]['options'] if o['is_correct'])
        if incoming=='D':
            for option in rows[0].options:option.is_correct=option.label=='A'
        rows[1].status='retired';db.commit()
        result=importer.publish_batch(db,data)
        assert result['conflicts']==1 and result['skipped']==1
        assert rows[1].status=='retired' and rows[0].version==1


def test_duplicate_under_different_reference_is_not_inserted(setup):
    _,_,factory=setup;data=sample_data(1)
    with factory() as db:
        importer.publish_batch(db,data)
        row=db.query(models.Question).one();row.ref='LEGACY-OTHER-REF';db.commit()
        result=importer.publish_batch(db,data)
        assert result['conflicts']==1 and db.query(models.Question).count()==1


def test_bad_numeric_missing_figure_and_unverified_solution_are_rejected(tmp_path):
    raw=__import__('json').loads((source.REPO/'datasets/jee-main-2024/questions.jsonl').read_text().splitlines()[0])
    q=deepcopy(raw);q['type']='numerical';q['options']=[];q['answer']=float('nan')
    with pytest.raises(ValueError,match='numerical'):source.validate(q,2024,tmp_path)
    q=deepcopy(raw);q['figure']={'url':'/question-images/pyq/missing.png'}
    with pytest.raises(ValueError,match='missing'):source.validate(q,2024,tmp_path)
    q=deepcopy(raw);q['solution_verified']=False;q['solution']='Unverified answer'
    with pytest.raises(ValueError,match='verification'):source.validate(q,2024,tmp_path)


def test_batch_failure_rolls_back_questions_taxonomy_and_history(setup,monkeypatch):
    _,_,factory=setup;data=sample_data(2);calls=[]
    original=importer._upsert_question_assets
    def fail_second(*args):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('Interrupted batch')
        return original(*args)
    monkeypatch.setattr(importer,'_upsert_question_assets',fail_second)
    with factory() as db:
        with pytest.raises(RuntimeError,match='Interrupted batch'):importer.publish_batch(db,data)
        assert db.query(models.Question).count()==0
        assert db.query(models.ImportRun).count()==0
        assert db.query(models.QuestionRevision).count()==0
        assert db.query(models.Chapter).count()==0
