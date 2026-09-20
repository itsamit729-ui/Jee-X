"""Download official sources from the checked-in registry; no third-party dependencies."""
import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    catalog = json.loads((root / 'frontend/src/data/officialSyllabi.json').read_text(encoding='utf-8'))
    for exam in catalog['exams']:
        folder = root / 'docs/syllabus' / str(exam['year'])
        folder.mkdir(parents=True, exist_ok=True)
        filename = exam['local_filename']
        if Path(filename).name != filename:
            raise SystemExit('Invalid destination filename in source registry.')
        path = folder / filename
        if path.exists() and not args.overwrite:
            print(f'Skipped existing file: {path.relative_to(root)}')
            continue
        try:
            request = Request(exam['pdf_url'], headers={'User-Agent': 'JeeX-Syllabus-Downloader/1.0'})
            with urlopen(request, timeout=45) as response:
                content = response.read(20 * 1024 * 1024 + 1)
            if not content.startswith(b'%PDF-') or len(content) > 20 * 1024 * 1024:
                raise ValueError('Response is not a PDF or exceeds 20 MiB.')
            with tempfile.NamedTemporaryFile(dir=folder, delete=False) as tmp:
                temp_path = Path(tmp.name)
                tmp.write(content)
            try:
                os.replace(temp_path, path)
            finally:
                temp_path.unlink(missing_ok=True)
            manifest_path = folder / 'downloads.json'
            manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
            manifest[exam['id']] = dict(filename=filename, url=exam['pdf_url'],
                downloaded_at=datetime.now(timezone.utc).isoformat(),
                sha256=hashlib.sha256(content).hexdigest(), size_bytes=len(content))
            manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
            print(f'Downloaded {path.relative_to(root)} ({len(content)} bytes)')
        except Exception as exc:
            raise SystemExit(f"Could not download {exam['title']}: {exc}") from exc


if __name__ == '__main__':
    main()
