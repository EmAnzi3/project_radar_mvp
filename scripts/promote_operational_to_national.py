from pathlib import Path
import csv
import json
import shutil

SRC = Path("reports/operational_shortlist.csv")
DST = Path("reports/national_operational_shortlist.csv")
OUT_JSON = Path("docs/national_operational_data.json")

if not SRC.exists():
    raise SystemExit("Manca reports/operational_shortlist.csv")

shutil.copyfile(SRC, DST)

rows = []
with DST.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f, delimiter=";")
    for r in reader:
        rows.append({
            "score": r.get("operational_score") or r.get("score") or "",
            "segment": r.get("primary_segment") or "",
            "title": r.get("title") or "",
            "category": r.get("category") or "",
            "region": r.get("region") or "",
            "province": r.get("province") or "",
            "municipality": r.get("municipality") or "",
            "value_eur": float(r.get("value_eur") or 0),
            "client": r.get("client") or "",
            "cup": r.get("cup") or "",
            "source_url": r.get("source_url") or "",
        })

OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"[OK] {SRC} -> {DST}")
print(f"[OK] JSON: {OUT_JSON}")
print(f"Record nazionali: {len(rows)}")
