#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.wind_agents.base import AgentFinding
from app.wind_agents.evidence import can_close_execution_scope, evidence_layer
from app.wind_agents.planner import (
    _merge_company_registries,
    _merge_institutional_registries,
    build_run_plan,
)
from app.wind_agents.runner import executable_agent_ids
from app.wind_agents import state


company_base, companies = _merge_company_registries()
institutional_base, sources = _merge_institutional_registries()
assert len(companies) >= 50, len(companies)
assert len(sources) >= 31, len(sources)
assert company_base["monitoring"]["high_priority_cadence_days"] == 7
assert institutional_base["monitoring"]["priority_regional_cadence_days"] == 3

plan = build_run_plan(as_of=date(2026, 9, 5))
project_ids = {task.task_id for task in plan.projects}
for required in ["andretta-bisaccia", "alia-sclafani", "serra-giannina"]:
    assert required in project_ids, f"priority project missing from wind-agent plan: {required}"
assert plan.institutional, "institutional due queue empty"
assert plan.companies, "company due queue empty"
assert "mase-via" in executable_agent_ids()

# Evidence discipline: generic capability / weak signals never close scope.
assert not can_close_execution_scope(
    confidence="B",
    project_specific=True,
    execution_scope="civil_bop",
    status="confirmed",
)
assert not can_close_execution_scope(
    confidence="A1",
    project_specific=False,
    execution_scope="civil_bop",
    status="confirmed",
)
assert not can_close_execution_scope(
    confidence="A1",
    project_specific=True,
    execution_scope=None,
    status="confirmed",
)
assert can_close_execution_scope(
    confidence="A1",
    project_specific=True,
    execution_scope="civil_bop",
    status="confirmed",
)
assert evidence_layer(project_specific=False, execution_scope=None) == "network_intelligence"

# PV-Agent-style raw/history persistence must detect new / unchanged / changed.
with tempfile.TemporaryDirectory() as tmp:
    state.DB_PATH = Path(tmp) / "wind_agent_test.sqlite"
    run_id = state.begin_run(plan.total_tasks, note="validator")
    finding = AgentFinding(
        external_id="test-1",
        source_name="validator",
        source_url="https://example.com/wind/1",
        title="Wind test",
        finding_type="project_source",
        payload={"mw": 10, "project_specific": True},
    )
    assert state.upsert_finding(run_id, "test_agent", finding) == "new"
    assert state.upsert_finding(run_id, "test_agent", finding) == "unchanged"
    changed = AgentFinding(
        external_id="test-1",
        source_name="validator",
        source_url="https://example.com/wind/1",
        title="Wind test",
        finding_type="project_source",
        payload={"mw": 12, "project_specific": True},
    )
    assert state.upsert_finding(run_id, "test_agent", changed) == "changed"
    state.finish_run(run_id, findings=3, changed_items=2)

print(
    f"v0.6 wind agents OK: {len(companies)} companies, {len(sources)} institutional nodes, "
    f"{len(plan.projects)} execution-watch projects, adapters={','.join(executable_agent_ids())}"
)
