#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.wind_agents.base import AgentFinding
from app.wind_agents.adapters.toscana import ToscanaWindAgent
from app.wind_agents.adapters.toscana_atos import ToscanaAtosWindAgent
from app.wind_agents.adapters.lombardia import LombardiaWindAgent
from app.wind_agents.adapters.sistema_puglia import SistemaPugliaWindAgent
from app.wind_agents.adapters.sicilia import SiciliaWindAgent
from app.wind_agents.adapters.basilicata import BasilicataEnergyWindAgent, BasilicataWindAgent
from app.wind_agents.adapters.calabria import CalabriaRegionalActsWindAgent
from app.wind_agents.adapters.campania import CampaniaWindAgent
from app.wind_agents.adapters.sardegna import SardegnaWindAgent
from app.wind_agents.company_watch import due_company_ids
from app.wind_agents.evidence import can_close_execution_scope, evidence_layer
from app.wind_agents.execution_watch import build_execution_queue
from app.wind_agents.planner import (
    _merge_company_registries,
    _merge_institutional_registries,
    build_company_watch_catalog,
    build_institutional_watch_catalog,
    build_run_plan,
)
from app.wind_agents.reconcile import build_digest, reconcile_finding
from app.wind_agents.runner import _bootstrap_decision, due_agent_ids, executable_agent_ids
from app.wind_agents import state


company_base, companies = _merge_company_registries()
institutional_base, sources = _merge_institutional_registries()
assert len(companies) >= 58, len(companies)
assert len(sources) >= 31, len(sources)
assert company_base["monitoring"]["high_priority_cadence_days"] == 7
assert institutional_base["monitoring"]["priority_regional_cadence_days"] == 3

as_of = date(2026, 9, 5)
plan = build_run_plan(as_of=as_of)
project_ids = {task.task_id for task in plan.projects}
for required in ["andretta-bisaccia", "alia-sclafani", "serra-giannina"]:
    assert required in project_ids, f"priority project missing from wind-agent plan: {required}"
assert plan.institutional, "institutional due queue empty"
assert plan.companies, "company due queue empty"

execution_queue = build_execution_queue(as_of=as_of)
execution_ids = {row["project_id"] for row in execution_queue["priority_projects"]}
assert {"andretta-bisaccia", "alia-sclafani", "serra-giannina"}.issubset(execution_ids)
assert execution_queue["projects"] == len(plan.projects), execution_queue
assert execution_queue["open_scope_count"] > 0
assert execution_queue["priority_projects"][0]["urgency_score"] >= 90
assert "A1/A2" in execution_queue["guard"]

catalog = {task.task_id: task for task in build_institutional_watch_catalog(as_of)}
company_catalog = build_company_watch_catalog(as_of)
assert len(company_catalog) >= 58, len(company_catalog)
assert sum(bool(task.watch_urls) for task in company_catalog) >= 50, "company watch URL coverage too low"

implemented = set(executable_agent_ids())
required_adapters = {
    "abruzzo-via",
    "basilicata-au-paur",
    "basilicata-via",
    "calabria-regional-acts",
    "calabria-via",
    "campania-viavas",
    "emilia-romagna-regional",
    "lazio-regional",
    "liguria-via-procedimenti",
    "lombardia-regional",
    "marche-via-regional",
    "mase-provvedimenti",
    "mase-via",
    "molise-au-eolico",
    "piemonte-regional",
    "puglia-au-paur",
    "puglia-sistema-energia",
    "sardegna-sira",
    "sicilia-sivvi",
    "terna-econnextion",
    "toscana-atos",
    "toscana-gea",
    "umbria-regional",
    "veneto-regional",
}
assert required_adapters.issubset(implemented), implemented
assert len(implemented) >= 24, implemented
assert required_adapters.issubset(catalog), f"adapter/registry id drift: {required_adapters - set(catalog)}"

# Parser/source revisions must rebaseline exactly once on an existing local DB.
legacy_runtime = {
    "last_success": "2026-09-30T12:00:00",
    "metadata": {"data_health": "empty_success"},
}
campania_revision = CampaniaWindAgent()
decision = _bootstrap_decision(
    legacy_runtime,
    campania_revision,
    bootstrap_new_sources=True,
)
assert decision[0] is True and decision[1] is True, decision
assert decision[2] == campania_revision.baseline_revision
assert decision[3] is None

migrated_runtime = {
    "last_success": "2026-10-01T12:00:00",
    "metadata": {"baseline_revision": campania_revision.baseline_revision},
}
decision = _bootstrap_decision(
    migrated_runtime,
    campania_revision,
    bootstrap_new_sources=True,
)
assert decision[0] is False and decision[1] is False, decision

sardegna_revision = SardegnaWindAgent(years=["2026"])
decision = _bootstrap_decision(
    legacy_runtime,
    sardegna_revision,
    bootstrap_new_sources=False,
)
assert decision[0] is False and decision[1] is False, decision

# Toscana GeA must degrade transparently to a channel-only snapshot when the
# project API is unavailable, rather than pretending project-level coverage.
toscana_fallback = ToscanaWindAgent(max_pages=1)
def _synthetic_gea_failure(_page_index: int):
    raise ConnectionError("synthetic GeA API DNS failure")
toscana_fallback._fetch_page = _synthetic_gea_failure
fallback_findings = toscana_fallback.fetch()
assert len(fallback_findings) == 1, fallback_findings
assert fallback_findings[0].finding_type == "source_channel_snapshot"
assert fallback_findings[0].payload.get("project_specific") is False
assert fallback_findings[0].payload.get("data_health") == "channel_only"

lombardia_fallback = LombardiaWindAgent(years=[2026])
def _synthetic_silvia_failure():
    raise requests.ConnectionError("synthetic SILVIA DNS failure")
lombardia_fallback._load_sectors = _synthetic_silvia_failure
lombardia_findings = lombardia_fallback.fetch()
assert len(lombardia_findings) == 1, lombardia_findings
assert lombardia_findings[0].finding_type == "source_channel_snapshot"
assert lombardia_findings[0].payload.get("project_specific") is False
assert lombardia_findings[0].payload.get("data_health") == "channel_only"

atos_fallback = ToscanaAtosWindAgent(max_details=1)
def _synthetic_atos_failure():
    raise requests.ConnectionError("synthetic ATOS DNS failure")
atos_fallback._fetch_map_results = _synthetic_atos_failure
atos_findings = atos_fallback.fetch()
assert len(atos_findings) == 1, atos_findings
assert atos_findings[0].finding_type == "source_channel_snapshot"
assert atos_findings[0].payload.get("project_specific") is False
assert atos_findings[0].payload.get("data_health") == "channel_only"

basilicata_channel = BasilicataEnergyWindAgent()
def _synthetic_basilicata_outage():
    raise requests.ConnectionError("synthetic Basilicata AU timeout")
basilicata_channel._fetch_energy_notices = _synthetic_basilicata_outage
basilicata_channel_findings = basilicata_channel.fetch()
assert len(basilicata_channel_findings) == 1
assert basilicata_channel_findings[0].finding_type == "source_channel_snapshot"
assert basilicata_channel_findings[0].payload.get("project_specific") is False
assert basilicata_channel_findings[0].payload.get("data_health") == "channel_only"

sicilia_channel = SiciliaWindAgent()
def _synthetic_sicilia_csv_outage():
    raise requests.ConnectionError("synthetic Sicilia CSV timeout")
def _synthetic_sicilia_gis_outage(_reason):
    raise requests.Timeout("synthetic Sicilia MapServer timeout")
sicilia_channel._findings_from_csv = _synthetic_sicilia_csv_outage
sicilia_channel._findings_from_gis = _synthetic_sicilia_gis_outage
sicilia_channel_findings = sicilia_channel.fetch()
assert len(sicilia_channel_findings) == 1
assert sicilia_channel_findings[0].finding_type == "source_channel_snapshot"
assert sicilia_channel_findings[0].payload.get("project_specific") is False
assert sicilia_channel_findings[0].payload.get("data_health") == "channel_only"
assert "CSV timeout" in sicilia_channel_findings[0].payload.get("csv_availability_issue", "")
assert "MapServer timeout" in sicilia_channel_findings[0].payload.get("gis_availability_issue", "")

# Minimum-field parser guards on real-style official regional act text.
puglia_text = (
    'Autorizzazione Unica ai sensi dell’art. 12 del D. Lgs. n. 387/2003 '
    'per un impianto eolico denominato "Ponticello" della potenza elettrica di 42 MW, '
    'da realizzarsi nei Comuni di Orta Nova e Stornarella (FG). '
    'Proponente: Inergia S.p.A. - C.F. e P. IVA: 01752630440'
)
assert SistemaPugliaWindAgent._power_from_text(puglia_text) == 42.0
assert SistemaPugliaWindAgent._proponent_from_text(puglia_text) == "Inergia S.p.A"
puglia_places = SistemaPugliaWindAgent._municipalities_from_text(puglia_text)
assert {"Orta Nova", "Stornarella"}.issubset(set(puglia_places)), puglia_places

basilicata_text = (
    'progetto definitivo per la realizzazione del parco eolico "Tempa dei Greci" '
    'avente una potenza complessiva di 21 MW e relative opere connesse, da realizzare '
    'nei comuni di Gorgoglione (MT), Corleto Perticara (PZ) e Guardia Perticara (PZ). '
    'Proponente: Tempa dei Greci S.r.l. ex FRI-EL S.p.a. '
    'Progressivo Interno: 540 - ID PAUR: 07_2020.'
)
assert BasilicataWindAgent._power_mw(basilicata_text) == 21.0
assert BasilicataWindAgent._proponent(basilicata_text) == "Tempa dei Greci S.r.l. ex FRI-EL S.p.a"
assert "Gorgoglione" in BasilicataWindAgent._municipalities(basilicata_text)

basilicata_2026_santarcangelo = (
    "Autorizzazione unica ex art. 12 del D.Lgs 387/2003 relativa al progetto per la costruzione "
    "e l'esercizio di un impianto eolico, e delle relative opere accessorie, della potenza di "
    "19,20 MW da realizzare nel Comune di Sant'Arcangelo (PZ). Società Proponente: Elettrowind Due srl "
    "Data di pubblicazione: 24/08/2026 - Codice di pubblicazione: P26-55"
)
assert BasilicataWindAgent._power_mw(basilicata_2026_santarcangelo) == 19.2
assert BasilicataWindAgent._proponent(basilicata_2026_santarcangelo) == "Elettrowind Due srl"
assert BasilicataWindAgent._municipalities(basilicata_2026_santarcangelo) == ["Sant'Arcangelo"]

basilicata_2026_servigliano = (
    'Autorizzazione Unica Regionale ai sensi dell art. 12 comma 3 del decreto legislativo 387/2003 '
    'per la costruzione e l esercizio di un impianto per la produzione di energia elettrica da fonte '
    'eolica denominato "Vento di Servigliano", di potenza nominale totale pari a 30 MW integrato con '
    'un sistema di accumulo di 21 MW, da realizzarsi nei Comuni di Montemurro e Armento con relative '
    'opere connesse ed infrastrutture indispensabili nei comuni di Montemurro, Armento e Viggiano. '
    'PROPONENTE: FRI-EL SERVIGLIANO S.r.l.'
)
assert BasilicataWindAgent._power_mw(basilicata_2026_servigliano) == 30.0
assert BasilicataWindAgent._proponent(basilicata_2026_servigliano) == "FRI-EL SERVIGLIANO S.r.l"
servigliano_places = BasilicataWindAgent._municipalities(basilicata_2026_servigliano)
assert servigliano_places == ["Montemurro", "Armento"], servigliano_places

basilicata_granted_text = (
    "D.LGS 152/2006 - L.R. N. 47/1998 - Progetto per la costruzione e l'esercizio "
    "di un impianto per la produzione di energia elettrica da fonte eolica, delle opere "
    "connesse e delle infrastrutture indispensabili in agro del Comune di Tolve (PZ) "
    "della potenza nominale di 19,80 MW proposto dalla società SERRA ENERGIE S.R.L."
)
assert BasilicataWindAgent._power_mw(basilicata_granted_text) == 19.8
assert BasilicataWindAgent._proponent(basilicata_granted_text) == "SERRA ENERGIE S.R.L"
assert BasilicataWindAgent._municipalities(basilicata_granted_text) == ["Tolve"]
assert BasilicataEnergyWindAgent.baseline_revision == "basilicata-energy-v3"

campania_total_text = (
    "PAUR progetto Repowering impianto eolico composto da 14 aerogeneratori da 7,2 MW "
    "per una potenza complessiva di 100,8 MW e relative opere di connessione "
    "nei Comuni di Lacedonia (AV)"
)
assert CampaniaWindAgent._power_mw(campania_total_text) == 100.8
campania_places = CampaniaWindAgent._municipalities(
    "LACEDONIA",
    campania_total_text.replace(
        "nei Comuni di Lacedonia (AV)",
        "nei Comuni di Lacedonia (AV), Monteverde (AV) e Bisaccia (AV) ed opera RTN"
    ),
)
assert {"LACEDONIA", "Monteverde", "Bisaccia"}.issubset(set(campania_places)), campania_places
assert CampaniaWindAgent.baseline_revision == "2026-10-current-project-table-v5-municipality-cleanup"

sardegna_detail_text = (
    'Titolo progetto: Impianto Eolico denominato "WHITE AND BLUE LUIGHIEDDA" della potenza '
    'di 21, 6 MW ubicato in località Sa Lughiedda nel Comune di Sassari (SS) '
    'Proponente: INNOVO DEVELOPMENT 8 S.R.L. Comune: SASSARI Provincia: SASSARI '
    'Stato del procedimento: CHIUSA Esito: NEGATIVO'
)
assert SardegnaWindAgent._power_mw(sardegna_detail_text) == 21.6
assert SardegnaWindAgent._proponent(
    sardegna_detail_text + " Consulta la documentazione ulteriori contenuti del portale"
) == "INNOVO DEVELOPMENT 8 S.R.L"
assert SardegnaWindAgent._municipality(sardegna_detail_text) == "SASSARI"
assert SardegnaWindAgent._status(sardegna_detail_text) == "Negativo"
assert SardegnaWindAgent.baseline_revision == "2026-10-news-project-detail-v4"

calabria_paladino_text = (
    "Oggetto: Provvedimento di Valutazione di Impatto Ambientale ai sensi degli art. 23 e segg. "
    "Progetto: Pratica n. 162 (CZ) sul sistema Calabria SUAP Sportello Ambiente - "
    "Parco Eolico Paladino di potenza nominale pari a 24,00 MW da realizzarsi in Provincia "
    "di Catanzaro, nei Comuni di Gasperina, Montauro, Montepaone, Palermiti, Petrizzi e Argusto. "
    "Comuni interessati: Gasperina, Montauro, Palermiti, Petrizzi, Montepaone e Argusto (CZ). "
    "Proponente: Paladino Energia S.r.l."
)
assert CalabriaRegionalActsWindAgent._power_mw(calabria_paladino_text) == 24.0
assert CalabriaRegionalActsWindAgent._proponent(
    calabria_paladino_text + " Ulteriori dati del provvedimento e allegati amministrativi"
) == "Paladino Energia S.r.l"
calabria_places = CalabriaRegionalActsWindAgent._municipalities(calabria_paladino_text)
assert {"Gasperina", "Montauro", "Montepaone", "Palermiti", "Petrizzi", "Argusto"}.issubset(set(calabria_places)), calabria_places
assert CalabriaRegionalActsWindAgent.baseline_revision == "calabria-regional-acts-v3"

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

# Reconciliation is conservative and advisory only.
synthetic_canonical = [
    {
        "id": "andretta-bisaccia",
        "name": "Andretta-Bisaccia",
        "mw": 88.5,
        "region": "Campania",
        "municipalities": ["Andretta", "Bisaccia", "Vallata"],
        "developer": "Edison Rinnovabili",
        "stage": "E6",
        "priority": "A+",
        "sources": [],
    }
]
project_finding = {
    "source_url": "https://example.com/andretta",
    "title": "Andretta-Bisaccia",
    "finding_type": "project_source",
    "payload": {
        "project_name": "Andretta-Bisaccia",
        "proponent": "Edison Rinnovabili",
        "region": "Campania",
        "municipalities": ["Andretta"],
        "power_mw": 88.5,
        "project_specific": True,
    },
}
project_match = reconcile_finding(project_finding, canonical=synthetic_canonical, discovery=[])
assert project_match["status"] == "high_confidence_match", project_match
assert project_match["auto_reconciled"] is True, project_match
assert project_match["best"]["target_id"] == "andretta-bisaccia", project_match

company_finding = {
    "source_url": "https://example.com/company",
    "title": "Edison direct source",
    "finding_type": "company_source_snapshot",
    "payload": {
        "company_name": "Edison Rinnovabili",
        "project_name": "Andretta-Bisaccia",
        "region": "Campania",
        "project_links_registry": ["andretta-bisaccia"],
        "project_specific": False,
        "signal_excerpt": "Wind construction project update.",
    },
}
company_match = reconcile_finding(company_finding, canonical=synthetic_canonical, discovery=[])
assert company_match["best"]["target_id"] == "andretta-bisaccia", company_match
assert company_match["auto_reconciled"] is False, company_match
assert reconcile_finding(project_finding, canonical=[], discovery=[])["best"] is None

# PV-Agent-style raw/history persistence must detect new / unchanged / changed.
# Operational cursors and live watch timestamps are separate from canonical data.
with tempfile.TemporaryDirectory() as tmp:
    state.DB_PATH = Path(tmp) / "wind_agent_test.sqlite"
    assert state.get_source_cursor("test-cursor") is None
    assert state.get_source_cursor("test-cursor", "100") == "100"
    state.set_source_cursor("test-cursor", 123, {"kind": "validator"})
    assert state.get_source_cursor("test-cursor") == "123"

    initial_due = set(due_agent_ids(as_of=as_of))
    assert required_adapters.issubset(initial_due), initial_due
    future_company_due = set(due_company_ids(as_of=date(2026, 10, 5)))
    assert future_company_due, "company watch future due queue unexpectedly empty"

    run_id = state.begin_run(plan.total_tasks, note="validator")
    state.mark_watch_attempt("mase-via", run_id, success=True, metadata={"validator": True})
    assert state.get_watch_status("mase-via")["last_success"]
    assert "mase-via" not in set(due_agent_ids(as_of=as_of))

    first_company = next(task for task in company_catalog if task.watch_urls)
    company_watch_id = f"company:{first_company.task_id}"
    state.mark_watch_attempt(company_watch_id, run_id, success=True, metadata={"validator": True})
    assert state.get_watch_status(company_watch_id)["last_success"]

    finding = AgentFinding(
        external_id="test-1",
        source_name="validator",
        source_url="https://example.com/wind/1",
        title="Wind test",
        finding_type="project_source",
        payload={"power_mw": 10, "proponent": "Wind Test S.r.l.", "municipalities": ["Comune Test"], "project_specific": True},
    )
    assert state.upsert_finding(run_id, "test_agent", finding) == "new"
    assert state.upsert_finding(run_id, "test_agent", finding) == "unchanged"
    changed = AgentFinding(
        external_id="test-1",
        source_name="validator",
        source_url="https://example.com/wind/1",
        title="Wind test",
        finding_type="project_source",
        payload={"power_mw": 12, "proponent": "Wind Test S.r.l.", "municipalities": ["Comune Test"], "project_specific": True},
    )
    assert state.upsert_finding(run_id, "test_agent", changed) == "changed"
    state.finish_run(run_id, findings=3, changed_items=2)

    events = state.get_run_events(run_id)
    assert [event["event_type"] for event in events] == ["new", "changed"], events
    digest = build_digest([run_id])
    assert digest["events"] == 2, digest
    assert digest["actionable_events"] == 2, digest
    assert all(item["action_type"] == "new_project_lead" for item in digest["items"]), digest
    assert "review-only" in digest["guard"].lower(), digest

print(
    f"v0.6 wind agents OK: {len(companies)} companies, {len(sources)} institutional nodes, "
    f"{len(plan.projects)} execution-watch projects, adapters={','.join(executable_agent_ids())}"
)
