from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "wind" / "data"


def load(name: str):
    with (DATA / name).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    raise SystemExit(f"[FAIL] {message}")


def main() -> None:
    meta = load("meta.json")
    scale = meta.get("maturity_scale", [])
    expected_codes = [f"E{i}" for i in range(9)]
    codes = [item.get("code") for item in scale]
    if codes != expected_codes:
        fail(f"scala maturità inattesa: {codes}; attesa {expected_codes}")
    for item in scale:
        if not item.get("label") or not item.get("description"):
            fail(f"{item.get('code')}: label/description canonica mancante")

    manifest = load("projects.json")
    projects = []
    for chunk in manifest["chunks"]:
        projects.extend(load(chunk))
    if len(projects) != 17:
        fail(f"seed inatteso: {len(projects)} progetti")

    invalid = [(p["id"], p.get("stage")) for p in projects if p.get("stage") not in expected_codes]
    if invalid:
        fail(f"stage non canonici: {invalid}")

    distribution = Counter(p["stage"] for p in projects)
    expected_distribution = {
        "E0": 0,
        "E1": 0,
        "E2": 3,
        "E3": 2,
        "E4": 1,
        "E5": 0,
        "E6": 2,
        "E7": 9,
        "E8": 0,
    }
    actual = {code: distribution.get(code, 0) for code in expected_codes}
    if actual != expected_distribution:
        fail(f"distribuzione stage inattesa: {actual}; attesa {expected_distribution}")

    by_id = {p["id"]: p for p in projects}
    guards = {
        "andretta-bisaccia": "E6",
        "tricarico": "E6",
        "nulvi-ploaghe": "E4",
        "fenice": "E3",
        "toritto": "E2",
        "castelfranco-cer": "E7",
    }
    for project_id, expected_stage in guards.items():
        actual_stage = by_id[project_id].get("stage")
        if actual_stage != expected_stage:
            fail(f"{project_id}: stage {actual_stage}, atteso {expected_stage}")

    if "lavori fisici" not in by_id["castelfranco-cer"].get("status_note", "").lower():
        fail("Castelfranco/CER: E7 deve essere motivato esplicitamente da lavori fisici osservati")

    print("[OK] scala E0-E8 canonica, sequenziale e completa")
    print(f"[OK] distribuzione 17 seed: {actual}")
    print("[OK] Castelfranco/CER corretto a E7; Andretta e Tricarico restano E6; Nulvi E4")
    print("[OK] fasi a zero conservate: E0, E1, E5, E8")


if __name__ == "__main__":
    main()
