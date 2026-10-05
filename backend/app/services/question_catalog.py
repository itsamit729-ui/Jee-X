"""Shared eligibility rules for practice papers and topic planning."""
from sqlalchemy import or_, and_, func
from app import models


def candidate_query(db, exam=None):
    # Only complete, supported question content. Do not fetch image bytes during selection.
    valid_url = or_(models.Asset.url.like('https://%'),
                    and_(models.Asset.url.like('/%'), ~models.Asset.url.like('//%')))
    bad_asset = or_(models.Asset.url.is_(None), ~valid_url)
    option_count = db.query(func.count(models.QuestionOption.id)).filter(
        models.QuestionOption.question_id == models.Question.id).correlate(models.Question).scalar_subquery()
    correct_count = db.query(func.count(models.QuestionOption.id)).filter(
        models.QuestionOption.question_id == models.Question.id, models.QuestionOption.is_correct.is_(True)
    ).correlate(models.Question).scalar_subquery()
    query = (db.query(models.Question.id, models.Question.subtopic_id, models.Question.difficulty,
                      models.Question.expected_time_sec, models.Subtopic.name.label('topic'),
                      models.Question.type, models.Chapter.subject_id, models.Chapter.id.label('chapter_id'))
             .select_from(models.Question)
             .join(models.Subtopic, models.Subtopic.id == models.Question.subtopic_id)
             .join(models.Chapter, models.Chapter.id == models.Subtopic.chapter_id)
             .filter(models.Question.status == 'published', func.length(func.trim(models.Question.stem)) > 0,
                     func.length(func.trim(models.Question.solution)) > 0,
                     ~models.Question.assets.any(bad_asset),
                     ~models.Question.passage.has(models.Passage.assets.any(bad_asset)),
                     or_(and_(models.Question.type == 'single_correct', option_count >= 2, correct_count == 1),
                         and_(models.Question.type == 'numerical', models.Question.answer_min.isnot(None),
                              models.Question.answer_max.isnot(None)))))
    if exam:
        query = query.filter(models.Question.exam == exam)
    else:
        query = query.filter(or_(models.Question.exam.is_(None), models.Question.exam.in_(['jee_main', 'jee_advanced'])))
    return query


