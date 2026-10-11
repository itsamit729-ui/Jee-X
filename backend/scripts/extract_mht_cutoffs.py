"""Extract regular G/L seat cutoffs from the official pdftotext -layout export.
Usage: python scripts/extract_mht_cutoffs.py input.txt output.json.gz
Special reservations, minority seats and later-stage conversions are deliberately excluded.
"""
import gzip
import json
import re
import sys
from pathlib import Path

SOURCE = 'https://fe2025.mahacet.org/ViewPublicDocument.aspx?MenuId=2449'
SEAT = re.compile(r'\b[GL](?:OPEN|SC|ST|VJ|NT1|NT2|NT3|OBC|SEBC)[HOS]\b')


def extract(text):
    colleges, courses, rows = {}, {}, []
    college = course = None
    scope = None
    for page, content in enumerate(text.split('\f'), 1):
        lines = content.splitlines()
        for i, line in enumerate(lines):
            c = re.match(r'^\s*(\d{5}) - (.+)', line)
            if c:
                college = c[1]
                colleges[college] = c[2].strip()
                course = None
            c = re.match(r'^\s*(\d{10}[A-Z]*) - (.+)', line)
            if c:
                course = c[1]
                name = c[2].strip()
                # Course names may wrap before the Status line.
                j = i + 1
                while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith('Status:'):
                    name += ' ' + lines[j].strip()
                    j += 1
                courses[course] = name
            if 'Seats Allotted to' in line or line.strip() == 'State Level':
                scope = line.strip()
            if scope not in ('State Level', 'Home University Seats Allotted to Home University Candidates', 'Other Than Home University Seats Allotted to Other Than Home University Candidates'):
                continue
            if 'Stage' not in line or not college or not course or not course.isdigit():
                continue
            headings = list(SEAT.finditer(line))
            if not headings:
                continue
            for j in range(i + 1, min(i + 10, len(lines) - 1)):
                if not re.match(r'^\s+I\s+\d', lines[j]):
                    continue
                ranks = list(re.finditer(r'\d+', lines[j]))
                percentiles = list(re.finditer(r'\((\d+(?:\.\d+)?)\)', lines[j+1]))
                for heading in headings:
                    center = (heading.start() + heading.end()) / 2
                    if not percentiles or not ranks:
                        continue
                    pct = min(percentiles, key=lambda m: abs((m.start()+m.end())/2-center))
                    rank = min(ranks, key=lambda m: abs(m.start()-pct.start()))
                    if abs((pct.start()+pct.end())/2-center) > 4 or abs(rank.start()-pct.start()) > 2:
                        continue
                    value = float(pct[1])
                    if not 0 <= value <= 100:
                        raise ValueError('Invalid percentile')
                    rows.append([college, course, heading[0], value, int(rank[0]), page])
                break
    keys = [(r[1], r[2]) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate choice/seat rows; inspect the source')
    return {'year': 2025, 'round': 1, 'stage': 'I', 'source': SOURCE,
            'coverage': 'Regular G/L category seats only; excludes special reservations, minority and conversion stages.',
            'colleges': colleges, 'courses': courses, 'rows': rows}


if __name__ == '__main__':
    data = extract(Path(sys.argv[1]).read_text())
    Path(sys.argv[2]).write_bytes(gzip.compress(json.dumps(data, separators=(',', ':')).encode(), mtime=0))
    print(len(data['rows']), 'cutoffs;', len(data['colleges']), 'institutes')
