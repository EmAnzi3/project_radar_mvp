#!/usr/bin/env python3
from __future__ import annotations

import sys
import hashlib
import json
import sqlite3
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.wind_agents.base import AgentFinding
from app.wind_agents.reconcile import classify_daily_discovery_event, load_canonical_projects
from app.wind_agents import state as wind_state


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
            "source_url": "https://example.invalid/provvedimento-not-equal-to-project-url",
            "title": known.get("name"),
            "finding_type": "project_source",
            "payload": {
                "project_specific": True,
                "project_url": source_url,
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
    assert novel_result["minimum_project_fields_complete"] is True

    for missing_key in ("proponent", "power_mw", "municipalities"):
        incomplete_event = {
            **novel_event,
            "external_id": f"test-incomplete-{missing_key}",
            "finding": {
                **novel_event["finding"],
                "external_id": f"test-incomplete-{missing_key}",
                "payload": dict(novel_event["finding"]["payload"]),
            },
        }
        if missing_key == "municipalities":
            incomplete_event["finding"]["payload"]["municipalities"] = []
        else:
            incomplete_event["finding"]["payload"][missing_key] = None
        incomplete_result = classify_daily_discovery_event(
            incomplete_event,
            canonical=canonical,
            discovery=[],
        )
        assert incomplete_result["category"] == "incomplete_project_record", incomplete_result
        assert incomplete_result["minimum_project_fields_complete"] is False
        expected_missing = "municipality" if missing_key == "municipalities" else (
            "company" if missing_key == "proponent" else "power_mw"
        )
        assert expected_missing in incomplete_result["minimum_project_fields_missing"], incomplete_result

    historical_event = {
        "event_type": "new",
        "external_id": "test-historical-small-wind",
        "finding": {
            "external_id": "test-historical-small-wind",
            "source_name": "ATOS Toscana FER",
            "source_url": "https://example.invalid/historical-small",
            "title": "EOL STORICO TEST",
            "finding_type": "project_source",
            "payload": {
                "project_specific": True,
                "project_name": "EOL STORICO TEST",
                "region": "Toscana",
                "power_mw": 0.9,
                "status_raw": "Autorizzato",
                "last_act_date": "2018-12-21",
            },
        },
    }
    historical_result = classify_daily_discovery_event(
        historical_event,
        canonical=canonical,
        discovery=[],
    )
    assert historical_result["category"] == "non_target_scale", historical_result

    follow_up_event = {
        "event_type": "new",
        "external_id": "test-old-compliance",
        "finding": {
            "external_id": "test-old-compliance",
            "source_name": "MASE VIA",
            "source_url": "https://example.invalid/old-compliance",
            "title": "Parco eolico storico test",
            "finding_type": "project_source",
            "payload": {
                "project_specific": True,
                "project_name": "Parco eolico storico test",
                "region": "Puglia",
                "power_mw": 50.0,
                "procedure": "Verifica di Ottemperanza",
                "status_raw": "Istruttoria tecnica CTVIA",
                "date_presented": "15/04/2019",
            },
        },
    }
    follow_up_result = classify_daily_discovery_event(
        follow_up_event,
        canonical=canonical,
        discovery=[],
    )
    assert follow_up_result["category"] == "existing_project_follow_up", follow_up_result

    archived_event = {
        "event_type": "new",
        "external_id": "test-archived-wind",
        "finding": {
            "external_id": "test-archived-wind",
            "source_name": "Regione Lazio VIA/PAUR",
            "source_url": "https://example.invalid/archived",
            "title": "Parco eolico archiviato test",
            "finding_type": "project_source",
            "payload": {
                "project_specific": True,
                "project_name": "Parco eolico archiviato test",
                "region": "Lazio",
                "power_mw": 30.0,
                "status_raw": "Archiviato",
            },
        },
    }
    archived_result = classify_daily_discovery_event(
        archived_event,
        canonical=canonical,
        discovery=[],
    )
    assert archived_result["category"] == "historical_or_closed", archived_result

    baseline_event = {
        **novel_event,
        "event_type": "baseline",
        "external_id": "test-baseline-unique-project",
        "finding": {
            **novel_event["finding"],
            "external_id": "test-baseline-unique-project",
        },
    }
    baseline_result = classify_daily_discovery_event(
        baseline_event,
        canonical=canonical,
        discovery=[],
    )
    assert baseline_result["category"] == "baseline_project_candidate", baseline_result

    with tempfile.TemporaryDirectory() as tmp:
        original_db = wind_state.DB_PATH
        wind_state.DB_PATH = Path(tmp) / "wind-agent-test.sqlite"
        try:
            sample = AgentFinding(
                external_id="bootstrap-state-test",
                source_name="Test source",
                source_url="https://example.invalid/bootstrap",
                title="Test wind project",
                finding_type="project_source",
                payload={"project_specific": True, "project_name": "Test wind project"},
            )
            first = wind_state.upsert_finding("run-1", "institutional_watch", sample, baseline_new=True)
            second = wind_state.upsert_finding("run-2", "institutional_watch", sample, baseline_new=False)
            changed = AgentFinding(
                external_id=sample.external_id,
                source_name=sample.source_name,
                source_url=sample.source_url,
                title=sample.title,
                finding_type=sample.finding_type,
                payload={**sample.payload, "power_mw": 55.0},
            )
            third = wind_state.upsert_finding("run-3", "institutional_watch", changed, baseline_new=False)
            assert first == "baseline", first
            assert second == "unchanged", second
            assert third == "changed", third

            # Sicilia migration/fallback regression:
            # a pre-patch full-payload hash must not create a fake "changed"
            # event when the same official procedure is read via MapServer.
            legacy = AgentFinding(
                external_id="SICILIA-SIVVI-1234",
                source_name="Regione Sicilia SI-VVI",
                source_url="https://example.invalid/sicilia.csv",
                title="PARCO EOLICO TEST SICILIA 30 MW",
                finding_type="project_source",
                payload={
                    "project_name": "PARCO EOLICO TEST SICILIA 30 MW",
                    "proponent": "TEST WIND SRL",
                    "region": "Sicilia",
                    "power_mw": 30.0,
                    "procedure": "VIA",
                    "status_raw": "In corso",
                    "source_code": "1234",
                    "ingestion_path": "official_csv",
                    "project_specific": True,
                },
            )
            legacy_first = wind_state.upsert_finding(
                "run-sicilia-1",
                "institutional_watch",
                legacy,
                baseline_new=True,
            )
            assert legacy_first == "baseline", legacy_first

            legacy_wrapper = {
                "external_id": legacy.external_id,
                "source_name": legacy.source_name,
                "source_url": legacy.source_url,
                "title": legacy.title,
                "finding_type": legacy.finding_type,
                "payload": legacy.payload,
            }
            legacy_raw = json.dumps(
                legacy_wrapper,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            legacy_full_hash = hashlib.sha256(legacy_raw.encode("utf-8")).hexdigest()
            conn = sqlite3.connect(wind_state.DB_PATH)
            try:
                conn.execute(
                    "UPDATE raw_findings SET content_hash = ? "
                    "WHERE agent_name = ? AND source_name = ? AND external_id = ?",
                    (
                        legacy_full_hash,
                        "institutional_watch",
                        legacy.source_name,
                        legacy.external_id,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            basis = {
                "source_code": "1234",
                "project_name": "PARCO EOLICO TEST SICILIA 30 MW",
                "proponent": "TEST WIND SRL",
                "procedure": "VIA",
                "power_mw": 30.0,
            }
            fallback = AgentFinding(
                external_id=legacy.external_id,
                source_name=legacy.source_name,
                source_url="https://example.invalid/mapserver/query?id=1234",
                title=legacy.title,
                finding_type=legacy.finding_type,
                payload={
                    **legacy.payload,
                    "status_raw": None,
                    "latitude": 37.5,
                    "longitude": 14.2,
                    "ingestion_path": "official_sivvi_mapserver_fallback",
                    "fallback_reason": "CSV timeout",
                    "_change_basis": basis,
                },
            )
            fallback_event = wind_state.upsert_finding(
                "run-sicilia-2",
                "institutional_watch",
                fallback,
            )
            assert fallback_event == "unchanged", fallback_event

            fallback_changed = AgentFinding(
                external_id=fallback.external_id,
                source_name=fallback.source_name,
                source_url=fallback.source_url,
                title=fallback.title,
                finding_type=fallback.finding_type,
                payload={
                    **fallback.payload,
                    "power_mw": 31.0,
                    "_change_basis": {**basis, "power_mw": 31.0},
                },
            )
            fallback_changed_event = wind_state.upsert_finding(
                "run-sicilia-3",
                "institutional_watch",
                fallback_changed,
            )
            assert fallback_changed_event == "changed", fallback_changed_event
        finally:
            wind_state.DB_PATH = original_db

    print("Wind daily discovery checks OK")
    print(f"Canonical: {len(canonical)} projects / {total_mw:.2f} MW")
    print("Known finding via payload.project_url -> known_project_update")
    print("Unmatched new complete project-specific finding -> new_project_candidate")
    print("Missing company/MW/municipality -> incomplete_project_record")
    print("First-seen source inventory -> baseline_project_candidate")
    print("Historical micro-wind -> non_target_scale")
    print("Unmatched verification of compliance -> existing_project_follow_up")
    print("Archived project -> historical_or_closed")
    print("State bootstrap -> baseline / unchanged / changed")
    print("Sicilia CSV/GIS path switch -> unchanged; semantic change -> changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
