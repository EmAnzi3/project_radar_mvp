import argparse
import csv
import json
import re
from pathlib import Path


COMPANY_RE = re.compile(
    r"""
    \b(
        [A-ZÀ-ÖØ-Ý0-9][A-ZÀ-ÖØ-Ý0-9&'’\.\-/ ]{1,90}?
        \s+
        (?:
            S\.?\s*R\.?\s*L\.?
            |S\.?\s*P\.?\s*A\.?
            |SRL
            |SPA
            |SOCIETÀ\s+COOPERATIVA
            |SOCIETA\s+COOPERATIVA
            |S\.?\s*C\.?\s*A\.?\s*R\.?\s*L\.?
            |CONSORZIO
            |COOP(?:ERATIVA)?\.?
        )
    )\b
    """,
    re.I | re.X,
)

VAT_RE = re.compile(r"\b\d{11}\b")

BAD_NAME_HINTS = [
    "CONDIVIDI",
    "FACEBOOK",
    "WHATSAPP",
    "LINKEDIN",
    "STAMPA",
    "CIG ",
    "CUP ",
    "PARTECIPAZIONE DI N.",
    "DIPENDENTI DELLA SOCIETÀ",
    "DIPENDENTI DELLA SOCIETA",
    "RETIAMBIENTE",
]

ROLE_HINTS = {
    "aggiudicatario": "aggiudicatario",
    "aggiudicataria": "aggiudicatario",
    "affidatario": "affidatario",
    "affidataria": "affidatario",
    "operatore economico": "operatore_economico",
    "impresa aggiudicataria": "aggiudicatario",
    "impresa appaltatrice": "appaltatore",
    "appaltatore": "appaltatore",
    "contraente": "contraente",
    "mandataria": "mandataria",
    "mandante": "mandante",
    "consorziata esecutrice": "consorziata_esecutrice",
    "subappaltatore": "subappaltatore",
}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm(value):
    return re.sub(r"[^A-Z0-9]", "", clean(value).upper())


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


def normalize_company_name(name):
    value = clean(name)

    # rimuove P.IVA/CF messi prima del nome
    value = re.sub(r"^\d{11}\s*[-–—:]*\s*", "", value)

    # rimuove prefissi spezzati tipo "S.R.L. - 01458130497 C.E.M.E.S. S.P.A"
    value = re.sub(
        r"^(S\.?\s*R\.?\s*L\.?|S\.?\s*P\.?\s*A\.?|SRL|SPA)\s*[-–—:]*\s*\d{11}\s*",
        "",
        value,
        flags=re.I,
    )

    value = re.sub(r"^[\-\:\;\,\.\s]+", "", value)
    value = re.sub(r"[\-\:\;\,\.\s]+$", "", value)

    value = re.sub(r"\bS\s*R\s*L\b", "S.R.L.", value, flags=re.I)
    value = re.sub(r"\bS\s*P\s*A\b", "S.P.A.", value, flags=re.I)
    value = re.sub(r"\bSRL\b", "S.R.L.", value, flags=re.I)
    value = re.sub(r"\bSPA\b", "S.P.A.", value, flags=re.I)

    return clean(value)


def is_bad_company_name(name):
    upper = name.upper()

    if len(name) < 5:
        return True

    if any(hint in upper for hint in BAD_NAME_HINTS):
        return True

    if len(name.split()) > 8:
        return True

    if re.fullmatch(r"\d{11}.*", name):
        return True

    return False


def split_blob(blob):
    parts = []

    # prima separa i candidati già divisi dallo script precedente
    for piece in re.split(r"\s*\|\s*", blob):
        piece = clean(piece)

        if not piece:
            continue

        # poi separa sequenze tipo "FRANGERINI IMPRESA S.R.L. - 01458130497 C.E.M.E.S. S.P.A"
        subparts = re.split(r"\s+[-–—]\s+", piece)

        for sub in subparts:
            sub = clean(sub)

            if sub:
                parts.append(sub)

    return parts


def extract_companies_from_piece(piece):
    companies = []

    for match in COMPANY_RE.finditer(piece):
        raw_name = match.group(1)
        name = normalize_company_name(raw_name)

        if is_bad_company_name(name):
            continue

        companies.append(
            {
                "name": name,
                "piece": piece,
                "start": match.start(),
                "end": match.end(),
            }
        )

    return companies


def find_nearest_vat(piece, start, end, actor_name, radius=120):
    # Se la P.IVA è immediatamente prima del nome, è molto probabilmente associata.
    before_name = piece[:start]
    before_vats = VAT_RE.findall(before_name[-80:])

    if before_vats:
        return before_vats[-1]

    after_name = piece[end:]
    after_vats = VAT_RE.findall(after_name[:80])

    if after_vats:
        return after_vats[0]

    # fallback: prima P.IVA nella porzione
    vats = VAT_RE.findall(piece)

    if vats:
        return vats[0]

    return ""


def infer_role(piece):
    lower = piece.lower()

    for hint, role in ROLE_HINTS.items():
        if hint in lower:
            return role

    return "oe_candidate"


def score_clean_actor(row, actor_name, actor_tax_code, actor_role):
    score = 0

    source_type = clean(row.get("source_type"))
    matched_cups = clean(row.get("matched_cups"))
    matched_cigs = clean(row.get("matched_cigs"))

    if matched_cups:
        score += 20

    if matched_cigs:
        score += 45

    if actor_name:
        score += 20

    if actor_tax_code:
        score += 5

    if source_type == "portaletrasparenza_attodigara":
        score += 20
    elif "bandi_contratti" in source_type:
        score += 5

    if actor_role in {
        "aggiudicatario",
        "affidatario",
        "appaltatore",
        "contraente",
        "mandataria",
        "mandante",
        "consorziata_esecutrice",
    }:
        score += 10

    return min(score, 100)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reports/portaletrasparenza_awards.csv"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reports/portaletrasparenza_awards_clean.csv"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("reports/portaletrasparenza_awards_clean_summary.json"),
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"File mancante: {args.input}")

    rows = read_csv(args.input)
    clean_rows = []
    seen = set()

    for row in rows:
        # Per ora teniamo solo le pagine gara vere. Le pagine elenco generano troppo rumore.
        if clean(row.get("source_type")) != "portaletrasparenza_attodigara":
            continue

        if not clean(row.get("matched_cigs")):
            continue

        blob = " | ".join(
            [
                clean(row.get("actor_candidates")),
                clean(row.get("actor_context")),
            ]
        )

        if not blob:
            continue

        pieces = split_blob(blob)

        for piece in pieces:
            companies = extract_companies_from_piece(piece)

            for company in companies:
                name = company["name"]
                name_norm = norm(name)

                if not name_norm:
                    continue

                actor_tax_code = find_nearest_vat(
                    company["piece"],
                    company["start"],
                    company["end"],
                    name,
                )

                actor_role = infer_role(company["piece"])

                confidence = score_clean_actor(
                    row,
                    actor_name=name,
                    actor_tax_code=actor_tax_code,
                    actor_role=actor_role,
                )

                key = (
                    row.get("project_key", ""),
                    row.get("cig", ""),
                    name_norm,
                    actor_tax_code,
                )

                if key in seen:
                    continue

                seen.add(key)

                clean_rows.append(
                    {
                        "project_key": row.get("project_key", ""),
                        "cup": row.get("cup", ""),
                        "cig": row.get("cig", ""),
                        "matched_cups": row.get("matched_cups", ""),
                        "matched_cigs": row.get("matched_cigs", ""),
                        "ente": row.get("ente", ""),
                        "tenant_domain": row.get("tenant_domain", ""),
                        "actor_name": name,
                        "actor_tax_code": actor_tax_code,
                        "actor_role": actor_role,
                        "confidence": confidence,
                        "raw_confidence": row.get("confidence", ""),
                        "source_type": row.get("source_type", ""),
                        "source_url": row.get("source_url", ""),
                        "checked_at": row.get("checked_at", ""),
                    }
                )

    # Deduplica finale: per stesso progetto/CIG/nome azienda tiene la riga migliore.
    best_by_actor = {}

    for row in clean_rows:
        key = (
            row.get("project_key", ""),
            row.get("matched_cigs", ""),
            norm(row.get("actor_name", "")),
        )

        current = best_by_actor.get(key)

        if current is None:
            best_by_actor[key] = row
            continue

        row_score = int(row.get("confidence") or 0)
        current_score = int(current.get("confidence") or 0)

        row_has_tax = bool(clean(row.get("actor_tax_code")))
        current_has_tax = bool(clean(current.get("actor_tax_code")))

        if (row_has_tax and not current_has_tax) or row_score > current_score:
            best_by_actor[key] = row

    clean_rows = list(best_by_actor.values())

    clean_rows.sort(
        key=lambda r: (
            r["project_key"],
            r["actor_name"],
            r["actor_tax_code"],
        )
    )

    fieldnames = [
        "project_key",
        "cup",
        "cig",
        "matched_cups",
        "matched_cigs",
        "ente",
        "tenant_domain",
        "actor_name",
        "actor_tax_code",
        "actor_role",
        "confidence",
        "raw_confidence",
        "source_type",
        "source_url",
        "checked_at",
    ]

    write_csv(args.out, clean_rows, fieldnames)

    summary = {
        "input_rows": len(rows),
        "clean_actor_rows": len(clean_rows),
        "output": str(args.out),
    }

    args.summary_out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Input rows:", len(rows))
    print("Clean actor rows:", len(clean_rows))
    print("Output:")
    print("-", args.out)
    print("-", args.summary_out)


if __name__ == "__main__":
    raise SystemExit(main())
