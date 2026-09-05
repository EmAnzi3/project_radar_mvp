from __future__ import annotations

from app.collectors.mase_via import collect_mase_via
from app.wind_agents.base import AgentFinding, BaseWindAgent


class MaseWindAgent(BaseWindAgent):
    """Wind-only adapter around the existing MASE collector.

    The underlying collector remains shared with the legacy Project Radar, while
    the agent constrains discovery to eolico/repowering/offshore terms and emits
    source findings instead of writing canonical data directly.
    """

    agent_name = "institutional_watch"
    source_name = "MASE VIA"
    base_url = "https://va.mite.gov.it"

    keywords = [
        "eolico",
        "parco eolico",
        "repowering eolico",
        "eolico offshore",
        "aerogeneratori",
    ]

    def __init__(self, max_pages_per_keyword: int = 2, max_details: int = 120) -> None:
        super().__init__()
        self.max_pages_per_keyword = max_pages_per_keyword
        self.max_details = max_details

    def fetch(self) -> list[AgentFinding]:
        records = collect_mase_via(
            keywords=self.keywords,
            max_pages_per_keyword=self.max_pages_per_keyword,
            max_details=self.max_details,
        )

        findings: list[AgentFinding] = []
        for record in records:
            if (record.sector or "").lower() != "eolico":
                continue
            external_id = record.external_id or record.source_url or record.title
            findings.append(
                AgentFinding(
                    external_id=str(external_id),
                    source_name=self.source_name,
                    source_url=record.source_url,
                    title=record.title,
                    finding_type="project_source",
                    payload={
                        "project_name": record.title,
                        "proponent": record.client,
                        "region": record.region,
                        "province": record.province,
                        "municipality": record.municipality,
                        "power_mw": record.power_mw,
                        "phase": record.phase,
                        "sector": record.sector,
                        "description": record.description,
                        "source_grade_ceiling": "A1",
                        "project_specific": True,
                    },
                )
            )

        return findings
