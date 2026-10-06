# Wind document audit — D1 / 0.1.0

## 2026-10-05 — first executable block

This is an additive access and extraction ledger, not a replacement for the daily radar.
The existing BAT, UI, canonical 51 projects and discovery matcher are unchanged.

Implemented:
- Seed all canonical and Discovery registries, including `discovery-census-v04*.json`, with canonical precedence by ID.
- Import 57 qualification source records (53 not linked to an existing ID), with spreadsheet SHA-256 and row provenance. These are NOT 53 certified new projects.
- Separate SQLite ledger for project identities, pending source records, document URLs, all access attempts, content-addressed file versions and page-local text.
- Distinguish index access, actual file bytes, PDF parsing, low-text/scanned pages, HTTP errors, unsupported formats and documents not yet reviewed.
- Numeric power mentions retain context/page and are unverified/unassigned. Turbine power, BESS, historical configuration and total wind power are never silently equated.
- Readable text is not a reviewed drawing/table or a complete dossier. All new pages remain pending visual/content review.
- A failed subsequent access does not delete the previously acquired file. Identical bytes reuse extraction; returning to an older version uses the correct current hash.
- HTML returned instead of an expected PDF is an explicit failure, not a successful PDF acquisition.
- Download limits and a strict public-host allowlist; no credential/login/CAPTCHA circumvention; no emails or contacts generated or messaged.
- Six seed resources test incomplete records, a published onshore project, Discovery and offshore. Up to three linked documents are downloaded in this bounded pilot; other discovered links remain pending.

## Execution

Install `requirements-wind-documents.txt` in an isolated runtime, then:

```text
python scripts/wind_document_audit.py --seed-repo . --qualification-json config/wind_document_qualification_seed.json --manifest config/wind_document_pilot.json --fetch --follow-limit 3
```

Default archive: `data/wind-document-audit/` (separate from `data/wind_agent.sqlite`).
The pilot workflow uses `reports/wind-document-audit/` and exports SQLite, original bytes, JSON and a Markdown access summary. Actions artifacts are temporary, not the production archive.

## Deliberately not claimed complete

D1 does not yet traverse every paginated/dynamic project portal, read every drawing, perform OCR, unwrap P7M/ZIP bundles, validate EPC roles/contacts or calculate schedules. An HTML index never certifies full inventory coverage. All these residuals remain explicit.

Next acceptance gates:
1. Per-portal exhaustive inventory with pagination/version/attachment checks and no silent cap.
2. Page-level visual/OCR fallback and content review with exact document hash + page provenance.
3. Evidence-backed fact and company-role review. Public-administration contacts, engineering firms and EPC contractors stay distinct.
4. Separate source dates, relative durations and assumption-backed schedule estimates.
5. Backfill across all 96 registered identities; qualify unresolved source records without excluding them solely for missing MW.

Test coverage includes HTML-for-PDF, access challenges, scanned/mixed pages, immutable versions, failed-access retention, URL restrictions, kW conversion and registry/canonical separation. A green pilot proves execution and at least one real PDF extraction, NOT a completed commercial audit.
