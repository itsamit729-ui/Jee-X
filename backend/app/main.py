import os
from time import perf_counter

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app import models  # noqa: F401 -- registers every table on Base.metadata
from app.database import Base, engine
from app.routers import (
    users,
    authentication,
    google_login,
    test_attempts,
    subjects,
    subject_tests,
    subject_test_attempts,
    predictions,
    daily_question,
    rewards,
    ranking,
    public_profiles,
    admin_dashboard,
    scenarios,
    roadmap,
)

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Jee Edge API", version="0.1.0")

from app.auth import trusted_origins, cookie_options
origins = list(trusted_origins())
cookie_options()  # Reject unsafe configuration at startup.

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

app.include_router(authentication.router)
app.include_router(google_login.router)
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
app.include_router(admin_dashboard.router)
app.include_router(scenarios.router)
app.include_router(roadmap.router)


@app.on_event('startup')
def import_predictor_reference_data():
    from app.predictor_bootstrap import start_reference_import
    start_reference_import()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic errors must not echo a password or reset token back to clients.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]})


@app.middleware("http")
async def response_security(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    response.headers["Server-Timing"] = f"app;dur={(perf_counter() - started) * 1000:.1f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith('/api/'):
        response.headers["Cache-Control"] = "no-store"
    return response


# The root Dockerfile builds React into /app/static, giving cookies one origin.
static_dir = Path(os.getenv('FRONTEND_DIST', '/app/static')).resolve()
if (static_dir / 'index.html').is_file():
    @app.get('/{path:path}', include_in_schema=False)
    def frontend(path: str):
        if path == 'api' or path.startswith('api/'):
            raise HTTPException(404, 'Not found')
        target = (static_dir / path).resolve()
        if not target.is_relative_to(static_dir):
            raise HTTPException(404, 'Not found')
        if target.is_file():
            # Vite assets have content hashes; HTML and unversioned files must revalidate.
            cache = 'public, max-age=31536000, immutable' if path.startswith('assets/') else 'no-cache'
            return FileResponse(target, headers={'Cache-Control': cache})
        if path.startswith(('assets/', 'question-images/')):
            raise HTTPException(404, 'Not found')
        return FileResponse(static_dir / 'index.html', headers={'Cache-Control': 'no-cache'})
