#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.wind_agents.reconcile import classify_daily_discovery_event, load_canonical_projects


def main() -> int:
    canonical = load_canonical_projects()
    assert len(canonical) == 51, f"canonical projects: {len(canonical)} != 51"
    total_mw = round(sum(float(p.get("mw") or 0) for p in canonical), 2)
    assert abs(total_mw - 11202.52) < 0.01, total_mw

    known = canonical[0]
    source_url = next(
        (s.get("url") for s in known.get("sources", []) if s.get("url")),
        f"https://example.invalid/{known['id']}",
    )
    known_event = {
        "event_type": "changed",
        "external_id": f"test-known-{known['id']}",
        "finding": {
            "external_id": f"test-known-{known['id']}",
            "source_name": "test",
            "source_url": source_url,
            "title": known.get("name"),
            "finding_type": "project_source",
            "payload": {
                "project_specific": True,
                "project_name": known.get("name"),
                "region": known.get("region"),
                "municipalities": known.get("municipalities") or [],
                "power_mw": known.get("mw"),
                "proponent": known.get("developer"),
            },
        },
    }
    known_result = classify_daily_discovery_event(
        known_event,
        canonical=canonical,
        discovery=[],
    )
    assert known_result["category"] == "known_project_update", known_result

    novel_event = {
        "event_type": "new",
        "external_id": "test-new-unique-project",
        "finding": {
            "external_id": "test-new-unique-project",
            "source_name": "test",
            "source_url": "https://example.invalid/wind-daily-discovery-new",
            "title": "Progetto Eolico Unico Test Zeta 987654",
            "finding_type": "project_source",
            "payload": {
                "project_specific": True,
                "project_name": "Progetto Eolico Unico Test Zeta 987654",
                "region": "Regione Test Unica",
                "municipalities": ["Comune Test Unico"],
                "power_mw": 777.7,
                "proponent": "Developer Test Unico 987654",
            },
        },
    }
    novel_result = classify_daily_discovery_event(
        novel_event,
        canonical=canonical,
        discovery=[],
    )
    assert novel_result["category"] == "new_project_candidate", novel_result

    print("Wind daily discovery checks OK")
    print(f"Canonical: {len(canonical)} projects / {total_mw:.2f} MW")
    print("Known finding -> known_project_update")
    print("Unmatched new project-specific finding -> new_project_candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
