"""
api_server.py — FastAPI Backend for Medical Affairs AI POC UI
=============================================================
Endpoints:
  POST /api/run-agent       → Run the full agent pipeline
  GET  /api/results/latest  → Return latest evidence report
  GET  /api/papers          → Return papers from SQLite DB
  GET  /api/health          → Health check
"""

import os
import sys
import json
import sqlite3
import threading
import traceback
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Fix Windows charmap encoding errors when printing Unicode from paper abstracts
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add backend folder to Python path so imports work
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

# Load .env from backend directory explicitly
from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

IS_VERCEL = bool(os.getenv("VERCEL"))

app = FastAPI(title="Medical Affairs AI — POC API", version="1.0.0")

# Allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR     = BACKEND_DIR
if IS_VERCEL:
    # Serverless filesystem is read-only except /tmp (ephemeral per invocation).
    _RUNTIME_ROOT = os.path.join("/tmp", "medaffairs_poc")
    DATA_DIR   = os.path.join(_RUNTIME_ROOT, "data")
    OUTPUT_DIR = os.path.join(_RUNTIME_ROOT, "outputs")
else:
    DATA_DIR     = os.path.abspath(os.path.join(BASE_DIR, "..", "data"))
    OUTPUT_DIR   = os.path.abspath(os.path.join(BASE_DIR, "..", "outputs"))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
DB_PATH      = os.path.join(DATA_DIR, "pubmed_papers.db")

# Make sure output dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ── In-memory agent status (for live progress polling) ───────────────────────
agent_status = {
    "running":    False,
    "steps":      [],
    "progress":   0,
    "task":       "",
    "started_at": None,
    "done":       False,
    "error":      None,
    "result":     None,
}

# ── Request Model ─────────────────────────────────────────────────────────────
class AgentRequest(BaseModel):
    drug:        str = "Niraparib"
    indication:  str = "Ovarian Cancer"
    geography:   str = "United States"
    stakeholder: str = "Payer (Aetna)"
    comparator:  str = "Olaparib"
    year_from:   str = "2019"
    year_to:     str = "2024"
    request_type:str = "Integrated Evidence Plan"
    pubmed_tier: str = "no_api_key"
    pubmed_requests_per_second: float = Field(default=3.0, gt=0, le=10)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "platform": "vercel" if IS_VERCEL else "local",
    }


@app.get("/api/pubmed-config")
def pubmed_config():
    """Return NCBI rate-limit disclosure and whether a PubMed API key is configured."""
    from tools.pubmed_rate_limiter import (
        NCBI_DISCLOSURE,
        NCBI_MAX_RPS_NO_KEY,
        NCBI_MAX_RPS_WITH_KEY,
    )

    api_key = os.getenv("PUBMED_API_KEY", "").strip()
    has_api_key = bool(api_key)
    default_tier = "with_api_key" if has_api_key else "no_api_key"
    default_rps = (
        NCBI_MAX_RPS_WITH_KEY if has_api_key else NCBI_MAX_RPS_NO_KEY
    )

    return {
        "has_api_key": has_api_key,
        "max_without_key": NCBI_MAX_RPS_NO_KEY,
        "max_with_key": NCBI_MAX_RPS_WITH_KEY,
        "default_tier": default_tier,
        "default_requests_per_second": default_rps,
        "disclosure": NCBI_DISCLOSURE,
    }


# ── Run agent in background thread ───────────────────────────────────────────
def _run_agent_thread(req: AgentRequest):
    global agent_status
    try:
        # Re-load .env inside thread (threads don't inherit module-level env)
        load_dotenv(os.path.join(BACKEND_DIR, ".env"))

        # Override DB and output paths in tools so they use poc/data/ and poc/outputs/
        import tools.pubmed_tools as pt
        import tools.analysis_tools as at
        from tools.pubmed_rate_limiter import configure_rate_limit
        pt.DB_PATH = DB_PATH
        at.OUTPUT_DIR = OUTPUT_DIR  # analysis_tools saves report here

        effective_rps = configure_rate_limit(
            tier=req.pubmed_tier,
            requests_per_second=req.pubmed_requests_per_second,
            has_api_key=bool(os.getenv("PUBMED_API_KEY", "").strip()),
        )
        agent_status["pubmed_rate"] = {
            "tier": req.pubmed_tier,
            "requests_per_second": effective_rps,
        }

        from agent_core import MedicalAffairsAgent, ToolRegistry
        from tools.pubmed_tools import pubmed_search, pubmed_fetch, save_to_db
        from tools.analysis_tools import (
            slr_screen, extract_evidence, gap_analysis, hcp_score, generate_report
        )

        reg = ToolRegistry()
        reg.register("pubmed_search",   pubmed_search,   "Search PubMed")
        reg.register("pubmed_fetch",    pubmed_fetch,    "Fetch paper metadata")
        reg.register("save_to_db",      save_to_db,      "Save to SQLite")
        reg.register("slr_screen",      slr_screen,      "AI SLR screening")
        reg.register("extract_evidence",extract_evidence, "Extract evidence data")
        reg.register("gap_analysis",    gap_analysis,    "Gap analysis")
        reg.register("hcp_score",       hcp_score,       "Score KOLs")
        reg.register("generate_report", generate_report, "Generate report")

        task = (
            f"Gather real-world evidence for {req.drug} in {req.indication} "
            f"for {req.stakeholder} submission in {req.geography}"
        )
        agent = MedicalAffairsAgent(
            task        = task,
            registry    = reg,
            drug        = req.drug,
            indication  = req.indication,
            comparator  = req.comparator,
            stakeholder = req.stakeholder,
            geography   = req.geography,
            year_from   = req.year_from,
            year_to     = req.year_to,
        )

        # Monkey-patch to capture live step updates
        original_add_step = agent.state.add_step
        total_steps = 9

        def _patched_add_step(thought, tool, tool_input, observation):
            original_add_step(thought, tool, tool_input, observation)
            step_num = len(agent.state.steps)
            agent_status["steps"] = agent.state.steps.copy()
            agent_status["progress"] = int((step_num / total_steps) * 100)

        agent.state.add_step = _patched_add_step

        final_state = agent.run()

        # Save result
        result = {
            "summary":        final_state.summary(),
            "evidence_table": final_state.evidence_rows,
            "gaps":           final_state.gaps,
            "kols":           final_state.hcp_scores,
            "steps":          final_state.steps,
        }

        out_path = os.path.join(
            OUTPUT_DIR,
            f"evidence_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)

        agent_status["result"]   = result
        agent_status["done"]     = True
        agent_status["running"]  = False
        agent_status["progress"] = 100

    except Exception as e:
        full_error = traceback.format_exc()
        print("[AGENT ERROR]\n" + full_error)   # also print to server console
        agent_status["error"]   = f"{e}\n\nFull traceback:\n{full_error}"
        agent_status["running"] = False
        agent_status["done"]    = True


@app.post("/api/run-agent")
def run_agent(req: AgentRequest):
    global agent_status
    if agent_status["running"]:
        return JSONResponse({"error": "Agent already running"}, status_code=409)

    from tools.pubmed_rate_limiter import configure_rate_limit

    try:
        configure_rate_limit(
            tier=req.pubmed_tier,
            requests_per_second=req.pubmed_requests_per_second,
            has_api_key=bool(os.getenv("PUBMED_API_KEY", "").strip()),
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    agent_status = {
        "running":    True,
        "steps":      [],
        "progress":   0,
        "task":       f"{req.drug} — {req.indication} — {req.geography}",
        "started_at": datetime.utcnow().isoformat(),
        "done":       False,
        "error":      None,
        "result":     None,
        "pubmed_rate": {
            "tier": req.pubmed_tier,
            "requests_per_second": req.pubmed_requests_per_second,
        },
    }

    # Vercel serverless: run synchronously (threads + in-memory state do not
    # survive across separate function invocations).
    if IS_VERCEL:
        _run_agent_thread(req)
        if agent_status.get("error"):
            return JSONResponse(
                {"error": agent_status["error"], "sync": True, "task": agent_status["task"]},
                status_code=500,
            )
        return {
            "message":  "Agent completed",
            "sync":     True,
            "task":     agent_status["task"],
            "done":     True,
            "progress": agent_status["progress"],
            "steps":    agent_status["steps"],
            "result":   agent_status["result"],
            "pubmed_rate": agent_status.get("pubmed_rate"),
        }

    thread = threading.Thread(target=_run_agent_thread, args=(req,), daemon=True)
    thread.start()

    return {"message": "Agent started", "task": agent_status["task"]}


@app.get("/api/agent-status")
def get_agent_status():
    return {
        "running":   agent_status["running"],
        "progress":  agent_status["progress"],
        "task":      agent_status["task"],
        "steps":     agent_status["steps"],
        "done":      agent_status["done"],
        "error":     agent_status["error"],
        "started_at":agent_status["started_at"],
        "pubmed_rate": agent_status.get("pubmed_rate"),
    }


@app.get("/api/results/latest")
def get_latest_results():
    # Try live agent result first
    if agent_status.get("result"):
        return agent_status["result"]

    # Fall back to last saved JSON file
    try:
        files = sorted(
            [f for f in os.listdir(OUTPUT_DIR) if f.startswith("evidence_report")],
            reverse=True
        )
        if files:
            with open(os.path.join(OUTPUT_DIR, files[0]), encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    return {"error": "No results available yet. Run the agent first."}


@app.get("/api/papers")
def get_papers(limit: int = 50, offset: int = 0):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT pmid, title, authors, journal, pub_year, doi, country, "
            "pub_types, mesh_terms, abstract FROM papers "
            "ORDER BY pub_year DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        conn.close()

        papers = []
        for r in rows:
            papers.append({
                "pmid":       r["pmid"],
                "title":      r["title"],
                "authors":    json.loads(r["authors"] or "[]"),
                "journal":    r["journal"],
                "pub_year":   r["pub_year"],
                "doi":        r["doi"],
                "country":    r["country"],
                "pub_types":  json.loads(r["pub_types"] or "[]"),
                "mesh_terms": json.loads(r["mesh_terms"] or "[]"),
                "abstract":   (r["abstract"] or "")[:400],
            })
        return {"total": total, "papers": papers}
    except Exception as e:
        return {"error": str(e), "papers": []}


# ── Serve frontend static files ───────────────────────────────────────────────
# On Vercel, all routes are rewritten to this FastAPI app (see vercel.json).
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    import socket

    def find_free_port(preferred=8000):
        for port in range(preferred, preferred + 20):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", port))
                    return port
                except OSError:
                    continue
        return preferred  # fallback, will show original error

    port = find_free_port(8000)
    print("\n" + "="*55)
    print("  Medical Affairs AI -- POC Server")
    print(f"  Open: http://localhost:{port}")
    if port != 8000:
        print(f"  (Port 8000 was busy, using {port})")
    print("="*55 + "\n")
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=False)
