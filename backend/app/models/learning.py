from sqlalchemy import JSON, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, func

from app.database import Base


class StudentSubtopicStats(Base):
    __tablename__ = "student_subtopic_stats"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), primary_key=True)
    attempted = Column(Integer, nullable=False, server_default="0")
    correct = Column(Integer, nullable=False, server_default="0")
    avg_time_sec = Column(Float, nullable=True)
    mastery = Column(Float, nullable=False, server_default="0.5")
    last_attempted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (CheckConstraint("mastery BETWEEN 0 AND 1", name="ck_student_subtopic_stats_mastery"),)


class StudentChapterCoverage(Base):
    __tablename__ = "student_chapter_coverage"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), primary_key=True)
    status = Column(String(20), nullable=False, server_default="not_started")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('not_started','in_progress','done')", name="ck_student_chapter_coverage_status"),
    )


class PracticeRecommendation(Base):
    __tablename__ = 'practice_recommendations'
    test_id = Column(Integer, ForeignKey('tests.id', ondelete='CASCADE'), primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id'), primary_key=True)
    explanation = Column(JSON, nullable=False)
