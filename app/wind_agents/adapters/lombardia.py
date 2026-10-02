from __future__ import annotations

import hashlib
import re
from datetime import date
from urllib.parse import urljoin

import requests

from app.wind_agents.base import AgentFinding, BaseWindAgent


BASE_URL = "https://www.silvia.servizirl.it/silviaweb/"
PUBLIC_INFO_URL = "https://www.regione.lombardia.it/ambiente-e-territorio/valutazione-di-impatto-ambientale-via/sistema-informativo-lombardo-per-la-valutazione-di-impatto-ambientale-%28silvia%29"
TIPO_PROCEDURA_LIST = "1,2,3,5,15"
TARGET_SECTORS = {"2", "8"}
WIND_TERMS = (
    "eolico",
    "eolica",
    "parco eolico",
    "impianto eolico",
    "aerogenerator",
    "repowering",
)
PROVINCE_NAME_TO_CODE = {
    "bergamo": "BG",
    "brescia": "BS",
    "como": "CO",
    "cremona": "CR",
    "lecco": "LC",
    "lodi": "LO",
    "mantova": "MN",
    "milano": "MI",
    "monza": "MB",
    "monza e brianza": "MB",
    "pavia": "PV",
    "sondrio": "SO",
    "varese": "VA",
}


class LombardiaWindAgent(BaseWindAgent):
    """Wind adaptation of pv_agent_mvp's Regione Lombardia SILVIA API collector."""

    agent_name = "institutional_watch"
    source_name = "Regione Lombardia SILVIA"
    base_url = BASE_URL

    def __init__(self, years: list[int] | None = None) -> None:
        super().__init__()
        current = date.today().year
        self.years = years or [current, current - 1, current - 2]

    @staticmethod
    def _clean(value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @classmethod
    def _norm(cls, value: object) -> str:
        return cls._clean(value).lower().translate(str.maketrans("àèéìòù", "aeeiou"))

    @classmethod
    def _is_wind(cls, text: str) -> bool:
        norm = cls._norm(text)
        return any(term in norm for term in WIND_TERMS)

    @classmethod
    def _first(cls, row: dict, keys: list[str]) -> str | None:
        normalized = {cls._norm(k).replace(" ", ""): v for k, v in row.items()}
        for key in keys:
            value = row.get(key)
            if value in (None, ""):
                value = normalized.get(cls._norm(key).replace(" ", ""))
            if isinstance(value, (dict, list)) or value in (None, ""):
                continue
            text = cls._clean(value)
            if text:
                return text
        return None

    def _request_json(self, path: str, *, params: dict[str, str] | None = None) -> object:
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                response = self.session.get(
                    urljoin(BASE_URL, path),
                    params=params,
                    timeout=(8, 35),
                )
                response.raise_for_status()
                return response.json()
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
                last_error = exc
                # SILVIA intermittently returns HTTP 500 from otherwise healthy
                # endpoints. One immediate retry is enough to absorb a transient
                # without turning the daily radar into a long retry loop.
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Lombardia SILVIA request failed: {path}")

    def _load_sectors(self) -> list[str]:
        data = self._request_json("getAllSettori.html")
        if not isinstance(data, list):
            raise RuntimeError("Lombardia getAllSettori did not return a list")
        found: list[str] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            sector_id = row.get("idSettore") or row.get("id_settore") or row.get("id")
            if str(sector_id) in TARGET_SECTORS:
                found.append(str(sector_id))
        return sorted(set(found))

    def _search(self, sector_id: str, year: int) -> list[dict]:
        params = {
            "tipoProcedura": TIPO_PROCEDURA_LIST,
            "rgroupAutorita": "",
            "codiceProcedura": "",
            "descrProcedura": "",
            "idMacroStato": "",
            "interessati": "",
            "strFiltroEnte": "",
            "optionSettore": sector_id,
            "dataAvvioDa": "",
            "dataAvvioA": "",
            "dataDepositoDa": "",
            "dataDepositoA": "",
            "checkedAutorita": "",
            "checkedTipologiaProg": "",
            "tipoProponente": "",
            "idReferenteSelect": "",
            "descrProponente": "",
            "idTipoEnte": "",
            "idEnteACSelected": "",
            "accTipoEnte": "",
            "accTipoProc": "",
            "annoAvvio": str(year),
            "idSett": sector_id,
        }
        data = self._request_json("avviaRicercaProcedura.html", params=params)
        return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []

    @classmethod
    def _status(cls, row: dict) -> str | None:
        macro = row.get("macroStato")
        if isinstance(macro, dict):
            value = cls._clean(macro.get("descrMacroStato") or "")
            if value:
                return value
        return cls._first(row, ["descrMacroStato", "stato", "descrStato", "descStato"])

    @classmethod
    def _procedure(cls, row: dict) -> str | None:
        return cls._first(row, ["group", "descrTipoProcedura", "tipoProcedura", "descTipoProcedura", "proceduraTipo"])

    @classmethod
    def _proponent(cls, row: dict) -> str | None:
        return cls._first(
            row,
            ["proponenti", "proponente", "descrProponente", "descrEnteAzienda", "enteProponente", "referente", "richiedente"],
        )

    @classmethod
    def _province(cls, text: str) -> str | None:
        match = re.search(r"\b(BG|BS|CO|CR|LC|LO|MN|MI|MB|PV|SO|VA)\b|\((BG|BS|CO|CR|LC|LO|MN|MI|MB|PV|SO|VA)\)", text, flags=re.I)
        if match:
            return (match.group(1) or match.group(2)).upper()
        norm = cls._norm(text)
        for name, code in PROVINCE_NAME_TO_CODE.items():
            if name in norm:
                return code
        return None

    @classmethod
    def _municipalities(cls, title: str) -> list[str]:
        out: list[str] = []
        for pattern in (
            r"(?:nel|nei)\s+Comuni?\s+di\s+(.+?)(?:\s*\([A-Z]{2}\)|\.|;|$)",
            r"Comune\s+di\s+(.+?)(?:\s*\([A-Z]{2}\)|\.|;|$)",
        ):
            match = re.search(pattern, title, flags=re.I)
            if not match:
                continue
            raw = re.sub(r"\([A-Z]{2}\)", "", match.group(1))
            for part in re.split(r",|\s+e\s+|\s+ed\s+", raw, flags=re.I):
                item = cls._clean(part).strip(" -–—:;,.()")
                if item and item.lower() not in {x.lower() for x in out}:
                    out.append(item)
            break
        return out[:12]

    @classmethod
    def _power_mw(cls, text: str) -> float | None:
        for match in re.finditer(
            r"(?<![\d.,])([0-9]+(?:[.\s][0-9]{3})*(?:,[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(MWp|MW)\b",
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
    def _external_id(cls, row: dict, title: str) -> str:
        proc_id = row.get("idProgetto") or row.get("idProcedura") or row.get("id_procedura") or row.get("id") or row.get("idStudio")
        if proc_id:
            return f"LOMBARDIA-WIND-{proc_id}"
        raw = f"{title}|{cls._proponent(row) or ''}"
        return "LOMBARDIA-WIND-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:18]

    def _channel_snapshot(self, issue: object) -> AgentFinding:
        return AgentFinding(
            external_id="LOMBARDIA-SILVIA-CHANNEL",
            source_name=self.source_name,
            source_url=PUBLIC_INFO_URL,
            title="Regione Lombardia SILVIA - canale temporaneamente degradato",
            finding_type="source_channel_snapshot",
            payload={
                "region": "Lombardia",
                "project_specific": False,
                "source_grade_ceiling": "A1",
                "data_health": "channel_only",
                "availability_issue": self._clean(issue),
                "source_adapter_origin": "pv_agent_mvp/lombardia.py",
                "guard": "Temporary SILVIA source error; do not infer project absence.",
            },
        )

    def fetch(self) -> list[AgentFinding]:
        unique: dict[str, AgentFinding] = {}
        issues: list[str] = []
        try:
            sectors = self._load_sectors()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            return [self._channel_snapshot(f"{type(exc).__name__}: {exc}")]
        if not sectors:
            return [self._channel_snapshot("SILVIA target sectors 2/8 not returned")]

        for sector_id in sectors:
            for year in self.years:
                try:
                    rows = self._search(sector_id, year)
                except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
                    issues.append(
                        f"sector={sector_id} year={year}: {type(exc).__name__}: {exc}"
                    )
                    continue
                for row in rows:
                    title = self._first(
                        row,
                        ["descrProgetto", "descrProcedura", "titolo", "oggetto", "descrizione", "descProcedura", "nomeProcedura", "procedura"],
                    )
                    if not title or not self._is_wind(title):
                        continue
                    proponent = self._proponent(row)
                    status = self._status(row)
                    procedure = self._procedure(row)
                    proc_id = row.get("idProgetto") or row.get("idProcedura") or row.get("id_procedura") or row.get("id") or row.get("idStudio")
                    detail_url = urljoin(BASE_URL, f"#/scheda-sintesi/{proc_id}") if proc_id else BASE_URL
                    external_id = self._external_id(row, title)
                    if external_id in unique:
                        continue
                    combined = self._clean(" ".join(x for x in [title, proponent, status, procedure] if x))
                    unique[external_id] = AgentFinding(
                        external_id=external_id,
                        source_name=self.source_name,
                        source_url=detail_url,
                        title=title[:700],
                        finding_type="project_source",
                        payload={
                            "project_name": title[:700],
                            "proponent": proponent,
                            "region": "Lombardia",
                            "province": self._province(combined),
                            "municipalities": self._municipalities(title),
                            "power_mw": self._power_mw(combined),
                            "procedure": procedure,
                            "status_raw": status,
                            "source_year": year,
                            "sector_id": sector_id,
                            "sector": "eolico",
                            "source_grade_ceiling": "A1",
                            "project_specific": True,
                            "source_adapter_origin": "pv_agent_mvp/lombardia.py",
                        },
                    )
        if issues:
            unique["LOMBARDIA-SILVIA-CHANNEL"] = self._channel_snapshot("; ".join(issues))
        return list(unique.values())
