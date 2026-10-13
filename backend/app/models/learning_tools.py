"""Additive learning-loop records; existing attempt history remains authoritative."""
from sqlalchemy import Column,Integer,String,DateTime,JSON,Boolean,ForeignKey,UniqueConstraint
from app.database import Base

class RevisionCard(Base):
    __tablename__='revision_cards'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    question_id=Column(Integer,ForeignKey('questions.id'),nullable=False)
    # Evidence may be rebuilt during answer-key corrections; do not block regrading.
    source_response_id=Column(Integer,nullable=False)
    assignment_id=Column(Integer,ForeignKey('teaching_assignments.id'))
    question=Column(JSON,nullable=False)
    stage=Column(Integer,nullable=False,default=0)
    due_at=Column(DateTime,nullable=False)
    last_result=Column(String(20))
    __table_args__=(UniqueConstraint('user_id','question_id',name='uq_revision_card'),)

class RevisionSession(Base):
    __tablename__='revision_sessions'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    cards=Column(JSON,nullable=False)
    created_at=Column(DateTime,nullable=False)
    result=Column(JSON(none_as_null=True))

class TaughtChapter(Base):
    __tablename__='teacher_taught_chapters'
    classroom_id=Column(Integer,ForeignKey('classrooms.id'),primary_key=True)
    chapter_id=Column(Integer,ForeignKey('chapters.id'),primary_key=True)
    updated_at=Column(DateTime,nullable=False)

class TeacherBlueprint(Base):
    __tablename__='teacher_blueprints'
    id=Column(Integer,primary_key=True)
    teacher_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    name=Column(String(150),nullable=False)
    configuration=Column(JSON,nullable=False)
    created_at=Column(DateTime,nullable=False)

class QuestionDoubt(Base):
    __tablename__='question_doubts'
    id=Column(Integer,primary_key=True)
    student_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    teacher_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    assignment_id=Column(Integer,ForeignKey('teaching_assignments.id'),nullable=False)
    question_id=Column(Integer,ForeignKey('questions.id'),nullable=False)
    message=Column(String(2000),nullable=False)
    allow_share=Column(Boolean,nullable=False,default=False)
    shared=Column(Boolean,nullable=False,default=False)
    answer=Column(String(5000))
    version=Column(Integer,nullable=False,default=1)
    created_at=Column(DateTime,nullable=False)
    answered_at=Column(DateTime)
    request_key=Column(String(64),nullable=False)
    __table_args__=(UniqueConstraint('student_id','request_key',name='uq_doubt_request'),)
