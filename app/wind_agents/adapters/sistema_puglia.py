from __future__ import annotations

import hashlib
import re
from io import BytesIO

from openpyxl import load_workbook

from app.wind_agents.base import AgentFinding, BaseWindAgent


XLSX_URL = (
    "https://dati.puglia.it/ckan/dataset/"
    "4af29dda-fdcc-4606-bf41-ad4fa3e30790/resource/"
    "1728acca-e2fc-4dcb-bb52-0fc1eaa628c2/download/via_fer.xlsx"
)
SOURCE_URL = "https://dati.puglia.it/ckan/dataset/impianti-proposti-via-fer"
WIND_TERMS = ("eolico", "eolica", "wind")


class SistemaPugliaWindAgent(BaseWindAgent):
    """Daily Puglia wind discovery from the official VIA FER dataset.

    This replaces the legacy sequential DettaglioInfo id probe. One dataset
    download gives the current regional inventory and makes daily execution
    bounded and deterministic.
    """

    agent_name = "institutional_watch"
    source_name = "Sistema Puglia Energia"
    base_url = SOURCE_URL

    @staticmethod
    def _clean(value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @classmethod
    def _header(cls, value: object) -> str:
        text = cls._clean(value).lower()
        for src, dst in (("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u")):
            text = text.replace(src, dst)
        return re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    @classmethod
    def _is_wind(cls, value: object) -> bool:
        text = cls._clean(value).lower()
        return any(term in text for term in WIND_TERMS)

    @classmethod
    def _power_mw(cls, value: object) -> float | None:
        text = cls._clean(value)
        if not text:
            return None
        match = re.search(r"[0-9]+(?:[.,][0-9]+)*", text)
        if not match:
            return None
        raw = match.group(0)
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
        elif "," in raw:
            raw = raw.replace(",", ".")
        try:
            power = float(raw)
        except ValueError:
            return None
        return power if 0 < power < 5000 else None

    @classmethod
    def _row_value(cls, row: dict[str, str], *keys: str) -> str | None:
        for key in keys:
            value = cls._clean(row.get(key) or "")
            if value:
                return value
        return None

    @classmethod
    def _external_id(cls, row: dict[str, str], *, province: str, municipality: str, source: str, power_mw: float | None) -> str:
        explicit = cls._row_value(
            row,
            "id", "id_progetto", "id_procedimento", "codice", "codice_pratica",
            "numero_pratica", "numero_procedimento", "procedimento",
        )
        if explicit:
            safe = re.sub(r"[^A-Za-z0-9._-]+", "-", explicit).strip("-")
            return f"PUGLIA-VIA-FER-{safe[:120]}"
        raw = "|".join([province, municipality, source, f"{power_mw:.6f}" if power_mw is not None else ""])
        return "PUGLIA-VIA-FER-" + hashlib.sha1(raw.lower().encode("utf-8")).hexdigest()[:20]

    def fetch(self) -> list[AgentFinding]:
        response = self.session.get(
            XLSX_URL,
            timeout=(8, 30),
            headers={"User-Agent": "Wind-Radar-Agent/0.6"},
        )
        response.raise_for_status()
        wb = load_workbook(BytesIO(response.content), read_only=True, data_only=True)
        ws = wb.active
        iterator = ws.iter_rows(values_only=True)
        raw_headers = next(iterator, None)
        if not raw_headers:
            return []
        headers = [self._header(value) for value in raw_headers]

        findings: list[AgentFinding] = []
        seen: set[str] = set()
        for values in iterator:
            row = {
                header: self._clean(values[index]) if index < len(values) and values[index] is not None else ""
                for index, header in enumerate(headers)
                if header
            }
            source = self._row_value(row, "fonte", "tipologia_fonte", "tecnologia") or ""
            if not self._is_wind(source):
                continue

            province = self._row_value(row, "provincia") or ""
            municipality = self._row_value(row, "comune", "municipio") or ""
            power_mw = self._power_mw(self._row_value(row, "potenza_mw", "potenza", "potenza_nominale"))
            status = self._row_value(row, "stato_del_procedimento", "stato", "esito")
            proponent = self._row_value(row, "proponente", "societa_proponente", "soggetto_proponente")
            project_name = self._row_value(row, "denominazione", "progetto", "oggetto", "nome_progetto")
            if not project_name:
                area = municipality or "Comune non indicato"
                if province:
                    area = f"{area} ({province})"
                project_name = f"Impianto eolico - {area}" + (f" - {power_mw:g} MW" if power_mw else "")

            external_id = self._external_id(
                row,
                province=province,
                municipality=municipality,
                source=source,
                power_mw=power_mw,
            )
            if external_id in seen:
                continue
            seen.add(external_id)

            findings.append(
                AgentFinding(
                    external_id=external_id,
                    source_name=self.source_name,
                    source_url=XLSX_URL,
                    title=project_name[:900],
                    finding_type="project_source",
                    payload={
                        "project_name": project_name[:900],
                        "proponent": proponent,
                        "region": "Puglia",
                        "province": province or None,
                        "municipalities": [municipality] if municipality else [],
                        "power_mw": power_mw,
                        "procedure": "VIA FER",
                        "status_raw": status,
                        "source_type": source,
                        "sector": "eolico",
                        "source_grade_ceiling": "A1",
                        "project_specific": True,
                        "source_adapter_origin": "pv_agent_mvp/puglia.py",
                        "ingestion_path": "official_via_fer_xlsx",
                    },
                )
            )

        return findings
