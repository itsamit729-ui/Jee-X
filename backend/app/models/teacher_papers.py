"""Teacher-owned drafts and reviewed offline responses. No changes to existing rows."""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, UniqueConstraint
from app.database import Base

class TeacherPaper(Base):
    __tablename__ = 'teacher_papers'
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    settings = Column(JSON, nullable=False)
    questions = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    finalized = Column(Boolean, nullable=False, default=False)
    assignment_id = Column(Integer, ForeignKey('teaching_assignments.id'))
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

class TeacherSheet(Base):
    __tablename__ = 'teacher_omr_sheets'
    id = Column(String(32), primary_key=True)
    paper_id = Column(Integer, ForeignKey('teacher_papers.id'), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    variant = Column(String(1), nullable=False)
    question_order = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
    __table_args__ = (UniqueConstraint('paper_id', 'student_id', 'variant', name='uq_teacher_sheet'),)

class TeacherScan(Base):
    __tablename__ = 'teacher_omr_scans'
    id = Column(String(32), primary_key=True)
    teacher_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    paper_id = Column(Integer, ForeignKey('teacher_papers.id'), nullable=False, index=True)
    sheet_id = Column(String(32), ForeignKey('teacher_omr_sheets.id'))
    state = Column(String(24), nullable=False)
    error = Column(String(300))
    detection = Column(JSON)
    answers = Column(JSON)
    result = Column(JSON)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False)
    reviewed_at = Column(DateTime)
