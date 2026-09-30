#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from html import escape
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.wind_agents.company_watch import due_company_ids, run_company_watch
from app.wind_agents.execution_watch import build_execution_queue
from app.wind_agents.reconcile import build_daily_discovery_report, build_digest
from app.wind_agents.runner import due_agent_ids, executable_agent_ids, run_agents

REPORT_DIR = ROOT / "reports" / "wind-agent"
LOCAL_STATUS = ROOT / "docs" / "wind" / "data" / "local-run-status.json"
WIND_DATA = ROOT / "docs" / "wind" / "data"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _daily_item_row(item: dict[str, Any]) -> dict[str, Any]:
    finding = item.get("finding") or {}
    payload = finding.get("payload") or {}
    reconciliation = item.get("reconciliation") or {}
    best = reconciliation.get("best") or {}
    municipalities = payload.get("municipalities") or payload.get("municipality") or []
    if isinstance(municipalities, list):
        municipalities_text = " | ".join(str(x) for x in municipalities if x)
    else:
        municipalities_text = str(municipalities or "")
    return {
        "category": item.get("category"),
        "event_type": item.get("event_type"),
        "source_name": finding.get("source_name") or item.get("source_name"),
        "external_id": finding.get("external_id") or item.get("external_id"),
        "project_name": payload.get("project_name") or finding.get("title"),
        "developer": payload.get("proponent") or payload.get("company_name"),
        "region": payload.get("region"),
        "province": payload.get("province"),
        "municipalities": municipalities_text,
        "power_mw": payload.get("power_mw"),
        "source_url": finding.get("source_url"),
        "match_status": reconciliation.get("status"),
        "matched_kind": best.get("target_kind"),
        "matched_id": best.get("target_id"),
        "matched_name": best.get("target_name"),
        "match_score": best.get("score"),
    }


def _write_daily_csv(path: Path, report: dict[str, Any]) -> None:
    fields = [
        "category", "event_type", "source_name", "external_id", "project_name",
        "developer", "region", "province", "municipalities", "power_mw",
        "source_url", "match_status", "matched_kind", "matched_id",
        "matched_name", "match_score",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter=";", lineterminator="\n")
        writer.writeheader()
        for item in report.get("items") or []:
            writer.writerow(_daily_item_row(item))


def _html_table(items: list[dict[str, Any]], empty_text: str) -> str:
    if not items:
        return f'<div class="empty">{escape(empty_text)}</div>'
    rows: list[str] = []
    for item in items:
        row = _daily_item_row(item)
        url = str(row.get("source_url") or "")
        source_link = (
            f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">fonte</a>'
            if url.startswith(("http://", "https://"))
            else "—"
        )
        match = "—"
        if row.get("matched_name"):
            score = row.get("match_score")
            score_text = f" ({score})" if score is not None else ""
            match = f"{escape(str(row['matched_name']))}{score_text}"
        rows.append(
            "<tr>"
            f"<td><b>{escape(str(row.get('project_name') or 'N/D'))}</b>"
            f"<small>{escape(str(row.get('developer') or ''))}</small></td>"
            f"<td>{escape(str(row.get('power_mw') or ''))}</td>"
            f"<td>{escape(str(row.get('region') or ''))}"
            f"<small>{escape(str(row.get('province') or ''))}</small></td>"
            f"<td>{escape(str(row.get('source_name') or ''))}</td>"
            f"<td>{escape(str(row.get('event_type') or ''))}</td>"
            f"<td>{match}</td>"
            f"<td>{source_link}</td>"
            "</tr>"
        )
    return (
        "<div class=\"table-wrap\"><table><thead><tr>"
        "<th>Progetto</th><th>MW</th><th>Area</th><th>Fonte</th>"
        "<th>Evento</th><th>Match</th><th>Link</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _write_daily_html(
    path: Path,
    report: dict[str, Any],
    *,
    generated_at: str,
    canonical: dict[str, Any],
    institutional: dict[str, Any],
    company: dict[str, Any],
) -> None:
    new_count = int(report.get("new_project_candidates") or 0)
    known_count = int(report.get("known_project_updates") or 0)
    discovery_count = int(report.get("discovery_candidate_updates") or 0)
    review_count = int(report.get("identity_reviews") or 0)
    filtered_count = int(report.get("filtered_non_pipeline") or 0)
    source_errors = {
        **(institutional.get("errors") or {}),
        **{f"company:{k}": v for k, v in (company.get("errors") or {}).items()},
    }
    if new_count:
        headline = f"{new_count} nuovo/i progetto/i candidato/i da verificare"
        headline_class = "alert"
    else:
        headline = "Nessun nuovo progetto candidato rilevato"
        headline_class = "ok"

    errors_html = (
        "<ul>" + "".join(
            f"<li><b>{escape(str(k))}</b>: {escape(str(v))}</li>"
            for k, v in sorted(source_errors.items())
        ) + "</ul>"
        if source_errors
        else '<div class="empty">Nessun errore fonte.</div>'
    )

    html = f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wind Radar — report giornaliero</title>
<style>
:root{{--bg:#f4f7f6;--card:#fff;--ink:#15221d;--muted:#64716b;--line:#dfe7e3;--green:#087f5b;--red:#b42318;--amber:#a15c00}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1320px;margin:auto;padding:24px}}h1{{margin:0 0 6px;font-size:28px}}h2{{margin:0 0 12px;font-size:18px}}
.meta{{color:var(--muted);margin-bottom:20px}}.headline{{padding:18px 20px;border-radius:14px;font-size:20px;font-weight:800;margin-bottom:18px}}
.headline.ok{{background:#e8f5ef;color:#086044;border:1px solid #b9dfd1}}.headline.alert{{background:#fff0ed;color:var(--red);border:1px solid #f2c4bc}}
.kpis{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-bottom:18px}}.kpi{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}}
.kpi small{{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;font-weight:700}}.kpi strong{{display:block;font-size:24px;margin-top:4px}}
section{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin:12px 0}}.empty{{color:var(--muted);padding:8px 0}}
.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;min-width:900px}}th,td{{text-align:left;border-bottom:1px solid var(--line);padding:9px;vertical-align:top}}th{{font-size:11px;text-transform:uppercase;color:var(--muted)}}td small{{display:block;color:var(--muted);margin-top:2px}}a{{color:var(--green);font-weight:700}}
.note{{color:var(--muted);font-size:12px}}ul{{margin:8px 0;padding-left:22px}}
@media(max-width:800px){{main{{padding:12px}}.kpis{{grid-template-columns:1fr 1fr}}}}
</style>
</head>
<body><main>
<h1>Wind Radar — report giornaliero</h1>
<div class="meta">Scansione {escape(generated_at)} · canonico: {canonical['projects']} progetti / {canonical['wind_mw']:.2f} MW wind</div>
<div class="headline {headline_class}">{escape(headline)}</div>
<div class="kpis">
<div class="kpi"><small>Nuovi candidati</small><strong>{new_count}</strong></div>
<div class="kpi"><small>Progetti noti aggiornati</small><strong>{known_count}</strong></div>
<div class="kpi"><small>Discovery aggiornati</small><strong>{discovery_count}</strong></div>
<div class="kpi"><small>Identità da verificare</small><strong>{review_count}</strong></div>
<div class="kpi"><small>Storici / fuori scala filtrati</small><strong>{filtered_count}</strong></div>
<div class="kpi"><small>Errori fonte</small><strong>{len(source_errors)}</strong></div>
</div>
<section><h2>Nuovi progetti candidati</h2>{_html_table(report.get('new_candidates') or [], 'Nessun nuovo progetto candidato.')}</section>
<section><h2>Aggiornamenti dei {canonical['projects']} progetti già noti</h2>{_html_table(report.get('known_updates') or [], 'Nessun aggiornamento significativo dei progetti canonici.')}</section>
<section><h2>Candidati Discovery già noti aggiornati</h2>{_html_table(report.get('discovery_updates') or [], 'Nessun aggiornamento della coda Discovery.')}</section>
<section><h2>Identità / matching da verificare</h2>{_html_table(report.get('identity_review_items') or [], 'Nessuna identità ambigua da verificare.')}</section>
<section><h2>Salute fonti</h2>{errors_html}
<div class="note">Institutional: {len(institutional.get('executed_agents') or [])} fonti eseguite · Company watch: {len(company.get('executed_companies') or [])} player eseguiti.</div>
</section>
<p class="note">Il report è review-only: nessun candidato viene aggiunto automaticamente ai 51 progetti canonici. La promozione richiede verifica di identità, attività corrente, configurazione e stage.</p>
</main></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _canonical_summary() -> dict[str, Any]:
    manifest = _load_json(WIND_DATA / "projects.json")
    meta = _load_json(WIND_DATA / manifest["meta"])
    projects: list[dict[str, Any]] = []
    for chunk in manifest["chunks"]:
        projects.extend(_load_json(WIND_DATA / chunk))
    return {
        "projects": len(projects),
        "wind_mw": round(sum(float(row.get("mw") or 0) for row in projects), 2),
        "bess_mw": round(sum(float(row.get("bess_mw") or 0) for row in projects), 2),
        "as_of": meta.get("as_of"),
        "version": meta.get("version"),
    }


def _safe(label: str, func: Callable[[], dict[str, Any]], fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return func()
    except Exception as exc:  # local launcher must remain usable if one layer fails
        result = dict(fallback)
        result["status"] = "error"
        result["errors"] = {"runner": f"{type(exc).__name__}: {exc}"}
        print(f"[WARN] {label}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return result


def _error_count(payload: dict[str, Any]) -> int:
    errors = payload.get("errors") or {}
    if isinstance(errors, dict):
        return len(errors)
    if isinstance(errors, list):
        return len(errors)
    return 1 if errors else 0


def _compact_institutional(payload: dict[str, Any], due_count: int) -> dict[str, Any]:
    return {
        "due": due_count,
        "executed": len(payload.get("executed_agents") or []),
        "findings": int(payload.get("findings") or 0),
        "new_or_changed": int(payload.get("new_or_changed") or 0),
        "errors": _error_count(payload),
        "data_health": payload.get("data_health") or {},
    }


def _compact_company(payload: dict[str, Any], due_count: int) -> dict[str, Any]:
    return {
        "due": due_count,
        "executed": len(payload.get("executed_companies") or []),
        "findings": int(payload.get("findings") or 0),
        "new_or_changed": int(payload.get("new_or_changed") or 0),
        "errors": _error_count(payload),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="One-click local updater for Wind Project & Contractor Radar")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="skip external network collection")
    mode.add_argument("--all", action="store_true", help="force all implemented institutional and company watches")
    args = parser.parse_args()

    started = time.monotonic()
    now = datetime.now().astimezone()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    canonical = _canonical_summary()
    # Il doppio clic è una vera scansione giornaliera: tutte le fonti
    # istituzionali project-discovery vengono interrogate a ogni run.
    institutional_due = [] if args.offline else executable_agent_ids()
    company_due = [] if args.offline else _safe(
        "company due queue",
        lambda: {"items": due_company_ids()},
        {"items": []},
    ).get("items", [])

    if args.offline:
        institutional = {
            "run_id": None,
            "executed_agents": [],
            "findings": 0,
            "new_or_changed": 0,
            "errors": {},
            "data_health": {},
            "status": "offline",
        }
        company = {
            "run_id": None,
            "executed_companies": [],
            "findings": 0,
            "new_or_changed": 0,
            "errors": {},
            "status": "offline",
        }
    else:
        institutional = _safe(
            "institutional daily project discovery",
            lambda: run_agents(None, due_only=False),
            {
                "run_id": None,
                "executed_agents": [],
                "findings": 0,
                "new_or_changed": 0,
                "errors": {},
                "data_health": {},
            },
        )
        company = _safe(
            "company watch",
            lambda: run_company_watch(None, due_only=not args.all),
            {
                "run_id": None,
                "executed_companies": [],
                "findings": 0,
                "new_or_changed": 0,
                "errors": {},
            },
        )

    execution = _safe(
        "execution investigation queue",
        build_execution_queue,
        {"projects": 0, "open_scope_count": 0, "priority_projects": []},
    )

    run_ids = [
        str(value)
        for value in (institutional.get("run_id"), company.get("run_id"))
        if value
    ]
    if run_ids:
        digest = _safe(
            "review-only digest",
            lambda: build_digest(run_ids),
            {"run_ids": run_ids, "events": 0, "actionable_events": 0, "items": [], "action_types": {}},
        )
    else:
        digest = {
            "run_ids": [],
            "events": 0,
            "actionable_events": 0,
            "non_actionable_events": 0,
            "items": [],
            "action_types": {},
        }

    daily_discovery = _safe(
        "daily project discovery report",
        lambda: build_daily_discovery_report(run_ids),
        {
            "run_ids": run_ids,
            "canonical_projects": canonical["projects"],
            "events": 0,
            "new_project_candidates": 0,
            "known_project_updates": 0,
            "discovery_candidate_updates": 0,
            "identity_reviews": 0,
            "filtered_non_pipeline": 0,
            "new_candidates": [],
            "known_updates": [],
            "discovery_updates": [],
            "identity_review_items": [],
            "items": [],
        },
    )

    _write_json(REPORT_DIR / "local-institutional-run.json", institutional)
    _write_json(REPORT_DIR / "local-company-run.json", company)
    _write_json(REPORT_DIR / "local-execution-queue.json", execution)
    _write_json(REPORT_DIR / "local-digest.json", digest)
    _write_json(REPORT_DIR / "daily-discovery-latest.json", daily_discovery)
    _write_daily_csv(REPORT_DIR / "daily-discovery-latest.csv", daily_discovery)
    _write_daily_html(
        REPORT_DIR / "daily-discovery-latest.html",
        daily_discovery,
        generated_at=now.isoformat(timespec="seconds"),
        canonical=canonical,
        institutional=institutional,
        company=company,
    )
    history_dir = REPORT_DIR / "daily"
    history_stamp = now.strftime("%Y-%m-%d_%H%M%S")
    _write_json(history_dir / f"{history_stamp}.json", daily_discovery)
    _write_daily_csv(history_dir / f"{history_stamp}.csv", daily_discovery)

    total_errors = _error_count(institutional) + _error_count(company)
    mode_name = "offline" if args.offline else ("all" if args.all else "daily")
    status = {
        "generated_at": now.isoformat(timespec="seconds"),
        "mode": mode_name,
        "duration_seconds": round(time.monotonic() - started, 1),
        "outcome": "partial" if total_errors else "ok",
        "canonical": canonical,
        "institutional": _compact_institutional(institutional, len(institutional_due)),
        "company": _compact_company(company, len(company_due)),
        "execution_queue": {
            "projects": int(execution.get("projects") or 0),
            "open_scope_count": int(execution.get("open_scope_count") or 0),
        },
        "digest": {
            "events": int(digest.get("events") or 0),
            "actionable_events": int(digest.get("actionable_events") or 0),
            "non_actionable_events": int(digest.get("non_actionable_events") or 0),
            "action_types": digest.get("action_types") or {},
        },
        "daily_discovery": {
            "new_project_candidates": int(daily_discovery.get("new_project_candidates") or 0),
            "known_project_updates": int(daily_discovery.get("known_project_updates") or 0),
            "discovery_candidate_updates": int(daily_discovery.get("discovery_candidate_updates") or 0),
            "identity_reviews": int(daily_discovery.get("identity_reviews") or 0),
            "filtered_non_pipeline": int(daily_discovery.get("filtered_non_pipeline") or 0),
            "report_html": str(REPORT_DIR / "daily-discovery-latest.html"),
        },
        "guard": (
            "Review-only: raw finding e digest non modificano automaticamente il canonico. "
            "Uno scope esecutivo si chiude solo con evidenza project-specific A1/A2."
        ),
    }
    _write_json(LOCAL_STATUS, status)

    print()
    print("=== Wind Radar local update ===")
    print(f"Mode: {mode_name}")
    print(f"Canonical: {canonical['projects']} projects / {canonical['wind_mw']:.2f} MW wind")
    print(
        "Institutional: "
        f"{status['institutional']['executed']} executed, "
        f"{status['institutional']['new_or_changed']} new/changed, "
        f"{status['institutional']['errors']} errors"
    )
    print(
        "Company watch: "
        f"{status['company']['executed']} executed, "
        f"{status['company']['new_or_changed']} new/changed, "
        f"{status['company']['errors']} errors"
    )
    print(
        "Daily discovery: "
        f"{status['daily_discovery']['new_project_candidates']} NEW project candidates / "
        f"{status['daily_discovery']['known_project_updates']} known-project updates / "
        f"{status['daily_discovery']['identity_reviews']} identity reviews / "
        f"{status['daily_discovery']['filtered_non_pipeline']} historical/non-target filtered"
    )
    print(f"Daily report: {REPORT_DIR / 'daily-discovery-latest.html'}")
    print(
        "Review digest: "
        f"{status['digest']['actionable_events']} actionable / "
        f"{status['digest']['events']} new-or-changed events"
    )
    print(
        "Execution queue: "
        f"{status['execution_queue']['projects']} projects / "
        f"{status['execution_queue']['open_scope_count']} open scopes"
    )
    if total_errors:
        print(f"[WARN] Completed with {total_errors} source/company errors; canonical unchanged.")
    else:
        print("[OK] Local intelligence refresh completed; canonical unchanged pending review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
