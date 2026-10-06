#!/usr/bin/env python3
"""D3: immutable, page-backed documentary reviews; never promote the canonico.

Structural validation is not semantic truth certification. An assistant/reviewer
supplies interpreted claims after inspecting the cited pages. Source hashes,
page anchors, role scope and timing semantics are checked before atomic import.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

KINDS = {'attribute', 'company_role', 'contact', 'schedule', 'issue'}
SCOPES = {'project', 'lot', 'shared_works', 'corporate', 'reviewed_subset'}
EXECUTION_ROLES = {'epc', 'bop_civil', 'bop_electrical', 'foundation_contractor', 'installation_contractor'}


class ReviewError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReviewError(message)


def normalized(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip().casefold()


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def hash_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inside(root, relative):
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), 'Path escapes the documentary archive')
    return path


class Reviews:
    def __init__(self, root):
        self.root = Path(root)
        require((self.root / 'audit.sqlite').is_file(), 'D1/D2 ledger missing')
        self.db = sqlite3.connect(self.root / 'audit.sqlite')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS documentary_reviews(
          review_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
          body_sha256 TEXT NOT NULL, body_json TEXT NOT NULL, imported_at TEXT NOT NULL);
        ''')
        self.db.commit()

    def close(self):
        self.db.close()

    def evidence(self, entry):
        require(entry.get('evidence'), 'At least one exact source/page is mandatory')
        texts, sources = [], []
        for evidence in entry['evidence']:
            sha = evidence.get('sha256', '')
            require(re.fullmatch(r'[a-f0-9]{64}', sha), 'Invalid SHA-256')
            row = self.db.execute('''SELECT d.id,d.project_id,d.url,d.label,v.extraction_json,
                  h.sha256 AS head_sha256 FROM documents d
                  JOIN versions v ON v.doc_id=d.id
                  LEFT JOIN document_heads h ON h.doc_id=d.id
                  WHERE d.project_id=? AND d.url=? AND v.sha256=?''',
                  (entry['project_id'], evidence.get('url'), sha)).fetchone()
            require(row is not None, 'Source version not acquired for this project')
            extraction = json.loads(row['extraction_json'])
            require(extraction.get('kind') == 'pdf', 'D3 review pilot requires a PDF source')
            original = inside(self.root, f'objects/{sha}.pdf')
            require(original.is_file() and hash_file(original) == sha, 'Original absent or hash mismatch')
            page = evidence.get('page')
            require(type(page) is int and page > 0, 'PDF page must be a positive integer')
            pages = {p['page']: p for p in extraction.get('pages', [])}
            require(page in pages, 'Page absent from acquired version')
            text = pages[page].get('text', '')
            anchor = normalized(evidence.get('anchor'))
            require(len(anchor) >= 8 and anchor in normalized(text), 'Page anchor not found')
            mode = evidence.get('reading_mode')
            require(mode in {'text', 'text_and_visual'}, 'Explicit reading mode required')
            if mode == 'text_and_visual':
                require(bool(evidence.get('visual_note')), 'Visual review needs an observation')
            texts.append(text)
            sources.append({'doc_id': row['id'], 'url': row['url'], 'label': row['label'],
                'sha256': sha, 'page': page, 'reading_mode': mode,
                'head_matches_reviewed_version': row['head_sha256'] == sha})
        return '\n'.join(texts), sources

    def validate(self, entry):
        require(isinstance(entry, dict), 'Review must be an object')
        require(re.fullmatch(r'[A-Za-z0-9_-]+', entry.get('id', '')), 'Stable review ID required')
        require(entry.get('kind') in KINDS, 'Unsupported review kind')
        require(entry.get('scope') in SCOPES, 'Explicit scope required')
        require(isinstance(entry.get('value'), dict), 'Value must be an object')
        require(bool(entry.get('statement')) and bool(entry.get('limits')), 'Statement and limits are mandatory')
        require(entry.get('reviewer') == 'assistant_document_review', 'Explicit reviewer provenance required')
        date.fromisoformat(entry['reviewed_on'])
        if entry.get('document_date') is not None:
            date.fromisoformat(entry['document_date'])
        pid = entry.get('project_id')
        known = self.db.execute('SELECT 1 FROM projects WHERE id=? UNION SELECT 1 FROM qualification WHERE id=?', (pid, pid)).fetchone()
        require(known is not None, 'Unknown project/qualification identity')
        text, sources = self.evidence(entry)
        value, kind = entry['value'], entry['kind']
        if kind == 'company_role':
            require(value.get('company') and value.get('role') and value.get('relationship'), 'Company, role and relationship required')
            if value['role'] in EXECUTION_ROLES:
                require(entry['scope'] in {'project', 'lot'}, 'Corporate/shared evidence cannot close EPC scope')
                require(value['relationship'] == 'explicit_execution_award', 'Execution award requires explicit project evidence')
                require(value.get('award_basis') in {'contract', 'public_award', 'company_explicit_project_statement'}, 'Missing award basis')
                require(bool(value.get('award_review_note')), 'Execution role must be explicitly reviewed')
            if value['relationship'] == 'corporate_capability':
                require(entry['scope'] == 'corporate', 'Corporate capability is not a project award')
        if kind == 'contact':
            allowed = {'name', 'company', 'role', 'email', 'phone', 'endpoint_scope', 'source_designation'}
            require(set(value) <= allowed, 'Unsupported/private contact field')
            require(value.get('company') and value.get('role') and value.get('source_designation'), 'Contact role/context missing')
            require(value.get('endpoint_scope') in {'company_project', 'corporate', 'press', 'public_authority'}, 'Contact endpoint scope missing')
            for key in ('name', 'email'):
                if value.get(key):
                    require(normalized(value[key]) in normalized(text), f'{key} is not literal source evidence')
            if value.get('phone'):
                digits = re.sub(r'\D', '', value['phone'])
                require(len(digits) >= 6 and digits in re.sub(r'\D', '', text), 'Phone not in source')
        if kind == 'schedule':
            basis = value.get('basis')
            require(basis in {'document_relative', 'publisher_forecast', 'analyst_estimate'}, 'Timing basis required')
            if basis == 'document_relative':
                require(value.get('unit') in {'months', 'weeks'}, 'Relative schedule unit missing')
                require(not value.get('start_date') and not value.get('end_date'), 'No calendar dates from relative Gantt')
                if value.get('duration') is not None:
                    require(type(value['duration']) in (int, float) and math.isfinite(value['duration']) and value['duration'] > 0, 'Invalid duration')
                else:
                    require(type(value.get('start_period')) is int and type(value.get('end_period')) is int
                        and 1 <= value['start_period'] <= value['end_period'], 'Invalid relative interval')
            elif basis == 'publisher_forecast':
                require(value.get('target') and value.get('precision') in {'year', 'quarter', 'month', 'day'}, 'Forecast precision required')
            else:
                require(value.get('assumptions') and value.get('dependencies') and value.get('anchor_review_id')
                    and value.get('earliest') and value.get('latest'), 'Estimate basis/range missing')
        if kind == 'attribute' and value.get('field') in {'grid_injection_mw', 'wtg_count', 'wtg_unit_mw', 'installed_wind_mw'}:
            require(value.get('qualifier') in {'declared', 'maximum', 'provisional'}, 'Configuration qualifier required')
        return sources

    def import_batch(self, batch):
        entries = batch.get('reviews', [])
        require(batch.get('schema_version') == '1.0' and entries, 'Nonempty versioned review batch required')
        require(len({e['id'] for e in entries}) == len(entries), 'Duplicate review IDs in batch')
        prepared = []
        for entry in entries:
            self.validate(entry)
            body = canonical_json(entry)
            sha = hashlib.sha256(body.encode()).hexdigest()
            old = self.db.execute('SELECT body_sha256 FROM documentary_reviews WHERE review_id=?', (entry['id'],)).fetchone()
            require(old is None or old[0] == sha, 'Immutable review changed: use a new ID')
            prepared.append((entry['id'], entry['project_id'], sha, body, datetime.now(timezone.utc).isoformat()))
        # No partial import when any source, page, claim or immutable ID fails validation.
        before = self.db.total_changes
        with self.db:
            self.db.executemany('INSERT OR IGNORE INTO documentary_reviews VALUES(?,?,?,?,?)', prepared)
        return self.db.total_changes - before

    def export(self):
        reviews = []
        for row in self.db.execute('SELECT body_json FROM documentary_reviews ORDER BY project_id,review_id'):
            entry = json.loads(row[0])
            try:
                sources = self.validate(entry)
                state = 'pinned_evidence_available' if all(s['head_matches_reviewed_version'] for s in sources) else 'source_version_changed_review_required'
                issue = None
            except (ReviewError, ValueError, KeyError) as exc:
                sources, state, issue = [], 'evidence_unavailable_review_required', str(exc)
            reviews.append({**entry, 'evidence_integrity': state, 'sources': sources, 'integrity_issue': issue,
                'commercial_currentness_certified': False})
        report = {'schema_version': '1.0', 'generated_at': datetime.now(timezone.utc).isoformat(),
            'reviews': reviews, 'review_count': len(reviews), 'projects_with_review': len({r['project_id'] for r in reviews}),
            'complete_dossiers': 0, 'canonical_writes': 0,
            'guard': 'Riscontri su documenti e pagine specifici, non certificazione integrale del fascicolo o dell’attualità commerciale. Nessuna promozione automatica.'}
        (self.root / 'review-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        cards = []
        for r in reviews:
            refs = ''.join(f'<li><a href="{escape(s["url"], quote=True)}">Fonte</a> · pagina PDF {s["page"]} · {escape(s["reading_mode"])} · SHA {s["sha256"][:12]}</li>' for s in r['sources'])
            cards.append('<article><h2>' + escape(r['project_id']) + ' · ' + escape(r['kind']) + '</h2><p><b>' + escape(r['statement']) + '</b></p><pre>' + escape(json.dumps(r['value'], ensure_ascii=False, indent=2)) + '</pre><p class="limits">Limiti: ' + escape(r['limits']) + '</p><p>Integrità: ' + escape(r['evidence_integrity']) + '</p><ul>' + refs + '</ul></article>')
        html = '<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wind — riscontri documentali D3</title><style>body{font:16px/1.5 system-ui;background:#f2f5f5;color:#192e34;max-width:1040px;margin:36px auto;padding:0 20px}article{background:#fff;border:1px solid #d5e0df;border-radius:12px;padding:20px;margin:18px 0}h1{font-size:30px}h2{font-size:19px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}.limits{border-left:4px solid #ae730a;padding:8px 12px;background:#fff7e8}a{color:#006e5d}li{overflow-wrap:anywhere}</style><h1>Wind Radar — riscontri documentali</h1><p>' + escape(report['guard']) + '</p><p><b>' + str(len(reviews)) + ' riscontri · ' + str(report['projects_with_review']) + ' progetti/record · 0 fascicoli completi</b></p>' + ''.join(cards) + '</html>'
        (self.root / 'review-report.html').write_text(html, encoding='utf-8')
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--reviews', required=True)
    args = parser.parse_args()
    store = Reviews(args.output)
    try:
        added = store.import_batch(json.loads(Path(args.reviews).read_text(encoding='utf-8')))
        report = store.export()
        print(json.dumps({'new_reviews': added, 'review_count': report['review_count'], 'projects': report['projects_with_review'], 'complete_dossiers': 0}))
    finally:
        store.close()


if __name__ == '__main__':
    main()
