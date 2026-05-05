"""Reference catalog endpoints for wizard dropdowns."""

from fastapi import APIRouter

from app.services import csv_store

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/drugs")
def list_drugs():
    return csv_store.read_table("drugs.csv")


@router.get("/therapy-areas")
def list_therapy_areas():
    return csv_store.read_table("therapy_areas.csv")


@router.get("/geographies")
def list_geographies():
    return csv_store.read_table("geographies.csv")


@router.get("/lifecycle-stages")
def list_lifecycle_stages():
    return csv_store.read_table("lifecycle_stages.csv")


@router.get("/data-sources")
def list_data_sources():
    return csv_store.read_table("data_sources.csv")


@router.get("/literature")
def list_literature():
    return csv_store.read_table("literature.csv")


@router.get("/hta-decisions")
def list_hta():
    return csv_store.read_table("hta_decisions.csv")


@router.get("/rwe-studies")
def list_rwe():
    return csv_store.read_table("rwe_studies.csv")
