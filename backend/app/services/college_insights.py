"""Reviewed source facts, persisted in MySQL. No web scraping on student requests."""
import hashlib
import json
from datetime import date
from pathlib import Path
import re
from urllib.parse import urlparse
from app import models
from app.services.admissions import NIT_STATES

DATA_PATH = Path(__file__).resolve().parents[1] / 'data/college_insights.json'
CATALOG_SOURCE = 'https://josaa.nic.in/or-cr/'


def valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and not parsed.password


def validate_bundle(records):
    names = set()
    for record in records:
        if not record.get('institute') or record['institute'] in names:
            raise ValueError('Duplicate or missing institute in college insights.')
        names.add(record['institute'])
        date.fromisoformat(record['verified_on'])
        for item in [record, *record.get('placements', []), *record.get('alumni', [])]:
            sources = item.get('sources', [])
            if not sources or any(not valid_url(s['url']) for s in sources):
                raise ValueError('Every insight must have HTTPS source attribution.')
        for item in record.get('placements', []):
            if item['scope'] not in ('branch', 'btech_overall'):
                raise ValueError('Unknown placement scope.')
            if item['scope'] == 'branch' and not item.get('program'):
                raise ValueError('Branch figures require an exact program title.')
            values = [item.get('highest_lpa'), item.get('average_lpa')]
            if not item.get('year') or all(v is None for v in values):
                raise ValueError('Placement record requires a year and reported metric.')
            if any(v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 < v < 1000) for v in values):
                raise ValueError('Invalid placement amount.')
            if all(v is not None for v in values) and values[0] < values[1]:
                raise ValueError('Average exceeds highest package; review source scope.')


def catalog_profile(name):
    state = NIT_STATES.get(name)
    summary = (f'A National Institute of Technology in {state}, listed in the JoSAA counselling catalog.' if state
               else 'This institute participates in JoSAA counselling, through which students can explore its listed programs and admission cutoffs.')
    return {'institute': name, 'summary': summary, 'coverage': 'catalog_only', 'verified_on': None,
            'sources': [{'label': 'JoSAA institute and course catalog', 'url': CATALOG_SOURCE}],
            'placements': [], 'alumni': []}


def sync_insights(db, path=DATA_PATH):
    bundle = json.loads(path.read_text())
    records = bundle['records']
    validate_bundle(records)
    curated = {r['institute']: r for r in records}
    existing = {r.institute_id: r for r in db.query(models.CollegeInsight).all()}
    added = updated = 0
    for institute in db.query(models.PredictorInstitute).all():
        content = curated.get(institute.name, catalog_profile(institute.name))
        digest = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        row = existing.get(institute.id)
        if row is not None and row.content_hash == digest:
            continue
        if row is None:
            row = models.CollegeInsight(institute_id=institute.id)
            db.add(row); added += 1
        else:
            updated += 1
        row.content, row.content_hash = content, digest
    db.commit()
    return {'added': added, 'updated': updated}


def for_program(content, program, today=None):
    today = today or date.today()
    # Full catalog title equality is intentional: never mix degrees, specializations or campuses.
    matched = [p for p in content.get('placements', []) if p['scope'] == 'branch' and p['program'] == program]
    placement = max(matched, key=lambda p: p['year']) if matched else None
    btech = bool(re.search(r'\(4 Years, Bachelor of Technology\)$', program or ''))
    overall = [p for p in content.get('placements', []) if p['scope'] == 'btech_overall'] if btech else []
    overall = max(overall, key=lambda p: p['year']) if overall else None
    checked = content.get('verified_on')
    return {'institute': content['institute'], 'program': program, 'summary': catalog_profile(content['institute'])['summary'] if content.get('coverage') == 'catalog_only' else content['summary'],
            'coverage': content.get('coverage', 'reviewed'), 'verified_on': checked,
            'review_due': bool(checked and (today - date.fromisoformat(checked)).days > 180),
            'placement': placement, 'overall_placement': overall,
            'alumni': content.get('alumni', [])[:3], 'sources': content['sources'],
            'placement_note': 'CTC in INR lakh per year; not take-home pay. Historical outcomes do not guarantee future offers.',
            'missing_note': 'Verified highest and average packages for this exact branch are not available in our records.' if not placement else None}
