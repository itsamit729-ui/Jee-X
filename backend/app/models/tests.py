from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    kind = Column(String(20), nullable=False)
    pattern = Column(String(20), nullable=False)
    duration_sec = Column(Integer, nullable=False)
    ranked = Column(Boolean, nullable=False, server_default="0")
    generated_for_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    opens_at = Column(DateTime(timezone=True), nullable=True)
    closes_at = Column(DateTime(timezone=True), nullable=True)
    results_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "kind IN ('free_diagnostic','mock','chapter','retest','daily')", name="ck_tests_kind"
        ),
        CheckConstraint("pattern IN ('jee_main','jee_advanced','bitsat')", name="ck_tests_pattern"),
        CheckConstraint(
            "kind <> 'retest' OR (generated_for_user_id IS NOT NULL AND ranked = 0)",
            name="ck_tests_retest_rules",
        ),
    )

    test_questions = relationship(
        "TestQuestion", back_populates="test", cascade="all, delete-orphan", order_by="TestQuestion.position"
    )
    attempts = relationship("TestAttempt", back_populates="test")


class TestQuestion(Base):
    __tablename__ = "test_questions"

    test_id = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), primary_key=True)
    section = Column(String(50), nullable=True)
    position = Column(Integer, nullable=False)
    marks_correct = Column(Integer, nullable=False)
    marks_wrong = Column(Integer, nullable=False, server_default="0")
    partial_marking = Column(Boolean, nullable=False, server_default="0")

    test = relationship("Test", back_populates="test_questions")
    question = relationship("Question")


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False, server_default="1")
    counts_for_rank = Column(Boolean, nullable=False, server_default="0")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # cached summary, rebuilt from question_responses
    score = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)
    accuracy = Column(Float, nullable=True)
    avg_time_seconds = Column(Float, nullable=True)
    subject_breakdown = Column(JSON, nullable=True)
    rank = Column(Integer, nullable=True)
    percentile = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "test_id", "attempt_number", name="uq_test_attempts_user_test_num"),)

    user = relationship("User", back_populates="test_attempts", foreign_keys=[user_id])
    test = relationship("Test", back_populates="attempts")
    responses = relationship("QuestionResponse", back_populates="attempt", cascade="all, delete-orphan")


class QuestionResponse(Base):
    __tablename__ = "question_responses"

    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False)
    question_version = Column(Integer, nullable=False)
    numeric_answer = Column(Float, nullable=True)
    outcome = Column(String(20), nullable=False)
    marks_awarded = Column(Integer, nullable=False, server_default="0")
    time_taken_sec = Column(Integer, nullable=False)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_question_responses_attempt_question"),
        CheckConstraint(
            "outcome IN ('correct','partial','wrong','skipped','timed_out')",
            name="ck_question_responses_outcome",
        ),
        ForeignKeyConstraint(
            ["question_id", "question_version"],
            ["question_revisions.question_id", "question_revisions.version"],
            name="fk_question_responses_revision",
        ),
        Index("ix_question_responses_user_question", "user_id", "question_id"),
    )

    attempt = relationship("TestAttempt", back_populates="responses")
    question = relationship("Question")
    chosen_options = relationship("ResponseOption", back_populates="response", cascade="all, delete-orphan")


class ResponseOption(Base):
    __tablename__ = "response_options"

    response_id = Column(Integer, ForeignKey("question_responses.id", ondelete="CASCADE"), primary_key=True)
    option_id = Column(Integer, ForeignKey("question_options.id", ondelete="RESTRICT"), primary_key=True)

    response = relationship("QuestionResponse", back_populates="chosen_options")
    option = relationship("QuestionOption")
