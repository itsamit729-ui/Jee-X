"""Public identity preferences, separate from private student data."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from app.database import Base


class PublicProfile(Base):
    __tablename__ = 'public_profiles'
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    # Legacy compatibility column; never used to gate public access.
    enabled = Column(Boolean, nullable=False, default=True)
    show_activity = Column(Boolean, nullable=False, default=False)
    display_name = Column(String(80), nullable=False, default='')
    bio = Column(String(280), nullable=False, default='')
