import argparse
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path


USER_AGENT = (
    "project-radar-mvp/0.1 "
    "(targeted public transparency probe; contact: internal research)"
)

SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
    ".css", ".js", ".ico", ".woff", ".woff2", ".ttf",
    ".zip", ".rar", ".7z",
)

INTERESTING_PATH_HINTS = [
    "bandi-di-gara",
    "bandi_di_gara",
    "bandi-gara",
    "contratti",
    "attodigara",
    "gara",
    "affidamento",
    "affidamenti",
    "aggiudicazione",
    "aggiudicazioni",
    "appalti",
    "avcp",
    "l190",
    "xml",
]

BLOCK_PATH_HINTS = [
    "/personale/",
    "/performance/",
    "/organizzazione/",
    "/consulenti/",
    "/collaboratori/",
    "/bilanci/",
    "/pagamenti/",
    "/sovvenzioni/",
    "/beni-immobili/",
    "/controlli-e-rilievi/",
    "/servizi-erogati/",
    "/altri-contenuti/",
    "/accesso-civico/",
    "/tassi-di-assenza/",
]

ACTOR_LABELS = [
    "aggiudicatario",
    "aggiudicataria",
    "affidatario",
    "affidataria",
    "operatore economico",
    "impresa aggiudicataria",
    "impresa appaltatrice",
    "appaltatore",
    "contraente",
    "ditta",
    "mandataria",
    "mandante",
    "consorziata esecutrice",
    "subappaltatore",
    "appalto",
]

COMPANY_RE = re.compile(
    r"\b([A-ZÀ-ÖØ-Ý0-9][A-ZÀ-ÖØ-Ý0-9\.\'’&,\- ]{2,90}?"
    r"(?:S\.?\s*R\.?\s*L\.?|S\.?\s*P\.?\s*A\.?|SRL|SPA|SOCIETÀ|SOCIETA|"
    r"COOP\.?|CONSORZIO|IMPRESA|S\.?C\.?A\.?R\.?L\.?))\b",
    re.I,
)

VAT_RE = re.compile(r"\b\d{11}\b")


def clean(value):
    return str(value or "").strip()


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def norm_code(value):
    return re.sub(r"[^A-Z0-9]", "", clean(value).upper())


def split_codes(value):
    parts = re.split(r"[|,;\s]+", clean(value))
    return [norm_code(part) for part in parts if norm_code(part)]


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=";",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def fetch_text(url, timeout=30):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,text/plain,*/*",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.7",
        },
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        final_url = response.geturl()
        raw = response.read()

    original_host = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    final_host = urllib.parse.urlparse(final_url).netloc.lower().replace("www.", "")

    if original_host != final_host:
        raise RuntimeError(f"redirect fuori dominio: {final_url}")

    # Pilot: per ora saltiamo PDF/binari. Se serve, aggiungiamo estrazione PDF dopo.
    if "pdf" in content_type.lower():
        return "", content_type

    text = raw.decode("utf-8", errors="replace")
    return text, content_type


def strip_html(value):
    text = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_links(base_url, html_text):
    links = []

    for match in re.finditer(r'href=["\']([^"\']+)["\']', html_text, flags=re.I):
        href = html.unescape(match.group(1)).strip()

        if not href or href.startswith("#"):
            continue

        url = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            continue

        lower_path = parsed.path.lower()

        if lower_path.endswith(SKIP_EXTENSIONS):
            continue

        links.append(url)

    return links


def same_domain_or_subpath(url, tenant_domain):
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc.lower().replace("www.", "") == tenant_domain.lower().replace("www.", "")


def is_interesting_url(url):
    lower = url.lower()

    if any(hint in lower for hint in BLOCK_PATH_HINTS):
        return False

    return any(hint in lower for hint in INTERESTING_PATH_HINTS)


def source_type(url):
    lower = url.lower()

    if "/dettagli/attodigara/" in lower:
        return "portaletrasparenza_attodigara"

    if "bandi-di-gara-e-contratti" in lower:
        return "portaletrasparenza_bandi_contratti"

    if "trasparenza" in lower:
        return "portaletrasparenza_trasparenza"

    if "download" in lower or "allegat" in lower:
        return "portaletrasparenza_allegato"

    return "portaletrasparenza_other"


def find_matches(text, cups, cigs):
    text_norm = norm_code(text)

    matched_cups = [cup for cup in cups if cup and cup in text_norm]
    matched_cigs = [cig for cig in cigs if cig and cig in text_norm]

    return matched_cups, matched_cigs


def windows_around_terms(text, terms, radius=500):
    lower = text.lower()
    windows = []

    for term in terms:
        term_lower = term.lower()
        start = 0

        while True:
            idx = lower.find(term_lower, start)

            if idx < 0:
                break

            a = max(0, idx - radius)
            b = min(len(text), idx + len(term) + radius)
            windows.append(text[a:b])
            start = idx + len(term)

            if len(windows) >= 20:
                return windows

    return windows


def extract_actor_candidates(text, matched_cups, matched_cigs):
    terms = list(matched_cups) + list(matched_cigs) + ACTOR_LABELS
    windows = windows_around_terms(text, terms, radius=700)

    if not windows:
        windows = [text[:2000]]

    blob = " ".join(windows)
    blob = re.sub(r"\s+", " ", blob)

    companies = []
    seen = set()

    for match in COMPANY_RE.finditer(blob):
        candidate = clean(match.group(1))
        candidate = re.sub(r"\s+", " ", candidate)

        key = candidate.upper()

        if len(candidate) < 4 or key in seen:
            continue

        seen.add(key)
        companies.append(candidate)

        if len(companies) >= 10:
            break

    vats = []
    seen_vat = set()

    for match in VAT_RE.finditer(blob):
        vat = match.group(0)

        if vat not in seen_vat:
            seen_vat.add(vat)
            vats.append(vat)

    # Contesto breve leggibile, utile per review.
    context = ""

    for window in windows:
        if any(label in window.lower() for label in ACTOR_LABELS):
            context = window
            break

    if not context and windows:
        context = windows[0]

    context = clean(re.sub(r"\s+", " ", context))[:1200]

    return companies, vats, context


def confidence_score(matched_cups, matched_cigs, actor_candidates, url):
    score = 0

    if matched_cups:
        score += 35

    if matched_cigs:
        score += 45

    if actor_candidates:
        score += 15

    if "/dettagli/attodigara/" in url.lower():
        score += 10

    return min(score, 100)


def default_start_urls(tenant_domain):
    base = f"https://{tenant_domain}"

    return [
        base + "/it/trasparenza/bandi-di-gara-e-contratti.html",
        base + "/it/trasparenza/bandi-di-gara-e-contratti/atti-e-documenti-di-carattere-generale-riferiti-a-tutte-le-procedure.html",
        base + "/it/trasparenza/bandi-di-gara-e-contratti/informazioni-sulle-singole-procedure-in-formato-tabellare.html",
        base,
    ]


def probe_target(target, max_pages, sleep_seconds):
    tenant = clean(target.get("tenant_domain"))

    if not tenant:
        return [], [{"error": "missing_tenant_domain", "target": target.get("project_key", "")}]

    cups = split_codes(target.get("cup"))
    cigs = split_codes(target.get("cig"))

    start_urls = []

    if clean(target.get("start_url")):
        start_urls.append(clean(target.get("start_url")))

    start_urls.extend(default_start_urls(tenant))

    queue = deque()
    seen = set()

    for url in start_urls:
        if url not in seen:
            queue.append((url, 0))
            seen.add(url)

    findings = []
    errors = []
    pages_checked = 0

    max_attempts = max_pages * 3
    max_errors = max_pages

    attempts = 0

    while queue and pages_checked < max_pages and attempts < max_attempts and len(errors) < max_errors:
        url, depth = queue.popleft()
        attempts += 1

        if not same_domain_or_subpath(url, tenant):
            continue

        try:
            html_text, content_type = fetch_text(url)
        except Exception as exc:
            errors.append(
                {
                    "target": target.get("project_key", ""),
                    "url": url,
                    "error": str(exc),
                }
            )
            continue

        pages_checked += 1

        if not html_text:
            continue

        text = strip_html(html_text)
        matched_cups, matched_cigs = find_matches(text, cups, cigs)

        if matched_cups or matched_cigs:
            actors, vats, context = extract_actor_candidates(
                text,
                matched_cups,
                matched_cigs,
            )

            score = confidence_score(matched_cups, matched_cigs, actors, url)

            findings.append(
                {
                    "project_key": target.get("project_key", ""),
                    "cup": target.get("cup", ""),
                    "cig": target.get("cig", ""),
                    "ente": target.get("ente", ""),
                    "tenant_domain": tenant,
                    "source_url": url,
                    "source_type": source_type(url),
                    "matched_cups": " | ".join(matched_cups),
                    "matched_cigs": " | ".join(matched_cigs),
                    "actor_candidates": " | ".join(actors),
                    "tax_code_candidates": " | ".join(vats),
                    "confidence": score,
                    "actor_context": context,
                    "checked_at": now_utc(),
                }
            )

        # Espansione controllata.
        if depth < 2:
            links = extract_links(url, html_text)

            for link in links:
                if len(seen) > max_pages * 12:
                    break

                if link in seen:
                    continue

                if not same_domain_or_subpath(link, tenant):
                    continue

                if not is_interesting_url(link):
                    continue

                seen.add(link)
                queue.append((link, depth + 1))

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    return findings, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--targets",
        type=Path,
        default=Path("reports/portaletrasparenza_probe_targets.csv"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reports/portaletrasparenza_awards.csv"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("reports/portaletrasparenza_awards_summary.json"),
    )
    parser.add_argument("--max-pages-per-target", type=int, default=80)
    parser.add_argument("--sleep", type=float, default=0.3)

    args = parser.parse_args()

    if not args.targets.exists():
        raise SystemExit(f"File target mancante: {args.targets}")

    targets = read_csv(args.targets)

    all_findings = []
    all_errors = []

    for index, target in enumerate(targets, start=1):
        print(
            f"[{index}/{len(targets)}] "
            f"{target.get('project_key')} "
            f"{target.get('tenant_domain')} "
            f"CUP={target.get('cup')} CIG={target.get('cig')}"
        )

        findings, errors = probe_target(
            target,
            max_pages=args.max_pages_per_target,
            sleep_seconds=args.sleep,
        )

        print(f"  findings: {len(findings)} | errors: {len(errors)}")

        all_findings.extend(findings)
        all_errors.extend(errors)

    fieldnames = [
        "project_key",
        "cup",
        "cig",
        "ente",
        "tenant_domain",
        "source_url",
        "source_type",
        "matched_cups",
        "matched_cigs",
        "actor_candidates",
        "tax_code_candidates",
        "confidence",
        "actor_context",
        "checked_at",
    ]

    write_csv(args.out, all_findings, fieldnames)

    summary = {
        "targets": len(targets),
        "findings": len(all_findings),
        "errors": len(all_errors),
        "max_pages_per_target": args.max_pages_per_target,
        "output": str(args.out),
        "error_samples": all_errors[:20],
    }

    args.summary_out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("Findings:", len(all_findings))
    print("Errors:", len(all_errors))
    print("Output:")
    print("-", args.out)
    print("-", args.summary_out)


if __name__ == "__main__":
    raise SystemExit(main())
