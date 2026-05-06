# Medical Affairs AI POC — Q&A 

---

## Q1. What does Evidence Table Extraction mean and what output does it show?

The AI reads the **abstract of each INCLUDED paper** and uses regex patterns + LLM to pull out specific clinical numbers.

**What it looks for in the abstract text:**

```
"PFS" or "progression-free survival" → extracts the number of months
"OS" or "overall survival"           → extracts the number of months
"n = 247" or "247 patients"          → extracts patient count
"retrospective / registry / RCT"     → extracts study design
"olaparib" mentioned                 → sets as comparator
```

**Defined in:** `F:\gen-brd\poc\backend\tools\analysis_tools.py` — lines 153–160

```python
_PFS_PATTERN = re.compile(
    r"(?:pfs|progression.free survival)[^\d]*?([\d.]+)\s*month", re.IGNORECASE
)
_OS_PATTERN = re.compile(
    r"(?:os|overall survival)[^\d]*?([\d.]+)\s*month", re.IGNORECASE
)
_N_PATTERN = re.compile(
    r"\bn\s*[=:]\s*([\d,]+)|\b([\d,]+)\s+patients?\b", re.IGNORECASE
)
```

**Sample Evidence Table output:**

| PMID | Title | Authors | Year | n_patients | Drug | Comparator | PFS (months) | OS (months) | Study Design | Country |
|------|-------|---------|------|-----------|------|------------|-------------|------------|-------------|---------|
| 41765029 | Niraparib real-world outcomes... | Smith J, Patel R | 2023 | 247 | Niraparib | Olaparib | 8.2 | 24.5 | Retrospective | USA |
| 41557987 | PARP inhibitor registry study... | Kumar A, Lee S | 2022 | 183 | Niraparib | null | 6.8 | null | Registry | Germany |

> **Limitation:** Extraction is from publicly available **abstracts only** — not full paper text. Numbers buried in the paper body won't be captured. With OpenAI connected, LLM extraction improves accuracy significantly.

---

## Q2. How does Gap Analysis work and where are the check items defined?

### Where the checks are defined

**File:** `F:\gen-brd\poc\backend\tools\analysis_tools.py` — lines 280–295

```python
# ── What we FOUND in the evidence table ──────────────────────────────
have_pfs      = any(r.get("pfs_months") for r in rows)
have_os       = any(r.get("os_months") for r in rows)
have_us       = any("United States" in (r.get("country") or "") 
                    or "USA" in (r.get("country") or "") for r in rows)
have_eu       = any(r.get("country") in 
                    ("Germany", "France", "UK", "Italy", "Spain", "Netherlands") 
                    for r in rows)
have_elderly  = False   # always a gap — can't determine from abstract alone
have_brca     = any("brca" in (r.get("title") or "").lower() for r in rows)
have_cost_eff = any("cost" in (r.get("title") or "").lower() for r in rows)

# ── Map check results to section names ───────────────────────────────
checks = {
    "US real-world PFS data":         have_pfs and have_us,
    "EU real-world OS data":          have_os and have_eu,
    "Cost-effectiveness vs Olaparib": have_cost_eff,
    "Elderly patient subgroup (65+)": have_elderly,
    "BRCA-mutated subgroup outcomes": have_brca,
}
```

### How it matches to required sections

**File:** `F:\gen-brd\poc\backend\tools\analysis_tools.py` — lines 297–308

```python
for section in required_sections:   # comes from agent_core.py (stakeholder-driven)
    covered = checks.get(section, False)
    gap_entry = {
        "required_section": section,
        "status":           "COVERED" if covered else "GAP",
        "recommendation":   (
            "Evidence available in retrieved papers."
            if covered else
            "No direct evidence found. Recommend designing a targeted RWE study "
            "or submitting a data request to IQVIA/Optum to address this gap."
        )
    }
```

### Sample Gap Analysis output (Regulator/FDA stakeholder)

| Required Section | Status | Recommendation |
|-----------------|--------|---------------|
| Phase III RCT evidence | ⚠️ GAP | No direct evidence found. Recommend IQVIA/Optum data request. |
| Long-term safety (3+ years) | ⚠️ GAP | No direct evidence found. Recommend targeted RWE study. |
| BRCA-mutated subgroup outcomes | ✅ COVERED | Evidence available in retrieved papers. |
| Comparative efficacy vs Olaparib | ⚠️ GAP | No direct evidence found. |
| Patient-reported outcomes (PROs) | ⚠️ GAP | No direct evidence found. |

> **⚠️ Known Limitation (current POC):** The `checks` dictionary keys are hardcoded to the old fixed section names. When a new stakeholder (e.g. FDA, NICE) is selected, the dynamic section names from `agent_core.py` won't match these hardcoded keys — so they'll always show as GAP. This needs to be fixed in the next iteration by making the checks dynamic too.

---

## Q3. How does it give a KOL list without you providing any doctor names?

**It mines author lists directly from the PubMed papers retrieved.**

**Defined in:** `F:\gen-brd\poc\backend\tools\analysis_tools.py` — lines 335–380

### The scoring logic

```python
for paper in all_retrieved_papers:
    for author in paper["authors"][:6]:   # first 6 authors only
        weight = 2 if paper was INCLUDED in SLR else 1
        author_score += weight
        track journals and years published
```

**Then ranked by score — top 20 = KOL list.**

### Scoring example

| Author | Papers Found | INCLUDED Papers | Raw Score | Priority |
|--------|-------------|----------------|-----------|---------|
| Smith J | 7 papers | 5 included | 5×2 + 2×1 = 12 | 🔴 HIGH (score ≥ 6) |
| Patel R | 4 papers | 3 included | 3×2 + 1×1 = 7 | 🔴 HIGH |
| Kumar A | 3 papers | 1 included | 1×2 + 2×1 = 4 | 🟡 MEDIUM (score ≥ 3) |
| Lee S | 2 papers | 0 included | 0×2 + 2×1 = 2 | 🟢 LOW |

**Priority thresholds (from code):**
```python
"HIGH"   if score >= 6
"MEDIUM" if score >= 3
"LOW"    otherwise
```

### Why this works

If a doctor has published **5+ papers specifically on Niraparib in Ovarian Cancer between 2019–2024**, they are almost certainly:
- An active clinical researcher prescribing or trialling this drug
- Influential in the oncology community
- Worth engaging for advisory boards or MSL visits

### Sample KOL Output

| Rank | Name | Papers Found | KOL Score | Journals | Active Years | Priority |
|------|------|-------------|-----------|---------|-------------|---------|
| 1 | Smith J | 7 | 12 | NEJM, Gynecol Oncol | 2022, 2023, 2024 | 🔴 HIGH |
| 2 | Patel R | 4 | 7 | Ann Oncol, JCO | 2022, 2023, 2024 | 🔴 HIGH |
| 3 | Kumar A | 3 | 4 | Lancet Oncol | 2021, 2023 | 🟡 MEDIUM |

> **Limitation:** List is based on **publication activity only** — not prescribing volume, affiliation, or CRM status. A production version would cross-reference with a CRM/HCP database (e.g. Veeva, IQVIA OneKey) to validate and enrich.

---

## Summary of Limitations (for transparency)

| Area | Current POC Approach | Production Upgrade |
|------|---------------------|-------------------|
| Evidence Extraction | Regex on abstracts | LLM on full paper text |
| Gap Analysis checks | Hardcoded keyword matching | LLM semantic matching + dynamic checks |
| KOL Scoring | Publication count only | Publication + prescribing + CRM data |
| SLR Screening | Rule-based without OpenAI key | GPT-4o / Gemini with PICO prompt |


---

## Q4 — What Does Stakeholder Do and How Does It Filter Results?

The **Stakeholder** field is the most powerful filter in the pipeline.
It changes **what the agent looks for** and **what gaps it reports**.

| Stakeholder | What It Changes |
|-------------|----------------|
| **Payer (Aetna / BCBS)** | Looks for RWE/observational/cost studies; gap list asks for cost-effectiveness, budget impact, treatment adherence data |
| **Regulator (FDA / EMA)** | Looks for RCT/pivotal trial papers; gap list asks for safety profile, BRCA subgroups, patient-reported outcomes |
| **HCP (Oncologist)** | Looks for mechanism of action + subgroup papers; gap list asks for combination therapy, biomarker-driven selection data |
| **NICE / HTA** | Looks for health economic studies; gap list asks for QALY, ICER, indirect treatment comparisons |

> **Think of it as:** Same drug, completely different evidence story for a different audience.


### How Stakeholder Changes Each Pipeline Step

| Pipeline Step | Payer | Regulator (FDA) | HCP (Oncologist) |
|--------------|-------|-----------------|-----------------|
| **PubMed Search** | "real world" OR "observational" OR "claims" | "randomized controlled trial" OR "phase III" | "mechanism" OR "subgroup" OR "biomarker" |
| **SLR Screening** | Real-world, cohort, registry studies | Phase III RCT, pivotal studies | Mechanistic studies, subgroup analyses |
| **Gap Analysis** | Cost-effectiveness vs comparator, adherence, budget impact | Long-term safety, BRCA subgroups, PROs | Combination therapy, patient selection evidence |

### Why This Matters for the IEP

A Payer submission and an FDA submission for the **same drug** require completely different dossiers:
- **Payer** cares about: *"Is this drug worth paying for vs the alternative?"*
- **FDA** cares about: *"Is this drug safe and proven in clinical trials?"*
- **HCP** cares about: *"Which patients should I prescribe this to?"*

Without this filter, a generic evidence package would fail to address the specific concerns of each audience.

