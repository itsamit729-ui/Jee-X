"""Additive classroom tables; existing user roles and published tests stay intact."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from app.database import Base


class TeacherAccess(Base):
    __tablename__ = 'teacher_access'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    active = Column(Boolean, nullable=False, default=True)
    granted_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)


class Classroom(Base):
    __tablename__ = 'classrooms'
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    join_code = Column(String(16), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False)


class ClassroomMember(Base):
    __tablename__ = 'classroom_members'
    classroom_id = Column(Integer, ForeignKey('classrooms.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True, index=True)
    joined_at = Column(DateTime, nullable=False)
    active = Column(Boolean, nullable=False, default=True)


class TeachingAssignment(Base):
    __tablename__ = 'teaching_assignments'
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    test_id = Column(Integer, ForeignKey('tests.id'), nullable=False, unique=True)
    title = Column(String(150), nullable=False)
    instructions = Column(String(2000), nullable=False, default='')
    opens_at = Column(DateTime, nullable=False)
    due_at = Column(DateTime, nullable=False, index=True)
    solutions_at = Column(DateTime, nullable=False)
    duration_sec = Column(Integer, nullable=False)
    marks_correct = Column(Integer, nullable=False)
    marks_wrong = Column(Integer, nullable=False)
    question_count = Column(Integer, nullable=False)
    questions = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
    # Request key makes retries after a lost network response safe.
    request_key = Column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint('teacher_id', 'request_key', name='uq_teaching_publish_key'),)


class AssignmentClassroom(Base):
    __tablename__ = 'assignment_classrooms'
    assignment_id = Column(Integer, ForeignKey('teaching_assignments.id'), primary_key=True)
    classroom_id = Column(Integer, ForeignKey('classrooms.id'), primary_key=True, index=True)


class AssignmentRecipient(Base):
    __tablename__ = 'assignment_recipients'
    assignment_id = Column(Integer, ForeignKey('teaching_assignments.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey('test_attempts.id'), unique=True)
    draft = Column(JSON, nullable=False, default=list)
    draft_version = Column(Integer, nullable=False, default=0)
    saved_at = Column(DateTime)
    result = Column(JSON)


class ClassroomNotification(Base):
    __tablename__ = 'classroom_notifications'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    assignment_id = Column(Integer, ForeignKey('teaching_assignments.id'))
    kind = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(String(500), nullable=False)
    href = Column(String(150), nullable=False)
    available_at = Column(DateTime, nullable=False)
    read_at = Column(DateTime)
    __table_args__ = (Index('ix_classroom_notifications_user_due', 'user_id', 'available_at'),)
