"""Shared exact-choice / numeric-range grading for practice and classroom tests."""
from app import models, schemas

def _grade_one(question: models.Question, answer: schemas.SubjectTestAnswerIn) -> tuple[str, set[int]]:
    """Returns (outcome, correct_option_ids)."""
    correct_option_ids = {o.id for o in question.options if o.is_correct}

    if question.type == "numerical":
        if answer.numeric_answer is None:
            return "skipped", correct_option_ids
        in_range = (question.answer_min or 0) <= answer.numeric_answer <= (question.answer_max or 0)
        return ("correct" if in_range else "wrong"), correct_option_ids

    chosen = set(answer.option_ids)
    if not chosen:
        return "skipped", correct_option_ids
    return ("correct" if chosen == correct_option_ids else "wrong"), correct_option_ids

