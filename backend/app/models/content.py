from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False, unique=True)
    name = Column(String(50), nullable=False)

    __table_args__ = (CheckConstraint("code IN ('PHY','CHEM','MATH','ENG','LR')", name="ck_subjects_code"),)

    chapters = relationship("Chapter", back_populates="subject")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    class_level = Column(String(2), nullable=False)
    in_main = Column(Boolean, nullable=False, server_default="1")
    in_advanced = Column(Boolean, nullable=False, server_default="1")
    position = Column(Integer, nullable=False, server_default="0")

    __table_args__ = (
        UniqueConstraint("subject_id", "slug", name="uq_chapters_subject_slug"),
        CheckConstraint("class_level IN ('11','12')", name="ck_chapters_class_level"),
    )

    subject = relationship("Subject", back_populates="chapters")
    subtopics = relationship("Subtopic", back_populates="chapter")


class Subtopic(Base):
    __tablename__ = "subtopics"

    id = Column(Integer, primary_key=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False, server_default="0")

    __table_args__ = (UniqueConstraint("chapter_id", "slug", name="uq_subtopics_chapter_slug"),)

    chapter = relationship("Chapter", back_populates="subtopics")
    questions = relationship("Question", back_populates="subtopic")


class Passage(Base):
    __tablename__ = "passages"

    id = Column(Integer, primary_key=True)
    ref = Column(String(50), nullable=False, unique=True)
    content = Column(Text, nullable=False)

    questions = relationship("Question", back_populates="passage")
    assets = relationship("Asset", back_populates="passage", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    ref = Column(String(50), nullable=False, unique=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=False, index=True)
    passage_id = Column(Integer, ForeignKey("passages.id"), nullable=True)
    type = Column(String(20), nullable=False)
    stem = Column(Text, nullable=False)
    answer_min = Column(Float, nullable=True)
    answer_max = Column(Float, nullable=True)
    solution = Column(Text, nullable=False)
    difficulty = Column(Integer, nullable=False)
    expected_time_sec = Column(Integer, nullable=False)
    source_type = Column(String(20), nullable=False)
    exam = Column(String(20), nullable=True)
    year = Column(Integer, nullable=True)
    shift = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, server_default="draft")
    version = Column(Integer, nullable=False, server_default="1")
    content_hash = Column(String(64), nullable=False, unique=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("type IN ('single_correct','multi_correct','numerical')", name="ck_questions_type"),
        CheckConstraint("difficulty BETWEEN 1 AND 10", name="ck_questions_difficulty"),
        CheckConstraint("source_type IN ('pyq','original','adapted')", name="ck_questions_source_type"),
        CheckConstraint("exam IS NULL OR exam IN ('jee_main','jee_advanced','bitsat')", name="ck_questions_exam"),
        CheckConstraint(
            "status IN ('draft','reviewed','published','retired')", name="ck_questions_status"
        ),
        CheckConstraint(
            "(type = 'numerical') = (answer_min IS NOT NULL AND answer_max IS NOT NULL)",
            name="ck_questions_numerical_answer",
        ),
        CheckConstraint(
            "answer_min IS NULL OR answer_max IS NULL OR answer_min <= answer_max",
            name="ck_questions_answer_range",
        ),
        CheckConstraint(
            "source_type <> 'pyq' OR (exam IS NOT NULL AND year IS NOT NULL)",
            name="ck_questions_pyq_exam_year",
        ),
    )

    subtopic = relationship("Subtopic", back_populates="questions")
    passage = relationship("Passage", back_populates="questions")
    options = relationship(
        "QuestionOption", back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.position"
    )
    also_subtopics = relationship("QuestionSubtopic", back_populates="question", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="question", cascade="all, delete-orphan")
    revisions = relationship("QuestionRevision", back_populates="question", cascade="all, delete-orphan")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(1), nullable=False)
    content = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    position = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("question_id", "label", name="uq_question_options_question_label"),
        CheckConstraint("label IN ('A','B','C','D')", name="ck_question_options_label"),
    )

    question = relationship("Question", back_populates="options")


class QuestionSubtopic(Base):
    __tablename__ = "question_subtopics"

    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), primary_key=True)

    question = relationship("Question", back_populates="also_subtopics")
    subtopic = relationship("Subtopic")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=True)
    passage_id = Column(Integer, ForeignKey("passages.id", ondelete="CASCADE"), nullable=True)
    url = Column(String(1024), nullable=True)
    alt_text = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "(question_id IS NULL) <> (passage_id IS NULL)", name="ck_assets_exactly_one_owner"
        ),
    )

    question = relationship("Question", back_populates="assets")
    passage = relationship("Passage", back_populates="assets")
