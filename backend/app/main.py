import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 -- registers every table on Base.metadata
from app.database import Base, engine
from app.routers import (
    users,
    test_attempts,
    subjects,
    subject_tests,
    subject_test_attempts,
    predictions,
    daily_question,
    rewards,
    ranking,
    public_profiles,
)

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Jee Edge API", version="0.1.0")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(test_attempts.router)
app.include_router(subjects.router)
app.include_router(subject_tests.router)
app.include_router(subject_test_attempts.router)
app.include_router(predictions.router)
app.include_router(daily_question.router)
app.include_router(rewards.router)
app.include_router(ranking.router)
app.include_router(public_profiles.router)


@app.get("/health")
def health():
    return {"status": "ok"}
