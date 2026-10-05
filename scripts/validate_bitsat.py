"""Validate BITSAT chapter JSON in the same format as the existing importer.
No question is generated or relabelled by this validator. Provenance and review
metadata are retained in the existing question_revisions.content JSON.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

SUBJECTS = {'PHY', 'CHEM', 'MATH', 'ENG', 'LR'}
YEARS = set(range(2022, 2027))

def validate(root, public):
    errors, counts, refs, fingerprints = [], Counter(), set(), set()
    files = sorted(p for p in root.glob('*/*.json') if not any(x.startswith('.') for x in p.relative_to(root).parts))
    if not files:
        errors.append('No chapter question files found.')
    for path in files:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            code = data['subject']
            chapter = data['chapter']
            assert code in SUBJECTS, 'invalid subject'
            assert chapter['class_level'] in ('11', '12'), 'invalid class_level'
            assert chapter['slug'] and chapter['name'], 'missing chapter metadata'
            if code in ('ENG', 'LR'):
                assert chapter.get('in_main') is False and chapter.get('in_advanced') is False, 'English/LR must not enter JEE syllabus'
            subtopics = {s['slug'] for s in data['subtopics']}
            passages = {p['ref'] for p in data.get('passages', [])}
            for q in data['questions']:
                try:
                    ref = q['ref']
                    assert ref.startswith('BITSAT-') and len(ref) <= 50, 'invalid BITSAT ref'
                    assert ref not in refs, 'duplicate ref'
                    refs.add(ref)
                    assert q['exam'] == 'bitsat' and q['source_type'] == 'pyq', 'invalid exam/source'
                    assert type(q['year']) is int and q['year'] in YEARS, 'year must be 2022–2026'
                    assert q['subtopic'] in subtopics, 'unknown subtopic'
                    assert not q.get('passage') or q['passage'] in passages, 'unknown passage'
                    assert all(s in subtopics for s in q.get('also_subtopics', [])), 'unknown secondary subtopic'
                    assert q['type'] == 'single_correct' and not q.get('answer'), 'BITSAT requires single-correct MCQs'
                    assert q['status'] in ('draft', 'reviewed', 'published'), 'invalid status'
                    assert type(q['difficulty']) is int and 1 <= q['difficulty'] <= 10, 'invalid difficulty'
                    assert type(q['expected_time_sec']) is int and q['expected_time_sec'] > 0, 'invalid expected time'
                    assert q['stem'].strip() and q['solution'].strip(), 'missing question or worked solution'
                    assert len(q.get('shift') or '') <= 50, 'shift too long'
                    options = q['options']
                    assert [o['label'] for o in options] == list('ABCD'), 'four A–D options required'
                    assert all(o['content'].strip() and type(o['is_correct']) is bool for o in options), 'invalid option'
                    assert sum(o['is_correct'] for o in options) == 1, 'exactly one answer required'
                    source = q['provenance']
                    assert source['kind'] == 'memory_based', 'must label recalled content memory_based'
                    assert source['source'].strip() and source['locator'].strip(), 'source file/URL and page/question locator required'
                    assert source['reuse_basis'].strip(), 'record permission/license/ownership basis'
                    assert source['answer_verified_by'].strip(), 'answer review attribution required'
                    fingerprint = (q['year'], ''.join(q['stem'].lower().split()))
                    assert fingerprint not in fingerprints, 'duplicate question text in this year'
                    fingerprints.add(fingerprint)
                    if q.get('image'):
                        url = q['image']['url']
                        assert url.startswith('/question-images/') and not url.startswith('//'), 'use a local question image'
                        image = (public / url.lstrip('/')).resolve()
                        assert image.is_relative_to(public.resolve()) and image.is_file(), 'missing or unsafe image path'
                    counts[(q['year'], code)] += 1
                except (KeyError, TypeError, ValueError, AssertionError, AttributeError) as exc:
                    errors.append(f"{path.name}/{q.get('ref', '?')}: {exc}")
        except (KeyError, TypeError, ValueError, AssertionError, AttributeError) as exc:
            errors.append(f'{path.name}: {exc}')
    if not sum(counts.values()):
        errors.append('No valid questions found.')
    return errors, counts

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--public', type=Path, default=Path(__file__).resolve().parents[1]/'frontend/public')
    args = parser.parse_args()
    errors, counts = validate(args.root, args.public)
    for (year, subject), count in sorted(counts.items()):
        print(f'{year} {subject}: {count}')
    for error in errors:
        print(error)
    raise SystemExit(bool(errors))
