import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
import copy
import json
from datetime import date
import pytest
from app import models
from app.services.college_insights import DATA_PATH, validate_bundle, sync_insights, for_program, catalog_profile
from app.routers.college_insights import router
from test_roadmap import setup


def test_source_bundle_uses_exact_catalog_programs():
    from pathlib import Path
    records = json.loads(DATA_PATH.read_text())['records']
    validate_bundle(records)
    catalog_path = Path(__file__).resolve().parents[2] / 'docs/JEE-Predictor-Data/jee-predictor-data/data/josaa_2026_round_5.json'
    catalog = json.loads(catalog_path.read_text())['records']
    pairs = {(r['institute'], r['program']) for r in catalog}
    for record in records:
        assert any(n == record['institute'] for n, _ in pairs)
        for placement in record['placements']:
            if placement['scope'] == 'branch':
                assert (record['institute'], placement['program']) in pairs


def test_exact_branch_degree_and_missing_metrics():
    record = json.loads(DATA_PATH.read_text())['records'][0]
    p = record['placements'][0]
    result = for_program(record, p['program'], today=date(2027, 10, 1))
    assert result['placement'] == p and result['review_due']
    assert result['overall_placement'] is not None
    other = for_program(record, 'Engineering and Computational Mechanics (4 Years, Bachelor of Technology)')
    assert other['placement'] is None and other['missing_note']
    dual = for_program(record, 'Computer Science and Engineering (5 Years, Bachelor and Master of Technology (Dual Degree))')
    assert dual['placement'] is None and dual['overall_placement'] is None
    fallback = for_program(catalog_profile('New College'), p['program'])
    assert fallback['placement'] is None and fallback['alumni'] == []
    assert fallback['coverage'] == 'catalog_only' and fallback['verified_on'] is None


@pytest.mark.parametrize('mutation', ['unsafe_url', 'bad_average', 'nan', 'missing_program', 'missing_source'])
def test_invalid_facts_rejected(mutation):
    r = copy.deepcopy(json.loads(DATA_PATH.read_text())['records'][0])
    if mutation == 'unsafe_url': r['sources'][0]['url'] = 'javascript:alert(1)'
    if mutation == 'bad_average': r['placements'][0]['average_lpa'] = 999
    if mutation == 'nan': r['placements'][0]['highest_lpa'] = float('nan')
    if mutation == 'missing_program': del r['placements'][0]['program']
    if mutation == 'missing_source': r['alumni'][0]['sources'] = []
    with pytest.raises(ValueError): validate_bundle([r])


def test_db_sync_idempotent_refresh_and_route_identity(setup, tmp_path):
    client, factory, _ = setup
    client.app.include_router(router)
    r = json.loads(DATA_PATH.read_text())['records'][0]
    program = r['placements'][0]['program']
    with factory() as db:
        db.add_all([models.PredictorInstitute(id=901, name=r['institute']), models.PredictorInstitute(id=902, name='Catalog only institute')]); db.flush()
        db.add(models.PredictorProgram(id=901, institute_id=901, name=program)); db.commit()
        first = sync_insights(db)
        assert first['added'] >= 2
        assert sync_insights(db) == {'added': 0, 'updated': 0}
        r['placements'][0]['average_lpa'] = 9
        path = tmp_path/'insights.json'; path.write_text(json.dumps({'records':[r]}))
        assert sync_insights(db, path)['updated'] == 1
        assert db.get(models.CollegeInsight, 902).content['coverage'] == 'catalog_only'
    params = {'institute':r['institute'], 'program':program}
    response = client.get('/api/colleges/insight', params=params)
    assert response.status_code == 200, response.text
    assert response.json()['placement']['average_lpa'] == 9
    assert client.get('/api/colleges/insight', params={**params,'institute':'Catalog only institute'}).status_code == 404
    assert client.get('/api/colleges/insight', params={**params,'program':'Wrong degree'}).status_code == 404
    assert client.get('/api/colleges/insight', params={**params,'institute':'Unknown'}).status_code == 404
