from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.routers import agencies, clients, generate, prompts, scan

app = FastAPI(title="Brandly API")
app.include_router(agencies.router)
app.include_router(clients.router)
app.include_router(prompts.router)
app.include_router(scan.router)
app.include_router(generate.router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}
