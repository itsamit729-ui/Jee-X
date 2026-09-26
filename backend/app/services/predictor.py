"""Service 4: rank/percentile/college prediction for a submitted test attempt.

Pipeline: raw score -> JEE-Main-equivalent marks (scaled to /300) -> estimated percentile band
-> estimated CRL rank band -> historical JoSAA college matches. See
docs/JEE-Predictor-Data/jee-predictor-data/README.md for the source data's own cautions, which
this pipeline follows: interpolate within the observed range only, never invent an upper/lower
bound the source doesn't have, and never claim category-specific ranks without a category rank
list (general/CRL only here — see models/predictor.py's module docstring).
"""

import math

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app import models

MAIN_EXAM_ROUTE = "JEE_MAIN_PAPER1"
CRL = "CRL"
FULL_LENGTH_MIN_QUESTIONS = 60
COLLEGE_MATCH_LIMIT = 30

DISCLAIMERS = {
    "full_length_mock": (
        "Estimated from a full-length mock, scaled to a JEE Main 300-mark paper. Historical "
        "reference data only — not an official NTA percentile or an admission promise."
    ),
    "partial_practice": (
        "Rough, indicative estimate — extrapolated from a shorter practice test, not a "
        "calibrated full-length mock. Treat this as a broad benchmark, not a precise national rank."
    ),
    "insufficient_data": (
        "Your scaled score is below the range covered by our reference data, so we can't "
        "estimate a reliable national percentile yet."
    ),
}


def scale_to_main_300(raw_score: float, raw_max_score: float) -> float:
    if raw_max_score <= 0:
        return 0.0
    scaled = raw_score / raw_max_score * 300
    return max(-75.0, min(300.0, scaled))


def _linear_interp(x: float, points: list[tuple[float, float]]) -> tuple[float | None, str]:
    """points: [(x, y), ...], any order. Returns (y at x, basis)."""
    if not points:
        return None, "insufficient_data"
    pts = sorted(points, key=lambda p: p[0])
    if x < pts[0][0]:
        return None, "insufficient_data"
    if x >= pts[-1][0]:
        basis = "interpolated" if x == pts[-1][0] else "above_highest_reference_band"
        return pts[-1][1], basis
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            if x1 == x0:
                return y0, "interpolated"
            frac = (x - x0) / (x1 - x0)
            return y0 + frac * (y1 - y0), "interpolated"
    return None, "insufficient_data"  # unreachable given sorted, bounded pts


def _log_interp(x: float, points: list[tuple[float, float]]) -> tuple[float | None, str]:
    """Like _linear_interp but interpolates y in log-space (for rank, which spans orders of
    magnitude while percentile doesn't)."""
    safe = [(px, math.log(py)) for px, py in points if py > 0]
    y, basis = _linear_interp(x, safe)
    if y is None:
        return None, basis
    return math.exp(y), basis


def _latest_year(db: Session, model, **filters) -> int | None:
    q = db.query(func.max(model.year))
    for key, value in filters.items():
        q = q.filter(getattr(model, key) == value)
    return q.scalar()


def _marks_percentile_curves(db: Session, year: int) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Combines generic + shift marks-estimate rows for `year`, grouped by percentile_target,
    into two curves: the min marks_low and max marks_high observed at each target. This is the
    band's real spread from the source data, not an invented widening constant."""
    rows = db.query(models.PredictorMainMarksEstimate).filter(models.PredictorMainMarksEstimate.year == year).all()
    by_target: dict[float, list[models.PredictorMainMarksEstimate]] = {}
    for r in rows:
        by_target.setdefault(r.percentile_target, []).append(r)

    low_curve = [(min(r.marks_low for r in g), target) for target, g in by_target.items()]
    high_curve = [(max(r.marks_high for r in g), target) for target, g in by_target.items()]
    return low_curve, high_curve


def estimate_percentile(db: Session, scaled_marks: float, year: int) -> dict:
    low_curve, high_curve = _marks_percentile_curves(db, year)
    # Reaching the LOW end of a percentile's marks band is the easier bar -> optimistic (high) estimate.
    percentile_high, basis_high = _linear_interp(scaled_marks, low_curve)
    # Reaching the HIGH end of a percentile's marks band is the harder bar -> conservative (low) estimate.
    percentile_low, basis_low = _linear_interp(scaled_marks, high_curve)

    if percentile_low is None or percentile_high is None:
        return {"percentile_low": None, "percentile_high": None, "basis": "insufficient_data"}

    percentile_low = max(0.0, min(percentile_low, 99.99))
    percentile_high = max(0.0, min(percentile_high, 99.999))
    basis = "above_highest_reference_band" if "above_highest_reference_band" in (basis_low, basis_high) else "interpolated"
    return {"percentile_low": percentile_low, "percentile_high": percentile_high, "basis": basis}


def estimate_rank(db: Session, percentile_low: float | None, percentile_high: float | None, year: int) -> dict:
    if percentile_low is None or percentile_high is None:
        return {"rank_low": None, "rank_high": None, "basis": "insufficient_data"}

    points = [
        (r.percentile_display, r.rank)
        for r in db.query(models.PredictorMainPercentileAnchor).filter(
            models.PredictorMainPercentileAnchor.year == year,
            models.PredictorMainPercentileAnchor.rank_list == CRL,
        )
    ]
    rank_low, basis_low = _log_interp(percentile_high, points)  # higher percentile -> better (lower) rank
    rank_high, basis_high = _log_interp(percentile_low, points)  # lower percentile -> worse (higher) rank

    if rank_low is None or rank_high is None:
        return {"rank_low": None, "rank_high": None, "basis": "insufficient_data"}

    basis = "above_highest_reference_band" if "above_highest_reference_band" in (basis_low, basis_high) else "interpolated"
    return {"rank_low": max(1, round(rank_low)), "rank_high": max(1, round(rank_high)), "basis": basis}


def _raw_score_and_max(attempt: "models.TestAttempt") -> tuple[float, float]:
    test = attempt.test
    if test.test_questions:
        max_score = sum(tq.marks_correct for tq in test.test_questions)
        if not max_score:
            max_score = (attempt.total_questions or 0) * 4
        return float(attempt.score or 0), float(max_score)

    # Legacy free_diagnostic / mock attempts have no TestQuestion rows — attempt.score is a raw
    # correct-answer COUNT, not marks-with-negative-marking (see frontend Analysis.jsx's
    # toAttemptPayload comment). Approximate marks as correct * 4; the disclaimer says so.
    total_q = attempt.total_questions or 0
    return float((attempt.score or 0) * 4), float(total_q * 4)


def _confidence(attempt: "models.TestAttempt") -> str:
    test = attempt.test
    if test.kind == "mock" and len(test.test_questions) == 75:
        return "full_length_mock"
    return "partial_practice"


def predict_for_attempt(db: Session, attempt: "models.TestAttempt") -> "models.PredictorAttemptPrediction":
    raw_score, raw_max_score = _raw_score_and_max(attempt)
    scaled_marks = scale_to_main_300(raw_score, raw_max_score)
    confidence = _confidence(attempt)

    marks_year = _latest_year(db, models.PredictorMainMarksEstimate)
    percentile = {"percentile_low": None, "percentile_high": None, "basis": "insufficient_data"}
    rank = {"rank_low": None, "rank_high": None, "basis": "insufficient_data"}
    reference_year = marks_year
    if marks_year is not None:
        percentile = estimate_percentile(db, scaled_marks, marks_year)
        rank_year = _latest_year(db, models.PredictorMainPercentileAnchor, rank_list=CRL) or marks_year
        rank = estimate_rank(db, percentile["percentile_low"], percentile["percentile_high"], rank_year)
        reference_year = rank_year

    if percentile["percentile_low"] is None:
        confidence = "insufficient_data"

    prediction = (
        db.query(models.PredictorAttemptPrediction)
        .filter(models.PredictorAttemptPrediction.attempt_id == attempt.id)
        .first()
    )
    if prediction is None:
        prediction = models.PredictorAttemptPrediction(attempt_id=attempt.id, user_id=attempt.user_id)
        db.add(prediction)

    prediction.raw_score = raw_score
    prediction.raw_max_score = raw_max_score
    prediction.scaled_marks_300 = scaled_marks
    prediction.reference_year = reference_year
    prediction.percentile_low = percentile["percentile_low"]
    prediction.percentile_high = percentile["percentile_high"]
    prediction.percentile_basis = percentile["basis"]
    prediction.rank_low = rank["rank_low"]
    prediction.rank_high = rank["rank_high"]
    prediction.rank_basis = rank["basis"]
    prediction.confidence = confidence
    prediction.disclaimer = DISCLAIMERS[confidence]

    db.commit()
    db.refresh(prediction)
    return prediction


MATCH_QUOTAS = ("AI", "OS")


def match_colleges(db: Session, rank_low: int | None, rank_high: int | None, quotas=MATCH_QUOTAS) -> list[dict]:
    """AI (all-India, used by IITs/IIITs) + OS (other-state, one of the two pools every NIT
    splits its seats into) — Gender-Neutral pool + CRL rank list only, deliberately.

    Without a student's home state we can't resolve HS ("home state") rows, so those are
    excluded — showing them would overstate access for students not actually from that state,
    and the data pack explicitly warns against guessing that. OS is the safe default: OS seats
    are open to a student from *any* state other than the institute's own, so it's the broadest
    quota we can show without knowing where the student lives. It just means an NIT's OWN home
    state's applicants would actually see a better (lower) rank there than what's shown here."""
    if rank_low is None:
        return []

    latest = (
        db.query(models.PredictorJosaaCutoff.year, models.PredictorJosaaCutoff.round)
        .filter(
            models.PredictorJosaaCutoff.exam_route == MAIN_EXAM_ROUTE,
            models.PredictorJosaaCutoff.rank_list == CRL,
        )
        .order_by(models.PredictorJosaaCutoff.year.desc(), models.PredictorJosaaCutoff.round.desc())
        .first()
    )
    if latest is None:
        return []
    year, round_ = latest

    rows = (
        db.query(models.PredictorJosaaCutoff)
        .options(joinedload(models.PredictorJosaaCutoff.institute), joinedload(models.PredictorJosaaCutoff.program))
        .filter(
            models.PredictorJosaaCutoff.year == year,
            models.PredictorJosaaCutoff.round == round_,
            models.PredictorJosaaCutoff.exam_route == MAIN_EXAM_ROUTE,
            models.PredictorJosaaCutoff.rank_list == CRL,
            models.PredictorJosaaCutoff.quota.in_(quotas),
            models.PredictorJosaaCutoff.gender_pool == "Gender-Neutral",
            models.PredictorJosaaCutoff.opening_is_preparatory.is_(False),
            models.PredictorJosaaCutoff.closing_is_preparatory.is_(False),
            models.PredictorJosaaCutoff.closing_rank.isnot(None),
            models.PredictorJosaaCutoff.closing_rank >= rank_low,
        )
        .order_by(models.PredictorJosaaCutoff.closing_rank.asc())
        .limit(COLLEGE_MATCH_LIMIT)
        .all()
    )

    nirf_year = db.query(func.max(models.PredictorNirfRanking.year)).scalar()
    nirf_by_institute: dict[int, int] = {}
    if nirf_year is not None:
        nirf_by_institute = {
            r.institute_id: r.rank
            for r in db.query(models.PredictorNirfRanking).filter(
                models.PredictorNirfRanking.year == nirf_year,
                models.PredictorNirfRanking.institute_id.isnot(None),
            )
        }

    return [
        {
            "institute": row.institute.name,
            "program": row.program.name,
            "quota": row.quota,
            "seat_type": row.seat_type,
            "gender_pool": row.gender_pool,
            "opening_rank": row.opening_rank,
            "closing_rank": row.closing_rank,
            "reference_year": row.year,
            "reference_round": row.round,
            "nirf_rank": nirf_by_institute.get(row.institute_id),
            "result_label": "within_historical_closing_rank",
            "meets_conservative_estimate": rank_high is not None and row.closing_rank >= rank_high,
        }
        for row in rows
    ]
