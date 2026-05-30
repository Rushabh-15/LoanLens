from contextlib import asynccontextmanager

from fastapi.staticfiles import StaticFiles

from fastapi import FastAPI

from app.db import init_db
from app.routes.applications import router as applications_router

# Import models so SQLAlchemy registers tables
from app.models.db_models import Application


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown lifecycle.
    """

    # Startup
    init_db()

    yield

    # Shutdown
    # Nothing needed yet


app = FastAPI(
    lifespan=lifespan
)

app.include_router(applications_router)

app.mount("/demo", StaticFiles(directory="static", html=True), name="demo")

@app.get("/health")
def health():
    return {"status": "ok"}