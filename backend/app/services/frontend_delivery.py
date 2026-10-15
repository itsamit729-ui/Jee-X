"""Serve built public HTML and a separate non-indexable application shell."""
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse


def frontend_response(static_dir: Path, path: str):
    static_dir=static_dir.resolve()
    if path=='api' or path.startswith('api/'):
        raise HTTPException(404,'Not found')
    target=(static_dir/path).resolve()
    if not target.is_relative_to(static_dir):
        raise HTTPException(404,'Not found')
    if target.is_dir() and (target/'index.html').is_file():
        return FileResponse(target/'index.html',headers={'Cache-Control':'no-cache'})
    if target.is_file():
        cache='public, max-age=31536000, immutable' if path.startswith('assets/') else 'no-cache'
        return FileResponse(target,headers={'Cache-Control':cache})
    # Missing resources must never masquerade as a successful HTML page.
    if path.startswith(('assets/','question-images/')) or (not path.startswith('u/') and Path(path).suffix.lower() in {'.xml','.txt','.json','.js','.css','.png','.jpg','.jpeg','.svg','.ico','.webp','.woff','.woff2','.mp4','.pdf'}):
        raise HTTPException(404,'Not found')
    return FileResponse(static_dir/'spa.html',headers={'Cache-Control':'no-cache','X-Robots-Tag':'noindex, follow'})
