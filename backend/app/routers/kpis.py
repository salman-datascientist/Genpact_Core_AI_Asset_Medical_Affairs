"""Dashboard KPI rows from CSV."""

from fastapi import APIRouter

from app.services import csv_store

router = APIRouter(prefix="/api", tags=["kpis"])


@router.get("/kpis")
def get_kpis():
    return csv_store.read_table("kpis.csv")
