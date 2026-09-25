from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import verify_token
from app.database import get_db
from app.utils import class_level_to_years

router = APIRouter(prefix="/api", tags=["users"])


def _class_level_from_years(class_12_year: int, target_year: int) -> str:
    # (class_12_year, target_year) alone is ambiguous between '11' and '12'
    # (both store class_12_year == target_year) — only the day this runs
    # tells you which one, so reverse via the same table class_level_to_years
    # builds, rather than comparing the two numbers directly.
    for level in ("11", "12", "dropper"):
        if class_level_to_years(level) == (class_12_year, target_year):
            return level
    return "dropper" if class_12_year < target_year else "12"


def _user_out(user: models.User) -> schemas.UserOut:
    profile = user.student_profile
    return schemas.UserOut(
        id=user.id,
        name=user.name,
        username=user.username,
        dob=profile.dob if profile else None,
        class_level=_class_level_from_years(profile.class_12_year, profile.target_year) if profile else None,
        email=user.email,
        avatar_url=f"/api/public-profiles/{user.username}/avatar" if user.avatar else None,
    )


@router.get("/me")
def read_me(payload: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.auth0_sub == payload["sub"]).first()
    if not user or not user.student_profile:
        return {"onboarded": False, "profile": None}
    return {"onboarded": True, "profile": _user_out(user)}


@router.get("/username-check/{username}", response_model=schemas.UsernameAvailability)
def check_username(username: str, db: Session = Depends(get_db)):
    username = username.strip().lower()
    exists = db.query(models.User).filter(models.User.username == username).first()
    return schemas.UsernameAvailability(username=username, available=exists is None)


@router.post("/onboarding", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def complete_onboarding(body: schemas.OnboardingIn, payload: dict = Depends(verify_token), db: Session = Depends(get_db)):
    sub = payload["sub"]
    email = payload.get("email")
    existing = db.query(models.User).filter(models.User.auth0_sub == sub).first()
    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists for this account.")
    if db.query(models.User).filter(models.User.username == body.username).first():
        raise HTTPException(status_code=409, detail="That username is already taken.")

    class_12_year, target_year = class_level_to_years(body.class_level)
    user = models.User(auth0_sub=sub, email=email, name=body.name, username=body.username, role="student", status="active")
    db.add(user)
    db.flush()
    profile = models.StudentProfile(
        user_id=user.id,
        dob=body.dob,
        class_12_year=class_12_year,
        target_year=target_year,
        target_exam="jee_main",
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.patch("/profile", response_model=schemas.UserOut)
def update_profile(
    body: schemas.ProfileUpdate,
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    sub = payload["sub"]
    user = db.query(models.User).filter(models.User.auth0_sub == sub).first()
    if not user or not user.student_profile:
        raise HTTPException(status_code=404, detail="Complete onboarding before editing your profile.")

    taken = (
        db.query(models.User)
        .filter(models.User.username == body.username, models.User.auth0_sub != sub)
        .first()
    )
    if taken:
        raise HTTPException(status_code=409, detail="That username is already taken.")

    class_12_year, target_year = class_level_to_years(body.class_level)
    user.name = body.name
    user.username = body.username
    user.student_profile.dob = body.dob
    user.student_profile.class_12_year = class_12_year
    user.student_profile.target_year = target_year
    db.commit()
    db.refresh(user)
    return _user_out(user)
