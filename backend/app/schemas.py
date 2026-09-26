import re
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


class OnboardingIn(BaseModel):
    name: str
    username: str
    dob: date
    class_level: Literal["11", "12", "dropper"]

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters.")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 3-20 characters: letters, numbers, underscore only.")
        return v

    @field_validator("dob")
    @classmethod
    def dob_reasonable(cls, v: date) -> date:
        age_days = (date.today() - v).days
        if age_days < 10 * 365 or age_days > 30 * 365:
            raise ValueError("Please enter a valid date of birth.")
        return v


class ProfileUpdate(BaseModel):
    name: str
    username: str
    dob: date
    class_level: Literal["11", "12", "dropper"]

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters.")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 3-20 characters: letters, numbers, underscore only.")
        return v

    @field_validator("dob")
    @classmethod
    def dob_reasonable(cls, v: date) -> date:
        age_days = (date.today() - v).days
        if age_days < 10 * 365 or age_days > 30 * 365:
            raise ValueError("Please enter a valid date of birth.")
        return v


class UserOut(BaseModel):
    id: int
    name: str
    username: str
    dob: date
    class_level: str
    email: str | None = None
    avatar_url: str | None = None

    class Config:
        from_attributes = True


class UsernameAvailability(BaseModel):
    username: str
    available: bool


class SubjectBreakdown(BaseModel):
    correct: int
    total: int


class TestAttemptIn(BaseModel):
    test_type: Literal["free_diagnostic", "full_mock"] = "free_diagnostic"
    score: int
    total_questions: int
    accuracy: float
    avg_time_seconds: float
    subject_breakdown: dict[str, SubjectBreakdown]

    @field_validator("score", "total_questions")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Value must not be negative.")
        return v

    @field_validator("accuracy")
    @classmethod
    def accuracy_in_range(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError("Accuracy must be between 0 and 100.")
        return v


class TestAttemptOut(BaseModel):
    id: int
    test_type: str
    score: int
    total_questions: int
    accuracy: float
    avg_time_seconds: float
    subject_breakdown: dict
    created_at: datetime


# ---------------------------------------------------------------------------
# Subject-wise tests: content catalog, test creation, submission/grading.
# ---------------------------------------------------------------------------


class SubjectOut(BaseModel):
    code: str
    name: str
    chapter_count: int
    published_question_count: int


class ChapterOut(BaseModel):
    id: int
    name: str
    slug: str
    class_level: str
    position: int
    published_question_count: int


class SubjectTestCreate(BaseModel):
    assessment: bool = False
    subject_code: Literal["PHY", "CHEM", "MATH"] | None = None
    mode: Literal["recommended", "topic", "revision"] = "topic"
    duration_minutes: Literal[5, 15, 30] | None = None
    chapter_id: int | None = None
    count: int = 10

    @field_validator("count")
    @classmethod
    def count_in_range(cls, v: int) -> int:
        if not (1 <= v <= 30):
            raise ValueError("count must be between 1 and 30.")
        return v


class TestOptionOut(BaseModel):
    id: int
    label: str
    content: str


class QuestionAssetOut(BaseModel):
    url: str | None = None
    alt_text: str = ""


class RecommendationOut(BaseModel):
    reason_code: str
    reason: str
    learning_goal: str
    evidence: dict
    repeated: bool = False


class TestQuestionOut(BaseModel):
    question_id: int
    ref: str
    type: str
    stem: str
    assets: list[QuestionAssetOut] = Field(default_factory=list)
    passage: str | None = None
    options: list[TestOptionOut]
    marks_correct: int
    marks_wrong: int
    recommendation: RecommendationOut | None = None


class SubjectTestOut(BaseModel):
    attempt_id: int
    test_id: int
    title: str
    subject_code: str
    duration_sec: int
    questions: list[TestQuestionOut]


class SubjectTestAnswerIn(BaseModel):
    question_id: int
    option_ids: list[int] = []
    numeric_answer: float | None = None
    time_taken_sec: int = Field(default=0, ge=0, le=86400)


class SubjectTestSubmitIn(BaseModel):
    answers: list[SubjectTestAnswerIn]


class QuestionResultOut(BaseModel):
    question_id: int
    ref: str
    outcome: str
    marks_awarded: int
    correct_option_ids: list[int]
    solution: str


class SubjectTestResultOut(BaseModel):
    attempt_id: int
    score: int
    total_questions: int
    accuracy: float
    avg_time_seconds: float
    subject_breakdown: dict
    questions: list[QuestionResultOut]
    coins_earned: int = 0
    current_streak: int | None = None


# ---------------------------------------------------------------------------
# Rank/percentile/college predictor: reads docs/JEE-Predictor-Data via
# app/services/predictor.py. General/CRL category, JEE Main only — see that
# module's docstring for scope notes.
# ---------------------------------------------------------------------------


class PercentileBand(BaseModel):
    low: float | None = None
    high: float | None = None
    basis: str


class RankBand(BaseModel):
    low: int | None = None
    high: int | None = None
    basis: str


class CollegeMatchOut(BaseModel):
    rank_list: str = "CRL"
    compared_rank_low: int | None = None
    compared_rank_high: int | None = None
    institute: str
    program: str
    quota: str
    seat_type: str
    gender_pool: str
    opening_rank: int | None = None
    closing_rank: int | None = None
    reference_year: int
    reference_round: int
    nirf_rank: int | None = None
    result_label: str
    meets_conservative_estimate: bool


class PredictionOut(BaseModel):
    attempt_id: int
    raw_score: float
    raw_max_score: float
    scaled_marks_300: float
    reference_year: int | None = None
    percentile: PercentileBand
    rank: RankBand
    confidence: Literal["full_length_mock", "partial_practice", "insufficient_data"]
    disclaimer: str
    colleges: list[CollegeMatchOut]


# ---------------------------------------------------------------------------
# Daily question & streaks: app/routers/daily_question.py. Grading reuses
# SubjectTestSubmitIn/SubjectTestResultOut above — no separate submit schema.
# ---------------------------------------------------------------------------


class DailyQuestionOut(BaseModel):
    attempt_id: int
    already_answered: bool
    question: TestQuestionOut
    current_streak: int
    longest_streak: int


class StreakCalendarOut(BaseModel):
    activity_dates: list[str]
    current_streak: int
    longest_streak: int


# ---------------------------------------------------------------------------
# Rewards (Edge Coins): app/routers/rewards.py.
# ---------------------------------------------------------------------------


class EdgeCoinTransactionOut(BaseModel):
    id: int
    amount: int
    reason: str
    note: str | None = None
    created_at: datetime


class RewardCatalogItemOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    cost_coins: int


class ShippingIn(BaseModel):
    name: str
    line1: str
    line2: str | None = None
    city: str
    state: str
    pincode: str
    phone: str

    @field_validator("name", "line1", "city", "state", "pincode", "phone")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Please fill in every required shipping field.")
        return v


class RedeemIn(BaseModel):
    catalog_item_id: int
    shipping: ShippingIn


class RewardRedemptionOut(BaseModel):
    id: int
    catalog_item_id: int
    catalog_item_name: str
    coins_spent: int
    status: str
    requested_at: datetime


class WalletOut(BaseModel):
    balance: int
    transactions: list[EdgeCoinTransactionOut]
    catalog: list[RewardCatalogItemOut]
    redemptions: list[RewardRedemptionOut]
