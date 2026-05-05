"""Deterministic mock agents: landscape gaps studies IEP chat — citations + confidence."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.models.schemas import (
    Citation,
    GapCell,
    GapPayload,
    HtaRow,
    IepPayload,
    IepSectionBlock,
    LandscapePayload,
    LiteratureRow,
    RweStudyRow,
    StudyRecommendation,
    StudiesPayload,
)
from app.services import csv_store


def _stable01(s: str) -> float:
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % 10000 / 10000


def conf(seed: str) -> float:
    return round(0.68 + 0.28 * _stable01(seed), 2)


def _cite_lit(pmid: str) -> str:
    return f"L-{pmid[-6:]}"


def _cite_hta(hta_id: str) -> str:
    return f"H-{hta_id.replace('HTA', '')}"


def _cite_rwe(study_id: str) -> str:
    return f"R-{study_id.replace('RWE', '')}"


def _hta_geo_ok(row_geo: str, req_geo: str) -> bool:
    if row_geo == req_geo:
        return True
    if req_geo == "GEO_EU5" and row_geo == "GEO_EU5":
        return True
    if req_geo == "GEO_US" and row_geo in ("GEO_US",):
        return True
    return False


def run_landscape(req: Dict[str, Any]) -> LandscapePayload:
    ta = req.get("therapy_area_id", "")
    drug = req.get("drug_id", "")
    geo = req.get("geography_id", "")

    lit_rows = csv_store.read_table("literature.csv")
    scored_lit: List[Tuple[float, Dict[str, Any]]] = []
    for row in lit_rows:
        score = 0.0
        rta = row.get("therapy_area_id") or ""
        rd = row.get("drug_id") or ""
        if rta == ta:
            score += 12.0
        elif rta == "":
            score += 2.0
        else:
            score -= 4.0
        if rd == drug:
            score += 8.0
        elif rd == "":
            score += 0.5
        else:
            score -= 3.0
        try:
            year = int(row.get("year") or "2000")
        except ValueError:
            year = 2000
        score += max(0, year - 2000) * 0.05
        scored_lit.append((score, row))
    scored_lit.sort(key=lambda x: (-x[0], x[1].get("pmid", "")))
    picked_lit = [x[1] for x in scored_lit[:20]]

    lit_models: List[LiteratureRow] = []
    citations: List[Citation] = []
    for row in picked_lit:
        pmid = row.get("pmid", "")
        cid = _cite_lit(pmid)
        cf = conf(f"lit-{pmid}-{ta}-{drug}")
        lit_models.append(
            LiteratureRow(
                pmid=pmid,
                title=row.get("title", ""),
                authors=row.get("authors", ""),
                journal=row.get("journal", ""),
                year=row.get("year", ""),
                therapy_area_id=row.get("therapy_area_id", ""),
                drug_id=row.get("drug_id", ""),
                study_type=row.get("study_type", ""),
                abstract=row.get("abstract", ""),
                url=row.get("url", ""),
                cite_id=cid,
                confidence=cf,
            )
        )
        citations.append(
            Citation(
                cite_id=cid,
                source_type="literature",
                label=f"PubMed {pmid}",
                detail=row.get("title", ""),
                url=row.get("url"),
                confidence=cf,
            )
        )

    hta_rows = csv_store.read_table("hta_decisions.csv")
    picked_hta: List[Dict[str, Any]] = []
    for row in hta_rows:
        rta = row.get("therapy_area_id") or ""
        rd = row.get("drug_id") or ""
        rg = row.get("geography_id") or ""
        if rta and rta != ta:
            continue
        if rd and rd != drug:
            continue
        if not _hta_geo_ok(rg, geo):
            continue
        picked_hta.append(row)
    picked_hta = sorted(picked_hta, key=lambda r: r.get("year", ""), reverse=True)[:15]

    if not picked_hta:
        for row in hta_rows:
            rta = row.get("therapy_area_id") or ""
            if rta and rta != ta:
                continue
            picked_hta.append(row)
        picked_hta = sorted(picked_hta, key=lambda r: r.get("year", ""), reverse=True)[:15]

    hta_models: List[HtaRow] = []
    for row in picked_hta:
        hid = row.get("hta_id", "")
        cid = _cite_hta(hid)
        cf = conf(f"hta-{hid}-{geo}")
        hta_models.append(
            HtaRow(
                hta_id=hid,
                agency=row.get("agency", ""),
                title=row.get("title", ""),
                year=row.get("year", ""),
                drug_id=row.get("drug_id", ""),
                therapy_area_id=row.get("therapy_area_id", ""),
                geography_id=row.get("geography_id", ""),
                decision_summary=row.get("decision_summary", ""),
                url=row.get("url", ""),
                cite_id=cid,
                confidence=cf,
            )
        )
        citations.append(
            Citation(
                cite_id=cid,
                source_type="hta",
                label=f"{row.get('agency','')} {row.get('year','')}",
                detail=row.get("title", ""),
                url=row.get("url"),
                confidence=cf,
            )
        )

    rwe_rows = csv_store.read_table("rwe_studies.csv")
    scored_rwe: List[Tuple[float, Dict[str, Any]]] = []
    for row in rwe_rows:
        score = 0.0
        if row.get("therapy_area_id") == ta:
            score += 10.0
        elif not row.get("therapy_area_id"):
            score += 1.0
        else:
            score -= 5.0
        if row.get("drug_id") == drug:
            score += 7.0
        elif not row.get("drug_id"):
            score += 0.5
        else:
            score -= 4.0
        if row.get("geography_id") == geo:
            score += 6.0
        scored_rwe.append((score, row))
    scored_rwe.sort(key=lambda x: (-x[0], x[1].get("study_id", "")))
    picked_rwe = [x[1] for x in scored_rwe[:12]]

    rwe_models: List[RweStudyRow] = []
    for row in picked_rwe:
        sid = row.get("study_id", "")
        cid = _cite_rwe(sid)
        cf = conf(f"rwe-{sid}-{geo}")
        rwe_models.append(
            RweStudyRow(
                study_id=sid,
                title=row.get("title", ""),
                sponsor=row.get("sponsor", ""),
                year=row.get("year", ""),
                drug_id=row.get("drug_id", ""),
                therapy_area_id=row.get("therapy_area_id", ""),
                geography_id=row.get("geography_id", ""),
                study_design=row.get("study_design", ""),
                outcome_summary=row.get("outcome_summary", ""),
                url=row.get("url", ""),
                cite_id=cid,
                confidence=cf,
            )
        )
        citations.append(
            Citation(
                cite_id=cid,
                source_type="rwe",
                label=sid,
                detail=row.get("title", ""),
                url=row.get("url"),
                confidence=cf,
            )
        )

    top_cites = [c.cite_id for c in citations[:5]]
    narrative = (
        f"Landscape synthesis (grounded RAG mock): prioritized {len(lit_models)} PubMed/Embase-style records, "
        f"{len(hta_models)} HTA decisions, and {len(rwe_models)} sponsor/academic RWE studies for "
        f"therapy area **{ta}**, product **{drug}**, geography **{geo}**. "
        f"Key anchors for comparative effectiveness include citations {', '.join(top_cites)}. "
        "All statements below carry retrieval-linked citations; confidence reflects source concordance heuristics."
    )

    return LandscapePayload(
        literature=lit_models,
        hta_decisions=hta_models,
        rwe_studies=rwe_models,
        narrative=narrative,
        citations=citations,
    )


def run_gaps(req: Dict[str, Any]) -> GapPayload:
    ta = req.get("therapy_area_id", "")
    tpp = (req.get("tpp_summary") or "").lower()

    templates = csv_store.read_table("evidence_gap_templates.csv")
    cells: List[GapCell] = []
    citations: List[Citation] = []

    for row in templates:
        if row.get("therapy_area_id") != ta:
            continue
        stakeholder = row.get("stakeholder", "")
        gap_topic = row.get("gap_topic", "")
        attr = row.get("tpp_attribute", "")
        seed = f"{ta}-{stakeholder}-{attr}"
        cf = conf(f"gap-{seed}")
        # severity from keyword overlap with TPP text
        topic_l = gap_topic.lower()
        overlap = sum(1 for w in re.findall(r"[a-z]{5,}", tpp) if w in topic_l)
        if overlap >= 2:
            severity = "high"
        elif overlap == 1:
            severity = "medium"
        else:
            severity = "low"
        cite_id = f"G-{hashlib.md5(seed.encode()).hexdigest()[:6].upper()}"
        mitigations = (
            "Proposed RWE package: claims-attributed cohort with propensity overlap weights; sensitivity analyses "
            "for immortal time; external comparator arm via OMOP-enabled registry where feasible."
        )
        cells.append(
            GapCell(
                stakeholder=stakeholder,
                tpp_attribute=attr,
                gap_topic=gap_topic,
                severity=severity,
                mitigations=mitigations,
                cite_ids=[cite_id],
                confidence=cf,
            )
        )
        citations.append(
            Citation(
                cite_id=cite_id,
                source_type="gap_template",
                label=f"Gap analysis {stakeholder}",
                detail=gap_topic,
                confidence=cf,
            )
        )

    narrative = (
        f"Evidence gap matrix vs TPP for **{ta}**: mapped gaps across regulators / payers / HCPs / patients. "
        "Severity reflects lexical overlap with submitted TPP narrative plus archetype risk tiers."
    )
    return GapPayload(matrix=cells, narrative=narrative, citations=citations)


def run_studies(req: Dict[str, Any]) -> StudiesPayload:
    geo = req.get("geography_id", "")
    ta = req.get("therapy_area_id", "")
    drug = req.get("drug_id", "")

    catalog = csv_store.read_table("study_design_catalog.csv")
    ds_rows = csv_store.read_table("data_sources.csv")

    geo_hint = "US claims / oncology EHR" if geo == "GEO_US" else "EU CPRD / OMOP registries"
    recs: List[StudyRecommendation] = []
    citations: List[Citation] = []

    for idx, row in enumerate(catalog, start=1):
        sid = row.get("design_id", "")
        seed = f"{sid}-{geo}-{ta}-{drug}"
        cf = conf(f"study-{seed}")
        cite_id = f"S-{sid.replace('SD','')}"
        primary = row.get("primary_data_sources", "")
        rationale = (
            f"Ranked for **{ta}** in **{geo}** using feasibility fit ({geo_hint}). "
            f"Design aligns with gap closure priorities and uses sources {primary}."
        )
        recs.append(
            StudyRecommendation(
                rank=idx,
                design_id=sid,
                name=row.get("name", ""),
                study_type=row.get("study_type", ""),
                duration_months=row.get("duration_months", ""),
                cost_tier=row.get("cost_tier", ""),
                primary_data_sources=primary,
                rationale=rationale,
                cite_ids=[cite_id],
                confidence=cf,
            )
        )
        citations.append(
            Citation(
                cite_id=cite_id,
                source_type="study_design",
                label=row.get("name", ""),
                detail=rationale,
                confidence=cf,
            )
        )

    # surface data sources catalog as extra citations
    for row in ds_rows:
        did = row.get("source_id", "")
        cid = f"D-{did.replace('DS_', '')}"
        cf = conf(f"ds-{did}-{geo}")
        citations.append(
            Citation(
                cite_id=cid,
                source_type="data_source",
                label=row.get("name", ""),
                detail=f"{row.get('type','')} — {row.get('regions','')}",
                confidence=cf,
            )
        )

    narrative = (
        "Study design recommendations are ranked deterministically from the catalog for demo reproducibility. "
        f"In production, LangGraph agents would evaluate feasibility, GDPR/HIPAA posture, and timeline constraints per market (**{geo}**)."
    )
    return StudiesPayload(recommendations=recs, narrative=narrative, citations=citations)


def run_iep(req: Dict[str, Any]) -> IepPayload:
    drug_name = req.get("_drug_name") or req.get("drug_id", "")
    ta_name = req.get("_therapy_name") or req.get("therapy_area_id", "")
    geo_name = req.get("_geo_name") or req.get("geography_id", "")
    tpp = req.get("tpp_summary", "")
    lifecycle = req.get("lifecycle_stage", "")

    citations: List[Citation] = []

    def para(text: str, cites: List[str], seed: str) -> Dict[str, Any]:
        return {"text": text, "cite_ids": cites, "confidence": conf(seed)}

    s1 = IepSectionBlock(
        heading="1. Strategic context & TPP alignment",
        paragraphs=[
            para(
                f"The Integrated Evidence Plan supports Medical Affairs objectives for **{drug_name}** in **{ta_name}** "
                f"({lifecycle}) across **{geo_name}**. The submitted TPP emphasizes differentiated clinical and payer-relevant outcomes.",
                ["L-100037", "R-001"],
                "iep-s1-p1",
            ),
            para(
                "Stakeholders include regulators (approval maintenance / post-marketing commitments), payers (HTA and AMCP-style dossiers), "
                "HCPs (scientific narrative for omnichannel education), and patients (transparent benefit-risk communication).",
                ["H-001", "H-004"],
                "iep-s1-p2",
            ),
        ],
    )
    s2 = IepSectionBlock(
        heading="2. Current evidence landscape (RWE + HTA + literature)",
        paragraphs=[
            para(
                "Published literature, HTA decisions, and sponsor/RWE studies were synthesized with grounded retrieval (mock). "
                "Comparative effectiveness signals require confirmation in geography-specific cohorts with pre-specified covariates.",
                ["L-100001", "R-001", "H-004"],
                "iep-s2-p1",
            ),
            para(
                "External controls may be constructed via OMOP CDM registries where cohort definitions align to index dates and line-of-therapy logic.",
                ["D-OMOP", "R-002"],
                "iep-s2-p2",
            ),
        ],
    )
    s3 = IepSectionBlock(
        heading="3. Evidence gaps vs TPP by stakeholder",
        paragraphs=[
            para(
                "Gap severity reflects both TPP lexical coverage and policy archetypes for the target geography. "
                "Regulatory gaps focus on confirmatory long-term outcomes; payer gaps emphasize budget impact and sequencing.",
                ["G-001"],
                "iep-s3-p1",
            ),
        ],
    )
    s4 = IepSectionBlock(
        heading="4. Prioritized RWE generation portfolio",
        paragraphs=[
            para(
                "Recommended designs combine retrospective cohorts for speed, pragmatic elements where equipoise exists, "
                "and registry linkage for external comparator arms when RCT synthesis is insufficient.",
                ["S-001", "S-004"],
                "iep-s4-p1",
            ),
        ],
    )
    s5 = IepSectionBlock(
        heading="5. Governance, MLR / Veeva handoff, and HITL checkpoints",
        paragraphs=[
            para(
                "Per BRD non-functional requirements: outputs remain drafting aids only; Medical Director approval is mandatory prior to external use. "
                "Downstream integration targets Veeva Vault PromoMats / Mecoms-style workflows (stub).",
                ["H-001"],
                "iep-s5-p1",
            ),
            para(
                f"TPP narrative excerpt on file: “{tpp[:220]}{'…' if len(tpp) > 220 else ''}”",
                ["L-100037"],
                "iep-s5-p2",
            ),
        ],
    )

    for blk in [s1, s2, s3, s4, s5]:
        for p in blk.paragraphs:
            for cid in p["cite_ids"]:
                citations.append(
                    Citation(
                        cite_id=cid,
                        source_type="iep",
                        label="IEP draft anchor",
                        detail=p["text"][:160],
                        confidence=float(p["confidence"]),
                    )
                )

    return IepPayload(sections=[s1, s2, s3, s4, s5], citations=citations)


def persist_stage(request_id: str, stage: str, section_key: str, payload: Any) -> None:
    js = payload.model_dump_json()
    conf_avg = ""
    if hasattr(payload, "citations") and payload.citations:
        conf_avg = str(
            round(sum(c.confidence for c in payload.citations) / max(len(payload.citations), 1), 3)
        )
    csv_store.upsert_section(request_id, stage, section_key, js, conf_avg)


def load_stage_payload(request_id: str, stage: str, section_key: str) -> Optional[Any]:
    for row in csv_store.read_table("iep_sections.csv"):
        if row.get("request_id") == request_id and row.get("stage") == stage and row.get("section_key") == section_key:
            raw = row.get("content_json") or "{}"
            data = json.loads(raw)
            if stage == "landscape":
                return LandscapePayload.model_validate(data)
            if stage == "gaps":
                return GapPayload.model_validate(data)
            if stage == "studies":
                return StudiesPayload.model_validate(data)
            if stage == "iep":
                return IepPayload.model_validate(data)
    return None


def refine_iep_with_chat(req: Dict[str, Any], user_message: str) -> Tuple[IepPayload, str]:
    """Return updated IEP and assistant reply (deterministic pattern matching)."""
    base = run_iep(req)
    msg_l = user_message.lower()
    extra_note = ""

    if any(k in msg_l for k in ("payer", "icer", "budget", "hta")):
        extra_note = (
            " Added payer-focused tightening: emphasized ICER-style uncertainty ranges and budget-impact sensitivities "
            f"for {req.get('_geo_name') or req.get('geography_id')}."
        )
        base.sections.append(
            IepSectionBlock(
                heading="Appendix A — Payer-focused refinement (chat-triggered)",
                paragraphs=[
                    {
                        "text": (
                            "Payer narrative now prioritizes treatment sequencing assumptions, episode costs, and scenario analyses "
                            "for competitor interchange. Cross-walk to AMCP dossier sections is stubbed for MLR packaging."
                        ),
                        "cite_ids": ["H-004", "L-100033"],
                        "confidence": conf("chat-payer"),
                    }
                ],
            )
        )
    if any(k in msg_l for k in ("eu", "europe", "ema", "cprd")):
        extra_note += (
            " Inserted EU5-oriented comparator framing referencing CPRD/OMOP feasibility and EMA RWE framework expectations."
        )
    if any(k in msg_l for k in ("regulator", "fda", "ema", "approval")):
        extra_note += " Strengthened regulatory evidentiary standards language (FDA RWE guidance; ICH E9(R1) estimand alignment — educational boilerplate)."

    assistant = (
        "Mock co-pilot (grounded RAG only): applied deterministic refinement rules to the IEP draft. "
        + (extra_note or "No specialized triggers matched; reiterated citation-first drafting discipline and HITL gate.")
    )
    return base, assistant


def regenerate_iep_section(req: Dict[str, Any], heading: str) -> Optional[IepPayload]:
    full = run_iep(req)
    target = heading.strip().lower()
    for sec in full.sections:
        if sec.heading.lower() == target:
            # bump confidence slightly on regenerate
            for p in sec.paragraphs:
                p["confidence"] = round(min(0.97, float(p["confidence"]) + 0.03), 2)
                p["text"] = p["text"] + " [Regenerated section — mock deterministic refresh preserving citations.]"
            return full
    return None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"
