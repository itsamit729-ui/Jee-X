"""Durable daily publication fence and public carousel media."""
from sqlalchemy import Column, String, Integer, DateTime, LargeBinary, ForeignKey
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from app.database import Base


class SocialJob(Base):
    __tablename__ = 'social_jobs'
    day = Column(String(10), primary_key=True)
    state = Column(String(24), nullable=False)
    owner = Column(String(32), nullable=False)
    updated_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, nullable=False, default=1)
    post_id = Column(String(128))
    error = Column(String(500))


class SocialMedia(Base):
    __tablename__ = 'social_media'
    id = Column(String(32), primary_key=True)
    day = Column(String(10), ForeignKey('social_jobs.day'), nullable=False, index=True)
    image = Column(LargeBinary().with_variant(MEDIUMBLOB(), 'mysql'), nullable=False)
