import argparse
import csv
import json
import re
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MASTER = ROOT / "reports" / "master_projects.json"
DEFAULT_BRANCH_INDEX = ROOT / "docs" / "data" / "branches" / "index.json"
DEFAULT_OUT = ROOT / "reports" / "opencup_value_audit.csv"
DEFAULT_CACHE = ROOT / "reports" / "opencup_value_audit_cache.json"

API_CUP_URL = "https://api.sogei.it/rgs/opencup/o/extServiceApi/v1/opendataes/cup/{cup}"
PORTAL_PROJECT_URL = "https://www.opencup.gov.it/portale/it/web/opencup/home/progetto/-/cup/{cup}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def norm_key(value: Any) -> str:
    text = clean(value).lower().replace("\ufeff", "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def parse_number(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        n = float(value)
        return n if n == n else None

    text = clean(value)
    if not text:
        return None

    text = (
        text.replace("\u00a0", " ")
        .replace("€", "")
        .replace("EUR", "")
        .replace("euro", "")
        .strip()
    )
    text = re.sub(r"\s+", "", text)

    # Mantiene solo cifre, separatori e segno.
    text = re.sub(r"[^0-9,.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None

    # Formato italiano classico: 1.234.567,89
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        # Se la virgola ha 1-2 cifre dopo, è decimale; altrimenti è separatore migliaia.
        tail = text.rsplit(",", 1)[-1]
        if len(tail) <= 2:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "." in text:
        parts = text.split(".")
        # 1.234.567 => migliaia; 123456.0 => decimale.
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            text = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            text = "".join(parts)

    try:
        return float(text)
    except ValueError:
        return None


def flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{prefix}_{key}" if prefix else str(key)
            out.update(flatten(value, new_key))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            new_key = f"{prefix}_{idx}" if prefix else str(idx)
            out.update(flatten(value, new_key))
    else:
        out[prefix] = obj

    return out


def load_json_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for key in ["projects", "records", "items", "data", "rows"]:
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

    raise ValueError(f"Formato JSON non riconosciuto: {path}")


def load_records(input_path: Path | None) -> list[dict[str, Any]]:
    if input_path:
        print(f"[LOAD] Input esplicito: {input_path}")
        return load_json_records(input_path)

    if DEFAULT_MASTER.exists():
        print(f"[LOAD] Uso master: {DEFAULT_MASTER}")
        return load_json_records(DEFAULT_MASTER)

    if DEFAULT_BRANCH_INDEX.exists():
        print(f"[LOAD] Master non trovato. Uso shard index: {DEFAULT_BRANCH_INDEX}")
        index = json.loads(DEFAULT_BRANCH_INDEX.read_text(encoding="utf-8"))
        rows: list[dict[str, Any]] = []
        base_dir = DEFAULT_BRANCH_INDEX.parent

        for branch in index.get("branches", []):
            for file_info in branch.get("files", []):
                filename = clean(file_info.get("file"))
                if not filename:
                    continue
                shard_path = base_dir / filename
                if not shard_path.exists():
                    print(f"[WARN] Shard mancante: {shard_path}")
                    continue
                rows.extend(load_json_records(shard_path))

        return rows

    raise FileNotFoundError(
        "Nessun input trovato. Attesi reports/master_projects.json "
        "oppure docs/data/branches/index.json"
    )


def get_record_value(record: dict[str, Any]) -> float | None:
    for key in ["project_value", "value_eur", "estimated_value_eur", "value", "importo"]:
        n = parse_number(record.get(key))
        if n is not None:
            return n
    return None


def extract_cup(record: dict[str, Any]) -> str:
    raw = clean(record.get("cup") or record.get("CUP") or record.get("codice_cup"))
    match = re.search(r"[A-Z0-9]{15}", raw.upper())
    return match.group(0) if match else raw.upper()


def compact_values(values: list[float]) -> list[float]:
    # Deduplica con arrotondamento ai centesimi per evitare 96000000 vs 96000000.0.
    seen = set()
    out = []
    for value in sorted(values):
        key = round(value, 2)
        if key not in seen:
            out.append(value)
            seen.add(key)
    return out


def build_cup_groups(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}

    for record in records:
        cup = extract_cup(record)
        if not cup:
            continue

        value = get_record_value(record)
        if value is None:
            continue

        item = groups.setdefault(cup, {
            "cup": cup,
            "records": 0,
            "values": [],
            "branches": set(),
            "titles": [],
            "clients": [],
            "regions": set(),
            "provinces": set(),
            "municipalities": set(),
            "source_urls": [],
            "ids": [],
        })

        item["records"] += 1
        item["values"].append(value)

        for field, target in [
            ("branch", "branches"),
            ("region", "regions"),
            ("province", "provinces"),
            ("municipality", "municipalities"),
        ]:
            v = clean(record.get(field))
            if v:
                item[target].add(v)

        for field, target in [
            ("title", "titles"),
            ("client", "clients"),
            ("source_url", "source_urls"),
            ("id", "ids"),
        ]:
            v = clean(record.get(field))
            if v:
                item[target].append(v)

    return groups


def load_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(path: Path, cache: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def score_cost_key(key: str) -> int:
    k = norm_key(key)

    reject_tokens = [
        "anno", "data", "codice", "cup", "cig", "cap", "istat",
        "percent", "quota", "id_", "_id", "lat", "lon", "telefono",
    ]
    if any(token in k for token in reject_tokens):
        return -1

    exact_scores = {
        "totale_costo_previsto": 120,
        "costo_previsto": 115,
        "costo_progetto": 105,
        "costo_del_progetto": 105,
        "costo_totale": 100,
        "totale_costo": 100,
        "totale_importo": 90,
        "importo_totale": 90,
        "totale_finanziamento_pubblico_previsto": 85,
        "finanziamento_pubblico_previsto": 80,
    }

    if k in exact_scores:
        return exact_scores[k]

    score = -1

    if "costo" in k and "previst" in k:
        score = max(score, 110)
    if "costo" in k and "totale" in k:
        score = max(score, 95)
    if "costo" in k:
        score = max(score, 75)
    if "finanziamento" in k and "previst" in k:
        score = max(score, 70)
    if "importo" in k and "totale" in k:
        score = max(score, 65)
    if k.endswith("importo") or k == "importo":
        score = max(score, 40)
    if k.endswith("finanziamento") or k == "finanziamento":
        score = max(score, 35)

    return score


def extract_official_value(api_payload: Any) -> tuple[float | None, str, str]:
    flat = flatten(api_payload)
    candidates = []

    for key, raw_value in flat.items():
        score = score_cost_key(key)
        if score < 0:
            continue

        value = parse_number(raw_value)
        if value is None or value <= 0:
            continue

        candidates.append((score, key, value, raw_value))

    if not candidates:
        return None, "", ""

    # Priorità al nome campo più credibile; in parità al valore maggiore.
    candidates.sort(key=lambda x: (x[0], x[2]), reverse=True)
    score, key, value, raw_value = candidates[0]

    preview = " | ".join(
        f"{k}={v}"
        for _, k, v, _raw in candidates[:8]
    )

    return value, key, preview


def fetch_official_value(cup: str, cache: dict[str, Any], sleep_s: float, timeout_s: int) -> dict[str, Any]:
    cached = cache.get(cup)
    if isinstance(cached, dict):
        return cached

    url = API_CUP_URL.format(cup=cup)
    result = {
        "cup": cup,
        "api_url": url,
        "ok": False,
        "official_value": None,
        "official_key": "",
        "candidate_values": "",
        "error": "",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout_s)
        response.raise_for_status()
        payload = response.json()

        value, key, candidates = extract_official_value(payload)

        result.update({
            "ok": value is not None,
            "official_value": value,
            "official_key": key,
            "candidate_values": candidates,
            "error": "" if value is not None else "NO_OFFICIAL_VALUE_FOUND",
        })

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    cache[cup] = result

    if sleep_s > 0:
        time.sleep(sleep_s)

    return result


def ratio(value: float | None, official: float | None) -> float | None:
    if value is None or official is None or official <= 0:
        return None
    return value / official


def is_close(value: float | None, target: float, tolerance_pct: float) -> bool:
    if value is None:
        return False
    return abs(value - target) / target <= tolerance_pct


def classify_ratio(r: float | None, tolerance_pct: float) -> tuple[str, str]:
    if r is None:
        return "NO_RATIO", ""

    if is_close(r, 1, tolerance_pct):
        return "OK", "keep"

    for multiplier in [10, 100, 1000]:
        if is_close(r, multiplier, tolerance_pct):
            return f"SUSPECT_X{multiplier}", f"use_official_or_divide_by_{multiplier}"

    for divisor in [10, 100, 1000]:
        target = 1 / divisor
        if is_close(r, target, tolerance_pct):
            return f"SUSPECT_TOO_LOW_X{divisor}", "review"

    return "REVIEW", "manual_review"


def first_common(values: list[str]) -> str:
    cleaned = [clean(v) for v in values if clean(v)]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


def join_set(values: set[str], limit: int = 8) -> str:
    out = sorted(clean(v) for v in values if clean(v))
    if len(out) > limit:
        return " | ".join(out[:limit]) + f" | + altri {len(out) - limit}"
    return " | ".join(out)


def write_audit_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "status",
        "suggested_action",
        "cup",
        "title",
        "client",
        "branches",
        "region",
        "province",
        "municipality",
        "records_with_cup",
        "radar_value_min",
        "radar_value_max",
        "radar_values_unique_count",
        "radar_values_unique",
        "official_value",
        "ratio_min",
        "ratio_max",
        "suggested_value",
        "official_key",
        "candidate_values",
        "api_error",
        "opencup_url",
        "sample_source_url",
        "sample_record_id",
    ]

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def parse_cups_arg(cups: str | None, cups_file: Path | None) -> set[str]:
    out: set[str] = set()

    if cups:
        for part in re.split(r"[,\s;]+", cups):
            part = clean(part).upper()
            match = re.search(r"[A-Z0-9]{15}", part)
            if match:
                out.add(match.group(0))

    if cups_file:
        text = cups_file.read_text(encoding="utf-8-sig", errors="ignore")
        for match in re.finditer(r"[A-Z0-9]{15}", text.upper()):
            out.add(match.group(0))

    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit valori progetto OpenCUP nel radar, senza modificare dataset o pagine."
    )
    parser.add_argument("--input", type=Path, default=None, help="JSON input. Default: reports/master_projects.json o shard.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT, help="CSV audit output.")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="Cache risposte API OpenCUP.")
    parser.add_argument("--cups", default=None, help="Lista CUP separati da virgola/spazio.")
    parser.add_argument("--cups-file", type=Path, default=None, help="File testo/CSV con CUP da controllare.")
    parser.add_argument("--limit", type=int, default=100, help="Numero massimo CUP da controllare se non passi --cups.")
    parser.add_argument("--min-value", type=float, default=10_000_000, help="Valore radar minimo per selezione automatica.")
    parser.add_argument("--sleep", type=float, default=0.25, help="Pausa tra chiamate API.")
    parser.add_argument("--timeout", type=int, default=45, help="Timeout chiamata API.")
    parser.add_argument("--tolerance-pct", type=float, default=0.03, help="Tolleranza ratio, es. 0.03 = 3%.")
    parser.add_argument("--no-cache", action="store_true", help="Ignora cache esistente e riscarica.")
    args = parser.parse_args()

    records = load_records(args.input)
    print(f"[LOAD] Record letti: {len(records):,}")

    groups = build_cup_groups(records)
    print(f"[GROUP] CUP con valore radar: {len(groups):,}")

    requested_cups = parse_cups_arg(args.cups, args.cups_file)

    if requested_cups:
        cups_to_check = [cup for cup in sorted(requested_cups) if cup in groups]
        missing = sorted(requested_cups - set(cups_to_check))
        if missing:
            print(f"[WARN] CUP richiesti non trovati nel radar: {', '.join(missing)}")
    else:
        sortable = []
        for cup, group in groups.items():
            values = compact_values(group["values"])
            if not values:
                continue
            max_value = max(values)
            if max_value >= args.min_value:
                sortable.append((max_value, cup))

        sortable.sort(reverse=True)
        cups_to_check = [cup for _value, cup in sortable[:args.limit]]

    print(f"[AUDIT] CUP da controllare: {len(cups_to_check):,}")

    cache = {} if args.no_cache else load_cache(args.cache)
    audit_rows = []

    for idx, cup in enumerate(cups_to_check, start=1):
        group = groups[cup]
        values = compact_values(group["values"])
        radar_min = min(values) if values else None
        radar_max = max(values) if values else None

        print(f"[{idx:,}/{len(cups_to_check):,}] {cup} | radar max: {radar_max}")

        official = fetch_official_value(
            cup=cup,
            cache=cache,
            sleep_s=args.sleep,
            timeout_s=args.timeout,
        )

        official_value = parse_number(official.get("official_value"))
        ratio_min = ratio(radar_min, official_value)
        ratio_max = ratio(radar_max, official_value)

        if official.get("error"):
            status = "API_ERROR_OR_NO_VALUE"
            suggested_action = "manual_review"
        else:
            status, suggested_action = classify_ratio(ratio_max, args.tolerance_pct)

        suggested_value = ""
        if official_value is not None and status.startswith("SUSPECT_X"):
            suggested_value = official_value
        elif radar_max is not None and status == "OK":
            suggested_value = radar_max

        audit_rows.append({
            "status": status,
            "suggested_action": suggested_action,
            "cup": cup,
            "title": first_common(group["titles"]),
            "client": first_common(group["clients"]),
            "branches": join_set(group["branches"]),
            "region": join_set(group["regions"]),
            "province": join_set(group["provinces"]),
            "municipality": join_set(group["municipalities"]),
            "records_with_cup": group["records"],
            "radar_value_min": radar_min if radar_min is not None else "",
            "radar_value_max": radar_max if radar_max is not None else "",
            "radar_values_unique_count": len(values),
            "radar_values_unique": " | ".join(str(round(v, 2)) for v in values[:12]),
            "official_value": official_value if official_value is not None else "",
            "ratio_min": round(ratio_min, 6) if ratio_min is not None else "",
            "ratio_max": round(ratio_max, 6) if ratio_max is not None else "",
            "suggested_value": suggested_value,
            "official_key": official.get("official_key", ""),
            "candidate_values": official.get("candidate_values", ""),
            "api_error": official.get("error", ""),
            "opencup_url": PORTAL_PROJECT_URL.format(cup=cup),
            "sample_source_url": first_common(group["source_urls"]),
            "sample_record_id": first_common(group["ids"]),
        })

        # Salvataggio progressivo: se il portale/API si pianta, non perdiamo tutto.
        if idx % 10 == 0:
            save_cache(args.cache, cache)
            write_audit_csv(audit_rows, args.output)

    save_cache(args.cache, cache)
    write_audit_csv(audit_rows, args.output)

    counts = Counter(row["status"] for row in audit_rows)

    print("")
    print(f"[OK] Audit scritto: {args.output}")
    print(f"[OK] Cache scritta: {args.cache}")
    print("[SUMMARY]")
    for status, count in counts.most_common():
        print(f"- {status}: {count}")

    suspicious = sum(count for status, count in counts.items() if status.startswith("SUSPECT_X"))
    if suspicious:
        print("")
        print(f"[ATTENZIONE] Casi sospetti con valore radar troppo alto: {suspicious}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
