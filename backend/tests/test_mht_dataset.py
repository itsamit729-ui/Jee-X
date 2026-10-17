import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
from copy import deepcopy
from pathlib import Path
import pytest
from app import models
from app.services import mht_dataset, pipeline_question_import as importer
from app.routers.admin_dashboard import _require_admin
from test_pipeline_questions import setup


def test_all_pinned_mht_exports_validate_assets_and_hold_unsupported_questions():
    datasets=[mht_dataset.dataset(year) for year in mht_dataset.YEARS]
    assert sum(d['total'] for d in datasets)==12385
    assert sum(d['eligible'] for d in datasets)==12382
    assert sum(d['figures'] for d in datasets)==531
    assert sum(d['source_pending'] for d in datasets)==207
    assert sum(d['verified_solutions'] for d in datasets)==0
    assert {q['ref'] for d in datasets for q in d['blocked']}=={'PYQ-CHEM-1c08a21e4758','PYQ-MATH-91cb79f0788c','PYQ-PHY-41cb568a9c48'}
    assert all(q['exam']=='mht_cet' and q['answer_source']=='examside' for d in datasets for q in d['questions'])


def test_mht_publication_is_explicit_authenticated_and_does_not_mix_exam_cursors(setup):
    client,app,factory=setup
    path='/api/admin/pipeline-questions/2020'
    assert client.get(path+'?exam=mht_cet').status_code==401
    app.dependency_overrides[_require_admin]=lambda:'verified-admin'
    preview=client.get(path+'?exam=mht_cet').json()
    assert preview['exam']=='mht_cet' and preview['database']['counts']['add']==443
    assert client.get(path+'?exam=other').status_code==422
    assert client.get('/api/admin/pipeline-questions/2019?exam=mht_cet').status_code==404
    with factory() as db:assert db.query(models.Question).count()==0
    body={'expected_digest':preview['digest'],'offset':0,'limit':25}
    assert client.post(path+'/publish',json=body).status_code==409
    published=client.post(path+'/publish?exam=mht_cet',json=body)
    assert published.status_code==200,published.text
    assert published.json()['added']==25
    replay=client.post(path+'/publish?exam=mht_cet',json=body).json()
    assert replay['already_processed'] and replay['progress']['added']==25
    assert client.get(path+'/progress').json()['offset']==0
    with factory() as db:
        assert db.query(models.Question).filter_by(exam='mht_cet',status='published').count()==25
        assert db.query(models.Question).filter_by(exam='jee_main').count()==0
        assert all(c.in_mht_cet and not c.in_main and not c.in_advanced for c in db.query(models.Chapter))
        assert db.query(models.ImportRun).one().file_path=='datasets/mht-cet-2020/questions.jsonl'
        assert all('reconstructed source key' in r.change_note for r in db.query(models.QuestionRevision))


def test_mht_preserves_existing_jee_taxonomy_and_holds_duplicates(setup):
    _,_,factory=setup
    data=deepcopy(mht_dataset.dataset(2020));data['questions']=data['questions'][:1]
    q=data['questions'][0]
    with factory() as db:
        subject=models.Subject(code=q['subject'],name='Existing');db.add(subject);db.flush()
        chapter=models.Chapter(subject_id=subject.id,slug=q['chapter_slug'],name='Keep name',class_level='11',in_main=True,in_advanced=True)
        db.add(chapter);db.commit()
        assert importer.publish_batch(db,data)['added']==1
        db.refresh(chapter)
        assert chapter.name=='Keep name' and chapter.class_level=='11' and chapter.in_main and chapter.in_advanced and chapter.in_mht_cet
        dupe=deepcopy(data);dupe['questions'][0]['ref']='PYQ-'+q['subject']+'-000000000000'
        result=importer.publish_batch(db,dupe)
        assert result['conflicts']==1 and result['added']==0
        assert db.query(models.Question).count()==1


def test_pinned_mht_export_rejects_tampering(tmp_path):
    folder=tmp_path/'mht-cet-2020';folder.mkdir()
    (folder/'questions.jsonl').write_text('{}\n')
    with pytest.raises(ValueError,match='differs from the pinned'):
        mht_dataset.load_dataset(2020,root=tmp_path)


def test_all_eligible_mht_questions_round_trip_without_inflating_repeat_imports(setup):
    _,_,factory=setup
    with factory() as db:
        added=0
        for year in mht_dataset.YEARS:
            data=mht_dataset.dataset(year)
            for offset in range(0,len(data['questions']),50):
                result=importer.publish_batch(db,data,offset,50)
                assert result['conflicts']==0 and result['skipped']==0
                added+=result['added']
        assert added==12382
        assert db.query(models.Question).filter_by(exam='mht_cet',status='published').count()==12382
        assert db.query(models.Question).filter(models.Question.solution!='').count()==0
        assert db.query(models.Asset).count()==531
        assert db.query(models.QuestionRevision).count()==12382
        rerun=importer.publish_batch(db,mht_dataset.dataset(2020),limit=50)
        assert rerun['unchanged']==50 and rerun['added']==0
        assert db.query(models.QuestionRevision).count()==12382


def test_importing_jee_after_mht_enables_shared_chapter_without_removing_cet_flag(setup):
    _,_,factory=setup
    data=deepcopy(mht_dataset.dataset(2020));data['questions']=data['questions'][:1]
    with factory() as db:
        assert importer.publish_batch(db,data)['added']==1
        chapter=db.query(models.Chapter).one()
        assert not chapter.in_main and chapter.in_mht_cet
        q=deepcopy(data['questions'][0]);q.update(exam='jee_main',ref='PYQ-'+q['subject']+'-000000000001')
        importer.taxonomy(db,q);db.flush()
        assert chapter.in_main and chapter.in_mht_cet


def test_existing_publication_without_an_admin_cursor_is_reported_as_current(setup):
    client,app,factory=setup
    data=mht_dataset.dataset(2020)
    with factory() as db:
        for offset in range(0,len(data['questions']),50):
            importer.publish_batch(db,data,offset,50)
        assert db.query(models.QuestionImportProgress).count()==0
    app.dependency_overrides[_require_admin]=lambda:'verified-admin'
    preview=client.get('/api/admin/pipeline-questions/2020?exam=mht_cet').json()
    assert preview['database']['counts']=={'add':0,'update':0,'unchanged':443,'skip':0,'conflict':0}
    assert preview['progress']['offset']==0 and not preview['progress']['finished']
    assert client.get('/api/admin/pipeline-questions/2026?exam=mht_cet').json()['eligible']==4003
