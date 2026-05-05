"""FastAPI entrypoint — Medical Affairs RWE Evidence Builder POC."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import catalog, kpis, requests, review
from app.services import csv_store


@asynccontextmanager
async def lifespan(_: FastAPI):
    csv_store.ensure_data_dir()
    yield


app = FastAPI(
    title="Medical Affairs RWE Evidence Builder",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(kpis.router)
app.include_router(requests.router)
app.include_router(review.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
