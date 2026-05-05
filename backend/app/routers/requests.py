"""IEP request lifecycle, mock agents, chat, HITL submission."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    ChatBody,
    ChatMessage,
    ChatResponse,
    CreateRequestBody,
    RegenerateSectionBody,
    RequestDetail,
    RequestSummary,
    ReviewBody,
    ReviewDecision,
    ReviewRecord,
)
from app.services import csv_store, mock_ai

router = APIRouter(prefix="/api/requests", tags=["requests"])


def _table(name: str) -> List[Dict[str, Any]]:
    return csv_store.read_table(name)


def _names(req_row: Dict[str, Any]) -> Dict[str, str]:
    drugs = {r["drug_id"]: r for r in _table("drugs.csv")}
    tas = {r["therapy_area_id"]: r for r in _table("therapy_areas.csv")}
    geos = {r["geography_id"]: r for r in _table("geographies.csv")}
    d = req_row.get("drug_id", "")
    ta = req_row.get("therapy_area_id", "")
    g = req_row.get("geography_id", "")
    return {
        "_drug_name": drugs.get(d, {}).get("name", d),
        "_therapy_name": tas.get(ta, {}).get("name", ta),
        "_geo_name": geos.get(g, {}).get("name", g),
    }


def _enriched(req_row: Dict[str, Any]) -> Dict[str, Any]:
    return {**req_row, **_names(req_row)}


def _detail_model(req_row: Dict[str, Any]) -> RequestDetail:
    rid = req_row.get("request_id", "")
    enriched = _enriched(req_row)
    payload = {
        **req_row,
        "drug_name": enriched.get("_drug_name"),
        "therapy_area_name": enriched.get("_therapy_name"),
        "geography_name": enriched.get("_geo_name"),
        "landscape": mock_ai.load_stage_payload(rid, "landscape", "main"),
        "gaps": mock_ai.load_stage_payload(rid, "gaps", "main"),
        "studies": mock_ai.load_stage_payload(rid, "studies", "main"),
        "iep": mock_ai.load_stage_payload(rid, "iep", "main"),
    }
    return RequestDetail.model_validate(payload)


@router.post("", response_model=RequestSummary)
def create_request(body: CreateRequestBody):
    csv_store.ensure_data_dir()
    rid = mock_ai.new_id("req")
    now = mock_ai.now_iso()
    row = {
        "request_id": rid,
        "created_at": now,
        "updated_at": now,
        "title": body.title,
        "tpp_summary": body.tpp_summary,
        "drug_id": body.drug_id,
        "therapy_area_id": body.therapy_area_id,
        "geography_id": body.geography_id,
        "lifecycle_stage": body.lifecycle_stage,
        "status": "draft",
    }
    csv_store.append_row("iep_requests.csv", row)

    if body.auto_run_agents:
        _run_landscape_internal(rid)
        _run_gaps_internal(rid)
        _run_studies_internal(rid)
        _run_iep_internal(rid)

    req_row = csv_store.get_request(rid)
    assert req_row
    return RequestSummary.model_validate(req_row)


@router.get("", response_model=List[RequestSummary])
def list_requests(status: Optional[str] = Query(None)):
    rows = _table("iep_requests.csv")
    if status:
        rows = [r for r in rows if r.get("status") == status]
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return [RequestSummary.model_validate(r) for r in rows]


@router.get("/{request_id}", response_model=RequestDetail)
def get_request(request_id: str):
    req_row = csv_store.get_request(request_id)
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    return _detail_model(req_row)


def _touch(req_id: str) -> None:
    csv_store.update_request_row(req_id, {"updated_at": mock_ai.now_iso()})


def _run_landscape_internal(req_id: str) -> None:
    req_row = csv_store.get_request(req_id)
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    if req_row.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Landscape requires status=draft")
    payload = mock_ai.run_landscape(_enriched(req_row))
    mock_ai.persist_stage(req_id, "landscape", "main", payload)
    csv_store.update_request_row(req_id, {"status": "landscape", "updated_at": mock_ai.now_iso()})


def _run_gaps_internal(req_id: str) -> None:
    req_row = csv_store.get_request(req_id)
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    if req_row.get("status") != "landscape":
        raise HTTPException(status_code=400, detail="Gap analysis requires status=landscape")
    payload = mock_ai.run_gaps(_enriched(req_row))
    mock_ai.persist_stage(req_id, "gaps", "main", payload)
    csv_store.update_request_row(req_id, {"status": "gaps", "updated_at": mock_ai.now_iso()})


def _run_studies_internal(req_id: str) -> None:
    req_row = csv_store.get_request(req_id)
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    if req_row.get("status") != "gaps":
        raise HTTPException(status_code=400, detail="Study designs require status=gaps")
    payload = mock_ai.run_studies(_enriched(req_row))
    mock_ai.persist_stage(req_id, "studies", "main", payload)
    csv_store.update_request_row(req_id, {"status": "studies", "updated_at": mock_ai.now_iso()})


def _run_iep_internal(req_id: str) -> None:
    req_row = csv_store.get_request(req_id)
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    if req_row.get("status") != "studies":
        raise HTTPException(status_code=400, detail="IEP draft requires status=studies")
    payload = mock_ai.run_iep(_enriched(req_row))
    mock_ai.persist_stage(req_id, "iep", "main", payload)
    csv_store.update_request_row(req_id, {"status": "iep", "updated_at": mock_ai.now_iso()})


@router.post("/{request_id}/run/landscape")
def run_landscape(request_id: str):
    _run_landscape_internal(request_id)
    return {"ok": True, "status": "landscape"}


@router.post("/{request_id}/run/gaps")
def run_gaps(request_id: str):
    _run_gaps_internal(request_id)
    return {"ok": True, "status": "gaps"}


@router.post("/{request_id}/run/studies")
def run_studies(request_id: str):
    _run_studies_internal(request_id)
    return {"ok": True, "status": "studies"}


@router.post("/{request_id}/run/iep")
def run_iep(request_id: str):
    _run_iep_internal(request_id)
    return {"ok": True, "status": "iep"}


@router.post("/{request_id}/orchestrate")
def orchestrate(request_id: str):
    """Run all four agents in sequence (wizard convenience)."""
    _run_landscape_internal(request_id)
    _run_gaps_internal(request_id)
    _run_studies_internal(request_id)
    _run_iep_internal(request_id)
    return {"ok": True, "status": "iep"}


@router.post("/{request_id}/submit-review")
def submit_for_review(request_id: str):
    req_row = csv_store.get_request(request_id)
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    if req_row.get("status") != "iep":
        raise HTTPException(status_code=400, detail="Submit requires status=iep (complete draft first)")
    csv_store.update_request_row(
        request_id, {"status": "in_review", "updated_at": mock_ai.now_iso()}
    )
    return {"ok": True, "status": "in_review"}


@router.post("/{request_id}/chat", response_model=ChatResponse)
def chat(request_id: str, body: ChatBody):
    req_row = csv_store.get_request(request_id)
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    iep_existing = mock_ai.load_stage_payload(request_id, "iep", "main")
    if iep_existing is None:
        raise HTTPException(status_code=400, detail="Generate IEP draft before chat refinement")

    user_msg = mock_ai.new_id("msg")
    csv_store.append_row(
        "chat_messages.csv",
        {
            "message_id": user_msg,
            "request_id": request_id,
            "role": "user",
            "content": body.message,
            "timestamp": mock_ai.now_iso(),
        },
    )

    updated_iep, assistant_text = mock_ai.refine_iep_with_chat(_enriched(req_row), body.message)
    mock_ai.persist_stage(request_id, "iep", "main", updated_iep)

    asst_msg = mock_ai.new_id("msg")
    csv_store.append_row(
        "chat_messages.csv",
        {
            "message_id": asst_msg,
            "request_id": request_id,
            "role": "assistant",
            "content": assistant_text,
            "timestamp": mock_ai.now_iso(),
        },
    )
    _touch(request_id)

    return ChatResponse(
        assistant_message=ChatMessage(
            message_id=asst_msg,
            request_id=request_id,
            role="assistant",
            content=assistant_text,
            timestamp=mock_ai.now_iso(),
        ),
        iep_updated=True,
    )


@router.get("/{request_id}/messages", response_model=List[ChatMessage])
def list_messages(request_id: str):
    rows = [r for r in _table("chat_messages.csv") if r.get("request_id") == request_id]
    rows.sort(key=lambda r: r.get("timestamp", ""))
    return [ChatMessage.model_validate(r) for r in rows]


@router.post("/{request_id}/regenerate-section")
def regenerate_section(request_id: str, body: RegenerateSectionBody):
    req_row = csv_store.get_request(request_id)
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    full = mock_ai.regenerate_iep_section(_enriched(req_row), body.section_heading)
    if full is None:
        raise HTTPException(status_code=404, detail="Section heading not found")
    mock_ai.persist_stage(request_id, "iep", "main", full)
    _touch(request_id)
    return {"ok": True}


@router.post("/{request_id}/review", response_model=ReviewRecord)
def review(request_id: str, body: ReviewBody):
    req_row = csv_store.get_request(request_id)
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    if req_row.get("status") != "in_review":
        raise HTTPException(status_code=400, detail="Review actions require status=in_review")

    rid = mock_ai.new_id("rev")
    now = mock_ai.now_iso()
    csv_store.append_row(
        "reviews.csv",
        {
            "review_id": rid,
            "request_id": request_id,
            "approver": body.approver,
            "decision": body.decision.value,
            "comments": body.comments,
            "timestamp": now,
        },
    )

    new_status = req_row.get("status")
    if body.decision == ReviewDecision.approve:
        new_status = "approved"
    elif body.decision == ReviewDecision.reject:
        new_status = "iep"
    else:
        new_status = "in_review"

    csv_store.update_request_row(request_id, {"status": new_status, "updated_at": now})

    return ReviewRecord(
        review_id=rid,
        request_id=request_id,
        approver=body.approver,
        decision=body.decision.value,
        comments=body.comments,
        timestamp=now,
    )
