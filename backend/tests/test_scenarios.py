"""Scenario sessions keep answer keys private and use server-side deadlines."""
import os
from datetime import timedelta

os.environ.setdefault("DATABASE_URL", "mysql+pymysql://test:test@localhost/unused")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.deps import get_current_db_user
from app.routers.scenarios import router
from app.services import scenarios


def test_session_lifecycle_and_isolation(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.add_all([
            models.User(id=1, auth0_sub="scenario-one", username="scenario_one", name="One"),
            models.User(id=2, auth0_sub="scenario-two", username="scenario_two", name="Two"),
        ])
        db.commit()

    def get_test_db():
        with Session() as db:
            yield db

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_db_user] = lambda: models.User(id=1)
    client = TestClient(app)

    listed = client.get("/api/scenarios").json()
    assert len(listed) == 6
    assert sorted(p["duration_minutes"] for p in listed) == [15, 20, 25, 30, 30, 45]
    started = client.post("/api/scenarios/final_check/start")
    assert started.status_code == 201, started.text
    run = started.json()
    run_id = run["id"]
    assert run["seconds_left"] == 15 * 60
    assert len(run["questions"]) == 8
    assert client.post("/api/scenarios/final_check/start").json()["id"] == run_id
    assert all("correct_option_ids" not in q and "solution" not in q and "answer_min" not in q
               for q in run["questions"])

    question = next(q for q in run["questions"] if q["type"] == "single_correct")
    path = f"/api/scenarios/runs/{run_id}/answers/{question['id']}"
    invalid = client.put(path, json={"option_ids": ["Z"]})
    assert invalid.status_code == 422
    saved = client.put(path, json={"option_ids": [question["options"][0]["id"]],
                                   "marked_for_review": True, "time_spent_sec": 0})
    assert saved.status_code == 200, saved.text
    resumed = client.get(f"/api/scenarios/runs/{run_id}").json()
    assert resumed["answers"][question["id"]]["marked_for_review"] is True

    app.dependency_overrides[get_current_db_user] = lambda: models.User(id=2)
    assert client.get(f"/api/scenarios/runs/{run_id}").status_code == 404
    assert client.put(path, json={"option_ids": []}).status_code == 404
    app.dependency_overrides[get_current_db_user] = lambda: models.User(id=1)

    started_at = scenarios.utcnow()
    monkeypatch.setattr(scenarios, "utcnow", lambda: started_at + timedelta(minutes=16))
    expired = client.get(f"/api/scenarios/runs/{run_id}")
    assert expired.status_code == 200, expired.text
    result = expired.json()
    assert result["status"] == "finished"
    assert result["seconds_left"] == 0
    assert result["result"]["attempted"] == 1
    assert len(result["result"]["questions"]) == 8
    assert client.put(path, json={"option_ids": []}).status_code == 409
    assert client.post(f"/api/scenarios/runs/{run_id}/finish").json()["result"] == result["result"]
    replay = client.post("/api/scenarios/final_check/start").json()
    assert replay["id"] != run_id
    replay_end = client.post(f"/api/scenarios/runs/{replay['id']}/finish").json()
    assert replay_end["status"] == "finished" and replay_end["result"]["attempted"] == 0
    assert replay_end["result"]["score"] == 0
    engine.dispose()
