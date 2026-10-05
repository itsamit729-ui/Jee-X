"""Collect an explicitly reviewed batch from a CC BY 4.0-labelled online dataset.

pip install beautifulsoup4
python scripts/collect_bitsat_open_data.py [--database /path/to/search_BITSAT.db]

The downloaded SQLite file is untrusted data, opened read-only. Only the reviewed
allowlist is exported, and its answer keys are independently compared. Other rows
are reported, not silently published. No exam year is invented or reassigned.
"""
import argparse
import ast
import hashlib
import json
import re
import sqlite3
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://huggingface.co/datasets/datavorous/entrance-exam-dataset'
DOWNLOAD = SOURCE + '/resolve/main/search_BITSAT.db'
SHA256 = '63bdcea44d5cafbe36771f72e4e25a52207505a9866c5234916d5bcb951de1fe'
SUBJECTS = {'Physics': ('PHY', 'physics'), 'Chemistry': ('CHEM', 'chemistry'),
            'Mathematics': ('MATH', 'mathematics')}


def content(html, option=False):
    soup = BeautifulSoup(html or '', 'html.parser')
    if soup.find(['img', 'math', 'iframe', 'script', 'table']):
        raise ValueError('Unsupported image or structured content requires separate review')
    for tag in soup.select('br'):
        tag.replace_with('\n')
    text = soup.get_text().strip().replace('\r', '')
    # Dataset option fragments escaped LaTeX backslashes twice. Stems did not.
    if option:
        text = text.replace('\\\\', '\\')
    return text


def collect(database):
    if hashlib.sha256(database.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Source snapshot changed. Review the new content before exporting.')
    reviews = json.loads((ROOT/'scripts/bitsat_reviews.json').read_text())
    conn = sqlite3.connect(database.resolve().as_uri()+'?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM questions ORDER BY id').fetchall()
    conn.close()
    files, published, seen, available = {}, set(), set(), Counter()
    for row in rows:
        tags = ast.literal_eval(row['tags'])
        year_match = re.search(r'\bBITSAT (202[2-6])\b', ' '.join(tags))
        if not year_match:
            continue
        year = int(year_match[1])
        available[year] += 1
        review = reviews.get(str(row['id']))
        if not review:
            continue
        code, folder = SUBJECTS[tags[0]]
        stem = content(row['question'])
        options = []
        for li in BeautifulSoup(row['options'], 'html.parser').select('ul.options > li'):
            label = li.select_one('.option-label').get_text(strip=True)
            options.append({'label': label, 'content': content(str(li.select_one('.option-data')), option=True),
                            'is_correct': label == review['answer']})
            if ('correct' in li.get('class', [])) != (label == review['answer']):
                raise ValueError(f"Source key differs from independent review: {row['id']}")
        if [o['label'] for o in options] != list('ABCD'):
            raise ValueError('Invalid option labels')
        answer_text = BeautifulSoup(row['correct_option'], 'html.parser').select_one('.option-value')
        if content(str(answer_text), option=True) != next(o['content'] for o in options if o['is_correct']):
            raise ValueError(f"Source answer text differs from option: {row['id']}")
        fingerprint = (year, re.sub(r'\s+', '', stem).lower())
        if fingerprint in seen:
            raise ValueError('Duplicate in reviewed batch')
        seen.add(fingerprint)
        slug = review['chapter_slug']
        key = (folder, slug)
        if key not in files:
            template = next((ROOT/'generated'/base/folder/(slug+'.json') for base in ('questions','scraped') if (ROOT/'generated'/base/folder/(slug+'.json')).is_file()), None)
            if template is None:
                raise ValueError(f'No existing chapter mapping for {folder}/{slug}')
            existing = json.loads(template.read_text())
            files[key] = {k: existing[k] for k in ('subject', 'chapter', 'subtopics')}
            files[key]['subtopics'] = list(files[key]['subtopics'])
            if not any(s['slug']=='bitsat-memory-based' for s in files[key]['subtopics']):
                files[key]['subtopics'].append({'slug':'bitsat-memory-based','name':'BITSAT memory-based practice','position':99})
            files[key].update(passages=[], questions=[])
        ref = f'BITSAT-{year}-{code}-HF{row["id"]}'
        files[key]['questions'].append({
            'ref':ref, 'subtopic':'bitsat-memory-based', 'type':'single_correct',
            'difficulty':3, 'expected_time_sec':90, 'source_type':'pyq', 'exam':'bitsat',
            'year':year, 'shift':None, 'status':'published', 'stem':stem, 'image':None,
            'options':options, 'solution':review['solution'],
            'provenance':{'kind':'memory_based', 'source':SOURCE,
                'locator':f'search_BITSAT.db questions.id={row["id"]}; {tags[-1]}',
                'source_sha256':SHA256, 'source_row_id':row['id'],
                'reuse_basis':'Dataset publisher declares CC BY 4.0; attribution in generated/bitsat/README.md and PYQ UI.',
                'license':'https://creativecommons.org/licenses/by/4.0/',
                'answer_verified_by':review['reviewer'], 'reviewed_at':review['reviewed_at'],
                'modifications':'HTML converted to text/LaTeX; option escape normalization; new independently derived solution; chapter mapping. Source year/wording retained.',
                'source_paper_label':tags[-1],
                'year_verification':'Dataset attribution; not independently confirmed against an official released paper.'},
        })
        published.add(str(row['id']))
    if published != set(reviews):
        raise ValueError(f'Reviewed records missing: {set(reviews)-published}')
    out = ROOT/'generated/bitsat'
    for (folder, slug), data in files.items():
        path = out/folder/(slug+'.json')
        if path.exists():
            old = json.loads(path.read_text())
            expected = {q['ref'] for q in data['questions']}
            # Retain questions from other import batches; do not erase manual content.
            data['questions'] += [q for q in old['questions'] if q['ref'] not in expected]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    report = {'source':SOURCE, 'source_sha256':SHA256, 'selected_years':list(range(2022,2027)),
              'source_rows_by_year':dict(sorted(available.items())),
              'published_batch_by_year':dict(Counter(q['year'] for f in files.values() for q in f['questions'])),
              'reviewed_source_ids':sorted(map(int,published)),
              'coverage':'Partial collection, not complete papers. No licensed records found for 2024–2026 in this source. No English or LR records in this source.',
              'not_exported':'All non-allowlisted rows, including duplicates and records needing diagram/answer review.',
              'known_source_issue':{'id':2,'reason':'Stem integral upper limit is pi/4; source key and solution use pi/2. Excluded rather than silently altering the question.'}}
    (out/'coverage.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path)
    args=parser.parse_args()
    if args.database:
        collect(args.database)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bitsat.db'
            with urllib.request.urlopen(DOWNLOAD,timeout=30) as response:
                data=response.read(12_000_001)
            if len(data)>12_000_000:
                raise ValueError('Unexpected source size')
            path.write_bytes(data)
            collect(path)

if __name__=='__main__':
    main()
