"""Private two-player matches; snapshots keep a match stable across bank edits."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Boolean, Index
from app.database import Base


class DuelMatch(Base):
    __tablename__ = 'duel_matches'
    id = Column(String(32), primary_key=True)
    challenger_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    opponent_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    state = Column(String(20), nullable=False, index=True)
    exam = Column(String(20), nullable=False)
    subject = Column(String(10), nullable=True)
    question_count = Column(Integer, nullable=False)
    duration_sec = Column(Integer, nullable=False)
    questions = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    starts_at = Column(DateTime, nullable=True)
    deadline_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    winner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    Index('ix_duel_inbox', opponent_id, state, created_at)


class DuelPlayer(Base):
    __tablename__ = 'duel_players'
    match_id = Column(String(32), ForeignKey('duel_matches.id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    ready_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    forfeited = Column(Boolean, nullable=False, default=False)
    last_seen_at = Column(DateTime, nullable=True)
    answers = Column(JSON, nullable=False, default=dict)
    result = Column(JSON, nullable=True)
