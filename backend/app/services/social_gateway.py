"""Forward social HTTP operations without importing or running the renderer."""
import hmac
import os
from urllib.parse import quote, urlsplit
import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from app.routers.admin_dashboard import _require_admin

MAX_REQUEST_BYTES=256*1024
MAX_RESPONSE_BYTES=12*1024*1024
RESPONSE_HEADERS={'content-type','content-length','cache-control','etag','accept-ranges','content-range','retry-after'}
REQUEST_HEADERS={'content-type','range','if-none-match','accept','x-hub-signature-256'}


def worker_config():
    origin=os.getenv('SOCIAL_WORKER_URL','').rstrip('/')
    parsed=urlsplit(origin)
    secret=os.getenv('SOCIAL_RELAY_SECRET','')
    if (parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment or len(secret)<32):
        raise RuntimeError('Set SOCIAL_WORKER_URL to an HTTPS origin and SOCIAL_RELAY_SECRET to at least 32 characters.')
    return origin,secret


def require_relay(x_social_relay: str=Header(default='')):
    secret=os.getenv('SOCIAL_RELAY_SECRET','')
    if len(secret)<32 or not hmac.compare_digest(x_social_relay.encode(),secret.encode()):
        raise HTTPException(401,'Authenticated social gateway required.')
    return 'social-gateway'


async def forward(request: Request):
    origin,secret=worker_config()
    path=request.url.path
    if any(part in ('.','..') for part in path.split('/')):
        raise HTTPException(400,'Invalid social path')
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>MAX_REQUEST_BYTES:raise HTTPException(413,'Social request too large')
    headers={key:value for key,value in request.headers.items() if key in REQUEST_HEADERS}
    headers['X-Social-Relay']=secret
    # Browser admin sessions live only on the main service. Never forward their
    # bearer token/cookies; the worker trusts the separately authenticated relay.
    if path.startswith('/api/social/') and request.headers.get('authorization'):
        headers['Authorization']=request.headers['authorization']
    url=origin+quote(path,safe='/:@-._~')
    if request.url.query:url+='?'+request.url.query
    try:
        upstream=await run_in_threadpool(requests.request,request.method,url,
            headers=headers,data=bytes(body),stream=True,allow_redirects=False,timeout=(5,25))
    except requests.RequestException:
        # Never retry POSTs: an accepted submission may have outlived the response.
        raise HTTPException(502,'Social worker did not confirm this request. Check the existing job before retrying.') from None
    response_headers={key.lower():value for key,value in upstream.headers.items() if key.lower() in RESPONSE_HEADERS}
    location=upstream.headers.get('Location')
    if location:
        redirect=urlsplit(location);target=urlsplit(origin)
        if (not redirect.netloc or (redirect.scheme,redirect.netloc)==(target.scheme,target.netloc)) and redirect.path.startswith(('/api/social/','/api/admin/social')):
            response_headers['location']=redirect.path+('?' + redirect.query if redirect.query else '')
    # requests decodes compressed responses, so do not retain a compressed length.
    if upstream.headers.get('Content-Encoding'):
        response_headers={key:value for key,value in response_headers.items() if key.lower()!='content-length'}
    if not path.startswith(('/api/social/assets/','/api/social/media/')):
        response_headers['cache-control']='no-store'
    else:
        # Already-compressed JPEG/MP4 bytes must bypass the web app's gzip layer.
        response_headers['content-encoding']='identity'
    def chunks():
        total=0
        try:
            for chunk in upstream.iter_content(chunk_size=64*1024):
                total+=len(chunk)
                if total>MAX_RESPONSE_BYTES:raise RuntimeError('Social response exceeded its size limit')
                yield chunk
        finally:upstream.close()
    return StreamingResponse(chunks(),status_code=upstream.status_code,headers=response_headers)


def gateway_router():
    router=APIRouter()
    router.add_api_route('/api/admin/social',forward,methods=['GET','POST'],dependencies=[Depends(_require_admin)],include_in_schema=False)
    router.add_api_route('/api/admin/social/{path:path}',forward,methods=['GET','POST'],dependencies=[Depends(_require_admin)],include_in_schema=False)
    router.add_api_route('/api/social/{path:path}',forward,methods=['GET','HEAD','POST'],include_in_schema=False)
    return router


def install_social_routes(app):
    mode=os.getenv('SOCIAL_EXECUTION_MODE','external' if os.getenv('SOCIAL_WORKER_URL') else 'embedded').lower()
    if mode=='external':
        worker_config()  # Configuration errors never fall back to local rendering.
        app.include_router(gateway_router())
    elif mode=='embedded':
        # Compatibility until the separate service has been deployed/configured.
        from app.routers import social_slots,social_comments
        app.include_router(social_slots.router)
        app.include_router(social_slots.admin_router)
        app.include_router(social_comments.router)
    else:raise RuntimeError('SOCIAL_EXECUTION_MODE must be embedded or external on the main web service.')
    app.state.social_execution_mode=mode
