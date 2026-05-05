"""HITL review queue."""

from typing import List

from fastapi import APIRouter

from app.models.schemas import RequestSummary
from app.services import csv_store

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/queue", response_model=List[RequestSummary])
def review_queue():
    rows = [r for r in csv_store.read_table("iep_requests.csv") if r.get("status") == "in_review"]
    rows.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return [RequestSummary.model_validate(r) for r in rows]
