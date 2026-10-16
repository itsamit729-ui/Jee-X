"""Standalone publisher: no student endpoints, frontend, OMR or predictor imports."""
import os
from time import perf_counter
from dotenv import load_dotenv
from fastapi import FastAPI, Request


def create_app():
    load_dotenv()
    if len(os.getenv('SOCIAL_RELAY_SECRET',''))<32:
        raise RuntimeError('The social worker requires a SOCIAL_RELAY_SECRET of at least 32 characters.')
    from app.access_logging import configure
    configure()
    from app.routers import social_slots,social_comments
    from app.routers.admin_dashboard import _require_admin
    from app.services.social_gateway import require_relay
    app=FastAPI(title='Jee Edge Publisher',docs_url=None,redoc_url=None,openapi_url=None)
    app.dependency_overrides[_require_admin]=require_relay
    app.include_router(social_slots.router)
    app.include_router(social_slots.admin_router)
    app.include_router(social_comments.router)

    @app.on_event('startup')
    def initialize_social_tables():
        from app.database import Base,engine
        Base.metadata.create_all(bind=engine,tables=[table for table in Base.metadata.sorted_tables if table.name.startswith('social_')])

    @app.get('/health')
    def health():return {'status':'ok','service':'publisher','execution_mode':'worker'}

    @app.middleware('http')
    async def headers(request: Request,call_next):
        started=perf_counter()
        response=await call_next(request)
        response.headers['Server-Timing']=f'app;dur={(perf_counter()-started)*1000:.1f}'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Frame-Options']='DENY'
        if not request.url.path.startswith(('/api/social/assets/','/api/social/media/')):
            response.headers['Cache-Control']='no-store'
        return response
    return app
