"""Isolated Crawl4AI experiment: MASE landing page -> links/PDF -> evidenced findings.

No write to canonical projects. Requires Python 3.10+ and Crawl4AI/browser setup.
"""
import argparse
import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.processors.pdf import PDFCrawlerStrategy, PDFContentScrapingStrategy

FIELDS = {
    "power_mw": r"\\b\\d{1,4}(?:[.,]\\d+)?\\s*MW\\b",
    "turbines": r"\\b(?:aerogeneratori|turbine|WTG)\\b",
    "developers": r"\\b(?:proponente|societ[aà] proponente|committente)\\b",
    "engineering": r"\\b(?:progettist[ao]|progettazione|direzione lavori)\\b",
    "contractors": r"\\b(?:appaltator[ei]|affidatari[ao]|EPC|BoP|fornitore|aggiudicatari[ao])\\b",
    "schedule": r"\\b(?:cronoprogramma|inizio lavori|fine lavori|entrata in esercizio|commissioning|mesi)\\b",
    "authorization": r"\\b(?:VIA|PAUR|autorizzazione unica|ottemperanza|decreto)\\b",
}
PATTERNS = {key: re.compile(pattern, re.I) for key, pattern in FIELDS.items()}

def normalized_link(href, base):
    url, _ = urldefrag(urljoin(base, href or ""))
    p = urlparse(url)
    return url if p.scheme == "https" and p.hostname else None

def is_allowed(url, domains):
    host = (urlparse(url).hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in domains)

def snippets(markdown, url, kind):
    lines = markdown.splitlines()
    findings = []
    for index, line in enumerate(lines):
        for field, pattern in PATTERNS.items():
            if pattern.search(line):
                excerpt = " ".join(lines[max(0,index-1):min(len(lines),index+2)]).strip()
                findings.append({
                    "field": field, "excerpt": excerpt[:650],
                    "source_url": url, "document_type": kind,
                    "line_number_in_extracted_text": index + 1,
                    "status": "candidate_not_verified"
                })
    return findings

async def run(args):
    root = normalized_link(args.url, args.url)
    if not root:
        raise ValueError("A public HTTPS URL is required")
    root_domain = (urlparse(root).hostname or "").lower()
    allowed = sorted(set([root_domain] + [d.strip().lower() for d in args.allow_domain]))
    report = {
        "project_label": args.project, "starting_url": root,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "allowed_domains": allowed, "status": "review_only",
        "visited_pages": [], "attachments": [], "findings": [], "failures": [],
        "limitations": ["Text hits are candidates, not validated project-specific evidence.",
                        "PDF text extraction is not proof all diagrams, tables or scanned pages were read.",
                        "Line numbers refer to extracted text, not original PDF pages."]
    }
    queue = [root]
    visited = set()
    pdfs = []
    page_config = CrawlerRunConfig(page_timeout=45000)
    async with AsyncWebCrawler() as crawler:
        while queue and len(visited) < args.max_pages:
            url = queue.pop(0)
            if url in visited or not is_allowed(url, allowed):
                continue
            visited.add(url)
            try:
                result = await crawler.arun(url=url, config=page_config)
                if not result.success:
                    raise RuntimeError(str(result.error_message))
                markdown = str(result.markdown or "")
                report["visited_pages"].append({"url": url, "sha256_extracted_text": hashlib.sha256(markdown.encode()).hexdigest()})
                report["findings"].extend(snippets(markdown, url, "html"))
                links = []
                for group in (result.links or {}).values():
                    links.extend(group)
                for item in links:
                    href = normalized_link(item.get("href", ""), url)
                    if not href or not is_allowed(href, allowed):
                        continue
                    if urlparse(href).path.lower().endswith(".pdf"):
                        if href not in pdfs:
                            pdfs.append(href)
                    elif href not in visited and href not in queue and len(queue) < args.max_pages * 5:
                        queue.append(href)
            except Exception as exc:
                report["failures"].append({"url": url, "phase": "html", "error": str(exc)[:300]})
    # PDF crawler requires a dedicated crawler + scraping strategy; HTML page PDF capture is not equivalent.
    pdf_cfg = CrawlerRunConfig(scraping_strategy=PDFContentScrapingStrategy(), page_timeout=90000)
    async with AsyncWebCrawler(crawler_strategy=PDFCrawlerStrategy()) as crawler:
        for url in pdfs[:args.max_pdf]:
            try:
                result = await crawler.arun(url=url, config=pdf_cfg)
                if not result.success:
                    raise RuntimeError(str(result.error_message))
                markdown = str(result.markdown or "")
                if not markdown.strip():
                    raise ValueError("No extractable PDF text")
                report["attachments"].append({"url":url, "sha256_extracted_text": hashlib.sha256(markdown.encode()).hexdigest(),
                                               "note":"Hash of extracted text, NOT original PDF bytes"})
                report["findings"].extend(snippets(markdown, url, "pdf"))
            except Exception as exc:
                report["failures"].append({"url":url, "phase":"pdf", "error":str(exc)[:300]})
    report["attachments_not_processed"] = pdfs[args.max_pdf:]
    report["counts"] = {key:len(report[key]) for key in ("visited_pages","attachments","findings","failures","attachments_not_processed")}
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output":str(destination), "counts":report["counts"]}, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Public HTTPS project/procedure page")
    parser.add_argument("--project", required=True, help="Human-readable project label")
    parser.add_argument("--allow-domain", action="append", default=[], help="Extra permitted host/domain for links")
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--max-pdf", type=int, default=3)
    parser.add_argument("--output", default="reports/wind-agent/crawl4ai-mase-pilot.json")
    args = parser.parse_args()
    if not (1 <= args.max_pages <= 20 and 0 <= args.max_pdf <= 20):
        parser.error("limits: max-pages 1..20, max-pdf 0..20")
    asyncio.run(run(args))

if __name__ == "__main__":
    main()
