#!/usr/bin/env python3
"""Reproduce reviewed NIRF salary candidates; never writes to the database.

Requires pdftotext. Exact institute mappings and PDF hashes are reviewed in the
manifest. Changed PDFs fail closed for manual review. Output is a candidate file,
not the serving bundle: review cohort labels before merging college_insights.json.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / 'docs/college-salary-nirf-sources.json'


def extract(text, architecture=False):
    sections = re.split(r'((?:UG|PG)[^\n]*: Placement[^\n]*)', text)
    placements = []
    for title, body in zip(sections[1::2], sections[2::2]):
        match = re.match(r'(UG|PG-Integrated|PG) \[([245]) Years Program\(s\)\]', title)
        if not match:
            continue
        kind, duration = match.groups()
        if kind == 'PG' and duration != '2':
            continue
        if kind == 'PG-Integrated' and duration != '5':
            continue
        if kind == 'UG' and duration not in ('4', '5'):
            continue
        candidates = []
        for row in body.splitlines():
            years = re.findall(r'\b20\d\d-\d\d\b', row)
            salary = re.search(r'\b(\d[\d,]*(?:\.\d+)?)\s*\(', row)
            if len(years) < 2 or not salary:
                continue
            amount = float(salary[1].replace(',', '')) / 100000
            if amount == 0:  # no reported salary, not a zero-salary outcome
                continue
            if not 0 < amount < 1000:
                raise ValueError('Unexpected salary amount; inspect PDF layout.')
            candidates.append((years[-1], amount, row.strip()))
        if not candidates:
            continue
        year, amount, row = max(candidates)
        if kind == 'PG':
            scope = 'pg2_overall'
        elif kind == 'PG-Integrated':
            scope = 'integrated5_overall'
        elif architecture:
            scope = 'barch_overall' if duration == '5' else 'bplan_overall'
        else:
            scope = f'ug{duration}_overall'
        placements.append({'scope': scope, 'year': year, 'median_lpa': amount, 'source_row': row})
    # PG outcomes can supply explicitly labelled college context when no UG table exists.
    return [p for p in placements if p['scope'] != 'pg2_overall'] or placements


def collect(manifest, cache):
    cache.mkdir(parents=True, exist_ok=True)
    result = []
    for source in manifest:
        ident = source['id']
        if not re.fullmatch(r'[A-Za-z0-9-]+', ident):
            raise ValueError('Unsafe cache identifier.')
        if not source['url'].startswith('https://'):
            raise ValueError('HTTPS source required.')
        pdf = cache / f'{ident}.pdf'
        if not pdf.exists():
            with urlopen(source['url'], timeout=30) as response:
                data = response.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024 or not data.startswith(b'%PDF'):
                raise ValueError(f'Unexpected response for {ident}.')
            pdf.write_bytes(data)
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if digest != source['sha256']:
            raise ValueError(f'{ident}: source changed; inspect and review before updating its hash.')
        txt = pdf.with_suffix('.txt')
        subprocess.run(['pdftotext', '-layout', str(pdf), str(txt)], check=True)
        facts = extract(txt.read_text(), architecture=ident.startswith('IR-A'))
        for fact in facts:
            fact['sources'] = [{'label': 'NIRF institution submission', 'url': source['url']}]
            fact['source_sha256'] = digest
        result.append({'institute': source['catalog'], 'placements': facts})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--cache-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = collect(json.loads(args.manifest.read_text()), args.cache_dir)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'Extracted {sum(len(r["placements"]) for r in result)} salary candidates for {len(result)} institutes.')


if __name__ == '__main__':
    main()
