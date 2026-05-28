from fastapi import FastAPI

from app.db import init_db
from app.routes.applications import router as applications_router

# Import models so SQLAlchemy registers tables
from app.models.db_models import Application


app = FastAPI()

app.include_router(applications_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}