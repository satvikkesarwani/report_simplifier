import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, evaluation, health, history, jobs, process, upload
from app.config import get_settings
from app.db.report_store import get_report_store
from app.utils.request_guard import client_key, enforce_optional_auth, rate_limiter

settings = get_settings()
get_report_store()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RAG-Based Medical Report Simplification System API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(process.router, prefix="/api", tags=["Process"])
app.include_router(history.router, prefix="/api", tags=["History"])
app.include_router(evaluation.router, prefix="/api", tags=["Evaluation"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
 
@app.on_event("startup")
async def startup_event():
    from app.services.background_jobs import get_job_manager
    get_job_manager().resume_pending_jobs()

static_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend_static")
if os.path.exists(static_path):
    app.mount("/app", StaticFiles(directory=static_path, html=True), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
    }


@app.middleware("http")
async def auth_and_rate_limit(request: Request, call_next):
    try:
        public_paths = {
            "/",
            "/api/health",
            "/api/docs",
            "/api/redoc",
            "/openapi.json",
            "/api/auth/register",
            "/api/auth/login",
        }
        if request.url.path not in public_paths:
            enforce_optional_auth(request)
            rate_limiter.check(client_key(request))
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "path": str(request.url.path),
            "error": str(exc),
        },
    )
