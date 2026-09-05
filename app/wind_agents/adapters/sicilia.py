from __future__ import annotations

import csv
import hashlib
import io
import re

from app.wind_agents.base import AgentFinding, BaseWindAgent


CSV_URL = (
    "https://dati.regione.sicilia.it/download/dataset/"
    "progetti-sottoposti-valutazione-ambientale/filesystem/"
    "progetti-sottoposti-valutazione-ambientale_csv.csv"
)
SOURCE_URL = "https://si-vvi.regione.sicilia.it/viavas/"
WIND_TERMS = ("eolico", "eolica", "aerogenerator", "repowering", "parco eolico")


class SiciliaWindAgent(BaseWindAgent):
    """Wind adaptation of pv_agent_mvp's Sicilia collector.

    The mature PV collector uses the same official regional CSV plus optional
    SI-VVI/GIS enrichment. This first wind adapter keeps the stable official CSV
    ingestion and project/detail identifiers; GIS enrichment remains a later
    additive pass and is not required to emit a finding.
    """

    agent_name = "institutional_watch"
    source_name = "Regione Sicilia SI-VVI"
    base_url = SOURCE_URL

    @staticmethod
    def _clean(value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @classmethod
    def _column(cls, value: object) -> str:
        text = cls._clean(value).lower()
        text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
        return text

    @classmethod
    def _is_wind(cls, text: str) -> bool:
        lowered = cls._clean(text).lower()
        return any(term in lowered for term in WIND_TERMS)

    @classmethod
    def _power_mw(cls, text: str) -> float | None:
        for match in re.finditer(
            r"(?<![\d.,])([0-9]+(?:[.\s][0-9]{3})*(?:,[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*MW\b",
            text,
            flags=re.I,
        ):
            raw = match.group(1).replace(" ", "")
            if "," in raw:
                raw = raw.replace(".", "").replace(",", ".")
            try:
                value = float(raw)
            except ValueError:
                continue
            if 0 < value < 5000:
                return value
        return None

    @classmethod
    def _province(cls, text: str) -> str | None:
        match = re.search(r"\(([A-Z]{2})\)", text)
        if match:
            return match.group(1)
        for code in ("AG", "CL", "CT", "EN", "ME", "PA", "RG", "SR", "TP"):
            if re.search(rf"\b{code}\b", text):
                return code
        return None

    @classmethod
    def _municipality(cls, text: str) -> str | None:
        for pattern in (
            r"comune\s+di\s+([A-ZÀ-Ú][A-Za-zÀ-Úà-ú'’\- ]+?)(?:\s*\([A-Z]{2}\)|,|;|\.|\s+e\s+|$)",
            r"comune\s*:?\s*([A-ZÀ-Ú][A-Za-zÀ-Úà-ú'’\- ]+?)(?:\s+provincia|\s*\([A-Z]{2}\)|,|;|\||$)",
        ):
            match = re.search(pattern, text, flags=re.I)
            if match:
                value = cls._clean(match.group(1)).strip(" .,:;")
                if value:
                    return value
        return None

    @staticmethod
    def _external_id(code: str | None, title: str, detail_url: str) -> str:
        if code:
            return f"SICILIA-SIVVI-{code}"
        raw = title + "|" + detail_url
        return "SICILIA-SIVVI-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:18]

    def fetch(self) -> list[AgentFinding]:
        response = self.session.get(
            CSV_URL,
            timeout=120,
            headers={"User-Agent": "Wind-Radar-Agent/0.6"},
        )
        response.raise_for_status()
        text = response.content.decode("utf-8-sig", errors="replace")

        reader = csv.DictReader(
            io.StringIO(text),
            delimiter=";",
            quotechar='"',
            escapechar="\\",
            doublequote=True,
        )

        findings: list[AgentFinding] = []
        seen: set[str] = set()
        for raw_row in reader:
            row = {
                self._column(key): self._clean(value)
                for key, value in raw_row.items()
                if key is not None
            }
            title = self._clean(
                row.get("procedura_progetto_oggetto")
                or row.get("oggetto")
                or row.get("titolo")
                or ""
            )
            title = re.sub(r"https?://\S+", "", title).strip(" ;")
            if not title or not self._is_wind(title):
                continue

            code = self._clean(row.get("procedura_codice") or row.get("codice") or "") or None
            detail_url = self._clean(row.get("procedura_url") or row.get("url") or "")
            if not detail_url.startswith("http"):
                url_match = re.search(r"https?://[^\s;\"']+", title)
                detail_url = url_match.group(0) if url_match else CSV_URL

            external_id = self._external_id(code, title, detail_url)
            if external_id in seen:
                continue
            seen.add(external_id)

            proponent = self._clean(
                row.get("proponente_progetto")
                or row.get("proponente")
                or ""
            ) or None
            procedure = self._clean(
                row.get("procedura_tipologia")
                or row.get("tipologia")
                or row.get("procedura")
                or ""
            ) or None
            status = self._clean(row.get("stato") or row.get("status") or "") or None
            municipality = self._municipality(title)

            findings.append(
                AgentFinding(
                    external_id=external_id,
                    source_name=self.source_name,
                    source_url=detail_url,
                    title=title[:900],
                    finding_type="project_source",
                    payload={
                        "project_name": title[:900],
                        "proponent": proponent,
                        "region": "Sicilia",
                        "province": self._province(title),
                        "municipality": municipality,
                        "power_mw": self._power_mw(title),
                        "procedure": procedure,
                        "status_raw": status,
                        "source_code": code,
                        "latitude": row.get("latitudine") or None,
                        "longitude": row.get("longitudine") or None,
                        "sector": "eolico",
                        "source_grade_ceiling": "A1",
                        "project_specific": True,
                        "source_adapter_origin": "pv_agent_mvp/sicilia.py",
                        "enrichment_note": "Official CSV adapter; SI-VVI detail/GIS enrichment remains additive work.",
                    },
                )
            )

        return findings
