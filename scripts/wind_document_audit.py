#!/usr/bin/env python3
"""Additive document-access/reading ledger. Never writes the Wind canonical data.

Extracted text and regex mentions are NOT validated facts. Every document and
page remains pending review, including drawings and apparently empty PDF pages.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import socket
import ipaddress
import sqlite3
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urldefrag

import requests
from pypdf import PdfReader

VERSION = '0.1.0'
MAX_BYTES = 30 * 1024 * 1024
ALLOWED_HOSTS = ('va.mite.gov.it', 'va.mase.gov.it', 'regione.marche.it',
                 'regione.sicilia.it', 'regione.liguria.it', 'regione.toscana.it',
                 'rete.toscana.it', 'rwe.com', 'renexia.it', 'gazzettaufficiale.it')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(value: bytes):
    return hashlib.sha256(value).hexdigest()


def compact(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def validate_url(url, *, resolve=True):
    parts = urlsplit(url)
    host = (parts.hostname or '').lower()
    if parts.scheme not in ('https', 'http') or parts.username or parts.password:
        raise ValueError('Unsupported URL scheme/credentials')
    if parts.port not in (None, 80, 443):
        raise ValueError('Unsupported port')
    if not any(host == root or host.endswith('.' + root) for root in ALLOWED_HOSTS):
        raise ValueError('Host not approved for this pilot: ' + host)
    if resolve:
        for address in socket.getaddrinfo(host, parts.port or 443):
            if not ipaddress.ip_address(address[4][0]).is_global:
                raise ValueError('Non-public destination refused')
    return urldefrag(url)[0]


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.parts, self.current, self.label = [], [], None, []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'a':
            self.current, self.label = dict(attrs).get('href'), []

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag == 'a' and self.current:
            self.links.append((self.current, compact(' '.join(self.label))))
            self.current = None

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)
            if self.current:
                self.label.append(data)


def parse_asset(body, content_type='', expected='auto'):
    """Return page-local text without claiming semantic/visual completion."""
    if b'%PDF-' in body[:1024]:
        try:
            reader = PdfReader(io.BytesIO(body), strict=False)
            if reader.is_encrypted and not reader.decrypt(''):
                return {'status': 'encrypted', 'pages': [], 'kind': 'pdf'}
            pages = []
            for number, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text() or ''
                    issue = None
                except Exception as exc:
                    text, issue = '', type(exc).__name__ + ': ' + str(exc)[:200]
                pages.append({'page': number, 'text': text,
                              'text_characters': len(compact(text)),
                              'needs_visual_review': True,
                              'text_status': 'extracted' if len(compact(text)) >= 40 else 'scanned_or_low_text',
                              'extraction_error': issue})
            state = 'text_extracted_pending_review'
            if not pages:
                state = 'invalid_pdf'
            elif any(p['text_status'] != 'extracted' for p in pages):
                state = 'partial_text_needs_visual_review'
            return {'status': state, 'kind': 'pdf', 'pages': pages,
                    'page_count': len(pages), 'links': [], 'inventory_complete': False}
        except Exception as exc:
            return {'status': 'invalid_pdf', 'kind': 'pdf', 'pages': [],
                    'error': type(exc).__name__ + ': ' + str(exc)[:200]}
    if expected == 'pdf':
        return {'status': 'not_a_pdf', 'kind': 'unexpected_response', 'pages': []}
    if 'html' in content_type.lower() or b'<html' in body[:2048].lower() or b'<!doctype html' in body[:2048].lower():
        parser = Links()
        parser.feed(body.decode('utf-8', errors='replace'))
        text = compact(' '.join(parser.parts))
        block = any(t in text.lower() for t in ('access denied', 'verify you are human', 'just a moment...', 'request rejected'))
        return {'status': 'access_challenge' if block else 'html_read_inventory_unconfirmed',
                'kind': 'html', 'pages': [{'page': 1, 'text': text, 'text_characters': len(text),
                'needs_visual_review': False, 'text_status': 'extracted'}],
                'links': parser.links if not block else [], 'inventory_complete': False}
    return {'status': 'unsupported_format', 'kind': 'binary', 'pages': []}


def power_mentions(text):
    """All numeric mentions, not automatically total wind MW or active design."""
    pattern = r'(?<![\w.,])([0-9]+(?:[.\s][0-9]{3})*(?:,[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(MWe|MWp|MW|kWp|kW)\b'
    found = []
    for match in re.finditer(pattern, text, re.I):
        raw, unit = re.sub(r'\s', '', match[1]), match[2]
        if ',' in raw:
            number = float(raw.replace('.', '').replace(',', '.'))
        elif unit.lower().startswith('kw') and re.fullmatch(r'\d{1,3}(?:\.\d{3})+', raw):
            number = float(raw.replace('.', ''))
        else:
            number = float(raw)
        found.append({'field': 'power_mention', 'source_value': match[0],
                      'normalized_mw': number / 1000 if unit.lower().startswith('kw') else number,
                      'context': compact(text[max(0, match.start()-120):match.end()+180]),
                      'review_status': 'unverified', 'scope': 'unassigned'})
    return found


class Ledger:
    def __init__(self, directory):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / 'objects').mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / 'audit.sqlite')
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT, bucket TEXT, inherited_json TEXT);
        CREATE TABLE IF NOT EXISTS qualification(id TEXT PRIMARY KEY, linked_project TEXT, inherited_json TEXT);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, project_id TEXT, url TEXT, label TEXT,
          expected TEXT, parent_id TEXT, discovered_at TEXT, UNIQUE(project_id,url));
        CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, doc_id TEXT, checked_at TEXT,
          status TEXT, http_status INTEGER, detail TEXT, elapsed REAL, final_url TEXT);
        CREATE TABLE IF NOT EXISTS versions(doc_id TEXT, sha256 TEXT, captured_at TEXT, byte_count INTEGER,
          etag TEXT, modified TEXT, extraction_json TEXT, PRIMARY KEY(doc_id,sha256));
        CREATE TABLE IF NOT EXISTS document_heads(doc_id TEXT PRIMARY KEY, sha256 TEXT);
        CREATE TABLE IF NOT EXISTS observations(doc_id TEXT, sha256 TEXT, page INTEGER, item_json TEXT,
          UNIQUE(doc_id,sha256,page,item_json));
        ''')
        self.db.commit()

    def seed(self, repo):
        data = Path(repo) / 'docs/wind/data'
        manifest = json.loads((data / 'projects.json').read_text(encoding='utf-8-sig'))
        canonical = []
        for chunk in manifest['chunks']:
            canonical.extend(json.loads((data / chunk).read_text(encoding='utf-8-sig')))
        paths = sorted(set(data.glob('discovery-v04*.json')) | set(data.glob('discovery-census-v04*.json')))
        rows = []
        for path in paths:
            rows.extend((row['candidate_id'], row, path.name) for row in json.loads(path.read_text(encoding='utf-8-sig')).get('candidates', []))
        rows.extend((row['id'], row, 'canonical') for row in canonical)
        # Canonical representation takes precedence; provenance remains in repo.
        for pid, row, origin in rows:
            bucket = 'canonical' if origin == 'canonical' else ('rejected' if row.get('status') == 'rejected' else
                     'recency_review' if row.get('activity_class') == 'stale_scoping' else 'discovery_current')
            self.db.execute('INSERT INTO projects VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,bucket=excluded.bucket,inherited_json=excluded.inherited_json',
                            (pid, row.get('name'), bucket, json.dumps({'origin': origin, 'record': row}, ensure_ascii=False)))
        self.db.commit()

    def import_qualification(self, path):
        rows = json.loads(Path(path).read_text(encoding='utf-8'))['records']
        for row in rows:
            self.db.execute('INSERT INTO qualification VALUES(?,?,?) ON CONFLICT(id) DO NOTHING',
                            (row['id'], row.get('linked_project'), json.dumps(row, ensure_ascii=False)))
        self.db.commit()

    def register(self, project_id, url, label='', expected='auto', parent_id=None):
        url = validate_url(url, resolve=False)
        did = digest((project_id + '|' + url).encode())[:24]
        self.db.execute('INSERT OR IGNORE INTO documents VALUES(?,?,?,?,?,?,?)',
                        (did, project_id, url, label, expected, parent_id, now()))
        self.db.commit()
        return did

    def persist(self, did, body, content_type, *, etag='', modified=''):
        doc = self.db.execute('SELECT * FROM documents WHERE id=?', (did,)).fetchone()
        sha = digest(body)
        existing = self.db.execute('SELECT extraction_json FROM versions WHERE doc_id=? AND sha256=?', (did, sha)).fetchone()
        self.db.execute('INSERT INTO document_heads VALUES(?,?) ON CONFLICT(doc_id) DO UPDATE SET sha256=excluded.sha256', (did, sha))
        self.db.commit()
        if existing:
            return 'unchanged_content', json.loads(existing[0])
        result = parse_asset(body, content_type, doc['expected'])
        extension = '.pdf' if result['kind'] == 'pdf' else '.bin'
        (self.root / 'objects' / (sha + extension)).write_bytes(body)
        self.db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?)',
                        (did, sha, now(), len(body), etag, modified, json.dumps(result, ensure_ascii=False)))
        if result['status'] not in ('access_challenge', 'not_a_pdf'):
            for page in result.get('pages', []):
                for item in power_mentions(page['text']):
                    self.db.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?)',
                                    (did, sha, page['page'], json.dumps(item, ensure_ascii=False)))
        self.db.commit()
        return result['status'], result

    def fetch(self, did, session=None):
        doc = self.db.execute('SELECT * FROM documents WHERE id=?', (did,)).fetchone()
        started, code, final, result = time.monotonic(), None, doc['url'], None
        own = session is None
        session = session or requests.Session()
        detail = ''
        try:
            for _ in range(6):
                validate_url(final)
                response = session.get(final, timeout=(6, 20), stream=True, allow_redirects=False,
                                       headers={'User-Agent': 'WindDocumentAudit/0.1 (+document review)'})
                code = response.status_code
                if code in (301, 302, 303, 307, 308):
                    target = response.headers.get('Location')
                    response.close()
                    if not target:
                        raise ValueError('Redirect without Location')
                    final = urljoin(final, target)
                    continue
                try:
                    if code >= 400:
                        status, detail = 'http_error', 'HTTP ' + str(code)
                        break
                    data = bytearray()
                    for block in response.iter_content(65536):
                        data.extend(block)
                        if len(data) > MAX_BYTES:
                            raise ValueError('Download exceeds 30 MiB; needs separately scheduled acquisition')
                        if time.monotonic() - started > 90:
                            raise TimeoutError('Overall asset download budget exceeded')
                    status, result = self.persist(did, bytes(data), response.headers.get('Content-Type', ''),
                        etag=response.headers.get('ETag', ''), modified=response.headers.get('Last-Modified', ''))
                finally:
                    response.close()
                break
            else:
                raise ValueError('Redirect limit exceeded')
        except Exception as exc:
            status, detail = 'access_failed', type(exc).__name__ + ': ' + str(exc)[:400]
        finally:
            if own:
                session.close()
        self.db.execute('INSERT INTO attempts(doc_id,checked_at,status,http_status,detail,elapsed,final_url) VALUES(?,?,?,?,?,?,?)',
                        (did, now(), status, code, detail, round(time.monotonic()-started, 2), final))
        self.db.commit()
        # Every linked file is registered, not silently dropped at a processing cap.
        if result:
            for href, label in result.get('links', []):
                url = urljoin(final, href)
                if re.search(r'\.(pdf|zip|p7m)(?:[?#]|$)|/File/Documento/', url, re.I):
                    try:
                        self.register(doc['project_id'], url, label, 'pdf' if '.pdf' in url.lower() or '/File/Documento/' in url else 'auto', did)
                    except ValueError:
                        # Unapproved hosts are recorded as unresolved discovery, not fetched.
                        self.db.execute('INSERT INTO attempts(doc_id,checked_at,status,detail) VALUES(?,?,?,?)',
                            (did, now(), 'linked_host_needs_approval', url))
                        self.db.commit()
        return status

    def export(self):
        assets = []
        for doc in self.db.execute('SELECT * FROM documents ORDER BY project_id,url').fetchall():
            row = dict(doc)
            row['attempts'] = [dict(r) for r in self.db.execute('SELECT * FROM attempts WHERE doc_id=? ORDER BY id', (doc['id'],))]
            row['versions'] = []
            for version in self.db.execute('SELECT * FROM versions WHERE doc_id=? ORDER BY captured_at,rowid', (doc['id'],)):
                v = dict(version)
                v['extraction'] = json.loads(v.pop('extraction_json'))
                row['versions'].append(v)
            head = self.db.execute('SELECT sha256 FROM document_heads WHERE doc_id=?', (doc['id'],)).fetchone()
            row['current_sha256'] = head[0] if head else None
            row['current_extraction'] = next((v['extraction'] for v in row['versions'] if v['sha256'] == row['current_sha256']), {})
            row['document_review_status'] = 'not_reviewed'
            row['fascicolo_complete'] = False
            assets.append(row)
        counts = dict(self.db.execute('SELECT bucket,COUNT(*) FROM projects GROUP BY bucket').fetchall())
        report = {'schema_version': VERSION, 'generated_at': now(), 'registry_counts': counts,
                  'qualification_records': self.db.execute('SELECT COUNT(*) FROM qualification').fetchone()[0],
                  'qualification_unlinked': self.db.execute('SELECT COUNT(*) FROM qualification WHERE linked_project IS NULL OR linked_project=""').fetchone()[0],
                  'documents': assets, 'guard': 'Access and text extraction only. No complete dossier, EPC award, contact role, schedule or canonical promotion certified.'}
        (self.root / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        lines = ['# Wind — collaudo documentale', '', report['guard'], '', '| Progetto | Risorsa | Ultimo accesso | Pagine PDF | Stato lettura |', '|---|---|---|---|---|']
        for row in assets:
            latest = row['current_extraction']
            attempt = row['attempts'][-1] if row['attempts'] else {'status':'not_attempted'}
            lines.append('| ' + ' | '.join([row['project_id'], row['label'].replace('|','/'), attempt['status'], str(latest.get('page_count', '-')), latest.get('status', 'not_read')]) + ' |')
        (self.root / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/wind-document-audit')
    parser.add_argument('--seed-repo')
    parser.add_argument('--qualification-json')
    parser.add_argument('--manifest')
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--follow-limit', type=int, default=0)
    args = parser.parse_args()
    ledger = Ledger(args.output)
    try:
        if args.seed_repo:
            ledger.seed(args.seed_repo)
        if args.qualification_json:
            ledger.import_qualification(args.qualification_json)
        seeds = []
        if args.manifest:
            manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
            for row in manifest['assets']:
                seeds.append(ledger.register(row['project_id'], row['url'], row['label'], row.get('expected', 'auto')))
        if args.fetch:
            for did in seeds:
                print(did, ledger.fetch(did), flush=True)
            pending = ledger.db.execute('SELECT id FROM documents WHERE parent_id IS NOT NULL AND id NOT IN (SELECT doc_id FROM attempts) ORDER BY id LIMIT ?', (max(0, args.follow_limit),)).fetchall()
            for row in pending:
                print(row[0], ledger.fetch(row[0]), flush=True)
        report = ledger.export()
        print(json.dumps({'registry_counts': report['registry_counts'], 'documents': len(report['documents']), 'fascicoli_certificati_completi': 0}))
    finally:
        ledger.db.close()


if __name__ == '__main__':
    main()
