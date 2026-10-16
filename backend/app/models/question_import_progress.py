"""Transactional cursor for resumable Admin question imports."""
from sqlalchemy import Column, DateTime, Integer, String, func
from app.database import Base


class QuestionImportProgress(Base):
    __tablename__='question_import_progress'
    digest=Column(String(64),primary_key=True)
    year=Column(Integer,nullable=False)
    offset=Column(Integer,nullable=False,default=0)
    total=Column(Integer,nullable=False)
    added=Column(Integer,nullable=False,default=0)
    updated=Column(Integer,nullable=False,default=0)
    unchanged=Column(Integer,nullable=False,default=0)
    skipped=Column(Integer,nullable=False,default=0)
    conflicts=Column(Integer,nullable=False,default=0)
    updated_at=Column(DateTime,server_default=func.now(),onupdate=func.now())
