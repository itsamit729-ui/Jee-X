"""Aggregate paper funnel counters; no visitor identifiers or personal data."""
from sqlalchemy import Column, Date, Integer, String, UniqueConstraint
from app.database import Base

class AcquisitionCount(Base):
    __tablename__ = 'acquisition_counts'
    id = Column(Integer, primary_key=True)
    day = Column(Date, nullable=False, index=True)
    paper = Column(String(120), nullable=False)
    source = Column(String(20), nullable=False)
    event = Column(String(20), nullable=False)
    count = Column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint('day', 'paper', 'source', 'event', name='uq_acquisition_bucket'),)
