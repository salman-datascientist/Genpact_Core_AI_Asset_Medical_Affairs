"""Unit tests for agent core orchestration."""

from unittest.mock import MagicMock

import pytest

from agent_core import AgentState, MedicalAffairsAgent, ToolRegistry, build_plan


class TestAgentState:
    def test_add_step_truncates_observation(self):
        state = AgentState("task")
        state.add_step("thought", "tool", {"q": "x"}, "x" * 600)
        assert len(state.steps[0]["observation"]) == 500

    def test_summary_counts(self, sample_paper):
        state = AgentState("task")
        state.papers_found = [sample_paper]
        state.evidence_rows = [{"a": 1}]
        summary = state.summary()
        assert summary["papers_found"] == 1
        assert summary["evidence_rows"] == 1


class TestToolRegistry:
    def test_call_unknown_tool(self):
        reg = ToolRegistry()
        result = reg.call("missing_tool")
        assert "ERROR" in result
        assert "missing_tool" in result

    def test_call_registered_tool(self):
        reg = ToolRegistry()
        reg.register("echo", lambda msg, **kw: f"echo:{msg}", "echo tool")
        assert reg.call("echo", msg="hi") == "echo:hi"


class TestBuildPlan:
    def test_payer_plan_includes_pubmed_and_gap_steps(self):
        plan = build_plan(
            task="test",
            drug="Niraparib",
            indication="Ovarian Cancer",
            comparator="Olaparib",
            stakeholder="Payer (Aetna)",
            geography="United States",
        )
        tools = [step["tool"] for step in plan]
        assert tools[0] == "pubmed_search"
        assert "pubmed_search" in tools
        assert "gap_analysis" in tools
        assert "generate_report" in tools
        assert len(plan) == 9

    def test_plan_without_comparator_omits_competitor_search(self):
        plan = build_plan(
            task="test",
            drug="Niraparib",
            indication="Ovarian Cancer",
            comparator="",
            stakeholder="Payer",
        )
        labels = [
            step["input"].get("label")
            for step in plan
            if step["tool"] == "pubmed_search"
        ]
        assert "competitor_search" not in labels
        assert len(plan) == 8

    def test_regulator_plan_uses_rct_study_design(self):
        plan = build_plan(
            task="test",
            drug="Drug",
            indication="Cancer",
            stakeholder="Regulator (FDA)",
        )
        slr = next(s for s in plan if s["tool"] == "slr_screen")
        assert "randomized controlled trial" in slr["input"]["criteria"]["study_design"]


class TestMedicalAffairsAgent:
    def test_run_executes_mocked_tools(self, monkeypatch):
        reg = ToolRegistry()
        calls = []

        def _track(name):
            def _fn(**kwargs):
                calls.append(name)
                state = kwargs.get("_state")
                if name == "pubmed_search" and state is not None:
                    state.papers_found.append({
                        "pmid": "1",
                        "_fetched": False,
                        "_label": "RWE_search",
                    })
                if name == "pubmed_fetch" and state is not None:
                    for p in state.papers_found:
                        p["_fetched"] = True
                        p.setdefault("title", "test")
                        p.setdefault("abstract", "real world niraparib n=50 pfs 6 months")
                        p.setdefault("authors", ["A B"])
                return f"ok:{name}"
            return _fn

        for tool in [
            "pubmed_search", "pubmed_fetch", "save_to_db",
            "slr_screen", "extract_evidence", "gap_analysis",
            "hcp_score", "generate_report",
        ]:
            reg.register(tool, _track(tool), tool)

        monkeypatch.setattr("agent_core.time.sleep", lambda *_: None)

        agent = MedicalAffairsAgent(
            task="Integration mock run",
            registry=reg,
            drug="Niraparib",
            indication="Ovarian Cancer",
            comparator="",
            stakeholder="Payer",
        )
        final = agent.run()

        assert final.final_answer is not None
        assert "pubmed_search" in calls
        assert "generate_report" in calls
        assert len(final.steps) >= 8
