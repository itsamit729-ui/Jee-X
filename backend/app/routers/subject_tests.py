"""Build fixed practice sessions and persist their recommendation evidence."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session, selectinload
from app import models, schemas
from app.database import get_db
from app.deps import get_current_db_user
from app.services.practice import choose_questions

router = APIRouter(prefix='/api/subject-tests', tags=['subject-tests'])


@router.post('', response_model=schemas.SubjectTestOut, status_code=201)
def create_subject_test(body: schemas.SubjectTestCreate,
                        user: models.User = Depends(get_current_db_user), db: Session = Depends(get_db)):
    if body.mode == 'topic' and not body.subject_code:
        raise HTTPException(422, 'Choose a subject for topic practice.')
    subject = db.query(models.Subject).filter_by(code=body.subject_code).first() if body.subject_code else None
    if body.subject_code and not subject:
        raise HTTPException(404, 'Unknown subject.')
    if body.chapter_id:
        chapter = db.get(models.Chapter, body.chapter_id)
        if not chapter or not subject or chapter.subject_id != subject.id:
            raise HTTPException(422, 'Choose a chapter belonging to this subject.')
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
                      models.Question.expected_time_sec, models.Subtopic.name.label('topic'))
             .join(models.Subtopic).join(models.Chapter)
             .filter(models.Question.status == 'published', func.length(func.trim(models.Question.stem)) > 0,
                     func.length(func.trim(models.Question.solution)) > 0,
                     ~models.Question.assets.any(bad_asset),
                     ~models.Question.passage.has(models.Passage.assets.any(bad_asset)),
                     or_(and_(models.Question.type == 'single_correct', option_count >= 2, correct_count == 1),
                         and_(models.Question.type == 'numerical', models.Question.answer_min.isnot(None),
                              models.Question.answer_max.isnot(None)))))
    if subject:
        query = query.filter(models.Chapter.subject_id == subject.id)
    if body.chapter_id:
        query = query.filter(models.Chapter.id == body.chapter_id)
    candidates = query.all()
    if not candidates:
        raise HTTPException(404, 'No complete practice questions are available for this choice yet. Try another topic.')
    history = (db.query(models.QuestionResponse.question_id, models.QuestionResponse.outcome,
                        models.QuestionResponse.time_taken_sec, models.QuestionResponse.answered_at,
                        models.Question.subtopic_id, models.Question.difficulty, models.Question.expected_time_sec)
               .join(models.Question, models.Question.id == models.QuestionResponse.question_id)
               .join(models.TestAttempt, models.TestAttempt.id == models.QuestionResponse.attempt_id)
               .filter(models.QuestionResponse.user_id == user.id, models.TestAttempt.user_id == user.id,
                       models.TestAttempt.submitted_at.isnot(None))
               .order_by(models.QuestionResponse.answered_at.desc(), models.QuestionResponse.id.desc()).limit(500).all())
    count = {5: 3, 15: 8, 30: 16}.get(body.duration_minutes, body.count)
    selection = choose_questions(candidates, history, count, body.mode)
    reasons = dict(selection)
    rows = (db.query(models.Question).filter(models.Question.id.in_(reasons))
            .options(selectinload(models.Question.options), selectinload(models.Question.assets),
                     selectinload(models.Question.passage).selectinload(models.Passage.assets)).all())
    by_id = {q.id: q for q in rows}
    picked = [by_id[qid] for qid, _ in selection]
    title = f'{subject.name} practice' if subject else 'Personalised practice'
    if body.mode == 'revision':
        title = 'Quick revision' + (f' · {subject.name}' if subject else '')
    test = models.Test(title=title, kind='chapter', pattern='jee_main',
                       duration_sec=(body.duration_minutes * 60 if body.duration_minutes else len(picked) * 90),
                       ranked=False, generated_for_user_id=user.id)
    db.add(test)
    db.flush()
    for position, q in enumerate(picked, 1):
        db.add(models.TestQuestion(test_id=test.id, question_id=q.id, position=position,
                                  marks_correct=4, marks_wrong=0 if q.type == 'numerical' else 1, partial_marking=False))
        db.add(models.PracticeRecommendation(test_id=test.id, question_id=q.id, explanation=reasons[q.id]))
    attempt = models.TestAttempt(user_id=user.id, test_id=test.id, attempt_number=1, counts_for_rank=False)
    db.add(attempt)
    db.flush()
    # Serialize before commit expires ORM objects, avoiding per-question reloads.
    result = schemas.SubjectTestOut(attempt_id=attempt.id, test_id=test.id, title=title,
        subject_code=subject.code if subject else 'MIX', duration_sec=test.duration_sec,
        questions=[schemas.TestQuestionOut(question_id=q.id, ref=q.ref, type=q.type, stem=q.stem,
            assets=[schemas.QuestionAssetOut(url=a.url, alt_text=a.alt_text)
                    for a in list(q.assets) + (list(q.passage.assets) if q.passage else [])],
            passage=q.passage.content if q.passage else None,
            options=[schemas.TestOptionOut(id=o.id, label=o.label, content=o.content) for o in q.options],
            marks_correct=4, marks_wrong=0 if q.type == 'numerical' else 1,
            recommendation=schemas.RecommendationOut(**reasons[q.id])) for q in picked])
    db.commit()
    return result
