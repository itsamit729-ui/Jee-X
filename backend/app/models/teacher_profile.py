"""Private teacher details, independent of student profiles and study history."""
from sqlalchemy import Column, Integer, ForeignKey, JSON
from app.database import Base

class TeacherProfile(Base):
    __tablename__ = 'teacher_profiles'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    details = Column(JSON, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
