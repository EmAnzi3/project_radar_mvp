import csv
import zipfile
from pathlib import Path


TARGETS = Path("reports/national_anac_cup_targets.csv")
ANAC_CUP_ZIP = Path("data/raw/anac/cup.zip")
OUT = Path("reports/national_anac_cup_cig_matches.csv")


def load_targets() -> set[str]:
    if not TARGETS.exists():
        raise SystemExit(f"File target non trovato: {TARGETS}")

    cups = set()

    with TARGETS.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cup = str(row.get("cup") or "").strip()
            if cup:
                cups.add(cup)

    return cups


def detect_delimiter(sample: str) -> str:
    candidates = [";", ",", "|", "\t"]
    return max(candidates, key=lambda d: sample.count(d))


def find_col(fieldnames: list[str], wanted: list[str]) -> str | None:
    normalized = {
        str(name).strip().lower().replace("_", "").replace(" ", ""): name
        for name in fieldnames or []
    }

    for w in wanted:
        key = w.lower().replace("_", "").replace(" ", "")
        if key in normalized:
            return normalized[key]

    return None


def main():
    cups = load_targets()
    print(f"CUP target: {len(cups)}")

    if not ANAC_CUP_ZIP.exists():
        raise SystemExit(
            f"File ANAC CUP non trovato: {ANAC_CUP_ZIP}\n"
            "Scarica il dataset ANAC cup e rinominalo in data/raw/anac/cup.zip"
        )

    matches = []
    scanned = 0

    with zipfile.ZipFile(ANAC_CUP_ZIP) as z:
        csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]

        if not csv_names:
            raise SystemExit("Nessun CSV trovato nello ZIP ANAC cup.")

        print(f"CSV nello ZIP: {csv_names}")

        for csv_name in csv_names:
            print(f"Leggo: {csv_name}")

            with z.open(csv_name) as raw:
                text = raw.read(8192).decode("utf-8-sig", errors="ignore")
                delimiter = detect_delimiter(text)

            with z.open(csv_name) as raw:
                wrapper = (line.decode("utf-8-sig", errors="ignore") for line in raw)
                reader = csv.DictReader(wrapper, delimiter=delimiter)

                print("Campi:", reader.fieldnames)

                cig_col = find_col(reader.fieldnames, ["CIG", "codice_cig", "codice identificativo gara"])
                cup_col = find_col(reader.fieldnames, ["CUP", "codice_cup", "codice unico progetto"])

                if not cig_col or not cup_col:
                    raise SystemExit(
                        f"Non trovo colonne CIG/CUP. cig_col={cig_col}, cup_col={cup_col}"
                    )

                for row in reader:
                    scanned += 1

                    if scanned % 500_000 == 0:
                        print(f"Righe lette: {scanned:,} | match: {len(matches):,}")

                    cup = str(row.get(cup_col) or "").strip()
                    if cup not in cups:
                        continue

                    cig = str(row.get(cig_col) or "").strip()

                    matches.append({
                        "cup": cup,
                        "cig": cig,
                        "source_dataset": csv_name,
                    })

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            delimiter=";",
            fieldnames=["cup", "cig", "source_dataset"],
        )
        writer.writeheader()
        writer.writerows(matches)

    print(f"Righe lette: {scanned:,}")
    print(f"Match CUP→CIG trovati: {len(matches):,}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
