"""D3 guard tests use synthetic text, never the pilot's real assertions."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from wind_document_audit import Ledger
from wind_document_review import Reviews, ReviewError

URL = 'https://va.mite.gov.it/File/Documento/123'
TEXT = ('Progetto Eolico Test. Potenza nominale 42 MW. RINA Consulting autore. '
        'Mario Rossi, Contact Manager. mario.rossi@example.org; Tel +39 02 1234567. '
        'Cronoprogramma relativo: messa in servizio. Societa EPC del gruppo.')


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        ledger = Ledger(self.root)
        ledger.db.execute('INSERT INTO projects VALUES(?,?,?,?)', ('test', 'Test', 'canonical', '{}'))
        ledger.db.commit()
        self.did = ledger.register('test', URL, 'Synthetic document', 'pdf')
        # This fixture exercises provenance checks, not PDF extraction itself.
        body = b'%PDF-1.4 synthetic fixture bytes'
        self.sha = hashlib.sha256(body).hexdigest()
        (self.root / 'objects' / (self.sha + '.pdf')).write_bytes(body)
        extraction = {'kind': 'pdf', 'pages': [{'page': 1, 'text': TEXT}], 'page_count': 1}
        ledger.db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?)', (self.did, self.sha, '2026-10-05', len(body), '', '', json.dumps(extraction)))
        ledger.db.execute('INSERT INTO document_heads VALUES(?,?)', (self.did, self.sha))
        ledger.db.commit()
        ledger.db.close()
        self.store = Reviews(self.root)
        self.addCleanup(self.store.close)
        self.entry = {'id':'review1','project_id':'test','kind':'attribute','scope':'project',
            'statement':'42 MW nominali nel documento','value':{'field':'grid_injection_mw','amount':42,'qualifier':'declared'},
            'limits':'Synthetic assertion; not real evidence.','document_date':None,'reviewed_on':'2026-10-05',
            'reviewer':'assistant_document_review','evidence':[{'url':URL,'sha256':self.sha,'page':1,
                'anchor':'Potenza nominale 42 MW','reading_mode':'text'}]}

    def import_entries(self, *entries):
        return self.store.import_batch({'schema_version':'1.0','reviews':list(entries)})

    def test_idempotent_atomic_import(self):
        self.assertEqual(self.import_entries(self.entry), 1)
        self.assertEqual(self.import_entries(self.entry), 0)
        self.assertEqual(self.store.export()['complete_dossiers'], 0)

    def test_immutable_review(self):
        self.import_entries(self.entry)
        self.entry['statement'] = 'A different statement'
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_missing_version(self):
        self.entry['evidence'][0]['sha256'] = 'a'*64
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_missing_original(self):
        (self.root/'objects'/(self.sha+'.pdf')).unlink()
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_corrupted_original(self):
        (self.root/'objects'/(self.sha+'.pdf')).write_bytes(b'corrupt')
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_wrong_project(self):
        self.entry['project_id'] = 'other'
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_wrong_page(self):
        self.entry['evidence'][0]['page'] = 2
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_anchor_not_in_text(self):
        self.entry['evidence'][0]['anchor'] = 'Unsupported passage'
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_visual_attestation_needed(self):
        self.entry['evidence'][0]['reading_mode'] = 'text_and_visual'
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_batch_rejection_does_not_partially_import(self):
        bad = copy.deepcopy(self.entry);bad['id']='bad';bad['evidence'][0]['page']=50
        with self.assertRaises(ReviewError): self.import_entries(self.entry, bad)
        self.assertEqual(self.store.export()['review_count'], 0)

    def test_duplicate_review_ids(self):
        with self.assertRaises(ReviewError): self.import_entries(self.entry, self.entry)

    def test_designer_is_not_epc(self):
        self.entry.update(kind='company_role',value={'company':'RINA','role':'epc','relationship':'document_author'})
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_corporate_capability_is_not_project_award(self):
        self.entry.update(kind='company_role',scope='corporate',value={'company':'Test','role':'epc','relationship':'explicit_execution_award','award_basis':'contract','award_review_note':'Test'})
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_corporate_lead_allowed_without_award(self):
        self.entry.update(kind='company_role',scope='corporate',value={'company':'Test','role':'epc_capability','relationship':'corporate_capability'})
        self.assertEqual(self.import_entries(self.entry),1)

    def contact(self):
        self.entry.update(kind='contact',value={'name':'Mario Rossi','company':'Test','role':'Contact Manager','email':'mario.rossi@example.org','phone':'+39 02 1234567','endpoint_scope':'company_project','source_designation':'Public business contact'})

    def test_literal_business_contact(self):
        self.contact();self.assertEqual(self.import_entries(self.entry),1)

    def test_generated_email_rejected(self):
        self.contact();self.entry['value']['email']='m.rossi@example.org'
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_private_extra_contact_fields_rejected(self):
        self.contact();self.entry['value']['home_address']='Private'
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_relative_timing_cannot_get_calendar_dates(self):
        self.entry.update(kind='schedule',value={'basis':'document_relative','unit':'months','duration':24,'start_date':'2026-10-05'})
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_unanchored_estimate_rejected(self):
        self.entry.update(kind='schedule',value={'basis':'analyst_estimate','earliest':'2027','latest':'2028'})
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_interval_needs_ordered_periods(self):
        self.entry.update(kind='schedule',value={'basis':'document_relative','unit':'months','start_period':24,'end_period':22})
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_configuration_qualifier_required(self):
        self.entry['value'].pop('qualifier')
        with self.assertRaises(ReviewError): self.import_entries(self.entry)

    def test_changed_source_head_keeps_old_review_but_flags_recheck(self):
        self.import_entries(self.entry)
        self.store.db.execute('UPDATE document_heads SET sha256=?', ('b'*64,));self.store.db.commit()
        row=self.store.export()['reviews'][0]
        self.assertEqual(row['evidence_integrity'],'source_version_changed_review_required')
        self.assertFalse(row['commercial_currentness_certified'])

    def test_missing_original_is_visible_on_export(self):
        self.import_entries(self.entry)
        (self.root/'objects'/(self.sha+'.pdf')).unlink()
        self.assertEqual(self.store.export()['reviews'][0]['evidence_integrity'],'evidence_unavailable_review_required')


if __name__ == '__main__':
    unittest.main()
