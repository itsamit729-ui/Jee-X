"""Loads backend/data/questions/<subject>/<chapter>.json (here: generated/questions/**)
into the database, per docs/database-schema.md section 15 (file -> table mapping) and
section 13 rule 2 (content_hash / version / question_revisions bookkeeping)."""

import hashlib
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app import models

SUBJECT_NAMES = {"PHY": "Physics", "CHEM": "Chemistry", "MATH": "Mathematics", "ENG": "English Proficiency", "LR": "Logical Reasoning"}


def _content_hash(question: dict) -> str:
    payload = json.dumps(question, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_or_create_subject(db: Session, code: str) -> models.Subject:
    subject = db.query(models.Subject).filter(models.Subject.code == code).first()
    if subject:
        return subject
    subject = models.Subject(code=code, name=SUBJECT_NAMES.get(code, code))
    db.add(subject)
    db.flush()
    return subject


def _upsert_chapter(db: Session, subject: models.Subject, chapter_data: dict) -> models.Chapter:
    chapter = (
        db.query(models.Chapter)
        .filter(models.Chapter.subject_id == subject.id, models.Chapter.slug == chapter_data["slug"])
        .first()
    )
    if not chapter:
        chapter = models.Chapter(subject_id=subject.id, slug=chapter_data["slug"])
        db.add(chapter)
    chapter.name = chapter_data["name"]
    chapter.class_level = chapter_data["class_level"]
    chapter.in_main = chapter_data.get("in_main", True)
    chapter.in_advanced = chapter_data.get("in_advanced", True)
    chapter.position = chapter_data.get("position", 0)
    db.flush()
    return chapter


def _upsert_subtopics(db: Session, chapter: models.Chapter, subtopics_data: list[dict]) -> dict[str, models.Subtopic]:
    by_slug: dict[str, models.Subtopic] = {}
    for st_data in subtopics_data:
        subtopic = (
            db.query(models.Subtopic)
            .filter(models.Subtopic.chapter_id == chapter.id, models.Subtopic.slug == st_data["slug"])
            .first()
        )
        if not subtopic:
            subtopic = models.Subtopic(chapter_id=chapter.id, slug=st_data["slug"])
            db.add(subtopic)
        subtopic.name = st_data["name"]
        subtopic.position = st_data.get("position", 0)
        db.flush()
        by_slug[st_data["slug"]] = subtopic
    return by_slug


def _upsert_passages(db: Session, passages_data: list[dict]) -> dict[str, models.Passage]:
    by_ref: dict[str, models.Passage] = {}
    for p_data in passages_data:
        passage = db.query(models.Passage).filter(models.Passage.ref == p_data["ref"]).first()
        if not passage:
            passage = models.Passage(ref=p_data["ref"])
            db.add(passage)
        passage.content = p_data["content"]
        db.flush()
        by_ref[p_data["ref"]] = passage
    return by_ref


def _upsert_question_assets(db: Session, question: models.Question, image: dict | None):
    existing = db.query(models.Asset).filter(models.Asset.question_id == question.id).first()
    if image is None:
        if existing:
            db.delete(existing)
        return
    if not existing:
        existing = models.Asset(question_id=question.id)
        db.add(existing)
    existing.url = image.get("url")
    existing.alt_text = image.get("alt", "")


def _upsert_options(db: Session, question: models.Question, options_data: list[dict]):
    existing_by_label = {o.label: o for o in question.options}
    for i, opt_data in enumerate(options_data, start=1):
        label = opt_data["label"]
        option = existing_by_label.get(label)
        if not option:
            option = models.QuestionOption(question_id=question.id, label=label)
            db.add(option)
        option.content = opt_data["content"]
        option.is_correct = opt_data["is_correct"]
        option.position = i


def _sync_also_subtopics(db: Session, question: models.Question, also_slugs: list[str], subtopics_by_slug: dict[str, models.Subtopic]):
    wanted_ids = {subtopics_by_slug[slug].id for slug in also_slugs if slug in subtopics_by_slug}
    existing = {qs.subtopic_id: qs for qs in question.also_subtopics}
    for subtopic_id in wanted_ids - existing.keys():
        db.add(models.QuestionSubtopic(question_id=question.id, subtopic_id=subtopic_id))
    for subtopic_id, row in existing.items():
        if subtopic_id not in wanted_ids:
            db.delete(row)


def import_chapter_file(db: Session, path: Path, run_by: int | None = None) -> dict:
    """Imports one chapter JSON file. Returns {'added': int, 'updated': int, 'errors': list}."""
    data = json.loads(path.read_text(encoding="utf-8"))
    subject = _get_or_create_subject(db, data["subject"])
    chapter = _upsert_chapter(db, subject, data["chapter"])
    subtopics_by_slug = _upsert_subtopics(db, chapter, data.get("subtopics", []))
    passages_by_ref = _upsert_passages(db, data.get("passages", []))

    added = 0
    updated = 0
    errors: list[str] = []

    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    import_run = models.ImportRun(file_path=str(path), file_hash=file_hash, run_by=run_by)
    db.add(import_run)
    db.flush()

    for q_data in data.get("questions", []):
        ref = q_data["ref"]
        try:
            subtopic = subtopics_by_slug[q_data["subtopic"]]
        except KeyError:
            errors.append(f"{ref}: unknown subtopic slug {q_data['subtopic']!r}")
            continue

        content_hash = _content_hash(q_data)
        question = db.query(models.Question).filter(models.Question.ref == ref).first()
        is_new = question is None
        if is_new:
            question = models.Question(ref=ref)
            db.add(question)
        elif question.content_hash == content_hash:
            # Unchanged since last import — nothing to do.
            continue

        answer = q_data.get("answer") or {}
        question.subtopic_id = subtopic.id
        question.passage_id = passages_by_ref[q_data["passage"]].id if q_data.get("passage") else None
        question.type = q_data["type"]
        question.stem = q_data["stem"]
        question.answer_min = answer.get("min")
        question.answer_max = answer.get("max")
        question.solution = q_data["solution"]
        question.difficulty = q_data["difficulty"]
        question.expected_time_sec = q_data["expected_time_sec"]
        question.source_type = q_data["source_type"]
        question.exam = q_data.get("exam")
        question.year = q_data.get("year")
        question.shift = q_data.get("shift")
        question.status = q_data.get("status", "draft")
        question.content_hash = content_hash
        question.version = 1 if is_new else question.version + 1
        db.flush()

        _upsert_options(db, question, q_data.get("options", []))
        _upsert_question_assets(db, question, q_data.get("image"))
        _sync_also_subtopics(db, question, q_data.get("also_subtopics", []), subtopics_by_slug)
        db.flush()

        db.add(
            models.QuestionRevision(
                question_id=question.id,
                version=question.version,
                content=q_data,
                import_run_id=import_run.id,
            )
        )

        if is_new:
            added += 1
        else:
            updated += 1

    import_run.added = added
    import_run.updated = updated
    import_run.errors = errors or None
    db.commit()
    return {"added": added, "updated": updated, "errors": errors}


def import_directory(db: Session, root: Path, run_by: int | None = None) -> dict:
    totals = {"added": 0, "updated": 0, "errors": [], "files": 0}
    for path in sorted(root.glob("*/*.json")):
        if any(part.startswith(".") for part in path.parts):
            continue
        result = import_chapter_file(db, path, run_by=run_by)
        totals["added"] += result["added"]
        totals["updated"] += result["updated"]
        totals["errors"].extend(f"{path.name}: {e}" for e in result["errors"])
        totals["files"] += 1
    return totals
