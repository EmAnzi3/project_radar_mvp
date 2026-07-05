import argparse
import csv
import json
import re
import urllib.parse
from pathlib import Path

from probe_portaletrasparenza import (
    clean,
    confidence_score,
    extract_actor_candidates,
    extract_links,
    fetch_text,
    find_matches,
    same_domain_or_subpath,
    source_type,
    split_codes,
    strip_html,
    write_csv,
    now_utc,
)


LIST_PATHS = [
    "/it/trasparenza/bandi-di-gara-e-contratti.html",
    "/it/trasparenza/bandi-di-gara-e-contratti/archivio-bandi-di-gara-e-contratti.html",
]


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def paginated_urls(base_url, max_pages):
    urls = [base_url]

    for page in range(1, max_pages + 1):
        sep = "&" if "?" in base_url else "?"
        urls.append(f"{base_url}{sep}pagina={page}")

    return urls


def collect_attodigara_links(tenant_domain, max_list_pages):
    base = f"https://{tenant_domain}"
    detail_links = []
    seen = set()
    list_pages_checked = 0
    errors = []

    for path in LIST_PATHS:
        start_url = base + path

        for url in paginated_urls(start_url, max_list_pages):
            try:
                html_text, content_type = fetch_text(url)
            except Exception as exc:
                errors.append({"url": url, "error": str(exc)})
                continue

            list_pages_checked += 1

            links = extract_links(url, html_text)

            for link in links:
                if not same_domain_or_subpath(link, tenant_domain):
                    continue

                if "/dettagli/attodigara/" not in link.lower():
                    continue

                if link in seen:
                    continue

                seen.add(link)
                detail_links.append(link)

    return detail_links, list_pages_checked, errors


def scan_target(target, max_list_pages, max_details):
    tenant = clean(target.get("tenant_domain"))
    cups = split_codes(target.get("cup"))
    cigs = split_codes(target.get("cig"))

    if not tenant:
        return [], {
            "project_key": target.get("project_key", ""),
            "tenant_domain": tenant,
            "detail_links_collected": 0,
            "details_checked": 0,
            "matches": 0,
            "errors": 1,
            "error_samples": [{"error": "missing tenant_domain"}],
        }

    detail_links, list_pages_checked, errors = collect_attodigara_links(
        tenant,
        max_list_pages=max_list_pages,
    )

    findings = []
    details_checked = 0

    for link in detail_links[:max_details]:
        try:
            html_text, content_type = fetch_text(link)
        except Exception as exc:
            errors.append({"url": link, "error": str(exc)})
            continue

        details_checked += 1
        text = strip_html(html_text)

        matched_cups, matched_cigs = find_matches(text, cups, cigs)

        if not matched_cups and not matched_cigs:
            continue

        actors, vats, context = extract_actor_candidates(
            text,
            matched_cups,
            matched_cigs,
        )

        score = confidence_score(matched_cups, matched_cigs, actors, link)

        findings.append(
            {
                "project_key": target.get("project_key", ""),
                "cup": target.get("cup", ""),
                "cig": target.get("cig", ""),
                "ente": target.get("ente", ""),
                "tenant_domain": tenant,
                "source_url": link,
                "source_type": source_type(link),
                "matched_cups": " | ".join(matched_cups),
                "matched_cigs": " | ".join(matched_cigs),
                "actor_candidates": " | ".join(actors),
                "tax_code_candidates": " | ".join(vats),
                "confidence": score,
                "actor_context": context,
                "checked_at": now_utc(),
            }
        )

    summary = {
        "project_key": target.get("project_key", ""),
        "tenant_domain": tenant,
        "list_pages_checked": list_pages_checked,
        "detail_links_collected": len(detail_links),
        "details_checked": details_checked,
        "matches": len(findings),
        "errors": len(errors),
        "error_samples": errors[:10],
    }

    return findings, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--targets",
        type=Path,
        default=Path("reports/portaletrasparenza_probe_targets_auto.csv"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reports/portaletrasparenza_awards_attodigara_scan.csv"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("reports/portaletrasparenza_awards_attodigara_scan_summary.json"),
    )
    parser.add_argument("--max-list-pages", type=int, default=20)
    parser.add_argument("--max-details", type=int, default=300)
    args = parser.parse_args()

    if not args.targets.exists():
        raise SystemExit(f"Target file mancante: {args.targets}")

    targets = read_csv(args.targets)

    all_findings = []
    summaries = []

    for index, target in enumerate(targets, start=1):
        print(
            f"[{index}/{len(targets)}] "
            f"{target.get('project_key')} "
            f"{target.get('tenant_domain')} "
            f"CIG={target.get('cig')}"
        )

        findings, summary = scan_target(
            target,
            max_list_pages=args.max_list_pages,
            max_details=args.max_details,
        )

        print(
            f"  detail_links={summary['detail_links_collected']} "
            f"checked={summary['details_checked']} "
            f"matches={summary['matches']} "
            f"errors={summary['errors']}"
        )

        all_findings.extend(findings)
        summaries.append(summary)

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

    global_summary = {
        "targets": len(targets),
        "findings": len(all_findings),
        "target_summaries": summaries,
        "output": str(args.out),
    }

    args.summary_out.write_text(
        json.dumps(global_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("Findings:", len(all_findings))
    print("Output:")
    print("-", args.out)
    print("-", args.summary_out)


if __name__ == "__main__":
    raise SystemExit(main())
