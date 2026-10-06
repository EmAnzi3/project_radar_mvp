"""D2 tests: malformed inventories/HTTP responses must fail closed."""
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from wind_document_inventory import D2, parse_index, index_scope, page_url, stream_download, extract_file
try:
    from wind_document_audit import Ledger
except ImportError:
    Ledger = None


def index(page=1, pages=2, count=2, docid=10):
    return f'''<html>(n.{count}) Documenti procedura <div>Pagina {page} di {pages}</div>
    <a href="?pagina=2">2</a><table><tr><th>Titolo</th></tr><tr>
    <td>Relazione generale</td><td>file.pdf</td><td>Elaborati</td><td>R1</td><td>01/10/2026</td><td>-</td><td>100 kB</td>
    <td><a href="/File/Documento/{docid}">Scarica</a></td></tr></table></html>'''.encode()

ROOT = 'https://va.mite.gov.it/it-IT/Oggetti/Documentazione/11241/16887'


class Response:
    def __init__(self, body=b'hello', code=200, headers=None, chunks=None):
        self.status_code = code
        self.headers = headers if headers is not None else {'Content-Length': str(len(body)), 'ETag': '"v1"'}
        self.chunks = chunks if chunks is not None else [body]
        self.closed = False

    def iter_content(self, _):
        for chunk in self.chunks:
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk

    def close(self):
        self.closed = True


class Session:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)

    def close(self):
        pass


class IndexTests(unittest.TestCase):
    def test_metadata(self):
        result = parse_index(index(), ROOT)
        self.assertEqual((result['current'], result['pages'], result['expected']), (1, 2, 2))
        self.assertEqual(result['rows'][0]['code'], 'R1')
        self.assertEqual(result['rows'][0]['url'], 'https://va.mite.gov.it/File/Documento/10')

    def test_challenge_rejected(self):
        with self.assertRaises(ValueError):
            parse_index(b'<html>Access denied</html>', ROOT)

    def test_counters_required(self):
        with self.assertRaises(ValueError):
            parse_index(index().replace(b'(n.2)', b''), ROOT)

    def test_pagination_link_required(self):
        with self.assertRaises(ValueError):
            parse_index(index().replace(b'?pagina=2', b'https://evil.invalid/?pagina=2'), ROOT)

    def test_wrong_scope_links_not_followed(self):
        self.assertNotEqual(index_scope(ROOT), index_scope(ROOT + '?sezione=1'))
        self.assertEqual(index_scope(ROOT), index_scope(ROOT + '?pagina=2'))

    def test_filter_preserved(self):
        self.assertEqual(page_url(ROOT + '?sezione=4&pagina=1', 3), ROOT + '?sezione=4&pagina=3')


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'asset'

    def call(self, session, **kwargs):
        return stream_download(ROOT, self.path, validate=lambda u: u, session=session, **kwargs)

    def test_stream_hash(self):
        response = Response()
        result = self.call(Session(response))
        self.assertEqual(result['sha256'], hashlib.sha256(b'hello').hexdigest())
        self.assertTrue(response.closed)

    def test_size_limit_not_portal_failure(self):
        result = self.call(Session(Response()), max_bytes=4)
        self.assertEqual(result['status'], 'deferred_size_limit')
        self.assertFalse(self.path.exists())

    def test_length_mismatch(self):
        result = self.call(Session(Response(headers={'Content-Length': '7'})))
        self.assertEqual(result['status'], 'partial_length_mismatch')
        self.assertFalse(self.path.exists())

    def test_http_error(self):
        result = self.call(Session(Response(code=403)))
        self.assertEqual((result['status'], result['http_status']), ('http_error', 403))

    def test_partial_and_validated_resume(self):
        a = Response(headers={'Content-Length': '5', 'ETag': '"v1"'}, chunks=[b'he', OSError('interrupted')])
        self.assertEqual(self.call(Session(a))['status'], 'network_error')
        b = Response(b'llo', code=206, headers={'Content-Range': 'bytes 2-4/5', 'Content-Length': '3', 'ETag': '"v1"'})
        session = Session(b)
        result = self.call(session)
        self.assertEqual(result['status'], 'downloaded')
        self.assertEqual(self.path.read_bytes(), b'hello')
        self.assertEqual(session.calls[0][1]['headers']['If-Range'], '"v1"')

    def partial(self):
        self.path.with_suffix('.part').write_bytes(b'he')
        self.path.with_suffix('.transfer.json').write_text(json.dumps({'source_url': ROOT, 'final_url': ROOT, 'validator': '"v1"', 'etag': '"v1"'}))

    def test_range_ignored_restarts(self):
        self.partial()
        result = self.call(Session(Response(b'new file')))
        self.assertEqual(result['status'], 'downloaded')
        self.assertEqual(self.path.read_bytes(), b'new file')
        self.assertEqual(result['resumed_from'], 0)

    def test_bad_content_range(self):
        self.partial()
        result = self.call(Session(Response(b'llo', 206, {'Content-Range': 'bytes 3-5/6'})))
        self.assertEqual(result['status'], 'invalid_range')
        self.assertEqual(self.path.with_suffix('.part').read_bytes(), b'he')

    def test_changed_etag(self):
        self.partial()
        result = self.call(Session(Response(b'llo', 206, {'Content-Range': 'bytes 2-4/5', 'ETag': '"v2"'})))
        self.assertEqual(result['status'], 'invalid_range')

    def test_compressed_transfer_explicit(self):
        result = self.call(Session(Response(headers={'Content-Encoding': 'gzip'})))
        self.assertEqual(result['status'], 'unsupported_transfer_encoding')

    def test_redirect_revalidated(self):
        response = Response(code=302, headers={'Location': 'https://evil.invalid/a'})
        def validator(url):
            if 'evil.invalid' in url:
                raise ValueError('unapproved host')
        result = stream_download(ROOT, self.path, validate=validator, session=Session(response))
        self.assertEqual(result['status'], 'network_error')
        self.assertIn('unapproved host', result['detail'])
        self.assertTrue(response.closed)

    def test_oversized_without_content_length(self):
        result = self.call(Session(Response(chunks=[b'he', b'llo'], headers={})), max_bytes=4)
        self.assertEqual(result['status'], 'deferred_size_limit')
        self.assertEqual(result['partial_bytes'], 2)

    def test_no_validator_no_unsafe_resume(self):
        self.path.with_suffix('.part').write_bytes(b'he')
        session = Session(Response(b'hello'))
        self.assertEqual(self.call(session)['status'], 'downloaded')
        self.assertNotIn('Range', session.calls[0][1]['headers'])
        self.assertEqual(self.path.read_bytes(), b'hello')

    def test_html_not_pdf(self):
        self.path.write_text('<html>Access denied</html>')
        self.assertEqual(extract_file(self.path)['status'], 'not_a_pdf')

    def test_zip_not_silently_read(self):
        self.path.write_bytes(b'PK\x03\x04anything')
        self.assertEqual(extract_file(self.path)['status'], 'container_pending_unpack')


@unittest.skipIf(Ledger is None, 'D1 source not materialized locally; integration runs in repository CI')
class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Ledger(self.tmp.name)
        self.addCleanup(self.ledger.db.close)

    def engine(self, *responses):
        return D2(self.ledger, lambda u: u, Session(*responses))

    def test_complete_inventory(self):
        engine = self.engine(Response(index()), Response(index(2, docid=11)))
        result = engine.inventory('p', ROOT, delay=0)
        self.assertEqual(result['status'], 'complete_index')
        self.assertEqual(result['unique_documents'], 2)
        self.assertFalse(result['dossier_complete'])

    def test_repeated_index_fails(self):
        engine = self.engine(Response(index()), Response(index(2)))
        result = engine.inventory('p', ROOT, delay=0)
        self.assertEqual(result['status'], 'incomplete_index')
        self.assertIn('Repeated', result['issues'][0]['reason'])

    def test_page_budget_reported(self):
        result = self.engine(Response(index())).inventory('p', ROOT, page_limit=1, delay=0)
        self.assertEqual(result['status'], 'incomplete_index')
        self.assertEqual(result['issues'][0]['unvisited_pages'], 1)

    def test_missing_page_keeps_queue(self):
        result = self.engine(Response(index()), Response(code=503)).inventory('p', ROOT, delay=0)
        self.assertEqual(result['unique_documents'], 1)
        self.assertEqual(result['status'], 'incomplete_index')
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM inventory_members').fetchone()[0], 1)

    def test_count_mismatch_not_complete(self):
        result = self.engine(Response(index(count=3)), Response(index(2, count=3, docid=11))).inventory('p', ROOT, delay=0)
        self.assertEqual(result['status'], 'incomplete_index')

    def test_old_pdf_head_survives_error_page(self):
        from pypdf import PdfWriter
        import io
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        blob = io.BytesIO()
        writer.write(blob)
        did = self.ledger.register('p', ROOT + '/file.pdf', expected='pdf')
        self.ledger.persist(did, blob.getvalue(), 'application/pdf')
        before = self.ledger.db.execute('SELECT sha256 FROM document_heads WHERE doc_id=?', (did,)).fetchone()[0]
        engine = self.engine(Response(b'<html>Access denied</html>'))
        self.assertEqual(engine.acquire(did, refresh=True)['status'], 'not_a_pdf')
        after = self.ledger.db.execute('SELECT sha256 FROM document_heads WHERE doc_id=?', (did,)).fetchone()[0]
        self.assertEqual(before, after)

    def test_export_queue_state(self):
        engine = self.engine(Response(index()), Response(index(2, docid=11)))
        engine.inventory('p', ROOT, delay=0)
        report = engine.export()
        self.assertEqual(report['complete_dossiers'], 0)
        self.assertIn('indexed_not_acquired', (Path(self.tmp.name) / 'inventory.csv').read_text())


if __name__ == '__main__':
    unittest.main()
