"""Category ranks and CRL never share a comparison. 2026 NIT quota rules are explicit."""
import json
from pathlib import Path
from sqlalchemy import func
from app import models

NIT_STATES = json.loads((Path(__file__).resolve().parents[1] / 'data/nit_states_2026.json').read_text())['institutes']
STATES = sorted(set(NIT_STATES.values()) | {'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu', 'Ladakh', 'Lakshadweep'})
DEFAULT = {'category': 'OPEN', 'state': None, 'female_pool': False, 'pwd': False,
           'crl': None, 'category_rank': None, 'crl_pwd': None, 'category_pwd_rank': None}


def quota_for(institute, state, year=2026):
    if not state or year != 2026 or institute not in NIT_STATES:
        return None
    if institute == 'National Institute of Technology Goa':
        if state == 'Goa': return 'GO'
        if state in ('Dadra and Nagar Haveli and Daman and Diu', 'Lakshadweep'): return 'HS'
        return 'OS'
    if institute == 'National Institute of Technology, Srinagar':
        return {'Jammu and Kashmir': 'JK', 'Ladakh': 'LA'}.get(state, 'OS')
    extra = {'National Institute of Technology Delhi': 'Chandigarh',
             'National Institute of Technology Puducherry': 'Andaman and Nicobar Islands'}
    return 'HS' if state in (NIT_STATES[institute], extra.get(institute)) else 'OS'


def rank_inputs(profile, crl_low=None, crl_high=None):
    ranks = {}
    if profile.get('crl'):
        ranks['CRL'] = (profile['crl'], profile['crl'])
    elif crl_low is not None:
        ranks['CRL'] = (crl_low, crl_high)
    category = profile['category']
    if category != 'OPEN' and profile.get('category_rank'):
        ranks[category] = (profile['category_rank'], profile['category_rank'])
    if profile.get('pwd'):
        if profile.get('crl_pwd'): ranks['CRL-PwD'] = (profile['crl_pwd'], profile['crl_pwd'])
        if category != 'OPEN' and profile.get('category_pwd_rank'):
            ranks[category + '-PwD'] = (profile['category_pwd_rank'], profile['category_pwd_rank'])
    return ranks


def cutoff_rows(db, profile):
    year = db.query(func.max(models.PredictorJosaaCutoff.year)).filter_by(exam_route='JEE_MAIN_PAPER1').scalar()
    if year is None: return []
    round_ = db.query(func.max(models.PredictorJosaaCutoff.round)).filter_by(year=year, exam_route='JEE_MAIN_PAPER1').scalar()
    seats = ['OPEN'] + ([profile['category']] if profile['category'] != 'OPEN' else [])
    if profile.get('pwd'): seats += [s + ' (PwD)' for s in list(seats)]
    q = (db.query(models.PredictorJosaaCutoff, models.PredictorInstitute.name, models.PredictorProgram.name)
         .join(models.PredictorInstitute, models.PredictorInstitute.id == models.PredictorJosaaCutoff.institute_id)
         .join(models.PredictorProgram, models.PredictorProgram.id == models.PredictorJosaaCutoff.program_id)
         .filter(models.PredictorJosaaCutoff.year == year, models.PredictorJosaaCutoff.round == round_,
                 models.PredictorJosaaCutoff.exam_route == 'JEE_MAIN_PAPER1',
                 models.PredictorJosaaCutoff.seat_type.in_(seats),
                 models.PredictorJosaaCutoff.closing_rank.isnot(None),
                 models.PredictorJosaaCutoff.opening_is_preparatory.is_(False),
                 models.PredictorJosaaCutoff.closing_is_preparatory.is_(False)))
    if not profile.get('female_pool'): q = q.filter(models.PredictorJosaaCutoff.gender_pool == 'Gender-Neutral')
    rows = []
    for r, institute, program in q.all():
        eligible = r.quota == 'AI' or r.quota == quota_for(institute, profile.get('state'), year)
        rows.append({'institute': institute, 'program': program, 'program_id': r.program_id,
            'quota': r.quota, 'seat_type': r.seat_type, 'gender_pool': r.gender_pool,
            'rank_list': r.rank_list, 'opening_rank': r.opening_rank, 'closing_rank': r.closing_rank,
            'reference_year': year, 'reference_round': round_, 'quota_resolved': eligible,
            'is_nit': institute in NIT_STATES})
    return rows


def matches(rows, ranks, limit=12):
    found = []
    for row in rows:
        band = ranks.get(row['rank_list'])
        if not row['quota_resolved'] or not band or row['closing_rank'] < band[0]: continue
        found.append({**row, 'result_label': 'within_historical_closing_rank', 'meets_conservative_estimate': band[1] is not None and row['closing_rank'] >= band[1],
                      'compared_rank_low': band[0], 'compared_rank_high': band[1]})
    # Rank positions are meaningful only within their own list; never sort CRL against category rank.
    found.sort(key=lambda r: (not r['is_nit'], r['rank_list'], r['closing_rank']))
    result, seen = [], set()
    for row in found:
        key = (row['program_id'], row['rank_list'], row['gender_pool'])
        if key not in seen:
            result.append(row); seen.add(key)
        if len(result) == limit: break
    return result


def preview(rows, profile):
    pool = [r for r in rows if r['is_nit'] and (r['quota_resolved'] or not profile.get('state'))]
    seat = profile['category'] + (' (PwD)' if profile.get('pwd') else '')
    pool = [r for r in pool if r['seat_type'] == seat]
    pool.sort(key=lambda r: (r['institute'], r['program'], r['quota']))
    result, seen = [], set()
    for row in pool:
        if row['institute'] not in seen:
            result.append(row); seen.add(row['institute'])
        if len(result) == 12: break
    return result
