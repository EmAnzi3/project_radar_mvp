from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.wind_agents.base import AgentFinding, BaseWindAgent


BASE_URL = "http://valutazioneambientale.regione.basilicata.it/valutazioneambie/"
ENERGY_NOTICE_URL = "https://www.regione.basilicata.it/?temi-im=espropri%2Favviso-di-avvio-di-procedimento"
WP_SEARCH_URL = "https://www.regione.basilicata.it/wp-json/wp/v2/search"
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
            r"(?:comune|comuni)\s+(?:di|del|della|dei)?\s*(.+?)(?="
            r"\s+(?:con\s+relative|e\s+delle\s+relative|nonch[eé]|proponente|societ[aà]\s+proponente|"
            r"potenza|progressivo\s+interno|id\s+paur|data\s+di\s+pubblicazione)|"
            r"\.|;|\s+-\s+|$)",
            text,
            flags=re.I,
        ):
            segment = re.sub(r"\((?:PZ|MT)\)", "", cls._clean(match.group(1)), flags=re.I)
            for part in re.split(r",|/|\s+e\s+|\s+ed\s+", segment, flags=re.I):
                item = cls._clean(part).strip(" -–—:;,.()")
                if (
                    item
                    and 2 <= len(item) <= 80
                    and not re.search(r"\b(?:opere|infrastrutture|relative|connessione)\b", item, flags=re.I)
                    and item.lower() not in {v.lower() for v in values}
                ):
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

    def _energy_candidate_pages(self) -> list[tuple[str, str]]:
        """Discover official Basilicata energy-notice pages.

        Prefer the thematic Ufficio Energia page, then use the official
        WordPress search API as a discovery layer because the thematic page can
        render only a subset of notices depending on CMS state.
        """
        pages: list[tuple[str, str]] = []
        seen: set[str] = set()

        # Always inspect the thematic page itself.
        primary_error: Exception | None = None
        try:
            response = self.session.get(
                ENERGY_NOTICE_URL,
                timeout=(8, 25),
                headers={"User-Agent": "Wind-Radar-Agent/0.6"},
            )
            response.raise_for_status()
            primary_html = response.text
            pages.append((ENERGY_NOTICE_URL, primary_html))
            seen.add(ENERGY_NOTICE_URL)
            primary_text = self._clean(
                BeautifulSoup(primary_html, "html.parser").get_text(" ", strip=True)
            )
            primary_lower = primary_text.lower()
            if self._is_wind(primary_text) and any(
                token in primary_lower
                for token in ("autorizzazione unica", "paur", "p.a.u.r", "d.lgs 387")
            ):
                # The thematic page already exposes the current notice inventory
                # with project text. Do not fan out to detail/search pages.
                return pages
        except Exception as exc:
            primary_error = exc

        discovered_urls: list[str] = []
        for term in ("eolico", "PAUR eolico"):
            try:
                search = self.session.get(
                    WP_SEARCH_URL,
                    params={"search": term, "per_page": 12},
                    timeout=(8, 25),
                    headers={"User-Agent": "Wind-Radar-Agent/0.6"},
                )
                search.raise_for_status()
                payload = search.json()
            except Exception:
                continue
            if not isinstance(payload, list):
                continue
            for row in payload:
                if not isinstance(row, dict):
                    continue
                url = self._clean(row.get("url") or "")
                if not url.startswith("http") or url in seen or url in discovered_urls:
                    continue
                discovered_urls.append(url)
                if len(discovered_urls) >= 8:
                    break
            if len(discovered_urls) >= 8:
                break

        # Fetch only a bounded current discovery window. The raw thematic page
        # remains the primary source, while WP search is a resilience layer.
        for url in discovered_urls:
            seen.add(url)
            try:
                detail = self.session.get(
                    url,
                    timeout=(6, 12),
                    headers={"User-Agent": "Wind-Radar-Agent/0.6"},
                )
                detail.raise_for_status()
                pages.append((url, detail.text))
            except Exception:
                continue

        # HTML search fallback if the REST search is disabled/restricted.
        if len(pages) == 1:
            try:
                search = self.session.get(
                    "https://www.regione.basilicata.it/",
                    params={"s": "eolico"},
                    timeout=(8, 25),
                    headers={"User-Agent": "Wind-Radar-Agent/0.6"},
                )
                search.raise_for_status()
                soup = BeautifulSoup(search.text, "html.parser")
                for anchor in soup.find_all("a", href=True):
                    url = urljoin(str(search.url), anchor.get("href") or "")
                    label = self._clean(anchor.get_text(" ", strip=True))
                    if url in seen or not url.startswith("https://www.regione.basilicata.it/"):
                        continue
                    if not self._is_wind(label):
                        continue
                    seen.add(url)
                    try:
                        detail = self.session.get(url, timeout=(8, 25))
                        detail.raise_for_status()
                        pages.append((url, detail.text))
                    except Exception:
                        continue
            except Exception:
                pass

        if not pages and primary_error is not None:
            raise primary_error
        return pages

    def _fetch_energy_notices(self) -> list[AgentFinding]:
        """Regional AU/PAUR/public-utility wind notices from Ufficio Energia."""
        findings: list[AgentFinding] = []
        seen: set[str] = set()

        for page_url, html_page in self._energy_candidate_pages():
            soup = BeautifulSoup(html_page, "html.parser")
            full_text = self._clean(soup.get_text(" ", strip=True))
            if not full_text:
                continue

            # A thematic listing may contain many publications; a detail page is
            # naturally one block. Splitting on publication markers works for both.
            blocks = re.split(
                r"(?=Data\s+di\s+pubblicazione\s*:)",
                full_text,
                flags=re.I,
            )
            if len(blocks) == 1:
                blocks = [full_text]

            for block in blocks:
                text = self._clean(block)
                lowered = text.lower()
                if len(text) < 80 or not self._is_wind(text):
                    continue
                if not any(token in lowered for token in (
                    "autorizzazione unica", "paur", "p.a.u.r",
                    "d. lgs. 387", "d.lgs 387", "d.lgs. 387",
                )):
                    continue

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
                    external_id = "BASILICATA-ENERGY-ACT-" + hashlib.sha1(
                        f"{page_url}|{text}".encode("utf-8")
                    ).hexdigest()[:18]

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
                        source_url=page_url,
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
        try:
            return self._fetch_energy_notices()
        except (requests.ConnectionError, requests.Timeout) as exc:
            return [
                AgentFinding(
                    external_id="BASILICATA-ENERGY-CHANNEL",
                    source_name=self.source_name,
                    source_url=ENERGY_NOTICE_URL,
                    title="Regione Basilicata Ufficio Energia - canale AU/PAUR temporaneamente non raggiungibile",
                    finding_type="source_channel_snapshot",
                    payload={
                        "region": "Basilicata",
                        "project_specific": False,
                        "source_grade_ceiling": "A1",
                        "data_health": "channel_only",
                        "availability_issue": f"{type(exc).__name__}: {exc}",
                        "source_adapter_origin": "regional_basilicata_energy_notices",
                    },
                )
            ]
