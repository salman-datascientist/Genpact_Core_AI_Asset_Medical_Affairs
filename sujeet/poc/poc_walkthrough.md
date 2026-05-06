# Medical Affairs AI POC —  Walkthrough

> **Purpose:** Explain the end-to-end flow of the POC from input to output, mapped to BRD pain points, in a way a  can present or review.

---

## The Problem We Are Solving (BRD Pain Points)

| # | Pain Point | Current State | Time Cost |
|---|-----------|--------------|-----------|
| 2 | Building Integrated Evidence Plans (IEP) | Manual literature search + Excel compilation | 13-week cycle |
| 3 | HCP / KOL Identification | Manual review of publication lists | Days of analyst time |
| 4 | Systematic Literature Reviews (SLR) | Manual abstract screening | ~130 hours per review |

**Our POC automates all three using an AI agent pipeline.**

---

## Step-by-Step Flow

### 🟦 STEP 1 —  / User Fills the Request Form (INPUT)

**Where:** Dashboard UI at `http://localhost:8000`

The user fills in:

| Field | Example Value | Why It Matters |
|-------|--------------|----------------|
| **Drug / Product** | Zejula (Niraparib) | Drives all PubMed search queries |
| **Indication** | Platinum-resistant Ovarian Cancer | Defines the patient population (PICO) |
| **Primary Stakeholder** | Regulator (FDA) | Determines what evidence gaps to look for |
| **Comparator Drug** | Olaparib | Used in head-to-head competitor search |
| **Geography** | United States | Scopes the evidence geographically |
| **Year Range** | 2019 – 2024 | Filters publications to recent evidence |
| **Request Type** | Integrated Evidence Plan | Sets the output format expectation |

> 💡 **Key point for :** The form is the "brief" — whatever the medical affairs team fills here drives the entire AI pipeline automatically. No manual configuration needed.

---

### 🟩 STEP 2 — AI Agent Searches PubMed (LITERATURE RETRIEVAL)

**What happens:** The AI agent makes two targeted PubMed searches:

**Search 1 — Real World Evidence for the drug:**
```
(niraparib) AND ("platinum-resistant ovarian cancer") 
AND ("real world" OR "observational" OR "claims") 
AND ("2019"[dp]:"2024"[dp])
```
→ Returns up to **50 paper IDs (PMIDs)**

**Search 2 — Competitor landscape:**
```
(olaparib) AND ("platinum-resistant ovarian cancer") 
AND ("real world" OR "efficacy" OR "outcomes") 
AND ("2019"[dp]:"2024"[dp])
```
→ Returns up to **30 paper IDs (PMIDs)**

> 💡 **Key point for :** This replaces a medical analyst spending **days manually searching** databases. The AI does it in **under 30 seconds**.

---

### 🟩 STEP 3 — AI Fetches Full Paper Details (METADATA EXTRACTION)

**What happens:** For each PMID found, the AI calls PubMed's API to retrieve full paper details in batches of 50.

**For each paper it extracts:**
- Title
- Authors (for KOL identification)
- Journal name & publication year
- Abstract (full text)
- MeSH terms (standardized medical keywords)
- DOI (link to full paper)
- Country of study
- Publication type (RCT, observational, review, etc.)

> 💡 **Key point for :** Without this, an analyst would manually open each paper and copy-paste this data into a spreadsheet.

---

### 🟨 STEP 4 — Papers Saved to Local Database

**What happens:** All fetched papers are stored in a **SQLite database** (`data/pubmed_papers.db`).

**Why this matters:**
- Creates a **persistent evidence repository**
- Future runs don't re-fetch already-known papers
- Can be queried anytime from the "Literature DB" tab in the dashboard

> 💡 **Key point for :** This is the foundation of an institutional evidence library — over time, it grows with every search run.

---

### 🟧 STEP 5 — AI Screens Papers (SLR AUTOMATION — BRD Pain Point 4)

**What happens:** Every paper abstract is screened by AI against **PICO criteria** (Population, Intervention, Comparator, Outcome).

**Screening criteria are set dynamically based on the form:**
| Stakeholder Selected | Study Design Looked For |
|---------------------|------------------------|
| Payer | Real-world, observational, cohort, claims |
| Regulator (FDA) | Phase III RCT, pivotal trials |
| NICE / HTA | Cost-effectiveness, HTA studies |
| KOL / Medical | Mechanistic, subgroup analyses |

**Each paper gets a verdict:**
- ✅ **INCLUDE** — relevant to the evidence package
- ❌ **EXCLUDE** — not relevant (with reason)

> 💡 **Key point for :** This is where **130 hours of manual SLR screening** is replaced. The AI screens abstracts in seconds, applying the same PICO logic a trained analyst would use.

---

### 🟧 STEP 6 — AI Extracts Structured Evidence (DATA EXTRACTION — BRD Pain Point 2)

**What happens:** For each INCLUDED paper, the AI pulls out structured data points:

| Field Extracted | Example |
|----------------|---------|
| Number of patients | n = 247 |
| PFS (Progression-Free Survival) | 8.2 months |
| OS (Overall Survival) | 24.5 months |
| Comparator drug used | vs. Olaparib |
| Study country | USA |
| Study design | Retrospective cohort |

This fills the **Evidence Table** tab in the dashboard.

> 💡 **Key point for :** This is the IEP evidence section that used to take **13 weeks** to compile manually. The AI produces a structured table in **minutes**.

---

### 🟥 STEP 7 — AI Identifies Evidence Gaps (GAP ANALYSIS — BRD Pain Point 2)

**What happens:** The AI compares what evidence was found against what the **stakeholder actually needs**.

**Example — if Stakeholder = "Regulator (FDA)":**

| Required Evidence | Found? | Gap? |
|------------------|--------|------|
| Phase III RCT data | ✅ Yes | No gap |
| Long-term safety (3+ years) | ❌ No | ⚠️ GAP |
| BRCA-mutated subgroup outcomes | ✅ Yes | No gap |
| Patient-reported outcomes (PROs) | ❌ No | ⚠️ GAP |
| Comparative efficacy vs Olaparib | ✅ Yes | No gap |

**Example — if Stakeholder = "Payer (Aetna)":**

| Required Evidence | Found? | Gap? |
|------------------|--------|------|
| Real-world PFS data in US | ✅ Yes | No gap |
| Cost-effectiveness vs Olaparib | ❌ No | ⚠️ GAP |
| Budget impact analysis | ❌ No | ⚠️ GAP |
| Treatment adherence data | ✅ Yes | No gap |

> 💡 **Key point for :** The system automatically tells the team **what is missing** so they know exactly what studies need to be commissioned or what gaps exist before a payer or regulatory submission.

---

### 🟪 STEP 8 — AI Scores KOLs / HCPs (KOL IDENTIFICATION — BRD Pain Point 3)

**What happens:** The AI ranks authors from the retrieved papers by:
- How many papers they authored
- How recently they published
- Their publication impact

**Output — Top KOL Scores:**

| Author | Papers Found | Score | Likely Role |
|--------|-------------|-------|-------------|
| Smith J | 7 papers | 0.92 | Lead KOL — Ovarian Cancer |
| Patel R | 4 papers | 0.74 | KOL — PARP inhibitors |
| Kumar A | 3 papers | 0.61 | Emerging KOL |

> 💡 **Key point for :** This replaces days of manually searching author lists. The team instantly knows **which oncologists** are most active in this space and should be engaged for advisory boards or MSL visits.

---

### 🏁 STEP 9 — Final Evidence Report Generated (OUTPUT)

**What happens:** A structured JSON report is saved to `outputs/evidence_report_YYYYMMDD_HHMMSS.json`

**The dashboard shows four output tabs:**

| Tab | What the  Sees |
|-----|-----------------------|
| **Evidence Table** | Structured data from included papers (PFS, OS, n, comparator) |
| **Gap Analysis** | List of missing evidence items with severity |
| **KOL Targets** | Ranked list of Key Opinion Leaders with scores |
| **Literature DB** | Full searchable database of all retrieved papers |

---

## End-to-End Summary for 

```
 FILLS FORM (2 minutes)
         ↓
AI searches PubMed → finds 80 papers (30 seconds)
         ↓
AI downloads full paper details (1-2 minutes)
         ↓
AI screens abstracts against PICO criteria (seconds)
         ↓
AI extracts efficacy data from included papers (seconds)
         ↓
AI compares evidence vs stakeholder needs → finds gaps (seconds)
         ↓
AI scores authors as potential KOLs (seconds)
         ↓
Dashboard shows: Evidence Table + Gaps + KOLs + Literature DB
         ↓
MEDICAL AFFAIRS TEAM REVIEWS OUTPUT (30 minutes)
```

**Total AI runtime: ~3–5 minutes**
**Vs. manual process: 13 weeks (IEP) + 130 hours (SLR)**

---

## How the Output Is Analyzed

### Evidence Table
- Review PFS / OS numbers — are they aligned with clinical trial data?
- Flag outliers (e.g. very small n, or very old studies)
- Use to build the clinical evidence narrative for the submission

### Gap Analysis
- Each gap = a **task for the team** (commission new study, seek unpublished data, or acknowledge limitation)
- Prioritize gaps marked CRITICAL (missing primary endpoint data)

### KOL Targets
- Top 5-10 names go into the **MSL engagement plan**
- Cross-reference with CRM to check if already engaged
- Use for advisory board invitations

### Literature DB Tab
- Full searchable list of all 80 papers retrieved
- Filter by year, journal, or publication type
- Click DOI to read full paper

---

> [!IMPORTANT]
> This is a **POC (Proof of Concept)**. The AI screening and extraction currently uses rule-based logic when no OpenAI key is set. With GPT-4o or Gemini Pro connected, the accuracy and depth of extraction will significantly improve.

> [!NOTE]
> All data stays **local** — PubMed papers are stored in `poc/data/pubmed_papers.db` on the server. No patient data or proprietary data is sent externally.
