from sqlalchemy import Column, Integer, ForeignKey, JSON, String, DateTime, func
from app.database import Base


class CollegeInsight(Base):
    __tablename__ = 'college_insights'
    institute_id = Column(Integer, ForeignKey('predictor_institutes.id', ondelete='CASCADE'), primary_key=True)
    content = Column(JSON, nullable=False)
    content_hash = Column(String(64), nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
