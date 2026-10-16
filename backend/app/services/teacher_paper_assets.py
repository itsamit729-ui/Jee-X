"""Resolve bundled question diagrams without fetching remote resources."""
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.avif'}


def local_diagram(url):
    if not isinstance(url, str):
        return False
    return unquote(urlsplit(url).path).startswith('/question-images/')


def diagram_file(url):
    if not local_diagram(url):
        return None
    path = unquote(urlsplit(url).path)
    if '\\' in path:
        return None
    roots = [Path(os.getenv('FRONTEND_DIST', '/app/static')),
             Path(__file__).resolve().parents[3] / 'frontend' / 'public']
    for root in roots:
        base = (root / 'question-images').resolve()
        target = (root / path.lstrip('/')).resolve()
        if not target.is_relative_to(base):
            return None
        if target.is_file() and target.suffix.lower() in IMAGE_SUFFIXES:
            if 0 < target.stat().st_size <= 10_000_000:
                return target
    return None
