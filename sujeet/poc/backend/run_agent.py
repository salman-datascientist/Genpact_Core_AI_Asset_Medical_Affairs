"""
run_agent.py  Entry Point
===========================
Wires together the agent core + all tools and launches the
Medical Affairs AI Agentic pipeline.

Usage:
    python run_agent.py
    python run_agent.py --task "Evidence for Olaparib in breast cancer"
    python run_agent.py --task "Niraparib real world evidence" --max 100

Requirements:
    pip install requests xmltodict python-dotenv openai
"""

import sys
import json
import argparse
from agent_core import MedicalAffairsAgent, ToolRegistry

# Import all tools
from tools.pubmed_tools import pubmed_search, pubmed_fetch, save_to_db
from tools.analysis_tools import (
    slr_screen, extract_evidence, gap_analysis, hcp_score, generate_report
)


def build_registry() -> ToolRegistry:
    """Register all available tools with descriptions."""
    reg = ToolRegistry()

    reg.register(
        "pubmed_search",
        pubmed_search,
        "Search PubMed for papers matching a clinical query. Returns PMIDs."
    )
    reg.register(
        "pubmed_fetch",
        pubmed_fetch,
        "Fetch full metadata (title, abstract, authors, MeSH) for queued PMIDs."
    )
    reg.register(
        "save_to_db",
        save_to_db,
        "Persist all fetched papers to local SQLite database."
    )
    reg.register(
        "slr_screen",
        slr_screen,
        "AI-powered PICO screening  include/exclude papers for SLR (Pain Point 4)."
    )
    reg.register(
        "extract_evidence",
        extract_evidence,
        "Extract structured data (n, PFS, OS, drug, comparator) from included papers."
    )
    reg.register(
        "gap_analysis",
        gap_analysis,
        "Identify evidence gaps vs payer requirements for IEP (Pain Point 2)."
    )
    reg.register(
        "hcp_score",
        hcp_score,
        "Score KOL authors by publication influence for HCP targeting (Pain Point 3)."
    )
    reg.register(
        "generate_report",
        generate_report,
        "Generate final structured Evidence Summary report (JSON)."
    )

    return reg


def print_final_summary(state):
    """Pretty-print the agent's final output."""
    summary = state.summary()

    print("\n" + "="*60)
    print("[SUMMARY] FINAL AGENT SUMMARY")
    print("="*60)
    print(f"  Task:            {summary['task']}")
    print(f"  Steps taken:     {summary['steps_taken']}")
    print(f"  Papers found:    {summary['papers_found']}")
    print(f"  Evidence rows:   {summary['evidence_rows']}")
    print(f"  Evidence gaps:   {summary['gaps_found']}")
    print(f"  KOLs scored:     {summary['hcp_scores']}")
    print(f"  Completed at:    {summary['completed_at']}")
    print(f"\n  Result: {summary['final_answer']}")

    # Print evidence table
    if state.evidence_rows:
        print("\n" + "-"*60)
        print("[TABLE] EVIDENCE EXTRACTION TABLE (top 5)")
        print(""*60)
        for row in state.evidence_rows[:5]:
            print(
                f"  [{row['year']}] {row['title'][:65]}\n"
                f"    Drug: {row['drug']} | N={row['n_patients']} | "
                f"PFS={row['pfs_months']}mo | OS={row['os_months']}mo | "
                f"Design: {row['study_design']}\n"
            )

    # Print gap analysis
    if state.gaps:
        print("-"*60)
        print("[GAP] EVIDENCE GAP ANALYSIS")
        print("-"*60)
        for g in state.gaps:
            icon = "[OK] " if g["status"] == "COVERED" else "[GAP]"
            print(f"  {icon} {g['required_section']}: {g['status']}")
            if g["status"] == "GAP":
                print(f"      {g['recommendation'][:100]}")

    # Print top KOLs
    if state.hcp_scores:
        print("\n" + "-"*60)
        print("[KOL] TOP KOLs (Key Opinion Leaders)")
        print("-"*60)
        for kol in state.hcp_scores[:5]:
            print(
                f"  #{kol['rank']} {kol['name']} | "
                f"Score={kol['kol_score']} | "
                f"Priority={kol['priority']} | "
                f"Papers={kol['papers_found']}"
            )

    print("\n" + "="*60)
    print("[DONE] POC COMPLETE -- Evidence report saved as JSON")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Medical Affairs AI Agent  PubMed Evidence Pipeline"
    )
    parser.add_argument(
        "--task",
        default="Gather real-world evidence for Niraparib in Ovarian Cancer for IEP submission",
        help="The high-level task for the agent"
    )
    args = parser.parse_args()

    print("\n[START] Initialising Medical Affairs AI Agent...")
    registry = build_registry()
    agent    = MedicalAffairsAgent(task=args.task, registry=registry)

    # Run the agentic pipeline
    final_state = agent.run()

    # Print human-readable summary
    print_final_summary(final_state)

    # Also dump the full agent trace for auditability
    trace_path = "agent_trace.json"
    try:
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "summary": final_state.summary(),
                    "steps":   final_state.steps,
                    "gaps":    final_state.gaps,
                    "evidence_table": final_state.evidence_rows,
                    "kols":    final_state.hcp_scores,
                },
                f, indent=2, default=str
            )
        print(f"[TRACE] Full agent trace saved -> {trace_path}")
    except Exception as e:
        print(f"Could not save trace: {e}")


if __name__ == "__main__":
    main()
