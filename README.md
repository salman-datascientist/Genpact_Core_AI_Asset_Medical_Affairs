# Medical Affairs RWE Evidence Builder — POC

End-to-end prototype for the **Genpact Medical Affairs BRD (v0.1)**: an **Automated RWE Evidence Package Builder** with a **React + Vite + TypeScript + Tailwind** UI and a **FastAPI** API. All “AI” behavior is **deterministic and CSV-backed** (no API keys). Data lives under [`backend/data/`](backend/data/) (seed + runtime files).

## Prerequisites

- **Python 3.10+** with `pip` (e.g. `apt install python3-pip python3-venv` on Debian/Ubuntu, or use pyenv).
- **Node.js 18+** and `npm` for the frontend.

## Quick start

### Backend (port 8000)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or: `./run.sh` (after `chmod +x run.sh`).

### Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — Vite proxies `/api` to **http://127.0.0.1:8000**.

### Smoke test

```bash
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/kpis | head
```

## Demo flow

1. **Dashboard** — KPI cards load from `kpis.csv`.
2. **New IEP Request** — 4-step wizard (BR-IEP-01). Submit runs **`POST /api/requests/{id}/orchestrate`** (landscape → gaps → studies → IEP).
3. **Request detail** — Tabs: Landscape, Gap matrix, Study recs, IEP draft (MAPS-style sections), Co-pilot chat (BR-IEP-07), HITL review (BR-IEP-06).
4. **Submit for HITL** — From status `iep`, moves to `in_review`.
5. **Review queue** — Lists `in_review` requests; open detail → **Review** tab, switch role to **Medical Director**, approve or reject.

Reject returns the request to **`iep`** so analysts can refine via chat and resubmit.

## BRD requirement mapping

| BRD ID | Implementation |
|--------|----------------|
| BR-IEP-01 | Wizard + `POST /api/requests` (TPP, therapy, geography, lifecycle). |
| BR-IEP-02 | `run_landscape` → literature + HTA + RWE from CSV. |
| BR-IEP-03 | `run_gaps` → gap matrix vs TPP / stakeholders. |
| BR-IEP-04 | `run_studies` → ranked designs + data sources. |
| BR-IEP-05 | `run_iep` → MAPS-style sections + citations. |
| BR-IEP-06 | Submit for review + `/api/reviews/queue` + `/review`. |
| BR-IEP-07 | `/chat` + per-section **Regenerate** on IEP tab. |
| BR-NFR-01 / 04 | Citations + confidence scores on agent outputs. |
| KPI dashboard | `GET /api/kpis` ↔ Success Criteria section of BRD. |

## Key API routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/kpis` | KPI rows |
| GET | `/api/catalog/*` | Drugs, therapy areas, geographies, lifecycle, data sources, literature, HTA, RWE |
| POST | `/api/requests` | Create request (`draft`) |
| POST | `/api/requests/{id}/orchestrate` | Run all four agents |
| POST | `/api/requests/{id}/run/{landscape\|gaps\|studies\|iep}` | Single agent |
| POST | `/api/requests/{id}/submit-review` | `iep` → `in_review` |
| GET | `/api/reviews/queue` | HITL inbox |
| POST | `/api/requests/{id}/review` | Approve / reject / comment |
| POST | `/api/requests/{id}/chat` | Chat refinement |
| POST | `/api/requests/{id}/regenerate-section` | Regenerate one IEP section |

## Data layout

**Seed (static):** `drugs.csv`, `therapy_areas.csv`, `geographies.csv`, `lifecycle_stages.csv`, `data_sources.csv`, `literature.csv`, `hta_decisions.csv`, `rwe_studies.csv`, `evidence_gap_templates.csv`, `study_design_catalog.csv`, `kpis.csv`.

**Runtime (created automatically):** `iep_requests.csv`, `iep_sections.csv`, `reviews.csv`, `chat_messages.csv`.

## Out of scope (explicit)

Real Azure / LangGraph production orchestration, live PubMed/Embase/HTA APIs, Veeva Vault integration, HIPAA/GDPR enforcement, auth — stubs only; suitable for demos and UX validation.

## Project layout

```
medical-affairs-poc/
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── run.sh
│   ├── data/           # CSVs
│   └── app/
│       ├── main.py
│       ├── models/schemas.py
│       ├── services/{csv_store.py,mock_ai.py}
│       └── routers/{catalog,kpis,requests,review}.py
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
```

## Authors / BRD

Aligned with **Genpact Medical Affairs BRD v0.1** (March 2026). POC implementation for demonstration purposes only — not for clinical or regulatory decisions.
