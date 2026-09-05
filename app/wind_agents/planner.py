from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .models import AgentRunPlan, AgentTask

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "wind" / "data"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _is_due(last_checked: Any, cadence_days: int, as_of: date) -> bool:
    checked = _parse_date(last_checked)
    if checked is None:
        return True
    return (as_of - checked).days >= cadence_days


def _priority_rank(value: str | None) -> int:
    return {"A+": 0, "A": 1, "B": 2, "C": 3}.get(value or "C", 9)


def _merge_company_registries() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base = _load_json(DATA / "company-network-v06.json")
    paths = [
        DATA / "company-network-v06b.json",
        DATA / "company-network-v06c.json",
        DATA / "company-network-v06d.json",
    ]
    companies = list(base.get("companies", []))
    seen = {row["id"] for row in companies}

    for path in paths:
        if not path.exists():
            continue
        extra = _load_json(path)
        for row in extra.get("companies", []):
            if row["id"] in seen:
                raise ValueError(f"duplicate company id across registries: {row['id']}")
            seen.add(row["id"])
            companies.append(row)

    return base, companies


def _merge_institutional_registries() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base = _load_json(DATA / "institutional-source-network-v06.json")
    sources = list(base.get("sources", []))
    seen = {row["id"] for row in sources}

    for path in [DATA / "institutional-source-network-v06b.json"]:
        if not path.exists():
            continue
        extra = _load_json(path)
        for row in extra.get("sources", []):
            if row["id"] in seen:
                raise ValueError(f"duplicate institutional source id: {row['id']}")
            seen.add(row["id"])
            sources.append(row)

    return base, sources


def _load_projects() -> list[dict[str, Any]]:
    manifest = _load_json(DATA / "projects.json")
    projects: list[dict[str, Any]] = []
    for chunk in manifest.get("chunks", []):
        projects.extend(_load_json(DATA / chunk))
    return projects


def _company_tasks(as_of: date, include_not_due: bool = False) -> list[AgentTask]:
    base, companies = _merge_company_registries()
    monitoring = base.get("monitoring", {})
    high = int(monitoring.get("high_priority_cadence_days", 7))
    standard = int(monitoring.get("standard_cadence_days", 14))
    universe = int(monitoring.get("universe_refresh_days", 30))

    out: list[AgentTask] = []
    for company in companies:
        priority = company.get("commercial_priority", "C")
        cadence = int(company.get("cadence_days") or (high if priority in {"A", "A+"} else standard if priority == "B" else universe))
        if not include_not_due and not _is_due(company.get("last_checked"), cadence, as_of):
            continue
        urls = [url for url in company.get("watch_urls", []) if url]
        next_action = company.get("next_action") or "Review direct company sources for awards, mobilisations, hiring and capability changes."
        out.append(
            AgentTask(
                agent="company_watch",
                task_id=company["id"],
                priority=priority,
                cadence_days=cadence,
                reason=next_action,
                target={
                    "name": company.get("name"),
                    "clusters": company.get("cluster", []),
                    "relationship_status": company.get("relationship_status"),
                    "project_links": company.get("project_links", []),
                    "last_checked": company.get("last_checked"),
                },
                watch_urls=urls,
            )
        )

    return sorted(out, key=lambda t: (_priority_rank(t.priority), t.target.get("name") or ""))


def build_company_watch_catalog(as_of: date | None = None) -> list[AgentTask]:
    """Return all company-watch definitions regardless of due state."""
    return _company_tasks(as_of or date.today(), include_not_due=True)


def _institutional_tasks(as_of: date, include_not_due: bool = False) -> list[AgentTask]:
    _, sources = _merge_institutional_registries()
    out: list[AgentTask] = []

    for source in sources:
        cadence = int(source.get("cadence_days") or 7)
        if not include_not_due and not _is_due(source.get("last_checked"), cadence, as_of):
            continue
        url = source.get("official_url") or source.get("url")
        out.append(
            AgentTask(
                agent="institutional_watch",
                task_id=source["id"],
                priority=source.get("priority", "B"),
                cadence_days=cadence,
                reason=source.get("wind_adaptation") or source.get("audit_note") or "Monitor official wind source.",
                target={
                    "institution": source.get("institution"),
                    "region": source.get("region"),
                    "channel": source.get("channel"),
                    "status": source.get("status"),
                    "last_checked": source.get("last_checked"),
                },
                watch_urls=[url] if url else [],
            )
        )

    return sorted(out, key=lambda t: (_priority_rank(t.priority), t.task_id))


def build_institutional_watch_catalog(as_of: date | None = None) -> list[AgentTask]:
    """Return all institutional source definitions regardless of due state."""
    return _institutional_tasks(as_of or date.today(), include_not_due=True)


def _project_tasks(as_of: date) -> list[AgentTask]:
    projects = _load_projects()
    out: list[AgentTask] = []
    for project in projects:
        stage = str(project.get("stage") or "")
        if stage not in {"E4", "E5", "E6", "E7"}:
            continue
        open_scopes = [scope for scope in (project.get("scopes") or []) if scope.get("status") != "covered"]
        if not open_scopes:
            continue
        priority = project.get("priority", "C")
        cadence = 7 if priority in {"A", "A+"} or stage in {"E6", "E7"} else 14
        out.append(
            AgentTask(
                agent="project_execution_watch",
                task_id=project["id"],
                priority=priority,
                cadence_days=cadence,
                reason=f"{stage}: {len(open_scopes)} execution scopes still open; hunt only project-specific A1/A2 evidence.",
                target={
                    "name": project.get("name"),
                    "stage": stage,
                    "region": project.get("region"),
                    "developer": project.get("developer"),
                    "open_scopes": [scope.get("id") for scope in open_scopes],
                    "timing": project.get("timing"),
                },
                watch_urls=[s.get("url") for s in project.get("sources", []) if s.get("url")],
            )
        )

    return sorted(out, key=lambda t: (_priority_rank(t.priority), t.target.get("stage") or "", t.target.get("name") or ""))


def build_run_plan(as_of: date | None = None) -> AgentRunPlan:
    as_of = as_of or date.today()
    return AgentRunPlan(
        as_of=as_of.isoformat(),
        institutional=_institutional_tasks(as_of),
        companies=_company_tasks(as_of),
        projects=_project_tasks(as_of),
    )
