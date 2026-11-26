import logging
import re
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.logging_setup import setup_logging
from app.routers import agencies, clients, generate, prompts, scan, templates

setup_logging()
logger = logging.getLogger("brandly")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

app = FastAPI(title="Brandly API")
app.include_router(agencies.router)
app.include_router(clients.router)
app.include_router(prompts.router)
app.include_router(scan.router)
app.include_router(generate.router)
app.include_router(templates.router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Give every request an id, log it, and turn unexpected crashes into clean JSON."""
    incoming = request.headers.get("x-request-id", "")
    request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex[:12]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "unhandled error request_id=%s %s %s", request_id, request.method, request.url.path
        )
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s -> %s %.0fms request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
        request_id,
    )
    return response


# Added last, so CORS is the outermost layer and even error responses carry its headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"],
)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}
