"""Small, normalized profile photos stored alongside the user's account."""
from sqlalchemy import Column, ForeignKey, Integer, LargeBinary
from sqlalchemy.dialects.mysql import MEDIUMBLOB

from app.database import Base


class ProfileAvatar(Base):
    __tablename__ = 'profile_avatars'

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    image = Column(LargeBinary().with_variant(MEDIUMBLOB(), 'mysql'), nullable=False)
