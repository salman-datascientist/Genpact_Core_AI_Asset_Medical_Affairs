"""
Medical Affairs AI Agent  Core Engine
========================================
Implements an agentic loop:
  THINK   Agent reasons about what to do next
  ACT     Agent calls a registered tool
  OBSERVE  Agent reads the tool output
  REFLECT  Agent decides: done or next step?

This is the orchestration layer. Tools live in tools/*.py
"""

import os
import json
import time
from datetime import datetime
from typing import Callable
from dotenv import load_dotenv

load_dotenv()


def safe_print(*args, **kwargs):
    """Print safely on Windows consoles that don't support Unicode (charmap)."""
    safe_args = [
        str(a).encode('ascii', 'replace').decode('ascii') for a in args
    ]
    print(*safe_args, **kwargs)


#  AGENT STATE 

class AgentState:
    """Holds the running context / memory of the agent."""

    def __init__(self, task: str):
        self.task          = task
        self.steps         = []          # list of {step, thought, tool, input, output}
        self.final_answer  = None
        self.started_at    = datetime.utcnow().isoformat()
        self.papers_found  = []          # accumulates fetched papers
        self.evidence_rows = []          # accumulates extracted evidence
        self.gaps          = []          # accumulates gap analysis results
        self.hcp_scores    = []          # accumulates HCP priority scores

    def add_step(self, thought: str, tool: str, tool_input: dict, observation: str):
        step_num = len(self.steps) + 1
        self.steps.append({
            "step":        step_num,
            "thought":     thought,
            "tool":        tool,
            "tool_input":  tool_input,
            "observation": observation[:500],   # truncate for display
            "timestamp":   datetime.utcnow().isoformat(),
        })
        # ASCII-safe print to avoid charmap errors on Windows console
        print(f"\n" + "-"*60)
        print(f"[STEP {step_num}] THINK")
        print(f"  {thought[:200]}")
        print(f"[ACT]  Tool: [{tool}]")
        print(f"  Input: {json.dumps(tool_input)[:120]}".encode('ascii', 'replace').decode('ascii'))
        print(f"[OBSERVE]")
        print(f"  {observation[:300]}".encode('ascii', 'replace').decode('ascii'))

    def summary(self) -> dict:
        return {
            "task":          self.task,
            "steps_taken":   len(self.steps),
            "papers_found":  len(self.papers_found),
            "evidence_rows": len(self.evidence_rows),
            "gaps_found":    len(self.gaps),
            "hcp_scores":    len(self.hcp_scores),
            "final_answer":  self.final_answer,
            "started_at":    self.started_at,
            "completed_at":  datetime.utcnow().isoformat(),
        }


#  TOOL REGISTRY 

class ToolRegistry:
    """Register and call named tools."""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._descriptions: dict[str, str] = {}

    def register(self, name: str, fn: Callable, description: str):
        self._tools[name] = fn
        self._descriptions[name] = description

    def call(self, name: str, **kwargs):
        if name not in self._tools:
            return f"ERROR: Tool '{name}' not found. Available: {list(self._tools.keys())}"
        try:
            return self._tools[name](**kwargs)
        except Exception as e:
            return f"ERROR in tool '{name}': {e}"

    def list_tools(self) -> str:
        return "\n".join(
            f"   {name}: {desc}"
            for name, desc in self._descriptions.items()
        )


#  AGENT PLAN 
# Agentic plan driven by UI form fields (drug, indication, comparator,
# stakeholder, geography, year_from, year_to).

def build_plan(
    task:        str,
    drug:        str = "niraparib",
    indication:  str = "ovarian cancer",
    comparator:  str = "olaparib",
    stakeholder: str = "Payer",
    geography:   str = "United States",
    year_from:   str = "2019",
    year_to:     str = "2024",
) -> list[dict]:
    """
    Returns a step-by-step plan the agent will execute.
    All parameters come from the UI form — nothing is hardcoded.
    Each step = { thought, tool, input }
    """
    drug_lower        = drug.lower()
    indication_lower  = indication.lower()
    comparator_lower  = comparator.lower() if comparator else ""
    has_comparator    = bool(comparator and comparator.strip())
    date_range        = f'("{year_from}"[dp]:"{year_to}"[dp])'

    # ── Stakeholder-specific gap sections ────────────────────────────────────
    stakeholder_lower = stakeholder.lower()
    if "payer" in stakeholder_lower:
        required_sections = [
            f"Real-world PFS data for {drug} in {geography}",
            f"Cost-effectiveness vs {comparator}",
            "Budget impact analysis",
            "Treatment adherence & persistence data",
            "Elderly patient subgroup (65+) outcomes",
        ]
        slr_study_design = "real world, observational, cohort, claims, or registry study"
    elif "regulator" in stakeholder_lower or "fda" in stakeholder_lower or "ema" in stakeholder_lower:
        required_sections = [
            f"Phase III RCT evidence for {drug}",
            "Long-term safety profile (3+ years)",
            "Biomarker subgroup outcomes (BRCA-mutated)",
            f"Comparative efficacy vs {comparator}",
            "Patient-reported outcomes (PROs)",
        ]
        slr_study_design = "randomized controlled trial, phase III, or pivotal study"
    elif "nice" in stakeholder_lower or "hta" in stakeholder_lower:
        required_sections = [
            "QALY and cost-per-QALY data",
            "Incremental cost-effectiveness ratio (ICER)",
            "Indirect treatment comparison (ITC) vs standard of care",
            "Budget impact model inputs",
            "Patient-reported quality of life data",
        ]
        slr_study_design = "health technology assessment, economic evaluation, or cost-effectiveness study"
    elif "kol" in stakeholder_lower or "medical" in stakeholder_lower:
        required_sections = [
            f"Mechanism of action publications for {drug}",
            "Subgroup analyses in high-risk populations",
            "Combination therapy data",
            "Biomarker-driven patient selection evidence",
            "Conference abstracts and emerging data",
        ]
        slr_study_design = "clinical trial, mechanistic study, or subgroup analysis"
    else:
        required_sections = [
            f"Real-world outcomes for {drug} in {geography}",
            f"Comparative data vs {comparator}",
            "Safety and tolerability profile",
            "Patient subgroup analyses",
        ]
        slr_study_design = "real world, observational, or randomized controlled trial"

    return [
        # PAIN POINT 4: SLR - Fetch RWE literature
        {
            "thought": (
                f"The user wants evidence on {drug} for {indication} "
                f"targeting {stakeholder} in {geography}. "
                "Searching PubMed for real-world evidence papers "
                "(BRD Pain Point 4 - SLR bottleneck)."
            ),
            "tool": "pubmed_search",
            "input": {
                "query": (
                    f'({drug_lower}) AND ("{indication_lower}") AND '
                    f'("real world" OR "observational" OR "claims" OR "registry") '
                    f'AND {date_range}'
                ),
                "max_results": 50,
                "label": "RWE_search",
            }
        },
        # PAIN POINT 2: Competitor landscape (only if comparator is selected)
        *(
            [{
                "thought": (
                    f"Now fetching competitor landscape: {comparator} vs {drug}. "
                    "This feeds into the IEP Competitor section (BRD Pain Point 2)."
                ),
                "tool": "pubmed_search",
                "input": {
                    "query": (
                        f'({comparator_lower}) AND ("{indication_lower}") AND '
                        f'("real world" OR "efficacy" OR "outcomes") AND {date_range}'
                    ),
                    "max_results": 30,
                    "label": "competitor_search",
                }
            }] if has_comparator else []
        ),
        # Fetch full metadata for all queued PMIDs
        {
            "thought": (
                "I have PMIDs from both searches. Now fetching full metadata "
                "(title, abstract, authors, MeSH terms, DOI) for all papers."
            ),
            "tool": "pubmed_fetch",
            "input": {"source": "state"}
        },
        # Save to local DB
        {
            "thought": (
                "Papers are fetched. Storing in SQLite for a persistent "
                "local evidence repository."
            ),
            "tool": "save_to_db",
            "input": {"source": "state"}
        },
        # PAIN POINT 4: AI SLR screening
        {
            "thought": (
                f"Running AI screening on abstracts using PICO criteria: "
                f"Population={indication}, Intervention={drug}, "
                f"Study design={slr_study_design}. "
                "Replaces 130+ hours of manual analyst work (BRD Pain Point 4)."
            ),
            "tool": "slr_screen",
            "input": {
                "criteria": {
                    "population":   f"{indication} patients",
                    "intervention": drug,
                    "outcome":      "progression-free survival, overall survival, or response rate",
                    "study_design": slr_study_design,
                }
            }
        },
        # PAIN POINT 2: Evidence extraction
        {
            "thought": (
                "Extracting structured data from included papers: n_patients, "
                "PFS months, OS months, comparator drug. "
                "Fills IEP Evidence section (BRD Pain Point 2)."
            ),
            "tool": "extract_evidence",
            "input": {"source": "screened_papers"}
        },
        # PAIN POINT 2: Gap analysis tailored to stakeholder
        {
            "thought": (
                f"Analyzing evidence gaps vs what {stakeholder} requires. "
                f"Geography focus: {geography}. "
                "Identifies missing comparisons and subgroups (BRD Pain Point 2)."
            ),
            "tool": "gap_analysis",
            "input": {
                "required_sections": required_sections
            }
        },
        # PAIN POINT 3: HCP/KOL scoring
        {
            "thought": (
                f"Generating HCP priority scores from authorship patterns. "
                f"Authors publishing on {drug} in {indication} are likely KOLs "
                "who influence prescribing (BRD Pain Point 3)."
            ),
            "tool": "hcp_score",
            "input": {"top_n": 20}
        },
        # Final report
        {
            "thought": (
                "All data collected, screened, extracted, and analysed. "
                "Generating final structured Evidence Summary report."
            ),
            "tool": "generate_report",
            "input": {"format": "json"}
        },
    ]


#  AGENT RUNNER 

class MedicalAffairsAgent:
    """
    The main agent. Executes the agentic plan step by step.
    Each step: Think -> Act (tool call) -> Observe -> next step.
    """

    def __init__(
        self,
        task:        str,
        registry:    ToolRegistry,
        drug:        str = "niraparib",
        indication:  str = "ovarian cancer",
        comparator:  str = "olaparib",
        stakeholder: str = "Payer",
        geography:   str = "United States",
        year_from:   str = "2019",
        year_to:     str = "2024",
    ):
        self.state       = AgentState(task)
        self.registry    = registry
        self.drug        = drug
        self.indication  = indication
        self.comparator  = comparator
        self.stakeholder = stakeholder
        self.geography   = geography
        self.year_from   = year_from
        self.year_to     = year_to

    def run(self) -> AgentState:
        safe_print("\n" + "="*60)
        safe_print("[AGENT] MEDICAL AFFAIRS AI AGENT STARTED")
        safe_print(f"  Task:        {self.state.task}")
        safe_print(f"  Drug:        {self.drug}")
        safe_print(f"  Indication:  {self.indication}")
        safe_print(f"  Comparator:  {self.comparator}")
        safe_print(f"  Stakeholder: {self.stakeholder}")
        safe_print(f"  Geography:   {self.geography}")
        safe_print(f"  Years:       {self.year_from} - {self.year_to}")
        safe_print(f"  Time:        {self.state.started_at}")
        safe_print("\n  Available Tools:")
        safe_print(self.registry.list_tools())
        safe_print("="*60)

        plan = build_plan(
            task        = self.state.task,
            drug        = self.drug,
            indication  = self.indication,
            comparator  = self.comparator,
            stakeholder = self.stakeholder,
            geography   = self.geography,
            year_from   = self.year_from,
            year_to     = self.year_to,
        )

        for step_def in plan:
            thought    = step_def["thought"]
            tool_name  = step_def["tool"]
            tool_input = step_def["input"]

            # Pass agent state to tools that need it
            tool_input["_state"] = self.state

            #  ACT 
            observation = self.registry.call(tool_name, **tool_input)

            #  LOG 
            self.state.add_step(thought, tool_name, 
                                {k: v for k, v in tool_input.items() if k != "_state"},
                                str(observation))

            # Small delay between steps (be kind to APIs)
            time.sleep(0.5)

        #  REFLECT: compose final answer 
        self.state.final_answer = (
            f"Agent completed {len(plan)} steps. "
            f"Found {len(self.state.papers_found)} papers, "
            f"screened to {len(self.state.evidence_rows)} included studies, "
            f"identified {len(self.state.gaps)} evidence gaps, "
            f"scored {len(self.state.hcp_scores)} potential KOLs."
        )

        safe_print("\n" + "="*60)
        safe_print("[AGENT] COMPLETE")
        safe_print(f"  {self.state.final_answer}")
        safe_print("="*60 + "\n")

        return self.state
