import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from wind_document_audit import Ledger, parse_asset, power_mentions, validate_url
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def pdf(text=None, blank=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    if text:
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
              NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
            DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(('BT /F1 12 Tf 40 780 Td (' + text + ') Tj ET').encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    if blank:
        writer.add_blank_page(width=595, height=842)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class AuditTests(unittest.TestCase):
    def test_units_are_mentions_not_facts(self):
        items = power_mentions('Totale 29.400 kW; turbine 4,2 MW; accumulo 20 MW')
        self.assertEqual([x['normalized_mw'] for x in items], [29.4, 4.2, 20])
        self.assertTrue(all(x['review_status'] == 'unverified' and x['scope'] == 'unassigned' for x in items))

    def test_html_instead_of_pdf_is_not_success(self):
        result = parse_asset(b'<html>Access denied</html>', 'text/html', 'pdf')
        self.assertEqual(result['status'], 'not_a_pdf')
        self.assertFalse(result['pages'])

    def test_html_index_is_not_complete_inventory(self):
        result = parse_asset(b'<html><a href="doc.pdf">Relazione</a></html>', 'text/html')
        self.assertEqual(result['links'], [('doc.pdf', 'Relazione')])
        self.assertIs(result['inventory_complete'], False)

    def test_challenge_does_not_supply_documents(self):
        result = parse_asset(b'<html>Verify you are human<a href="doc.pdf">x</a></html>', 'text/html')
        self.assertEqual(result['status'], 'access_challenge')
        self.assertEqual(result['links'], [])

    def test_pdf_pages_and_visual_work_remain(self):
        result = parse_asset(pdf('Impianto eolico Apecchio - VSE - potenza totale 29.400 kW'))
        self.assertEqual(result['page_count'], 1)
        self.assertEqual(result['pages'][0]['page'], 1)
        self.assertIn('29.400', result['pages'][0]['text'])
        self.assertTrue(result['pages'][0]['needs_visual_review'])
        self.assertEqual(result['status'], 'text_extracted_pending_review')

    def test_mixed_pdf_is_not_fully_read(self):
        result = parse_asset(pdf('This is a synthetic test page with sufficient text for extraction.', blank=True))
        self.assertEqual(result['status'], 'partial_text_needs_visual_review')
        self.assertEqual(result['pages'][1]['text_status'], 'scanned_or_low_text')

    def test_private_urls_and_unapproved_hosts_refused(self):
        for url in ['http://127.0.0.1/a', 'file:///etc/passwd', 'https://va.mite.gov.it.evil.test/a',
                    'https://x:y@va.mite.gov.it/a', 'https://va.mite.gov.it:8080/a']:
            with self.assertRaises(ValueError):
                validate_url(url, resolve=False)
        self.assertTrue(validate_url('https://monitoraggivia.regione.marche.it/a', resolve=False))

    def test_versions_persist_no_fake_new_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(tmp)
            did = ledger.register('RAW-039', 'https://monitoraggivia.regione.marche.it/a.pdf', expected='pdf')
            first = pdf('Impianto eolico potenza totale 29.400 kW - VSE - Apecchio.')
            self.assertEqual(ledger.persist(did, first, 'application/pdf')[0], 'text_extracted_pending_review')
            self.assertEqual(ledger.persist(did, first, 'application/pdf')[0], 'unchanged_content')
            ledger.persist(did, pdf('Impianto eolico variante con potenza totale 30 MW - VSE - Apecchio.'), 'application/pdf')
            self.assertEqual(ledger.db.execute('SELECT COUNT(*) FROM versions').fetchone()[0], 2)
            ledger.persist(did, first, 'application/pdf')
            report = ledger.export()
            self.assertIn('29.400', report['documents'][0]['current_extraction']['pages'][0]['text'])
            self.assertFalse(report['documents'][0]['fascicolo_complete'])
            ledger.db.close()

    def test_failure_keeps_last_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(tmp)
            did = ledger.register('p', 'https://va.mite.gov.it/a.pdf', expected='pdf')
            ledger.persist(did, pdf('Document previously downloaded with power 42 MW.'), 'application/pdf')
            with patch('wind_document_audit.validate_url', side_effect=ValueError('DNS test')):
                self.assertEqual(ledger.fetch(did), 'access_failed')
            self.assertEqual(ledger.db.execute('SELECT COUNT(*) FROM versions').fetchone()[0], 1)
            ledger.db.close()

    def test_census_includes_old_registry_canonical_precedence_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); data = root / 'repo/docs/wind/data'; data.mkdir(parents=True)
            fixtures = {'projects.json': {'chunks':['chunk.json']},
                        'chunk.json': [{'id':'p1','name':'Canonical'}],
                        'discovery-v04.json': {'candidates':[{'candidate_id':'p1','name':'Old'}]},
                        'discovery-census-v04b.json': {'candidates':[{'candidate_id':'p2','name':'Previously missed'},
                              {'candidate_id':'p3','name':'Negative','status':'rejected'}]}}
            for name, obj in fixtures.items():
                (data / name).write_text(json.dumps(obj))
            before = {p.name:p.read_bytes() for p in data.iterdir()}
            ledger = Ledger(root / 'ledger')
            ledger.seed(root / 'repo'); ledger.seed(root / 'repo')
            self.assertEqual(dict(ledger.db.execute('SELECT bucket,COUNT(*) FROM projects GROUP BY bucket')), 
                             {'canonical':1,'discovery_current':1,'rejected':1})
            self.assertEqual(before, {p.name:p.read_bytes() for p in data.iterdir()})
            ledger.db.close()


if __name__ == '__main__':
    unittest.main()
