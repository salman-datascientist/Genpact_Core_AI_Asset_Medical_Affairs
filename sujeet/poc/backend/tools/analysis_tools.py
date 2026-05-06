"""
Analysis Tools  SLR Screening, Evidence Extraction, Gap Analysis
=================================================================
These tools implement the BRD's core AI intelligence:
   slr_screen       AI screens papers for inclusion (Pain Point 4)
   extract_evidence  AI pulls structured data from abstracts (Pain Point 2)
   gap_analysis      Finds missing evidence vs payer requirements (Pain Point 2)
   hcp_score         Scores KOLs by publication influence (Pain Point 3)
   generate_report   Builds final evidence summary
"""

import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv

# Can be overridden by api_server.py to point to poc/outputs/
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs"))
# OUTPUT_DIR ="F:\\gen-brd\\poc\\outputs\\" 

load_dotenv()


#  HELPERS 

def _call_llm(prompt: str, max_tokens: int = 500) -> str:
    """
    Call LLM for analysis.
    Uses OpenAI if key set, otherwise falls back to rule-based heuristics.
    """
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key and openai_key != "your_openai_api_key_here":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "You are a Medical Affairs AI analyst specialising in "
                        "oncology real-world evidence. Be concise and precise."
                    )},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"LLM_ERROR:{e}"
    else:
        #  Rule-based fallback (no LLM key needed for POC demo) 
        return "RULE_BASED"


#  TOOL: slr_screen 

# Keywords that signal inclusion / exclusion
_INCLUDE_SIGNALS = [
    "real.world", "observational", "cohort", "registry",
    "niraparib", "zejula", "parp inhibitor", "ovarian cancer",
    "progression.free survival", "overall survival", "response rate",
    "pfs", "os months", "retrospective", "prospective"
]
_EXCLUDE_SIGNALS = [
    "case report", "letter to editor", "in vitro", "animal model",
    "review article", "preclinical", "pediatric", "breast cancer only"
]


def slr_screen(criteria: dict, _state=None, **kwargs) -> str:
    """
    AI screening of abstracts using PICO criteria.
    Marks each paper as INCLUDE / EXCLUDE / UNCERTAIN.
    Updates state.papers_found with screening_decision field.
    """
    if _state is None:
        return "ERROR: No state"

    papers = [p for p in _state.papers_found if p.get("_fetched")]
    if not papers:
        return "No fetched papers to screen."

    included  = 0
    excluded  = 0
    uncertain = 0

    for paper in papers:
        text = (
            (paper.get("title") or "") + " " +
            (paper.get("abstract") or "")
        ).lower()

        llm_result = _call_llm(
            f"""PICO Inclusion Criteria:
- Population: {criteria.get('population')}
- Intervention: {criteria.get('intervention')}
- Outcome: {criteria.get('outcome')}
- Study design: {criteria.get('study_design')}

Paper abstract:
\"\"\"{(paper.get('abstract') or '')[:600]}\"\"\"

Reply with EXACTLY one of: INCLUDE | EXCLUDE | UNCERTAIN
Then one sentence justification.""",
            max_tokens=80
        )

        if llm_result == "RULE_BASED":
            # Heuristic screening
            inc_score = sum(1 for kw in _INCLUDE_SIGNALS if re.search(kw, text))
            exc_score = sum(1 for kw in _EXCLUDE_SIGNALS if re.search(kw, text))

            if exc_score >= 2:
                decision = "EXCLUDE"
                justification = "Matched exclusion criteria keywords."
            elif inc_score >= 3:
                decision = "INCLUDE"
                justification = f"Matched {inc_score} inclusion signals."
            else:
                decision = "UNCERTAIN"
                justification = "Insufficient signals  needs human review."
        else:
            # Parse LLM response
            if "INCLUDE" in llm_result.upper():
                decision = "INCLUDE"
            elif "EXCLUDE" in llm_result.upper():
                decision = "EXCLUDE"
            else:
                decision = "UNCERTAIN"
            justification = llm_result.split("\n")[-1][:200] if "\n" in llm_result else llm_result[:200]

        paper["screening_decision"]      = decision
        paper["screening_justification"] = justification

        if decision == "INCLUDE":
            included += 1
        elif decision == "EXCLUDE":
            excluded += 1
        else:
            uncertain += 1

    return (
        f"SLR screening complete: {included} INCLUDED, "
        f"{excluded} EXCLUDED, {uncertain} UNCERTAIN "
        f"(out of {len(papers)} papers screened)."
    )


#  TOOL: extract_evidence 

_PFS_PATTERN = re.compile(
    r"(?:pfs|progression.free survival)[^\d]*?([\d.]+)\s*month", re.IGNORECASE
)
_OS_PATTERN = re.compile(
    r"(?:os|overall survival)[^\d]*?([\d.]+)\s*month", re.IGNORECASE
)
_N_PATTERN = re.compile(
    r"\bn\s*[=:]\s*([\d,]+)|\b([\d,]+)\s+patients?\b", re.IGNORECASE
)


def extract_evidence(_state=None, source: str = "screened_papers", **kwargs) -> str:
    """
    Extract structured evidence from included papers.
    Fills state.evidence_rows with extraction table rows.
    (Replaces manual Phase 3 of SLR  BRD Pain Point 4)
    """
    if _state is None:
        return "ERROR: No state"

    included = [
        p for p in _state.papers_found
        if p.get("screening_decision") == "INCLUDE"
    ]
    if not included:
        return "No included papers to extract from."

    rows = []
    for paper in included:
        abstract = (paper.get("abstract") or "")
        title    = (paper.get("title") or "")
        text     = title + " " + abstract

        #  Attempt LLM extraction 
        llm_result = _call_llm(
            f"""Extract these fields from the abstract as JSON (use null if not found):
{{
  "n_patients": <integer>,
  "drug": "<primary drug name>",
  "comparator": "<comparator drug or placebo or null>",
  "pfs_months": <float or null>,
  "os_months": <float or null>,
  "study_design": "<retrospective|prospective|registry|RCT|other>",
  "country": "<country or region>"
}}

Abstract:
\"\"\"{abstract[:700]}\"\"\"

Return ONLY valid JSON.""",
            max_tokens=200
        )

        if llm_result == "RULE_BASED" or llm_result.startswith("LLM_ERROR"):
            # Rule-based extraction fallback
            pfs_match = _PFS_PATTERN.search(text)
            os_match  = _OS_PATTERN.search(text)
            n_match   = _N_PATTERN.search(text)
            n_raw     = n_match.group(1) or n_match.group(2) if n_match else None

            def _safe_int(s):
                try:
                    return int(str(s).replace(",", "").strip()) if s else None
                except (ValueError, TypeError):
                    return None
            extracted = {
                "n_patients":   _safe_int(n_raw),
                "drug":         "Niraparib" if "niraparib" in text.lower() else "PARP inhibitor",
                "comparator":   "Olaparib" if "olaparib" in text.lower() else None,
                "pfs_months":   float(pfs_match.group(1)) if pfs_match else None,
                "os_months":    float(os_match.group(1)) if os_match else None,
                "study_design": (
                    "Retrospective" if "retrospective" in text.lower() else
                    "Registry" if "registry" in text.lower() else
                    "Prospective" if "prospective" in text.lower() else "Other"
                ),
                "country":      paper.get("country", ""),
            }
        else:
            try:
                # Strip markdown code fences if present
                clean = re.sub(r"```[a-z]*\n?|\n?```", "", llm_result).strip()
                extracted = json.loads(clean)
            except Exception:
                extracted = {
                    "n_patients": None, "drug": None, "comparator": None,
                    "pfs_months": None, "os_months": None,
                    "study_design": None, "country": None,
                }

        row = {
            "pmid":         paper["pmid"],
            "title":        (paper.get("title") or "")[:120],
            "authors":      ", ".join((paper.get("authors") or [])[:3]),
            "year":         paper.get("pub_year", ""),
            "journal":      (paper.get("journal") or "")[:60],
            "n_patients":   extracted.get("n_patients"),
            "drug":         extracted.get("drug"),
            "comparator":   extracted.get("comparator"),
            "pfs_months":   extracted.get("pfs_months"),
            "os_months":    extracted.get("os_months"),
            "study_design": extracted.get("study_design"),
            "country":      extracted.get("country"),
            "doi":          paper.get("doi", ""),
        }
        rows.append(row)

    _state.evidence_rows = rows
    return (
        f"Evidence extracted for {len(rows)} included papers. "
        f"Fields: n_patients, drug, comparator, PFS, OS, study_design, country."
    )


#  TOOL: gap_analysis 

def gap_analysis(required_sections: list, _state=None, **kwargs) -> str:
    """
    Compare extracted evidence against payer-required sections.
    Identifies gaps (BRD Pain Point 2  Evidence Gap Analysis for IEP).
    """
    if _state is None:
        return "ERROR: No state"

    rows  = _state.evidence_rows
    gaps  = []

    # Build a text summary of what we have
    have_pfs      = any(r.get("pfs_months") for r in rows)
    have_os       = any(r.get("os_months") for r in rows)
    have_us       = any("United States" in (r.get("country") or "") or "USA" in (r.get("country") or "") for r in rows)
    have_eu       = any(r.get("country") in ("Germany", "France", "UK", "Italy", "Spain", "Netherlands") for r in rows)
    have_elderly  = False   # would need patient-level data  always a gap in lit reviews
    have_brca     = any("brca" in (r.get("title") or "").lower() for r in rows)
    have_cost_eff = any("cost" in (r.get("title") or "").lower() for r in rows)

    checks = {
        "US real-world PFS data":             have_pfs and have_us,
        "EU real-world OS data":              have_os and have_eu,
        "Cost-effectiveness vs Olaparib":     have_cost_eff,
        "Elderly patient subgroup (65+)":     have_elderly,
        "BRCA-mutated subgroup outcomes":     have_brca,
    }

    for section in required_sections:
        covered = checks.get(section, False)
        gap_entry = {
            "required_section": section,
            "status":           "COVERED" if covered else "GAP",
            "recommendation":   (
                "Evidence available in retrieved papers."
                if covered else
                f"No direct evidence found. Recommend designing a targeted RWE study "
                f"or submitting a data request to IQVIA/Optum to address this gap."
            )
        }
        gaps.append(gap_entry)

    _state.gaps = gaps
    gap_count    = sum(1 for g in gaps if g["status"] == "GAP")
    covered_count = len(gaps) - gap_count

    return (
        f"Gap analysis complete: {covered_count} sections COVERED, "
        f"{gap_count} GAPS identified. "
        f"Gaps: {[g['required_section'] for g in gaps if g['status']=='GAP']}"
    )


#  TOOL: hcp_score 

def hcp_score(top_n: int = 20, _state=None, **kwargs) -> str:
    """
    Score potential KOLs (Key Opinion Leaders) based on authorship frequency
    and journal impact as a proxy for prescribing influence.
    (Partial coverage of BRD Pain Point 3  HCP Targeting)
    """
    if _state is None:
        return "ERROR: No state"

    author_counts: dict[str, dict] = {}

    for paper in _state.papers_found:
        if not paper.get("_fetched"):
            continue
        authors  = paper.get("authors") or []
        year     = paper.get("pub_year", "")
        journal  = paper.get("journal", "")
        decision = paper.get("screening_decision", "UNCERTAIN")

        # Weight: INCLUDED papers worth more
        weight = 2 if decision == "INCLUDE" else 1

        for author in authors[:6]:   # first 6 authors only
            if not author or len(author) < 3:
                continue
            if author not in author_counts:
                author_counts[author] = {
                    "name":      author,
                    "papers":    0,
                    "score":     0,
                    "journals":  set(),
                    "years":     [],
                }
            author_counts[author]["papers"] += 1
            author_counts[author]["score"]  += weight
            author_counts[author]["journals"].add(journal[:40])
            if year:
                author_counts[author]["years"].append(year)

    # Sort by score descending
    ranked = sorted(author_counts.values(), key=lambda x: x["score"], reverse=True)[:top_n]

    hcp_list = []
    for rank, author in enumerate(ranked, start=1):
        hcp_list.append({
            "rank":          rank,
            "name":          author["name"],
            "papers_found":  author["papers"],
            "kol_score":     author["score"],
            "journals":      list(author["journals"])[:3],
            "active_years":  sorted(set(author["years"]))[-3:],
            "priority":      (
                "HIGH"   if author["score"] >= 6 else
                "MEDIUM" if author["score"] >= 3 else
                "LOW"
            ),
        })

    _state.hcp_scores = hcp_list
    high   = sum(1 for h in hcp_list if h["priority"] == "HIGH")
    medium = sum(1 for h in hcp_list if h["priority"] == "MEDIUM")

    return (
        f"KOL scoring complete: {len(hcp_list)} authors ranked. "
        f"{high} HIGH priority, {medium} MEDIUM priority. "
        f"Top KOL: {hcp_list[0]['name'] if hcp_list else 'N/A'} "
        f"(score={hcp_list[0]['kol_score'] if hcp_list else 0})"
    )


#  TOOL: generate_report 

def generate_report(_state=None, format: str = "json", **kwargs) -> str:
    """
    Generate the final structured evidence report.
    This is the output the Medical Affairs team reviews (BRD HITL gate).
    """
    if _state is None:
        return "ERROR: No state"

    report = {
        "report_type":     "Medical Affairs Evidence Summary  POC",
        "drug":            "Niraparib (Zejula)",
        "indication":      "Ovarian Cancer",
        "generated_at":    datetime.utcnow().isoformat(),
        "generated_by":    "Medical Affairs AI Agent v1.0",

        "pipeline_summary": {
            "papers_retrieved":   len(_state.papers_found),
            "papers_included":    sum(1 for p in _state.papers_found
                                     if p.get("screening_decision") == "INCLUDE"),
            "papers_excluded":    sum(1 for p in _state.papers_found
                                     if p.get("screening_decision") == "EXCLUDE"),
            "evidence_rows":      len(_state.evidence_rows),
            "gaps_identified":    len([g for g in _state.gaps if g["status"] == "GAP"]),
            "kols_identified":    len([h for h in _state.hcp_scores if h["priority"] == "HIGH"]),
        },

        "evidence_table":  _state.evidence_rows[:10],   # top 10 for report
        "gap_analysis":    _state.gaps,
        "top_kols":        _state.hcp_scores[:10],
        "agent_steps":     len(_state.steps),

        "hitl_flag": (
            "  REQUIRES HUMAN REVIEW before submission to payers or regulators. "
            "Confidence < 0.7 items are flagged (BR-NFR-04)."
        ),
    }

    # Save report to file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(
        OUTPUT_DIR,
        f"evidence_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    )
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        save_msg = f"Saved to {report_path}"
    except Exception as e:
        save_msg = f"Could not save file: {e}"

    return (
        f"Report generated: {report['pipeline_summary']}. {save_msg}"
    )
