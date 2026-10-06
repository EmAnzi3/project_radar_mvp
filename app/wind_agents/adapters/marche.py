from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.wind_agents.base import AgentFinding, BaseWindAgent


BASE_URL = "https://monitoraggivia.regione.marche.it/sitoregionale/avvisiregionale.aspx"
STATE_URL = "https://monitoraggivia.regione.marche.it/sitoregionale/avvisistatali.aspx"
REGISTRY_URLS = (
    (BASE_URL, "VIA regionale"),
    (STATE_URL, "VIA statale"),
)
WIND_TERMS = ("eolico", "eolica", "aerogenerator", "parco eolico", "repowering")
PROVINCE_REGION = {
    "AN": "Marche", "AP": "Marche", "FM": "Marche", "MC": "Marche", "PU": "Marche",
    "AR": "Toscana",
    "PG": "Umbria", "TR": "Umbria",
    "RN": "Emilia-Romagna", "FC": "Emilia-Romagna",
    "TE": "Abruzzo", "AQ": "Abruzzo",
}


class MarcheWindAgent(BaseWindAgent):
    """Regione Marche public VIA-start registry filtered to wind projects.

    The regional portal can reject automated runners with HTTP 403 even when the
    public page is otherwise available to a browser. In that case the adapter
    emits an explicit non-project channel snapshot instead of failing the whole
    source group or pretending that project rows were collected.
    """

    agent_name = "institutional_watch"
    source_name = "Regione Marche VIA"
    base_url = BASE_URL
    baseline_revision = "marche-monitoraggivia-v2-geography-cleanup"

    @staticmethod
    def _clean(value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @classmethod
    def _is_wind(cls, text: str) -> bool:
        lowered = cls._clean(text).lower()
        return any(term in lowered for term in WIND_TERMS)

    @staticmethod
    def _power_mw(text: str) -> float | None:
        match = re.search(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*MW\b", text, flags=re.I)
        if not match:
            return None
        try:
            value = float(match.group(1).replace(",", "."))
        except ValueError:
            return None
        return value if 0 < value < 5000 else None

    @classmethod
    def _proponent(cls, text: str) -> str | None:
        match = re.search(r"\bProponente\s*:\s*(.+?)(?=(?:\.|\s+Comunicazione\b|\s+Tipo\s+protocollo\b|$))", text, flags=re.I)
        if not match:
            return None
        return cls._clean(match.group(1)).strip(" .,:;–—-")[:250] or None

    @classmethod
    def _municipalities(cls, text: str) -> list[str]:
        out: list[str] = []
        text = re.sub(r"\[[^\]]+\]", " ", text)
        patterns = [
            r"\bComuni\s+di\s+(.+?)(?=\.\s|\s+Restart\b|\s+Procedimento\b|\s+Proponente\b|\s+denominat[oa]\b|$)",
            r"\bComune\s+di\s+(.+?)(?=\.\s|\s+Proponente\b|\s+denominat[oa]\b|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if not match:
                continue
            raw = re.sub(r"\([^)]*\)", "", match.group(1))
            for part in re.split(r",|\s+e\s+|;", raw, flags=re.I):
                item = cls._clean(part).strip(" -–—:;,.()")
                item = re.split(
                    r"\s+(?:cavidotto|cabina|relative\s+opere|opere\s+di\s+connessione)\b",
                    item,
                    maxsplit=1,
                    flags=re.I,
                )[0].strip(" -–—:;,.()")
                if item and len(item) <= 80 and item.lower() not in {x.lower() for x in out}:
                    out.append(item)
            if out:
                break
        return out[:20]

    @classmethod
    def _province_codes(cls, text: str) -> list[str]:
        out: list[str] = []
        for code in re.findall(r"\(([A-Z]{2})\)", text):
            if code in PROVINCE_REGION and code not in out:
                out.append(code)
        return out

    @classmethod
    def _province(cls, text: str) -> str | None:
        codes = cls._province_codes(text)
        return " / ".join(codes) if codes else None

    @classmethod
    def _region(cls, text: str, procedure_label: str) -> str | None:
        regions: list[str] = []
        for code in cls._province_codes(text):
            region = PROVINCE_REGION[code]
            if region not in regions:
                regions.append(region)
        if regions:
            return " / ".join(regions)
        return "Marche" if procedure_label == "VIA regionale" else None

    @classmethod
    def _procedure(cls, text: str) -> str | None:
        lowered = text.lower()
        if "27-bis" in lowered or "27bis" in lowered or "paur" in lowered:
            return "PAUR"
        if "verifica di assoggettabil" in lowered or "art.19" in lowered or "art. 19" in lowered:
            return "Verifica di assoggettabilità a VIA"
        if "valutazione di impatto ambientale" in lowered or "procedimento di via" in lowered:
            return "VIA"
        return None

    @classmethod
    def _external_id(cls, text: str) -> str:
        for pattern in (r"\((V\d{4,6})\)", r"\[ID\s*:?\s*(\d+)\]", r"\b(ID\d{4,8})\b"):
            match = re.search(pattern, text, flags=re.I)
            if match:
                return "MARCHE-VIA-" + re.sub(r"[^A-Za-z0-9]+", "-", match.group(1).upper()).strip("-")
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:18]
        return f"MARCHE-VIA-{digest}"

    def _get(self, url: str) -> BeautifulSoup:
        response = self.session.get(
            url,
            timeout=60,
            allow_redirects=True,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "it-IT,it;q=0.9,en;q=0.7",
                "Referer": "https://www.regione.marche.it/",
            },
        )
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _channel_snapshot(self, *, primary_error: str | None = None) -> AgentFinding:
        return AgentFinding(
            external_id="MARCHE-VIA-CHANNEL",
            source_name=self.source_name,
            source_url=BASE_URL,
            title="Regione Marche — Monitoraggio VIA",
            finding_type="source_channel_snapshot",
            payload={
                "region": "Marche",
                "sector": "eolico",
                "source_grade_ceiling": "A1",
                "project_specific": False,
                "execution_scope": None,
                "evidence_layer": "institutional_channel",
                "availability": "degraded_primary_unavailable" if primary_error else "channel_only",
                "primary_url": BASE_URL,
                "primary_fetch_error": primary_error,
                "runtime_note": (
                    "No wind project rows were collected from the official Monitoraggio VIA "
                    "regional/state registries in this run."
                ),
            },
        )

    @classmethod
    def _row_external_id(cls, code: str | None, description: str) -> str:
        if code:
            safe = re.sub(r"[^A-Za-z0-9_-]+", "-", code.upper()).strip("-")
            if safe:
                return f"MARCHE-VIA-{safe}"
        return cls._external_id(description)

    def _registry_findings(self, url: str, procedure_label: str) -> list[AgentFinding]:
        soup = self._get(url)
        rows: list[AgentFinding] = []
        for tr in soup.find_all("tr"):
            cells = [self._clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
            if len(cells) < 5:
                continue

            proponent, description, publication_date, deadline, code = cells[:5]
            searchable = self._clean(f"{proponent} {description}")
            if not description or not self._is_wind(searchable):
                continue

            source_url = url
            for anchor in tr.find_all("a", href=True):
                label = self._clean(anchor.get_text(" ", strip=True)).lower()
                if "avviso" in label:
                    source_url = urljoin(url, anchor.get("href") or "")
                    break

            external_id = self._row_external_id(code, description)
            rows.append(
                AgentFinding(
                    external_id=external_id,
                    source_name=self.source_name,
                    source_url=source_url,
                    title=description[:700],
                    finding_type="project_source",
                    payload={
                        "project_name": description[:700],
                        "proponent": proponent or None,
                        "region": self._region(description, procedure_label),
                        "province": self._province(description),
                        "municipalities": self._municipalities(description),
                        "power_mw": self._power_mw(description),
                        "procedure": procedure_label,
                        "status_raw": "Avviso/pubblicazione procedimento",
                        "practice_code": code or None,
                        "publication_date": publication_date or None,
                        "observation_deadline": deadline or None,
                        "sector": "eolico",
                        "source_grade_ceiling": "A1",
                        "project_specific": True,
                        "source_adapter_origin": "monitoraggivia.regione.marche.it",
                    },
                )
            )
        return rows

    def fetch(self) -> list[AgentFinding]:
        last_errors: list[str] = []

        # The official ASP.NET registry occasionally returns an empty/transient
        # response to automated clients while succeeding immediately afterwards.
        # It is a cheap source (~1-2 s), so retry the whole two-registry cycle once
        # before degrading to a channel snapshot.
        for _attempt in range(2):
            findings: dict[str, AgentFinding] = {}
            errors: list[str] = []

            for url, procedure_label in REGISTRY_URLS:
                try:
                    rows = self._registry_findings(url, procedure_label)
                except Exception as exc:
                    errors.append(f"{procedure_label}: {type(exc).__name__}: {exc}")
                    continue

                # The registries can repeat the same practice when a new notice is
                # published. Keep the first/current row for a stable project identity.
                for finding in rows:
                    findings.setdefault(finding.external_id, finding)

            if findings:
                return list(findings.values())
            last_errors = errors

        return [self._channel_snapshot(primary_error="; ".join(last_errors) if last_errors else None)]
