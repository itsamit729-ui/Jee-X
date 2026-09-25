from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    auth0_sub = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), index=True, nullable=True)
    username = Column(String(150), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, server_default="student")
    status = Column(String(20), nullable=False, server_default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('student','reviewer','admin')", name="ck_users_role"),
        CheckConstraint("status IN ('active','suspended')", name="ck_users_status"),
    )

    student_profile = relationship(
        "StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    avatar = relationship("ProfileAvatar", uselist=False, cascade="all, delete-orphan")
    guardian_consents = relationship("GuardianConsent", back_populates="user", cascade="all, delete-orphan")
    test_attempts = relationship(
        "TestAttempt", back_populates="user", cascade="all, delete-orphan", foreign_keys="TestAttempt.user_id"
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    dob = Column(Date, nullable=False)
    class_12_year = Column(Integer, nullable=False)
    target_year = Column(Integer, nullable=False)
    target_exam = Column(String(20), nullable=False, server_default="jee_main")
    state = Column(String(10), nullable=True)
    category = Column(String(10), nullable=True)
    pwd = Column(Boolean, nullable=True)
    leaderboard_visibility = Column(String(20), nullable=False, server_default="username")
    edge_coins = Column(Integer, nullable=False, server_default="0")
    current_streak = Column(Integer, nullable=False, server_default="0")
    longest_streak = Column(Integer, nullable=False, server_default="0")
    last_streak_date = Column(Date, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("target_exam IN ('jee_main','jee_advanced')", name="ck_student_profiles_target_exam"),
        CheckConstraint("category IN ('gen','gen_ews','obc_ncl','sc','st')", name="ck_student_profiles_category"),
        CheckConstraint("leaderboard_visibility IN ('username','hidden')", name="ck_student_profiles_visibility"),
        CheckConstraint("target_year >= class_12_year", name="ck_student_profiles_target_year"),
    )

    user = relationship("User", back_populates="student_profile")


class GuardianConsent(Base):
    __tablename__ = "guardian_consents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    guardian_name = Column(String(255), nullable=True)
    guardian_email = Column(String(255), nullable=False)
    method = Column(String(100), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="guardian_consents")
