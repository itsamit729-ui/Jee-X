"""Public server-rendered discovery pages. Mock creation remains authenticated."""
import json
import os
from html import escape
from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from app import models
from app.database import get_db
from app.auth import require_browser_request
from app.routers.pyqs import catalog, eligible
from app.routers.admin_dashboard import _require_admin
from app.services.paper_discovery import paper_slug, count_event

router = APIRouter()
ORIGIN = 'https://jeeedge.in'

def papers(db):
    return [dict(p, year=y['year'], slug=paper_slug(y['year'], p['shift']))
            for y in catalog('mht_cet', db)['years'] for p in y['papers']]

def path_for(p):
    return f"/mhtcet/papers/{p['year']}/{p['slug']}"

def get_paper(db, year, slug):
    paper = next((p for p in papers(db) if p['year'] == year and p['slug'] == slug), None)
    if not paper:
        raise HTTPException(404, 'Paper not found')
    return paper

def assets():
    root = Path(os.getenv('FRONTEND_DIST', '/app/static'))
    manifest = root / '.vite/manifest.json'
    if not manifest.is_file():
        return ''
    entries = json.loads(manifest.read_text())
    entry = entries.get('src/publicPapers.js', {})
    styles, seen = set(), set()
    def collect(key):
        if key in seen:
            return
        seen.add(key)
        item = entries.get(key, {})
        styles.update(item.get('css', []))
        for dependency in item.get('imports', []):
            collect(dependency)
    collect('src/publicPapers.js')
    tags = ''.join(f'<link rel="stylesheet" href="/{escape(css, quote=True)}">' for css in sorted(styles))
    if entry.get('file'):
        tags += f'<script type="module" src="/{escape(entry["file"], quote=True)}"></script>'
    return tags

def page(title, description, path, content, paper='archive'):
    title, description, url = escape(title), escape(description), escape(ORIGIN + path)
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Jee Edge</title><meta name="description" content="{description}"><meta name="robots" content="index, follow"><link rel="canonical" href="{url}">
<meta property="og:title" content="{title} · Jee Edge"><meta property="og:description" content="{description}"><meta property="og:url" content="{url}"><meta property="og:type" content="website"><meta name="twitter:card" content="summary">
<link rel="stylesheet" href="/public-papers.css">{assets()}</head><body data-paper="{escape(paper, quote=True)}"><a class="skip" href="#main">Skip to papers</a><header><a class="brand" href="/">JEE <span>EDGE</span></a><nav><a href="/mhtcet/papers">MHT-CET papers</a><a href="/pricing">Plans</a></nav></header><main id="main">{content}</main><footer><p>Independent preparation platform. Not affiliated with the examination authority.</p><a href="/terms">Terms</a> · <a href="/privacy">Privacy</a> · <a href="mailto:admin@jeeedge.in">Contact</a></footer></body></html>''', headers={'Cache-Control': 'no-cache'})

@router.get('/mhtcet/papers', response_class=HTMLResponse)
def archive(db: Session = Depends(get_db)):
    rows = papers(db)
    years = sorted({p['year'] for p in rows}, reverse=True)
    content = '<p class="eyebrow">THE MHT-CET ARCHIVE</p><h1>Your next mock.<br>Choose your paper.</h1><p class="intro">Browse reconstructed MHT-CET papers by year and shift. Preview questions freely; sign in when you’re ready for a timed mock.</p>'
    content += '<nav class="years" aria-label="Jump to year">' + ''.join(f'<a href="#year-{y}">{y}</a>' for y in years) + '</nav>'
    if not rows:
        content += '<section class="card"><h2>Papers are being prepared</h2><p>There are no published shift papers available yet. Try the <a href="/free-test">free warm-up</a> while the archive is updated.</p></section>'
    for year in years:
        content += f'<section id="year-{year}"><h2>MHT-CET {year} papers</h2><div class="grid">'
        for p in rows:
            if p['year'] != year:
                continue
            full = all(next((s['available'] for s in p['subjects'] if s['code'] == code), 0) == 50 for code in ('PHY', 'CHEM', 'MATH'))
            content += f'<article class="card"><span class="eyebrow">{"150-question reconstruction" if full else "Partial reconstruction"}</span><h3>{escape(p["shift"])}</h3><p>{p["available"]} available questions · 180-minute mock</p><a class="button secondary" href="{path_for(p)}">Preview paper →</a></article>'
        content += '</div></section>'
    content += '<aside class="note">These are reconstructed questions, not official examination papers. Coverage and original question order may differ. The count shown reflects currently available questions.</aside>'
    return page('MHT-CET Previous Year Papers by Year and Shift', 'Browse available MHT-CET reconstructed papers by year and shift, preview questions and sign in to take a timed mock.', '/mhtcet/papers', content)

@router.get('/mhtcet/papers/{year}/{slug}', response_class=HTMLResponse)
def paper_page(year: int, slug: str, db: Session = Depends(get_db)):
    p = get_paper(db, year, slug)
    ids = [r.id for r in eligible(db, 'mht_cet').join(models.Subject, models.Subject.id == models.Chapter.subject_id)
           .filter(models.Question.year == year, models.Question.shift == p['shift'], models.Subject.code.in_(['PHY', 'CHEM', 'MATH']))
           .order_by(models.Question.ref).limit(3).all()]
    questions = db.query(models.Question).filter(models.Question.id.in_(ids)).options(selectinload(models.Question.options), selectinload(models.Question.assets), selectinload(models.Question.passage).selectinload(models.Passage.assets)).order_by(models.Question.ref).all()
    target = '/pyq?' + urlencode({'exam': 'mht_cet', 'year': year, 'shift': p['shift']})
    full = all(next((s['available'] for s in p['subjects'] if s['code'] == code), 0) == 50 for code in ('PHY', 'CHEM', 'MATH'))
    content = f'<nav aria-label="Breadcrumb"><a href="/mhtcet/papers">MHT-CET papers</a> / {year}</nav><p class="eyebrow">{"150-QUESTION RECONSTRUCTION" if full else "PARTIAL RECONSTRUCTION"}</p><h1>MHT-CET {escape(p["shift"])}</h1><p class="intro">{p["available"]} available questions. Rehearse your pace, then review your answers.</p><a class="button" data-start href="{escape(target, quote=True)}">Continue to timed mock →</a><p class="hint">Sign-in required to start and save an attempt. You’ll return to this paper.</p>'
    content += '<div class="grid stats">' + ''.join(f'<div class="card"><strong>{s["available"]}</strong><span>{escape(s["name"])}</span></div>' for s in p['subjects']) + '</div>'
    content += '<section class="note"><h2>Before you start</h2><p>90 minutes for Physics and Chemistry, followed by 90 minutes for Mathematics. Physics/Chemistry questions carry 1 mark each and Mathematics questions carry 2. No negative marking.</p><p>Reconstructed from the available ExamSIDE question collection. This is not an official paper. Some questions may be missing and the order may differ. Solutions are still being added; some questions show only the answer key after submission. College outlooks use historical cutoffs and are not admission guarantees.</p></section><section><h2>A look inside the paper</h2><p>Sample questions only. Start the mock to attempt the available paper.</p>'
    for i, q in enumerate(questions, 1):
        content += f'<article class="card preview"><p class="eyebrow">PREVIEW {i}</p>'
        if q.passage:
            content += f'<p class="math">{escape(q.passage.content)}</p>'
        content += f'<p class="math">{escape(q.stem)}</p>'
        for asset in list(q.assets) + (list(q.passage.assets) if q.passage else []):
            content += f'<img loading="lazy" src="{escape(asset.url, quote=True)}" alt="{escape(asset.alt_text or "Question diagram", quote=True)}">'
        content += '<ol class="options">' + ''.join(f'<li class="math">{escape(o.content)}</li>' for o in sorted(q.options, key=lambda o: o.position)) + '</ol></article>'
    content += f'</section><a class="button" data-start href="{escape(target, quote=True)}">Continue to timed mock →</a><p><a href="/mhtcet/papers">Explore more papers</a></p>'
    return page(f'MHT-CET {p["shift"]} Question Paper & Mock', f'Preview {p["available"]} available questions from MHT-CET {p["shift"]}. Sign in for a timed reconstructed mock.', path_for(p), content, p['slug'])

@router.get('/sitemap.xml', include_in_schema=False)
def sitemap(db: Session = Depends(get_db)):
    paths = ['/', '/syllabus', '/pricing', '/free-test', '/image-questions', '/mhtcet-mock-tests', '/mhtcet/papers']
    paths += [path_for(p) for p in papers(db)]
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{escape(ORIGIN + p)}</loc></url>' for p in paths) + '</urlset>'
    return Response(xml, media_type='application/xml', headers={'Cache-Control': 'public, max-age=300'})

class Event(BaseModel):
    paper: str = Field(max_length=120)
    source: Literal['direct', 'google', 'youtube', 'instagram', 'whatsapp', 'telegram', 'teacher', 'other'] = 'direct'
    event: Literal['view', 'start_click']

@router.post('/api/public-papers/events', status_code=204, dependencies=[Depends(require_browser_request)])
def event(body: Event, db: Session = Depends(get_db)):
    if body.paper != 'archive' and not any(p['slug'] == body.paper for p in papers(db)):
        raise HTTPException(404, 'Paper not found')
    count_event(db, body.paper, body.source, body.event)
    db.commit()
    return Response(status_code=204)

@router.get('/api/admin/paper-acquisition', dependencies=[Depends(_require_admin)])
def acquisition(db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc).date() - timedelta(days=29)
    rows = db.query(models.AcquisitionCount.source, models.AcquisitionCount.event, func.sum(models.AcquisitionCount.count)).filter(models.AcquisitionCount.day >= since).group_by(models.AcquisitionCount.source, models.AcquisitionCount.event).all()
    return {'days': 30, 'rows': [{'source': s, 'event': e, 'count': n} for s, e, n in rows]}
