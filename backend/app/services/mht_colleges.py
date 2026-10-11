"""Historical CAP cutoff scenarios; never map a mock mark to an official percentile."""
import gzip
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def reference():
    path = Path(__file__).resolve().parents[2] / 'data' / 'mht_cap_2025_r1.json.gz'
    with gzip.open(path, 'rt') as handle:
        return json.load(handle)


def lookup(percentile, category='OPEN', quota='S', pool='G', search='', offset=0):
    data = reference()
    seat = f'{pool}{category}{quota}'
    query = search.casefold().strip()
    rows = []
    if percentile is not None:
        for college, course, code, cutoff, rank, page in data['rows']:
            if code != seat or cutoff > percentile:
                continue
            institute, program = data['colleges'][college], data['courses'][course]
            if query and query not in f'{institute} {program}'.casefold():
                continue
            rows.append({'institute': institute, 'program': program, 'choice_code': course,
                         'seat_code': code, 'closing_percentile': cutoff, 'closing_merit_rank': rank,
                         'source_page': page})
    rows.sort(key=lambda row: (-row['closing_percentile'], row['choice_code']))
    return {'reference_year': data['year'], 'round': data['round'], 'source': data['source'],
            'coverage': data['coverage'], 'percentile': percentile, 'seat_code': seat,
            'total_matches': len(rows), 'colleges': rows[offset:offset+30],
            'next_offset': offset+30 if offset+30 < len(rows) else None,
            'basis': 'Historical cutoff comparison using your entered percentile, not a percentile predicted from this mock.',
            'disclaimer': 'Meeting a historical cutoff is not an admission guarantee. Category, gender pool, home university, domicile and CAP eligibility must be verified. Only regular Stage I seats are included; special reservations, minority, conversions and suffixed choice codes are excluded.'}
