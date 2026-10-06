"""Durable comment inbox, reply fence, and immutable post lesson snapshots."""
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.database import Base


class SocialLesson(Base):
    __tablename__ = 'social_lessons'
    slot = Column(String(32), primary_key=True)
    content = Column(Text, nullable=False)


class SocialComment(Base):
    __tablename__ = 'social_comments'
    id = Column(String(64), primary_key=True)
    media_id = Column(String(64), nullable=False, index=True)
    author_id = Column(String(64), nullable=False, index=True)
    parent_id = Column(String(64))
    text = Column(Text, nullable=False)
    state = Column(String(24), nullable=False, index=True)
    owner = Column(String(32))
    reply = Column(Text)
    reply_id = Column(String(64))
    reason = Column(String(300))
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, index=True)
    updated_at = Column(DateTime, nullable=False)
    next_attempt = Column(DateTime, nullable=False)
    sent_at = Column(DateTime)


class SocialCommentDispatch(Base):
    __tablename__ = 'social_comment_dispatch'
    id = Column(Integer, primary_key=True)
    owner = Column(String(32))
    expires_at = Column(DateTime)
