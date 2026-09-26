"""Loads docs/JEE-Predictor-Data/jee-predictor-data/data/*.json into predictor_* tables.

Mirrors app/importer.py's upsert-by-natural-key pattern, but these are pre-flattened JSON record
lists rather than nested chapter files. Each import_<dataset>() upserts by the unique key the data
pack's README documents ("Database fields and indexes") and returns (added, updated) counts.
Verifies each file's sha256 against manifest.json before loading — the pack's own integrity check.
"""

import hashlib
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app import models


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _record_run(db: Session, path: Path, added: int, updated: int, errors: list[str]):
    db.add(
        models.PredictorImportRun(
            file_path=str(path), file_hash=_sha256(path), added=added, updated=updated, errors=errors or None
        )
    )


def _get_or_create_institute(db: Session, cache: dict, name: str) -> models.PredictorInstitute:
    institute = cache.get(name)
    if institute:
        return institute
    institute = db.query(models.PredictorInstitute).filter(models.PredictorInstitute.name == name).first()
    if not institute:
        institute = models.PredictorInstitute(name=name)
        db.add(institute)
        db.flush()
    cache[name] = institute
    return institute


def _get_or_create_program(db: Session, cache: dict, institute: models.PredictorInstitute, name: str) -> models.PredictorProgram:
    key = (institute.id, name)
    program = cache.get(key)
    if program:
        return program
    program = (
        db.query(models.PredictorProgram)
        .filter(models.PredictorProgram.institute_id == institute.id, models.PredictorProgram.name == name)
        .first()
    )
    if not program:
        program = models.PredictorProgram(institute_id=institute.id, name=name)
        db.add(program)
        db.flush()
    cache[key] = program
    return program


def import_josaa(db: Session, path: Path) -> tuple[int, int]:
    data = _load(path)
    meta = data["metadata"]
    counselling, year, round_ = meta["counselling"], meta["year"], meta["round"]

    # Seed dimensions in batches: avoid thousands of network round trips on deployment.
    institute_cache = {r.name: r for r in db.query(models.PredictorInstitute).all()}
    names = {r['institute'] for r in data['records']}
    new_institutes = [models.PredictorInstitute(name=name) for name in names - institute_cache.keys()]
    db.add_all(new_institutes)
    db.flush()
    institute_cache.update({r.name: r for r in new_institutes})
    program_cache = {(r.institute_id, r.name): r for r in db.query(models.PredictorProgram).all()}
    keys = {(institute_cache[r['institute']].id, r['program']) for r in data['records']}
    new_programs = [models.PredictorProgram(institute_id=i, name=name) for i, name in keys - program_cache.keys()]
    db.add_all(new_programs)
    db.flush()
    program_cache.update({(r.institute_id, r.name): r for r in new_programs})
    existing = {
        (r.year, r.counselling, r.round, r.institute_id, r.program_id, r.quota, r.seat_type, r.gender_pool): r
        for r in db.query(models.PredictorJosaaCutoff).filter(
            models.PredictorJosaaCutoff.year == year,
            models.PredictorJosaaCutoff.counselling == counselling,
            models.PredictorJosaaCutoff.round == round_,
        )
    }

    added = updated = 0
    for rec in data["records"]:
        quota, seat_type, rank_list = rec.get("quota") or "", rec.get("seat_type") or "", rec.get("rank_list") or ""
        if not quota or not seat_type or not rank_list:
            continue  # blank quota/seat_type/rank_list rows aren't usable for rank-based matching

        institute = _get_or_create_institute(db, institute_cache, rec["institute"])
        program = _get_or_create_program(db, program_cache, institute, rec["program"])
        key = (year, counselling, round_, institute.id, program.id, quota, seat_type, rec["gender_pool"])
        row = existing.get(key)
        is_new = row is None
        if is_new:
            row = models.PredictorJosaaCutoff(
                year=year, counselling=counselling, round=round_,
                institute_id=institute.id, program_id=program.id,
                quota=quota, seat_type=seat_type, gender_pool=rec["gender_pool"],
            )
            db.add(row)
            existing[key] = row
        row.exam_route = rec["exam_route"]
        row.rank_list = rank_list
        row.opening_rank = rec.get("opening_rank")
        row.closing_rank = rec.get("closing_rank")
        row.opening_is_preparatory = rec.get("opening_is_preparatory", False)
        row.closing_is_preparatory = rec.get("closing_is_preparatory", False)
        row.opening_rank_raw = rec.get("opening_rank_raw")
        row.closing_rank_raw = rec.get("closing_rank_raw")
        added += is_new
        updated += not is_new

    db.flush()
    _record_run(db, path, added, updated, [])
    return added, updated


def import_main_percentile_anchors(db: Session, path: Path) -> tuple[int, int]:
    data = _load(path)
    meta = data["metadata"]
    exam, year, rank_list = meta["exam"], meta["year"], meta["rank_list"]

    existing = {
        r.rank: r
        for r in db.query(models.PredictorMainPercentileAnchor).filter(
            models.PredictorMainPercentileAnchor.exam == exam,
            models.PredictorMainPercentileAnchor.year == year,
            models.PredictorMainPercentileAnchor.rank_list == rank_list,
        )
    }
    added = updated = 0
    for rec in data["records"]:
        row = existing.get(rec["rank"])
        is_new = row is None
        if is_new:
            row = models.PredictorMainPercentileAnchor(exam=exam, year=year, rank_list=rank_list, rank=rec["rank"])
            db.add(row)
            existing[rec["rank"]] = row
        row.percentile_display = rec["percentile_display"]
        row.source_type = meta["source_type"]
        row.source_url = meta.get("source_url")
        added += is_new
        updated += not is_new

    db.flush()
    _record_run(db, path, added, updated, [])
    return added, updated


def _upsert_marks_estimate(db: Session, existing: dict, *, year, session, shift_label, percentile_target, source_type, marks_low, marks_high, total_marks) -> bool:
    key = (year, session, shift_label, percentile_target, source_type)
    row = existing.get(key)
    is_new = row is None
    if is_new:
        row = models.PredictorMainMarksEstimate(
            year=year, session=session, shift_label=shift_label,
            percentile_target=percentile_target, source_type=source_type,
        )
        db.add(row)
        existing[key] = row
    row.marks_low = marks_low
    row.marks_high = marks_high
    row.total_marks = total_marks
    return is_new


def import_main_marks_estimates_generic(db: Session, path: Path) -> tuple[int, int]:
    """Single publisher threshold per percentile target (e.g. '230+') — stored as a degenerate
    marks_low == marks_high band; the shift-estimate file supplies real bands."""
    data = _load(path)
    existing = {
        (r.year, r.session, r.shift_label, r.percentile_target, r.source_type): r
        for r in db.query(models.PredictorMainMarksEstimate).filter(
            models.PredictorMainMarksEstimate.source_type == "generic_estimate"
        )
    }
    added = updated = 0
    for rec in data["records"]:
        is_new = _upsert_marks_estimate(
            db, existing,
            year=rec["year"], session=None, shift_label=None, percentile_target=rec["percentile_target"],
            source_type="generic_estimate",
            marks_low=rec["marks_threshold_reported"], marks_high=rec["marks_threshold_reported"],
            total_marks=rec["total_marks"],
        )
        added += is_new
        updated += not is_new

    db.flush()
    _record_run(db, path, added, updated, [])
    return added, updated


def import_main_marks_estimates_shift(db: Session, path: Path) -> tuple[int, int]:
    data = _load(path)
    existing = {
        (r.year, r.session, r.shift_label, r.percentile_target, r.source_type): r
        for r in db.query(models.PredictorMainMarksEstimate).filter(
            models.PredictorMainMarksEstimate.source_type == "shift_estimate"
        )
    }
    added = updated = 0
    for rec in data["records"]:
        is_new = _upsert_marks_estimate(
            db, existing,
            year=rec["year"], session=rec["session"], shift_label=rec["shift_label"],
            percentile_target=rec["percentile_target"], source_type="shift_estimate",
            marks_low=rec["marks_low"], marks_high=rec["marks_high"], total_marks=rec["total_marks"],
        )
        added += is_new
        updated += not is_new

    db.flush()
    _record_run(db, path, added, updated, [])
    return added, updated


def import_main_cohort_metrics(db: Session, path: Path) -> tuple[int, int]:
    data = _load(path)
    year = data["metadata"]["year"]
    existing = {
        (r.metric, r.category): r
        for r in db.query(models.PredictorMainCohortMetric).filter(models.PredictorMainCohortMetric.year == year)
    }
    added = updated = 0
    for rec in data["records"]:
        key = (rec["metric"], rec.get("category"))
        row = existing.get(key)
        is_new = row is None
        if is_new:
            row = models.PredictorMainCohortMetric(year=year, metric=rec["metric"], category=rec.get("category"))
            db.add(row)
            existing[key] = row
        row.value = rec["value"]
        added += is_new
        updated += not is_new

    db.flush()
    _record_run(db, path, added, updated, [])
    return added, updated


def import_advanced_marks_rank(db: Session, path: Path) -> tuple[int, int]:
    data = _load(path)
    year = data["metadata"]["year"]
    existing = {
        (r.rank_list, r.rank): r
        for r in db.query(models.PredictorAdvancedMarksRankAnchor).filter(
            models.PredictorAdvancedMarksRankAnchor.year == year
        )
    }
    added = updated = 0
    for rec in data["records"]:
        key = (rec["rank_list"], rec["rank"])
        row = existing.get(key)
        is_new = row is None
        if is_new:
            row = models.PredictorAdvancedMarksRankAnchor(year=year, rank_list=rec["rank_list"], rank=rec["rank"])
            db.add(row)
            existing[key] = row
        row.marks = rec["marks"]
        row.total_marks = rec["total_marks"]
        row.pdf_page = rec.get("pdf_page")
        row.section = rec.get("section")
        added += is_new
        updated += not is_new

    db.flush()
    _record_run(db, path, added, updated, [])
    return added, updated


def import_advanced_qualifying_cutoffs(db: Session, path: Path) -> tuple[int, int]:
    data = _load(path)
    year = data["metadata"]["year"]
    existing = {
        r.rank_list: r
        for r in db.query(models.PredictorAdvancedQualifyingCutoff).filter(
            models.PredictorAdvancedQualifyingCutoff.year == year
        )
    }
    added = updated = 0
    for rec in data["records"]:
        row = existing.get(rec["rank_list"])
        is_new = row is None
        if is_new:
            row = models.PredictorAdvancedQualifyingCutoff(year=year, rank_list=rec["rank_list"])
            db.add(row)
            existing[rec["rank_list"]] = row
        row.minimum_each_subject = rec["minimum_each_subject"]
        row.minimum_aggregate = rec["minimum_aggregate"]
        added += is_new
        updated += not is_new

    db.flush()
    _record_run(db, path, added, updated, [])
    return added, updated


def import_nirf_rankings(db: Session, path: Path) -> tuple[int, int]:
    data = _load(path)
    year = data["metadata"]["year"]
    existing = {
        r.nirf_id: r
        for r in db.query(models.PredictorNirfRanking).filter(models.PredictorNirfRanking.year == year)
    }
    added = updated = 0
    for rec in data["records"]:
        row = existing.get(rec["nirf_id"])
        is_new = row is None
        if is_new:
            row = models.PredictorNirfRanking(year=year, nirf_id=rec["nirf_id"])
            db.add(row)
            existing[rec["nirf_id"]] = row
        row.institute_name = rec["institute"]
        row.rank = rec["rank"]
        row.score = rec.get("score")
        # Exact-name match only against already-imported institutes — never fuzzy-merged.
        matched = db.query(models.PredictorInstitute).filter(models.PredictorInstitute.name == rec["institute"]).first()
        row.institute_id = matched.id if matched else None
        added += is_new
        updated += not is_new

    db.flush()
    _record_run(db, path, added, updated, [])
    return added, updated


# Order matters a little: institutes get created while importing JoSAA, so NIRF (which resolves
# institute_id by exact-name lookup) runs after.
FILE_IMPORTERS = {
    "josaa_2025_round_6.json": import_josaa,
    "josaa_2026_round_5.json": import_josaa,
    "main_2025_percentile_rank_sample.json": import_main_percentile_anchors,
    "main_2026_percentile_rank_sample.json": import_main_percentile_anchors,
    "main_2024_2026_generic_marks_estimates.json": import_main_marks_estimates_generic,
    "main_2026_april_shift_estimates.json": import_main_marks_estimates_shift,
    "main_2026_cohort_and_qualifying_cutoffs.json": import_main_cohort_metrics,
    "advanced_2024_marks_rank.json": import_advanced_marks_rank,
    "advanced_2025_marks_rank.json": import_advanced_marks_rank,
    "advanced_2025_qualifying_cutoffs.json": import_advanced_qualifying_cutoffs,
    "nirf_2025_engineering_top10.json": import_nirf_rankings,
}


def import_all(db: Session, data_dir: Path) -> dict:
    """data_dir is the pack's data/ folder; manifest.json is expected one level up."""
    manifest_path = data_dir.parent / "manifest.json"
    checksums: dict[str, str] = {}
    if manifest_path.is_file():
        manifest = _load(manifest_path)
        checksums = {f["path"]: f["sha256"] for f in manifest.get("files", [])}

    totals = {"files": 0, "added": 0, "updated": 0, "errors": []}
    for filename, importer in FILE_IMPORTERS.items():
        path = data_dir / filename
        if not path.is_file():
            totals["errors"].append(f"{filename}: not found, skipped")
            continue

        expected_hash = checksums.get(f"data/{filename}")
        if expected_hash and expected_hash != _sha256(path):
            totals["errors"].append(f"{filename}: sha256 does not match manifest.json — skipped")
            continue

        try:
            added, updated = importer(db, path)
        except Exception as e:  # noqa: BLE001 -- one bad file shouldn't abort the whole run
            db.rollback()
            totals["errors"].append(f"{filename}: {e}")
            continue

        totals["files"] += 1
        totals["added"] += added
        totals["updated"] += updated

    db.commit()
    return totals
