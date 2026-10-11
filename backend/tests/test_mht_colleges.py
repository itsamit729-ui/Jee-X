from app.services.mht_colleges import lookup, reference


def test_official_anchor_and_exact_seat_filters():
    data = reference()
    row = next(r for r in data['rows'] if r[1] == '0100224210' and r[2] == 'GOPENS')
    assert row[3:5] == [97.3737374, 9196]
    result = lookup(98, search='Amravati')
    assert all(c['seat_code'] == 'GOPENS' and c['closing_percentile'] <= 98 for c in result['colleges'])
    assert any(c['choice_code'] == '0100224210' for c in result['colleges'])
    assert not any(c['choice_code'] == '0100224210' for c in lookup(97, search='Amravati')['colleges'])
    assert lookup(None)['colleges'] == []
    assert all(c['seat_code'] == 'LOBCH' for c in lookup(100, category='OBC', quota='H', pool='L')['colleges'])


def test_pagination_and_data_integrity():
    data = reference()
    assert len(data['rows']) == len({(r[1], r[2]) for r in data['rows']})
    assert all(0 <= r[3] <= 100 and r[4] > 0 and r[5] > 0 for r in data['rows'])
    first = lookup(100)
    second = lookup(100, offset=first['next_offset'])
    assert not ({r['choice_code'] for r in first['colleges']} & {r['choice_code'] for r in second['colleges']})
