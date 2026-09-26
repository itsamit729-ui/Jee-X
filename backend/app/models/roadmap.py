from sqlalchemy import Column, Integer, ForeignKey, JSON, DateTime, func
from app.database import Base


class StudentRoadmap(Base):
    __tablename__ = 'student_roadmaps'
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    settings = Column(JSON, nullable=False)
    plan = Column(JSON, nullable=False)
    checkpoints = Column(JSON, nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())
