from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String

from app.database import Base


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_key = Column(String(40), nullable=False)
    started_at = Column(DateTime, nullable=False)
    deadline_at = Column(DateTime, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    # This is a private snapshot. Never return it directly: it contains answer keys.
    questions = Column(JSON, nullable=False)
    answers = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
