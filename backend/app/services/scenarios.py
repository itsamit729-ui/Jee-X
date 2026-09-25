"""Short JEE Main situations placed on a fictional three-hour exam timeline."""
import json
import math
import random
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app import models

EXAM_MINUTES = 180
PRESETS = (
    dict(key="stuck_30", title="The 30-minute trap", start_minute=70, duration_minutes=20,
         prior_answered=12, question_count=10, pressure="Two difficult questions took 30 minutes. One answer still feels uncertain.",
         objective="Recover your pace: scan, solve, skip, and return only when time permits."),
    dict(key="weak_subject", title="A subject took over", start_minute=95, duration_minutes=30,
         prior_answered=24, question_count=12, pressure="Mathematics took longer than planned. Physics and Chemistry need attention.",
         objective="Change subjects deliberately and collect reachable marks."),
    dict(key="review_overload", title="Too many to revisit", start_minute=135, duration_minutes=25,
         prior_answered=39, question_count=10, pressure="You marked several questions for review, but time is running down.",
         objective="Choose which questions deserve another look."),
    dict(key="easy_marks", title="The last easy marks", start_minute=150, duration_minutes=30,
         prior_answered=44, question_count=12, pressure="There are still approachable questions on the paper. You have 30 minutes left.",
         objective="Spot quick opportunities before committing to a long calculation."),
    dict(key="final_check", title="Final answer check", start_minute=165, duration_minutes=15,
         prior_answered=55, question_count=8, pressure="The exam ends in 15 minutes. Some answers need checking.",
         objective="Review selectively while keeping unanswered questions in sight."),
    dict(key="bad_start", title="Recover after a bad hour", start_minute=60, duration_minutes=45,
         prior_answered=10, question_count=18, pressure="The first hour did not go to plan. Many questions remain untouched.",
         objective="Rebuild momentum across all three subjects."),
)
BY_KEY = {preset["key"]: preset for preset in PRESETS}
_SUBJECTS = ("PHY", "CHEM", "MATH")
_AUTHORED = json.loads((Path(__file__).resolve().parents[1] / "data/scenario_questions.json").read_text(encoding="utf-8"))


def utcnow():
    # MySQL DATETIME returns naive timestamps; all scenario timestamps are UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_preset(key):
    preset = BY_KEY.get(key)
    if preset is None:
        raise HTTPException(404, "Unknown scenario.")
    return preset


def _authored_snapshot(item):
    return dict(id="sample:" + item["id"], ref=item["id"], subject=item["subject"],
                type=item["type"], stem=item["stem"], passage=None, assets=[],
                options=[dict(id=chr(65 + i), label=chr(65 + i), content=content)
                         for i, content in enumerate(item.get("options", []))],
                correct_option_ids=[item["correct"]] if item["type"] == "single_correct" else [],
                answer_min=item.get("answer"), answer_max=item.get("answer"), solution=item["solution"])


def _bank_snapshot(q, subject):
    return dict(id="bank:" + str(q.id), ref=q.ref, subject=subject, type=q.type,
                stem=q.stem, passage=q.passage.content if q.passage else None,
                assets=[dict(url=a.url, alt_text=a.alt_text) for a in list(q.assets) + (list(q.passage.assets) if q.passage else [])],
                options=[dict(id=o.label, label=o.label, content=o.content) for o in q.options],
                correct_option_ids=[o.label for o in q.options if o.is_correct],
                answer_min=q.answer_min, answer_max=q.answer_max, solution=q.solution)


def choose_questions(db, count):
    """Published JEE Main questions first, authored originals fill sparse subjects."""
    rows = (db.query(models.Question, models.Subject.code)
            .join(models.Subtopic, models.Question.subtopic_id == models.Subtopic.id)
            .join(models.Chapter, models.Subtopic.chapter_id == models.Chapter.id)
            .join(models.Subject, models.Chapter.subject_id == models.Subject.id)
            .options(joinedload(models.Question.options), joinedload(models.Question.assets),
                     joinedload(models.Question.passage).joinedload(models.Passage.assets))
            .filter(models.Question.status == "published", models.Question.type.in_(("single_correct", "numerical")),
                    or_(models.Question.exam == "jee_main", models.Question.exam.is_(None))).all())
    pools = {subject: [] for subject in _SUBJECTS}
    for q, subject in rows:
        if q.type == "single_correct" and (len(q.options) != 4 or sum(bool(o.is_correct) for o in q.options) != 1):
            continue
        if q.type == "numerical" and (q.answer_min is None or q.answer_max is None or
                                      not math.isfinite(q.answer_min) or not math.isfinite(q.answer_max) or
                                      q.answer_min != q.answer_max or not float(q.answer_min).is_integer()):
            continue
        pools[subject].append(_bank_snapshot(q, subject))
    for items in pools.values():
        random.shuffle(items)
    authored = {subject: [] for subject in _SUBJECTS}
    for item in _AUTHORED:
        authored[item["subject"]].append(_authored_snapshot(item))
    for subject in _SUBJECTS:
        random.shuffle(authored[subject])
        pools[subject] = deque(pools[subject] + authored[subject])
    picked = []
    while len(picked) < count and any(pools.values()):
        for subject in _SUBJECTS:
            if pools[subject] and len(picked) < count:
                picked.append(pools[subject].popleft())
    if len(picked) < count:
        raise HTTPException(503, "Not enough questions are available for this scenario yet.")
    random.shuffle(picked)
    return picked


def public_question(q):
    return {key: q[key] for key in ("id", "ref", "subject", "type", "stem", "passage", "assets", "options")}


def grade(questions, answers):
    results = []
    for q in questions:
        a = answers.get(q["id"], {})
        selected = a.get("option_ids", [])
        number = a.get("numeric_answer")
        attempted = number is not None if q["type"] == "numerical" else bool(selected)
        correct = (q["answer_min"] <= number <= q["answer_max"]) if q["type"] == "numerical" and attempted else (
            set(selected) == set(q["correct_option_ids"]) if attempted else False)
        outcome = "correct" if correct else "wrong" if attempted else "skipped"
        results.append(dict(id=q["id"], ref=q["ref"], outcome=outcome,
                            marks=4 if correct else -1 if attempted else 0,
                            correct_option_ids=q["correct_option_ids"],
                            correct_numeric_answer=q["answer_min"] if q["type"] == "numerical" else None,
                            solution=q["solution"], time_spent_sec=a.get("time_spent_sec", 0),
                            marked_for_review=a.get("marked_for_review", False)))
    attempted = sum(r["outcome"] != "skipped" for r in results)
    correct = sum(r["outcome"] == "correct" for r in results)
    return dict(score=sum(r["marks"] for r in results), possible_marks=len(results) * 4,
                attempted=attempted, correct=correct, wrong=attempted - correct,
                skipped=len(results) - attempted, questions=results)


def finish(run, now=None):
    if run.submitted_at is None:
        run.submitted_at = now or utcnow()
        run.result = grade(run.questions, run.answers or {})
    return run


def serialize(run, now=None):
    now = now or utcnow()
    preset = get_preset(run.scenario_key)
    end = run.submitted_at or now
    elapsed = min(preset["duration_minutes"] * 60, max(0, int((end - run.started_at).total_seconds())))
    return dict(id=run.id, scenario=preset, exam_minutes=EXAM_MINUTES,
                started_at=run.started_at.isoformat() + "Z", deadline_at=run.deadline_at.isoformat() + "Z",
                server_now=now.isoformat() + "Z", elapsed_sec=elapsed,
                seconds_left=0 if run.submitted_at else max(0, int((run.deadline_at - now).total_seconds())),
                status="finished" if run.submitted_at else "active",
                questions=[public_question(q) for q in run.questions], answers=run.answers or {}, result=run.result)
