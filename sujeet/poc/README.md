# Medical Affairs AI — POC

**Agentic AI system for Pharmaceutical Medical Affairs Evidence Generation**

---

## Project Structure

```
poc/
├── backend/
│   ├── api_server.py          ← FastAPI REST API (run this first)
│   ├── agent_core.py          ← Agentic loop: Think→Act→Observe→Reflect
│   ├── run_agent.py           ← CLI runner (standalone, no UI)
│   ├── .env                   ← API keys (PUBMED_API_KEY, OPENAI_API_KEY)
│   └── tools/
│       ├── pubmed_tools.py    ← PubMed search, fetch, save tools
│       └── analysis_tools.py  ← SLR screen, extract, gap, KOL, report tools
├── frontend/
│   ├── index.html             ← POC Dashboard (5 screens)
│   ├── style.css              ← Styling
│   └── app.js                 ← Frontend logic & API calls
├── data/
│   └── pubmed_papers.db       ← SQLite: all fetched PubMed papers
├── outputs/
│   └── evidence_report_*.json ← Agent run results
└── requirements.txt           ← All Python dependencies
```

---

## Quick Start

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Set API key
Edit `backend/.env`:
```
PUBMED_API_KEY=your_ncbi_api_key_here
OPENAI_API_KEY=your_openai_key_here   # optional — uses rule-based fallback if not set
```

### Step 3 — Start the API server
```bash
cd poc/backend
python api_server.py
```
Server starts at: **http://localhost:8000**

### Step 4 — Open the UI
Open `poc/frontend/index.html` in your browser  
*(or visit http://localhost:8000 once server is running)*

---

## What the Agent Does (9 Steps)

| Step | Tool | BRD Pain Point |
|------|------|----------------|
| 1 | PubMed Search (RWE papers) | Pain Point 4 — SLR |
| 2 | PubMed Search (competitors) | Pain Point 2 — IEP |
| 3 | Fetch full paper metadata | Pain Point 1 — Data retrieval |
| 4 | Save to SQLite database | Pain Point 5 — Fragmentation |
| 5 | AI SLR Screening (PICO) | Pain Point 4 — 130hr → 2min |
| 6 | Evidence data extraction | Pain Point 2 — IEP evidence table |
| 7 | Gap analysis | Pain Point 2 — Evidence Gap Analysis |
| 8 | KOL / HCP scoring | Pain Point 3 — HCP targeting |
| 9 | Generate JSON report | Pain Point 2 — IEP draft |

---

## UI Screens

| Screen | What it Shows |
|--------|--------------|
| New Request | Input form: drug, indication, stakeholder, geography |
| Agent Progress | Live step-by-step agent log with progress bar |
| Evidence Table | AI-extracted structured data (N, PFS, OS, design) |
| Gap Analysis | What evidence exists vs what payers need |
| KOL Targets | Ranked Key Opinion Leaders from publication data |
| Literature DB | All PubMed papers in local database |

---

## CLI Usage (without UI)
```bash
cd poc/backend
python run_agent.py
python run_agent.py --task "Evidence for Olaparib in Breast Cancer"
```

---

*Built with: PubMed E-utilities API · FastAPI · SQLite · Vanilla JS*
