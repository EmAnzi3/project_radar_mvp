import csv
import zipfile
from pathlib import Path

ZIP_PATH = Path("data/raw/anac/aggiudicazioni.zip")

def detect_delimiter(sample: str) -> str:
    candidates = [";", ",", "|", "\t"]
    return max(candidates, key=lambda d: sample.count(d))

def main():
    if not ZIP_PATH.exists():
        raise SystemExit(f"File non trovato: {ZIP_PATH}")

    with zipfile.ZipFile(ZIP_PATH) as z:
        csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]

        print("CSV trovati:", csv_names)

        for csv_name in csv_names:
            print("=" * 100)
            print("File:", csv_name)

            with z.open(csv_name) as raw:
                sample = raw.read(8192).decode("utf-8-sig", errors="ignore")
                delimiter = detect_delimiter(sample)

            print("Delimitatore:", repr(delimiter))

            with z.open(csv_name) as raw:
                wrapper = (line.decode("utf-8-sig", errors="ignore") for line in raw)
                reader = csv.DictReader(wrapper, delimiter=delimiter)

                print("Campi:")
                print(reader.fieldnames)

                print()
                print("Prime 3 righe:")
                for i, row in enumerate(reader, 1):
                    print("-" * 80)
                    for k, v in row.items():
                        if v:
                            print(f"{k}: {v}")
                    if i >= 3:
                        break

if __name__ == "__main__":
    main()
