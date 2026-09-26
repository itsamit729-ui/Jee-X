"""Import bundled, checksum-verified reference data using the deployment's DB connection."""
import logging
import os
from pathlib import Path
from threading import Thread
from sqlalchemy import text
from sqlalchemy.orm import Session
from app import models
from app.database import engine
from app.predictor_importer import FILE_IMPORTERS, _load, _sha256

log = logging.getLogger(__name__)
STATUS = {'state': 'not_started', 'files': 0, 'added': 0, 'updated': 0, 'message': ''}


def import_missing(db, root):
    manifest = _load(root / 'manifest.json')
    checksums = {r['path']: r['sha256'] for r in manifest['files']}
    totals = {'files': 0, 'added': 0, 'updated': 0}
    for filename, importer in FILE_IMPORTERS.items():
        path = root / 'data' / filename
        digest = _sha256(path)
        if checksums.get('data/' + filename) != digest:
            raise ValueError('Reference file checksum validation failed: ' + filename)
        previous = db.query(models.PredictorImportRun).filter_by(file_hash=digest).all()
        if any(not row.errors for row in previous):
            continue
        try:
            added, updated = importer(db, path)
            db.commit()  # Each file is atomic; an interrupted deployment resumes at the next file.
        except Exception:
            db.rollback()
            raise
        totals['files'] += 1
        totals['added'] += added
        totals['updated'] += updated
    return totals


def run_reference_import():
    STATUS.update(state='importing', message='Loading verified historical cutoff data.')
    root = Path(os.getenv('PREDICTOR_DATA_ROOT', '')) if os.getenv('PREDICTOR_DATA_ROOT') else Path('/app/predictor-data')
    if not root.is_dir():
        root = Path(__file__).resolve().parents[2] / 'docs/JEE-Predictor-Data/jee-predictor-data'
    try:
        # Connection-level lock survives per-file commits and serializes overlapping deploys/workers.
        with engine.connect() as connection:
            acquired = connection.execute(text("SELECT GET_LOCK('jeex_predictor_import_v1', 0)")).scalar()
            if not acquired:
                STATUS.update(state='another_worker', message='Another worker is importing reference data.')
                return
            connection.commit()
            try:
                with Session(bind=connection) as db:
                    totals = import_missing(db, root)
                STATUS.update(state='ready', message='Bundled reference data is available.', **totals)
                log.info('Predictor reference import complete: %s', totals)
            finally:
                connection.execute(text("SELECT RELEASE_LOCK('jeex_predictor_import_v1')"))
                connection.commit()
    except Exception as exc:
        # Do not put database connection details or credentials into API responses/logs.
        STATUS.update(state='failed', message='Reference import failed. Check database access and bundle integrity.')
        log.error('Predictor reference import failed (%s)', type(exc).__name__)


def start_reference_import():
    if os.getenv('AUTO_IMPORT_PREDICTOR_DATA', 'true').lower() not in ('true', '1', 'yes'):
        STATUS.update(state='disabled', message='Automatic reference-data import is disabled.')
        return
    Thread(target=run_reference_import, name='predictor-reference-import', daemon=True).start()
