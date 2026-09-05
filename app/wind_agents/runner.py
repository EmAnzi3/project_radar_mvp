from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .adapters import (
    BasilicataWindAgent,
    CalabriaWindAgent,
    CampaniaWindAgent,
    LazioWindAgent,
    MaseWindAgent,
    SardegnaWindAgent,
    SiciliaWindAgent,
    SistemaPugliaWindAgent,
    ToscanaAtosWindAgent,
    ToscanaWindAgent,
)
from .planner import build_run_plan
from .state import begin_run, finish_run, upsert_finding


AGENT_FACTORIES = {
    "basilicata-via": BasilicataWindAgent,
    "calabria-via": CalabriaWindAgent,
    "campania-via": CampaniaWindAgent,
    "lazio-via": LazioWindAgent,
    "mase-via": MaseWindAgent,
    "sardegna-sira": SardegnaWindAgent,
    "sicilia-sivvi": SiciliaWindAgent,
    "sistema-puglia": SistemaPugliaWindAgent,
    "toscana-gea": ToscanaWindAgent,
    "toscana-atos": ToscanaAtosWindAgent,
}


def executable_agent_ids() -> list[str]:
    return sorted(AGENT_FACTORIES)


def run_agents(source_ids: Iterable[str] | None = None) -> dict[str, Any]:
    """Run implemented source adapters and persist raw/history state.

    The broader company/institutional/project queues are built by planner.py.
    Only source adapters explicitly present in AGENT_FACTORIES execute HTTP
    collection; unimplemented registry nodes remain visible as due work rather
    than silently pretending to be monitored.
    """

    plan = build_run_plan()
    requested = set(source_ids or executable_agent_ids())
    unknown = requested - set(AGENT_FACTORIES)
    if unknown:
        raise ValueError(f"unknown/unimplemented wind agent ids: {sorted(unknown)}")

    run_id = begin_run(
        planned_tasks=plan.total_tasks,
        note=f"executed adapters: {', '.join(sorted(requested))}",
    )

    findings_count = 0
    changed_count = 0
    per_agent: dict[str, dict[str, int]] = {}

    try:
        for source_id in sorted(requested):
            agent = AGENT_FACTORIES[source_id]()
            findings = agent.fetch()
            counters = {"findings": 0, "new": 0, "changed": 0, "unchanged": 0}

            for finding in findings:
                event = upsert_finding(run_id, agent.agent_name, finding)
                counters["findings"] += 1
                counters[event] += 1
                findings_count += 1
                if event in {"new", "changed"}:
                    changed_count += 1

            per_agent[source_id] = counters
    finally:
        finish_run(run_id, findings=findings_count, changed_items=changed_count)

    return {
        "run_id": run_id,
        "planned_tasks": plan.total_tasks,
        "executed_agents": sorted(requested),
        "findings": findings_count,
        "new_or_changed": changed_count,
        "per_agent": per_agent,
    }
