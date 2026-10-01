from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.wind_agents.base import AgentFinding, BaseWindAgent


BASE_URL = "http://valutazioneambientale.regione.basilicata.it/valutazioneambie/"
ENERGY_NOTICE_URL = "https://www.regione.basilicata.it/?temi-im=espropri%2Favviso-di-avvio-di-procedimento"
START_URLS = (
    (urljoin(BASE_URL, "section.jsp?sec=100002"), "Screening"),
    (urljoin(BASE_URL, "section.jsp?sec=145352"), "Screening - 2025"),
    (urljoin(BASE_URL, "section.jsp?sec=150868"), "Screening - 2026"),
    (urljoin(BASE_URL, "section.jsp?sec=100003"), "VIA regionale"),
    (urljoin(BASE_URL, "section.jsp?sec=145351"), "VIA regionale - 2025"),
    (urljoin(BASE_URL, "section.jsp?sec=150867"), "VIA regionale - 2026"),
)
WIND_TERMS = ("eolico", "eolica", "aerogenerator", "repowering", "parco eolico")


class BasilicataWindAgent(BaseWindAgent):
    """Wind adaptation of pv_agent_mvp's Basilicata VIA/Screening collector."""

    agent_name = "institutional_watch"
    source_name = "Regione Basilicata VIA/Screening"
    base_url = BASE_URL

    @staticmethod
    def _clean(value: object) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    @classmethod
    def _is_wind(cls, value: object) -> bool:
        text = cls._clean(value).lower()
        return any(term in text for term in WIND_TERMS)

    def _get_html(self, url: str) -> str | None:
        try:
            response = self.session.get(
                url,
                headers={
                    "User-Agent": "Wind-Radar-Agent/0.6",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                    "Referer": BASE_URL,
                    "Connection": "close",
                },
                timeout=(8, 20),
                allow_redirects=True,
            )
            response.raise_for_status()
            return response.content.decode("utf-8", errors="replace")
        except Exception:
            return None

    @classmethod
    def _power_mw(cls, text: str) -> float | None:
        for match in re.finditer(
            r"(?<![\d.,])([0-9]+(?:[.\s][0-9]{3})*(?:[,\.]\d+)?|[0-9]+(?:[,\.]\d+)?)\s*(MW|MWe)\b",
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
    def _municipalities(cls, text: str) -> list[str]:
        values: list[str] = []
        for match in re.finditer(
            r"(?:comune|comuni)\s+(?:di|del|della|dei)?\s*(.+?)(?:\s*\((?:PZ|MT)\)|\.|;|\s+-\s+|$)",
            text,
            flags=re.I,
        ):
            segment = cls._clean(match.group(1))
            for part in re.split(r",|/|\s+e\s+", segment, flags=re.I):
                item = cls._clean(part).strip(" -–—:;,.()")
                if item and 2 <= len(item) <= 80 and item.lower() not in {v.lower() for v in values}:
                    values.append(item)
            if values:
                break
        return values[:12]

    @staticmethod
    def _province(text: str, municipalities: list[str]) -> str | None:
        match = re.search(r"\b(PZ|MT)\b|\((PZ|MT)\)", text, flags=re.I)
        if match:
            return (match.group(1) or match.group(2)).upper()
        # Preserve only a tiny verified fallback map inherited from the PV agent.
        pz = {"banzi", "genzano di lucania", "maschito", "melfi", "montemilone", "oppido lucano", "palazzo san gervasio", "tito", "tolve", "venosa"}
        mt = {"bernalda", "colobraro", "ferrandina", "grottole", "montescaglioso", "pomarico"}
        for municipality in municipalities:
            key = municipality.lower()
            if key in pz:
                return "PZ"
            if key in mt:
                return "MT"
        return None

    @classmethod
    def _proponent(cls, text: str) -> str | None:
        for pattern in (
            r"Proponente\s*:?\s*(.+?)(?:\s+Comune|\s+Localizz|\s+Proced|\s+Potenza|\s+Progressivo\s+Interno|\s+ID\s+PAUR|\s+Data\s+di\s+pubblicazione|\||$)",
            r"Societ[aà]\s+proponente\s*:?\s*(.+?)(?:\s+Comune|\s+Localizz|\s+Proced|\s+Potenza|\s+Progressivo\s+Interno|\s+ID\s+PAUR|\s+Data\s+di\s+pubblicazione|\||$)",
            r"Societ[aà]\s+(.+?)(?:\s+ha\s+presentato|\s+ha\s+depositato|\s+richiede|\||$)",
        ):
            match = re.search(pattern, text, flags=re.I)
            if match:
                item = cls._clean(match.group(1)).strip(" -–—:;,.")
                if 2 <= len(item) <= 220:
                    return item
        return None

    @staticmethod
    def _external_id(url: str) -> str:
        return "BASILICATA-WIND-" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:18]

    @classmethod
    def _project_name(cls, text: str, fallback: str) -> str:
        for pattern in (
            r"denominat[oa]\s+[“\"']([^”\"']+)[”\"']",
            r"parco\s+eolico\s+[“\"']([^”\"']+)[”\"']",
            r"impianto\s+eolico\s+[“\"']([^”\"']+)[”\"']",
        ):
            match = re.search(pattern, text, flags=re.I)
            if match:
                return cls._clean(match.group(1))[:900]
        return cls._clean(fallback)[:900]

    def _fetch_energy_notices(self) -> list[AgentFinding]:
        """Regional AU/PAUR/public-utility wind notices from Ufficio Energia."""
        html_page = self._get_html(ENERGY_NOTICE_URL)
        if not html_page:
            return []
        soup = BeautifulSoup(html_page, "html.parser")
        full_text = self._clean(soup.get_text(" ", strip=True))
        if not full_text:
            return []

        findings: list[AgentFinding] = []
        seen: set[str] = set()
        blocks = re.split(
            r"(?=Data\s+di\s+pubblicazione\s*:)",
            full_text,
            flags=re.I,
        )

        for block in blocks:
            text = self._clean(block)
            lowered = text.lower()
            if len(text) < 80 or not self._is_wind(text):
                continue
            if not any(token in lowered for token in ("autorizzazione unica", "paur", "p.a.u.r", "d. lgs. 387", "d.lgs 387", "d.lgs. 387")):
                continue

            # Stop each publication block before the next unrelated metadata area.
            proponent = self._proponent(text)
            power_mw = self._power_mw(text)
            municipalities = self._municipalities(text)
            title = self._project_name(text, text)

            progressivo = re.search(r"Progressivo\s+Interno\s*:\s*([A-Za-z0-9._/-]+)", text, flags=re.I)
            paur_id = re.search(r"ID\s+PAUR\s*:\s*([A-Za-z0-9._/-]+)", text, flags=re.I)
            pub_code = re.search(r"Codice\s+di\s+pubblicazione\s*:?\s*([A-Za-z0-9._/-]+)", text, flags=re.I)
            stable_code = (
                progressivo.group(1) if progressivo else
                paur_id.group(1) if paur_id else
                pub_code.group(1) if pub_code else
                None
            )
            if stable_code:
                safe_code = re.sub(r"[^A-Za-z0-9._-]+", "-", stable_code).strip("-")
                external_id = f"BASILICATA-ENERGY-{safe_code}"
            elif proponent and municipalities and power_mw:
                identity = "|".join([
                    self._clean(title).lower(),
                    self._clean(proponent).lower(),
                    "|".join(sorted(self._clean(x).lower() for x in municipalities)),
                    f"{power_mw:.4f}",
                ])
                external_id = "BASILICATA-ENERGY-" + hashlib.sha1(identity.encode("utf-8")).hexdigest()[:20]
            else:
                external_id = "BASILICATA-ENERGY-ACT-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:18]

            if external_id in seen:
                continue
            seen.add(external_id)

            date_match = re.search(
                r"Data\s+di\s+pubblicazione\s*:\s*(\d{1,2}/\d{1,2}/20\d{2})",
                text,
                flags=re.I,
            )
            procedure = "PAUR / Autorizzazione Unica" if ("paur" in lowered or "p.a.u.r" in lowered) else "Autorizzazione Unica"
            if "proroga" in lowered:
                procedure = "Proroga AU/PAUR"

            findings.append(
                AgentFinding(
                    external_id=external_id,
                    source_name="Regione Basilicata Ufficio Energia",
                    source_url=ENERGY_NOTICE_URL,
                    title=title,
                    finding_type="project_source",
                    payload={
                        "project_name": title,
                        "proponent": proponent,
                        "region": "Basilicata",
                        "province": self._province(text, municipalities),
                        "municipalities": municipalities,
                        "power_mw": power_mw,
                        "procedure": procedure,
                        "status_raw": text[:1800],
                        "source_date": date_match.group(1) if date_match else None,
                        "publication_code": pub_code.group(1) if pub_code else None,
                        "paur_id": paur_id.group(1) if paur_id else None,
                        "progressivo_interno": progressivo.group(1) if progressivo else None,
                        "sector": "eolico",
                        "source_grade_ceiling": "A1",
                        "project_specific": True,
                        "source_adapter_origin": "regional_basilicata_energy_notices",
                        "ingestion_path": "official_ufficio_energia_au_paur",
                    },
                )
            )
        return findings

    def fetch(self) -> list[AgentFinding]:
        unique: dict[str, AgentFinding] = {}
        for page_url, procedure in START_URLS:
            html_page = self._get_html(page_url)
            if not html_page:
                continue
            soup = BeautifulSoup(html_page, "html.parser")
            for h2 in soup.find_all("h2"):
                anchor = h2.find("a", href=True)
                if not anchor:
                    continue
                title = self._clean(anchor.get_text(" ", strip=True))
                subtitle_node = h2.find_next_sibling("p")
                subtitle = self._clean(subtitle_node.get_text(" ", strip=True)) if subtitle_node else ""
                combined = self._clean(f"{title} {subtitle}")
                if not title or not self._is_wind(combined):
                    continue
                detail_url = urljoin(page_url, anchor.get("href") or "")

                # Read detail when available: this often carries proponent/location
                # omitted by the list page, but failure does not discard the source hit.
                detail_html = self._get_html(detail_url)
                detail_text = ""
                if detail_html:
                    detail_text = self._clean(BeautifulSoup(detail_html, "html.parser").get_text(" ", strip=True))
                evidence_text = self._clean(f"{combined} {detail_text}")
                municipalities = self._municipalities(evidence_text)
                proponent = self._proponent(evidence_text)
                external_id = self._external_id(detail_url)
                unique.setdefault(
                    external_id,
                    AgentFinding(
                        external_id=external_id,
                        source_name=self.source_name,
                        source_url=detail_url,
                        title=title[:900],
                        finding_type="project_source",
                        payload={
                            "project_name": title[:900],
                            "proponent": proponent,
                            "region": "Basilicata",
                            "province": self._province(evidence_text, municipalities),
                            "municipalities": municipalities,
                            "power_mw": self._power_mw(evidence_text),
                            "procedure": procedure,
                            "status_raw": procedure,
                            "sector": "eolico",
                            "source_grade_ceiling": "A1",
                            "project_specific": True,
                            "source_adapter_origin": "pv_agent_mvp/basilicata.py",
                        },
                    ),
                )
        return list(unique.values())


class BasilicataEnergyWindAgent(BasilicataWindAgent):
    """Independent Ufficio Energia AU/PAUR source with its own bootstrap."""

    source_name = "Regione Basilicata Ufficio Energia"
    base_url = ENERGY_NOTICE_URL

    def fetch(self) -> list[AgentFinding]:
        return self._fetch_energy_notices()
