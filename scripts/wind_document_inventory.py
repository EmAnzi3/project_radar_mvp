#!/usr/bin/env python3
"""D2: complete MASE index inventory, bounded large downloads and visual queue.

This module extends the D1 ledger. An inventory is not a read dossier, an
extracted page is not a reviewed page, and no observation is an EPC award.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def file_hash(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class IndexParser(HTMLParser):
    """Read table cells and actual links; no guesses at attachment identifiers."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.rows = [], [], []
        self.cells, self.cell, self.row_links = None, None, []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'tr':
            self.cells, self.row_links = [], []
        if tag in ('td', 'th') and self.cells is not None:
            self.cell = []
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)
                if self.cells is not None:
                    self.row_links.append(href)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag in ('td', 'th') and self.cell is not None:
            self.cells.append(clean(' '.join(self.cell)))
            self.cell = None
        if tag == 'tr' and self.cells is not None:
            self.rows.append((self.cells, self.row_links))
            self.cells = None

    def handle_data(self, text):
        if not self.hidden:
            self.text.append(text)
            if self.cell is not None:
                self.cell.append(text)


def index_scope(url):
    p = urlsplit(url)
    return (p.scheme, p.netloc.lower(), p.path.rstrip('/'),
            tuple(sorted((k, v) for k, v in parse_qsl(p.query) if k != 'pagina')))


def page_url(root, page):
    p = urlsplit(root)
    query = [(k, v) for k, v in parse_qsl(p.query) if k != 'pagina']
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(query + [('pagina', str(page))]), ''))


def parse_index(body, root):
    parser = IndexParser()
    parser.feed(body.decode('utf-8-sig', errors='replace'))
    text = clean(' '.join(parser.text))
    count = re.search(r'\(n\.?\s*([\d.]+)\)\s*Documenti', text, re.I)
    pager = re.search(r'Pagina\s+(\d+)\s+di\s+(\d+)', text, re.I)
    if not count or not pager:
        raise ValueError('Index counters absent: blocked response or unrecognized layout')
    expected, current, pages = int(count[1].replace('.', '')), int(pager[1]), int(pager[2])
    if not 1 <= current <= pages or pages > 10000:
        raise ValueError('Invalid pagination counters')
    observed_paging = any(index_scope(urljoin(root, href)) == index_scope(root)
                          and 'pagina' in dict(parse_qsl(urlsplit(href).query))
                          for href in parser.links)
    if pages > 1 and not observed_paging:
        raise ValueError('No same-scope pagination link: refuse fabricated navigation')
    rows = []
    for cells, links in parser.rows:
        for href in links:
            if not re.search(r'/File/Documento/\d+|\.(?:pdf|zip|p7m)(?:[?#]|$)', href, re.I):
                continue
            if len(cells) < 7:
                raise ValueError('Attachment row has incomplete metadata')
            rows.append({'url': urljoin(root, href), 'title': cells[0], 'filename': cells[1],
                         'section': cells[2], 'code': cells[3], 'published': cells[4],
                         'scale': cells[5], 'declared_size': cells[6]})
    return {'expected': expected, 'current': current, 'pages': pages, 'rows': rows}


class AcquisitionError(RuntimeError):
    def __init__(self, status, detail):
        super().__init__(detail)
        self.status = status


def stream_download(url, destination, *, validate, session=None, max_bytes=256 * 1024**2,
                    budget=180, clock=time.monotonic):
    """Resume only with a stable validator and verified Content-Range.

    A 200 response to a Range request restarts, never concatenates. Partial bytes
    remain on disk and are never presented as a complete original.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_suffix('.part')
    state = destination.with_suffix('.transfer.json')
    saved = json.loads(state.read_text()) if state.exists() else {}
    offset = part.stat().st_size if part.exists() else 0
    validator = saved.get('validator') if saved.get('source_url') == url else None
    if not validator:
        offset = 0
    headers = {'User-Agent': 'WindDocumentAudit/0.2', 'Accept-Encoding': 'identity'}
    if offset:
        headers.update({'Range': f'bytes={offset}-', 'If-Range': validator})
    own, client = session is None, session or requests.Session()
    start, final, response, code = clock(), url, None, None
    result = {'source_url': url, 'started_at': stamp(), 'resumed_from': offset}
    try:
        for _ in range(6):
            validate(final)
            response = client.get(final, headers=headers, timeout=(8, 30),
                                  stream=True, allow_redirects=False)
            code = response.status_code
            if code not in (301, 302, 303, 307, 308):
                break
            target = response.headers.get('Location')
            response.close()
            if not target:
                raise AcquisitionError('invalid_redirect', 'Redirect without Location')
            final = urljoin(final, target)
        else:
            raise AcquisitionError('redirect_limit', 'Too many redirects')
        if code not in (200, 206):
            raise AcquisitionError('http_error', f'HTTP {code}')
        encoding = response.headers.get('Content-Encoding', 'identity').lower()
        if encoding not in ('', 'identity'):
            raise AcquisitionError('unsupported_transfer_encoding', encoding)
        total = None
        if code == 206:
            span = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
            if not span or not offset or int(span[1]) != offset or int(span[2]) + 1 != int(span[3]):
                raise AcquisitionError('invalid_range', 'Partial response does not match saved offset/full suffix')
            if saved.get('final_url') != final:
                raise AcquisitionError('invalid_range', 'Resume destination changed')
            total = int(span[3])
            received_etag = response.headers.get('ETag')
            if received_etag and saved.get('etag') and received_etag != saved['etag']:
                raise AcquisitionError('invalid_range', 'ETag changed during resume')
        else:
            offset = 0
            if response.headers.get('Content-Length'):
                total = int(response.headers['Content-Length'])
        result['resumed_from'] = offset
        if total and total > max_bytes:
            raise AcquisitionError('deferred_size_limit', f'Declared {total} bytes; limit {max_bytes}')
        required = (total - offset if total else min(max_bytes, 64 * 1024**2)) + 64 * 1024**2
        if shutil.disk_usage(destination.parent).free < required:
            raise AcquisitionError('deferred_disk_space', 'Insufficient disk reserve')
        etag = response.headers.get('ETag', '')
        validator = etag if etag and not etag.startswith('W/') else response.headers.get('Last-Modified')
        saved = {'source_url': url, 'final_url': final, 'validator': validator,
                 'etag': etag, 'expected_bytes': total}
        state.write_text(json.dumps(saved), encoding='utf-8')
        written = offset
        with part.open('ab' if offset else 'wb') as out:
            for chunk in response.iter_content(128 * 1024):
                if clock() - start > budget:
                    raise AcquisitionError('partial_time_budget', 'Download time budget reached; partial retained')
                if written + len(chunk) > max_bytes:
                    raise AcquisitionError('deferred_size_limit', f'Observed bytes exceed {max_bytes}; partial retained')
                out.write(chunk)
                written += len(chunk)
        if total is not None and written != total:
            raise AcquisitionError('partial_length_mismatch', f'Received {written}; expected {total}')
        if not written:
            raise AcquisitionError('empty_response', 'Zero-byte response')
        part.replace(destination)
        state.unlink(missing_ok=True)
        result.update(status='downloaded', path=str(destination), bytes=written,
                      sha256=file_hash(destination), content_type=response.headers.get('Content-Type', ''),
                      etag=etag, modified=response.headers.get('Last-Modified', ''), expected_bytes=total)
    except Exception as exc:
        result.update(status=getattr(exc, 'status', 'network_error'), detail=f'{type(exc).__name__}: {exc}',
                      partial_bytes=part.stat().st_size if part.exists() else 0)
    finally:
        if response is not None:
            response.close()
        if own:
            client.close()
    result.update(http_status=code, final_url=final, seconds=round(clock() - start, 3))
    return result


def extract_file(path):
    """Page-local extraction from disk. All pages remain pending semantic/visual review."""
    from pypdf import PdfReader
    path = Path(path)
    with path.open('rb') as stream:
        prefix = stream.read(1024)
    if b'%PDF-' not in prefix:
        kind = 'zip' if prefix.startswith(b'PK\x03\x04') else 'non_pdf'
        return {'kind': kind, 'status': 'container_pending_unpack' if kind == 'zip' else 'not_a_pdf', 'pages': []}
    pages = []
    try:
        with path.open('rb') as stream:
            reader = PdfReader(stream, strict=False)
            if reader.is_encrypted and not reader.decrypt(''):
                return {'kind': 'pdf', 'status': 'encrypted', 'pages': []}
            for number, page in enumerate(reader.pages, 1):
                error = None
                try:
                    text = page.extract_text() or ''
                except Exception as exc:
                    text, error = '', str(exc)[:300]
                resources = page.get('/Resources', {})
                try:
                    resources = resources.get_object()
                    has_xobjects = bool(resources.get('/XObject'))
                except Exception:
                    has_xobjects = None
                low_text = len(clean(text)) < 40
                pages.append({'page': number, 'text': text, 'text_characters': len(clean(text)),
                              'text_status': 'scanned_or_low_text' if low_text else 'extracted',
                              'has_image_or_form_objects': has_xobjects,
                              'extraction_error': error, 'needs_visual_review': True,
                              'visual_review_status': 'not_reviewed'})
        status = 'partial_text_needs_visual_review' if any(p['text_status'] != 'extracted' for p in pages) else 'text_extracted_pending_review'
        return {'kind': 'pdf', 'status': status, 'pages': pages, 'page_count': len(pages),
                'inventory_complete': False, 'fascicolo_complete': False}
    except Exception as exc:
        return {'kind': 'pdf', 'status': 'invalid_pdf', 'pages': pages, 'error': str(exc)[:400]}


class D2:
    def __init__(self, ledger, validate, session=None):
        self.ledger, self.validate = ledger, validate
        self.db, self.root = ledger.db, ledger.root
        self.session = session or requests.Session()
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS inventory_runs(id TEXT PRIMARY KEY, project_id TEXT, root_url TEXT,
            started_at TEXT, result_json TEXT);
        CREATE TABLE IF NOT EXISTS inventory_pages(run_id TEXT,page INTEGER,url TEXT,sha256 TEXT,
            status TEXT,row_count INTEGER,detail TEXT,PRIMARY KEY(run_id,page));
        CREATE TABLE IF NOT EXISTS inventory_members(run_id TEXT,doc_id TEXT,metadata_json TEXT,
            PRIMARY KEY(run_id,doc_id));
        CREATE TABLE IF NOT EXISTS visual_queue(doc_id TEXT,sha256 TEXT,page INTEGER,path TEXT,
            render_sha256 TEXT,status TEXT,detail TEXT,PRIMARY KEY(doc_id,sha256,page));
        ''')
        self.db.commit()

    def attempt(self, did, result):
        self.db.execute('INSERT INTO attempts(doc_id,checked_at,status,http_status,detail,elapsed,final_url) VALUES(?,?,?,?,?,?,?)',
            (did, stamp(), result['status'], result.get('http_status'), json.dumps(result, ensure_ascii=False),
             result.get('seconds'), result.get('final_url')))
        self.db.commit()

    def inventory(self, project_id, root, *, page_limit=200, delay=0.25):
        if page_limit < 1:
            raise ValueError('page_limit must be positive')
        run = uuid.uuid4().hex
        self.db.execute('INSERT INTO inventory_runs VALUES(?,?,?,?,?)', (run, project_id, root, stamp(), '{}'))
        self.db.commit()
        expected, total, fingerprints, issues, ids, done = None, None, set(), [], set(), 0
        number = 1
        while number <= min(total or 1, page_limit):
            url = root if number == 1 else page_url(root, number)
            did = self.ledger.register(project_id, url, f'MASE index page {number}', 'auto')
            transfer = stream_download(url, self.root / 'transfers' / did, validate=self.validate,
                                       session=self.session, max_bytes=8 * 1024**2, budget=60)
            self.attempt(did, transfer)
            row_count, sha, error = 0, transfer.get('sha256'), None
            if transfer['status'] == 'downloaded':
                source = Path(transfer['path'])
                target = self.root / 'objects' / (sha + '.bin')
                shutil.copyfile(source, target)
                try:
                    data = parse_index(source.read_bytes(), root)
                    expected = data['expected'] if expected is None else expected
                    total = data['pages'] if total is None else total
                    if (data['expected'], data['pages'], data['current']) != (expected, total, number):
                        raise ValueError('Counters changed or requested page was not served')
                    fingerprint = tuple(sorted(r['url'] for r in data['rows']))
                    if fingerprint in fingerprints and data['rows']:
                        raise ValueError('Repeated attachment page; navigation did not advance')
                    fingerprints.add(fingerprint)
                    for metadata in data['rows']:
                        filename = metadata['filename'].lower()
                        expected_type = 'pdf' if filename.endswith('.pdf') else 'auto'
                        child = self.ledger.register(project_id, metadata['url'], metadata['title'], expected_type, did)
                        self.db.execute('INSERT INTO inventory_members VALUES(?,?,?) ON CONFLICT(run_id,doc_id) DO UPDATE SET metadata_json=excluded.metadata_json',
                                        (run, child, json.dumps(metadata, ensure_ascii=False)))
                        ids.add(child)
                    row_count, done = len(data['rows']), done + 1
                except Exception as exc:
                    error = str(exc)
                source.unlink(missing_ok=True)
            else:
                error = transfer.get('detail', transfer['status'])
            if error:
                issues.append({'page': number, 'url': url, 'reason': error})
            self.db.execute('INSERT INTO inventory_pages VALUES(?,?,?,?,?,?,?)',
                            (run, number, url, sha, 'failed' if error else 'indexed', row_count, error))
            result = {'run_id': run, 'project_id': project_id, 'root_url': root,
                      'expected_documents': expected, 'expected_pages': total,
                      'indexed_pages': done, 'unique_documents': len(ids), 'issues': issues,
                      'status': 'in_progress', 'dossier_complete': False}
            self.db.execute('UPDATE inventory_runs SET result_json=? WHERE id=?', (json.dumps(result), run))
            self.db.commit()
            print(f'INDEX {project_id} {number}/{total}: {row_count} rows; {error or "OK"}', flush=True)
            if total is None:
                break
            number += 1
            if delay:
                time.sleep(delay)
        if total and total > page_limit:
            issues.append({'reason': 'pagination_budget_exhausted', 'unvisited_pages': total - page_limit})
        complete = expected is not None and total is not None and done == total and len(ids) == expected and not issues
        result.update(status='complete_index' if complete else 'incomplete_index', issues=issues,
                      guard='Completeness applies only to this procedure index snapshot, not to document reading or every project procedure.')
        self.db.execute('UPDATE inventory_runs SET result_json=? WHERE id=?', (json.dumps(result), run))
        self.db.commit()
        return result

    def acquire(self, did, *, max_bytes=256 * 1024**2, render_limit=4, refresh=False):
        doc = self.db.execute('SELECT * FROM documents WHERE id=?', (did,)).fetchone()
        old = self.db.execute('SELECT v.* FROM versions v JOIN document_heads h ON v.doc_id=h.doc_id AND v.sha256=h.sha256 WHERE v.doc_id=?', (did,)).fetchone()
        if old and not refresh:
            extraction = json.loads(old['extraction_json'])
            original = self.root / 'objects' / (old['sha256'] + '.pdf')
            if original.exists() and extraction.get('kind') == 'pdf' and file_hash(original) == old['sha256']:
                self.render(did, old['sha256'], original, extraction, render_limit)
                cached = {'status': 'cached_verified', 'doc_id': did, 'sha256': old['sha256']}
                self.attempt(did, cached)
                return cached
        transfer = stream_download(doc['url'], self.root / 'transfers' / did,
                                   validate=self.validate, session=self.session, max_bytes=max_bytes)
        self.attempt(did, transfer)
        if transfer['status'] != 'downloaded':
            return transfer
        source, sha = Path(transfer['path']), transfer['sha256']
        extraction = extract_file(source)
        target = self.root / 'objects' / (sha + ('.pdf' if extraction['kind'] == 'pdf' else '.bin'))
        shutil.copyfile(source, target)
        source.unlink(missing_ok=True)
        self.db.execute('INSERT OR IGNORE INTO versions VALUES(?,?,?,?,?,?,?)',
                        (did, sha, stamp(), transfer['bytes'], transfer.get('etag'), transfer.get('modified'),
                         json.dumps(extraction, ensure_ascii=False)))
        # Never replace a previously readable head with an HTML error page.
        if extraction['status'] not in ('not_a_pdf', 'invalid_pdf', 'encrypted'):
            self.db.execute('INSERT INTO document_heads VALUES(?,?) ON CONFLICT(doc_id) DO UPDATE SET sha256=excluded.sha256', (did, sha))
        from wind_document_audit import power_mentions
        for page in extraction.get('pages', []):
            for item in power_mentions(page['text']):
                self.db.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?)',
                    (did, sha, page['page'], json.dumps(item, ensure_ascii=False)))
        self.db.commit()
        self.attempt(did, {'status': extraction['status'], 'sha256': sha, 'final_url': transfer['final_url']})
        if extraction['kind'] == 'pdf' and extraction.get('pages'):
            self.render(did, sha, target, extraction, render_limit)
        return {'doc_id': did, 'status': extraction['status'], 'bytes': transfer['bytes'],
                'sha256': sha, 'pages': extraction.get('page_count')}

    def render(self, did, sha, source, extraction, limit):
        pages = extraction.get('pages', [])
        # Rich-text pages are not exempt: every page enters the visual queue.
        for page in pages:
            self.db.execute('INSERT OR IGNORE INTO visual_queue VALUES(?,?,?,?,?,?,?)',
                            (did, sha, page['page'], None, None, 'not_rendered', None))
        self.db.commit()
        ordered = sorted(pages, key=lambda p: (0 if p['page'] == 1 else 1 if p['text_characters'] < 40 else 2, p['page']))
        candidates = [p for p in ordered if not self.db.execute('SELECT path FROM visual_queue WHERE doc_id=? AND sha256=? AND page=?',
                      (did, sha, p['page'])).fetchone()[0]][:limit]
        if not candidates:
            return
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(str(source))
            try:
                for item in candidates:
                    page = pdf[item['page'] - 1]
                    try:
                        bitmap = page.render(scale=min(1.5, 1600 / max(page.get_size())))
                        try:
                            target = self.root / 'renders' / sha / f'page-{item["page"]:04d}.png'
                            target.parent.mkdir(parents=True, exist_ok=True)
                            bitmap.to_pil().save(target)
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
                    self.db.execute('UPDATE visual_queue SET path=?,render_sha256=?,status=? WHERE doc_id=? AND sha256=? AND page=?',
                        (str(target.relative_to(self.root)), file_hash(target), 'rendered_pending_review', did, sha, item['page']))
                    self.db.commit()
            finally:
                pdf.close()
        except Exception as exc:
            self.db.execute('UPDATE visual_queue SET detail=? WHERE doc_id=? AND sha256=? AND path IS NULL', (str(exc)[:300], did, sha))
            self.db.commit()

    def export(self):
        runs = [json.loads(r[0]) for r in self.db.execute('SELECT result_json FROM inventory_runs ORDER BY rowid')]
        render_rows = [dict(r) for r in self.db.execute('SELECT * FROM visual_queue ORDER BY doc_id,page')]
        acquisitions = [dict(r) for r in self.db.execute('SELECT * FROM attempts ORDER BY id')]
        report = {'schema_version': '0.2.0', 'generated_at': stamp(), 'inventories': runs,
                  'registered_resources': self.db.execute('SELECT COUNT(*) FROM documents').fetchone()[0],
                  'acquisitions': acquisitions, 'visual_queue': render_rows,
                  'complete_dossiers': 0, 'guard': 'No semantic review or EPC/contact/schedule validation is inferred from acquisition/rendering.'}
        (self.root / 'inventory-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        rows = [dict(r) for r in self.db.execute('SELECT d.project_id,d.id,d.url,m.run_id,m.metadata_json,v.extraction_json FROM inventory_members m JOIN documents d ON d.id=m.doc_id LEFT JOIN document_heads h ON d.id=h.doc_id LEFT JOIN versions v ON h.doc_id=v.doc_id AND h.sha256=v.sha256')]
        with (self.root / 'inventory.csv').open('w', newline='', encoding='utf-8-sig') as out:
            keys = ['project_id', 'id', 'run_id', 'url', 'title', 'filename', 'section', 'code', 'published', 'scale', 'declared_size', 'acquisition_status', 'page_count']
            writer = csv.DictWriter(out, keys, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                extraction = json.loads(row.pop('extraction_json') or '{}')
                writer.writerow({**row, **json.loads(row.pop('metadata_json')),
                    'acquisition_status': extraction.get('status', 'indexed_not_acquired'),
                    'page_count': extraction.get('page_count', '')})
        cards = ''.join(f'<tr><td>{escape(r["project_id"])}</td><td>{r["indexed_pages"]}/{r["expected_pages"]}</td><td>{r["unique_documents"]}/{r["expected_documents"]}</td><td>{escape(r["status"])}</td></tr>' for r in runs)
        images = ''.join(f'<figure><a href="{escape(r["path"])}"><img loading="lazy" src="{escape(r["path"])}"></a><figcaption>{escape(r["doc_id"])} · p. {r["page"]} · da verificare</figcaption></figure>' for r in render_rows if r['path'])
        failures = ''.join(f'<li>{escape(r["status"])} — {escape(str(r["final_url"]))}: {escape(str(r["detail"]))}</li>' for r in acquisitions if r['status'] not in ('downloaded', 'cached_verified', 'text_extracted_pending_review', 'partial_text_needs_visual_review'))
        html = '<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wind — inventari e accesso documentale D2</title><style>body{font:16px system-ui;margin:36px auto;padding:0 24px;max-width:1200px;background:#f4f7f8;color:#182d34}table{border-collapse:collapse;width:100%;background:white}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}figure{margin:0;background:white;padding:12px}img{max-width:100%;max-height:480px}li{overflow-wrap:anywhere}h1{font-size:28px}</style><h1>Wind Radar — inventari e accesso documentale</h1><p>Inventario completo ≠ documenti tutti letti. Estrazione e rendering ≠ verifica semantica. Fascicoli certificati completi: <b>0</b>.</p><table><tr><th>Progetto</th><th>Pagine indice</th><th>Allegati</th><th>Esito inventario</th></tr>' + cards + '</table><p><a href="inventory.csv">Inventario CSV</a> · <a href="inventory-report.json">Registro JSON</a></p><h2>Accessi da verificare</h2><ul>' + failures + '</ul><h2>Pagine rese disponibili alla verifica visiva</h2><div class="gallery">' + images + '</div></html>'
        (self.root / 'inventory-report.html').write_text(html, encoding='utf-8')
        return report


def main():
    from wind_document_audit import Ledger, validate_url
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--page-limit', type=int, default=200)
    parser.add_argument('--render-limit', type=int, default=4)
    parser.add_argument('--skip-inventory', action='store_true', help='Reuse saved inventory for a warm acquisition pass')
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
    ledger = Ledger(args.output)
    engine = D2(ledger, validate_url)
    try:
        for entry in ([] if args.skip_inventory else plan.get('inventories', [])):
            engine.inventory(entry['project_id'], entry['url'], page_limit=args.page_limit)
        # Metadata-based priority is a pilot processing order, not an exclusion.
        # Every indexed attachment remains in inventory_members and inventory.csv.
        selected = set()
        for rule in plan.get('select_from_inventory', []):
            entries = ledger.db.execute('SELECT m.doc_id,m.metadata_json FROM inventory_members m JOIN inventory_runs i ON i.id=m.run_id WHERE i.project_id=? ORDER BY i.rowid DESC', (rule['project_id'],)).fetchall()
            unique = {}
            for row in entries:
                unique.setdefault(row['doc_id'], json.loads(row['metadata_json']))
            def date_key(item):
                try:
                    return datetime.strptime(item[1].get('published', ''), '%d/%m/%Y')
                except ValueError:
                    return datetime.min
            matches = [(did, meta) for did, meta in unique.items()
                       if re.search(rule['title_pattern'], meta['title'], re.I)]
            for did, meta in sorted(matches, key=date_key, reverse=True)[:rule.get('limit', 1)]:
                if did not in selected:
                    selected.add(did)
                    print('PRIORITY', meta['title'], json.dumps(engine.acquire(did,
                        max_bytes=rule.get('max_mib', 64) * 1024**2,
                        render_limit=args.render_limit), ensure_ascii=False), flush=True)
        for asset in plan.get('assets', []):
            did = ledger.register(asset['project_id'], asset['url'], asset['label'], asset.get('expected', 'pdf'))
            print('ASSET', json.dumps(engine.acquire(did, max_bytes=asset.get('max_mib', 256) * 1024**2,
                                                    render_limit=args.render_limit), ensure_ascii=False), flush=True)
    finally:
        engine.export()
        ledger.export()
        engine.session.close()
        ledger.db.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
