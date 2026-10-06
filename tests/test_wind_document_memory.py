"""D5 regressions: no repeated read, no phantom completion, no original archive."""
import copy, hashlib, io, json, sqlite3, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from wind_document_audit import Ledger
from wind_document_memory import Memory, FIELDS, thin_extraction, MemoryD2 as D2, MemoryQueue as Queue, MemoryReviews as Reviews

URL='https://va.mite.gov.it/File/Documento/42'


def pdf(text='Synthetic project power 42 MW. Contact in the document. Schedule 24 months.'):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    w=PdfWriter();page=w.add_blank_page(width=400,height=400)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):w._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 10 300 Td ('+text+') Tj ET').encode())
    page[NameObject('/Contents')]=w._add_object(stream);b=io.BytesIO();w.write(b);return b.getvalue()


class Response:
    def __init__(self,code,body=b'',headers=None,broken=False):
        self.status_code=code;self.body=body;self.headers=headers or {};self.reads=0;self.closed=False;self.broken=broken
    def iter_content(self,size):
        self.reads+=1
        if self.status_code==304:raise AssertionError('304 must never read a body')
        if self.broken:raise OSError('transfer interrupted')
        yield self.body
    def close(self):self.closed=True


class Client:
    def __init__(self,*responses):self.responses=list(responses);self.calls=[]
    def get(self,url,**kwargs):
        self.calls.append((url,copy.deepcopy(kwargs)))
        if not self.responses:raise AssertionError('unexpected extra HTTP call')
        return self.responses.pop(0)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'work'
        self.ledger=Ledger(self.root);self.addCleanup(self.ledger.db.close)
        self.ledger.db.execute('INSERT INTO projects VALUES(?,?,?,?)',('test','Fixture','canonical','{}'));self.ledger.db.commit()
        self.did=self.ledger.register('test',URL,'Fixture','pdf');self.body=pdf();self.sha=hashlib.sha256(self.body).hexdigest()
        self.ledger.persist(self.did,self.body,'application/pdf',etag='"v1"',modified='Wed, 01 Oct 2025 08:00:00 GMT')
        self.reviews=Reviews(self.root);self.addCleanup(self.reviews.close)
        self.review={'id':'r1','project_id':'test','kind':'attribute','scope':'project','statement':'Fixture only',
            'value':{'field':'installed_wind_mw','amount':42,'qualifier':'declared'},'limits':'Not a real project',
            'document_date':None,'reviewed_on':'2026-10-05','reviewer':'assistant_document_review',
            'evidence':[{'url':URL,'sha256':self.sha,'page':1,'anchor':'Synthetic project power 42 MW','reading_mode':'text'}]}
        self.batch={'schema_version':'1.0','reviews':[self.review]};self.reviews.import_batch(self.batch)
        self.memory=Memory(self.ledger);self.q=Queue(self.ledger);self.q.sync_documents()
        self.plan={'schema_version':'1.0','doc_id':self.did,'sha256':self.sha,'project_id':'test',
            'reviewer':'assistant_document_review','reviewed_on':'2026-10-05',
            'pages':[{'page':1,'mode':'text_and_visual','note':'Synthetic page reviewed; fixture only.'}],
            'outcomes':{k:{'status':'not_found_in_document','note':'Synthetic outcome, fixture only.'} for k in FIELDS}}
        self.plan['outcomes']['power']={'status':'recorded','note':'Synthetic power field backed by r1','review_ids':['r1']}

    def done(self):
        self.memory.complete(self.plan);self.memory.release(self.did)

    def request(self,*responses,**kwargs):
        c=Client(*responses);r=self.memory.check_remote(self.did,session=c,validate=lambda u:None,force=True,**kwargs);return r,c

    def test_partial_claims_are_not_completed_reading(self):
        self.assertIsNone(self.memory.completed(self.did))
        with self.assertRaises(ValueError):self.memory.release(self.did)

    def test_all_pages_required(self):
        self.plan['pages']=[]
        with self.assertRaises(ValueError):self.memory.complete(self.plan)

    def test_visual_reading_required(self):
        self.plan['pages'][0]['mode']='text'
        with self.assertRaises(ValueError):self.memory.complete(self.plan)

    def test_field_outcomes_required(self):
        del self.plan['outcomes']['companies']
        with self.assertRaises(ValueError):self.memory.complete(self.plan)

    def test_recorded_field_needs_evidence(self):
        self.plan['outcomes']['power']['review_ids']=[]
        with self.assertRaises(ValueError):self.memory.complete(self.plan)

    def test_foreign_version_cannot_be_completed(self):
        self.plan['sha256']='a'*64
        with self.assertRaises(ValueError):self.memory.complete(self.plan)

    def test_missing_original_cannot_first_complete(self):
        (self.root/'objects'/(self.sha+'.pdf')).unlink()
        with self.assertRaises(ValueError):self.memory.complete(self.plan)

    def test_complete_release_and_warm_acquire_no_io(self):
        self.done();client=Client()
        with patch('wind_document_inventory.extract_file',side_effect=AssertionError('No re-extraction')):
            result=D2(self.ledger,lambda u:None,client).acquire(self.did)
        self.assertEqual(result['status'],'read_memory_reused');self.assertEqual(client.calls,[])
        self.assertFalse((self.root/'objects'/(self.sha+'.pdf')).exists())
        self.assertEqual(self.reviews.export()['reviews'][0]['evidence_integrity'],'recorded_page_evidence')

    def test_compacted_text_is_not_a_second_document_archive(self):
        self.done();body=self.ledger.db.execute('SELECT extraction_json FROM versions').fetchone()[0]
        self.assertNotIn('Synthetic project',body);self.assertTrue(json.loads(body)['text_released'])

    def test_different_claim_needs_original_even_after_receipt(self):
        self.done();self.review['value']['amount']=99;self.review['id']='r2'
        with self.assertRaises(ValueError):self.reviews.import_batch(self.batch)

    def test_completion_idempotent(self):
        self.done();self.assertEqual(self.memory.complete(self.plan),'already_completed')
        self.assertEqual(self.memory.release(self.did),0)

    def test_no_silent_rewrite_completion(self):
        self.done();self.plan['pages'][0]['note']='A changed interpretation.'
        with self.assertRaises(ValueError):self.memory.complete(self.plan)

    def test_seed_does_not_requeue_completed_doc(self):
        self.done();self.q.seed();self.q.sync_documents()
        self.assertEqual(self.q.candidates(['test']),[])
        self.assertEqual(self.ledger.db.execute('SELECT state FROM document_work WHERE doc_id=?',(self.did,)).fetchone()[0],'read_complete')

    def test_304_zero_bytes_and_zero_reading(self):
        self.done();response=Response(304)
        with patch('wind_document_inventory.extract_file',side_effect=AssertionError('No parser')):
            result,client=self.request(response)
        self.assertEqual(result['status'],'unchanged_by_server');self.assertEqual(response.reads,0)
        self.assertEqual(result['bytes_transferred'],0);self.assertEqual(client.calls[0][1]['headers']['If-None-Match'],'"v1"')
        self.assertIsNotNone(self.memory.completed(self.did))

    def test_last_modified_when_no_strong_etag(self):
        self.done();self.ledger.db.execute('UPDATE document_remote_checks SET etag=?',('W/"weak"',));self.ledger.db.commit()
        result,client=self.request(Response(304))
        self.assertIn('If-Modified-Since',client.calls[0][1]['headers']);self.assertNotIn('If-None-Match',client.calls[0][1]['headers'])

    def test_same_hash_no_reparse_when_server_ignores_conditions(self):
        self.done()
        with patch('wind_document_inventory.extract_file',side_effect=AssertionError('No parser')):
            r,_=self.request(Response(200,self.body,{'Content-Length':str(len(self.body)),'ETag':'"v2-same-bytes"'}))
        self.assertEqual(r['status'],'unchanged_by_hash');self.assertEqual(r['text_extractions'],0)
        self.assertFalse((self.root/'objects'/(self.sha+'.pdf')).exists());self.assertFalse(list(self.root.glob('*.compare')))

    def test_changed_hash_one_request_requeues_only_document(self):
        self.done();changed=pdf('Synthetic changed project power 43 MW. The new document needs explicit review.')
        r,c=self.request(Response(200,changed,{'Content-Length':str(len(changed)),'ETag':'"new"'}))
        self.assertEqual(r['status'],'content_changed_review_required');self.assertEqual(len(c.calls),1)
        self.assertEqual(r['text_extractions'],1);self.assertIsNone(self.memory.completed(self.did))
        self.assertIsNotNone(self.memory.completed(self.did,self.sha))
        self.assertEqual(self.reviews.export()['reviews'][0]['evidence_integrity'],'source_version_changed_review_required')
        self.assertEqual(self.ledger.db.execute('SELECT state FROM document_work WHERE doc_id=?',(self.did,)).fetchone()[0],'text_available_review_pending')

    def test_http_error_does_not_forget_previous_read(self):
        self.done()
        for code in [403,404,429,500]:
            r,_=self.request(Response(code))
            self.assertEqual(r['status'],'remote_check_failed');self.assertIsNotNone(self.memory.completed(self.did))

    def test_error_html_is_not_a_new_document_head(self):
        self.done();r,_=self.request(Response(200,b'<html>Access denied</html>'))
        self.assertEqual(r['status'],'remote_check_failed');self.assertIsNotNone(self.memory.completed(self.did))

    def test_check_cadence(self):
        self.done();self.request(Response(304));client=Client()
        r=self.memory.check_remote(self.did,session=client,validate=lambda u:None)
        self.assertEqual(r['status'],'check_not_due');self.assertEqual(client.calls,[])

    def test_no_validator_304_is_error(self):
        self.done();self.ledger.db.execute("UPDATE document_remote_checks SET etag='',modified=''");self.ledger.db.commit()
        r,_=self.request(Response(304));self.assertEqual(r['status'],'remote_check_failed')

    def test_no_validator_hash_fallback(self):
        self.done();self.ledger.db.execute("UPDATE document_remote_checks SET etag='',modified=''");self.ledger.db.commit()
        r,c=self.request(Response(200,self.body));self.assertEqual(r['status'],'unchanged_by_hash')
        self.assertNotIn('If-None-Match',c.calls[0][1]['headers'])

    def test_partial_body_not_compared(self):
        self.done();r,_=self.request(Response(200,self.body,{'Content-Length':str(len(self.body)+1)}))
        self.assertEqual(r['status'],'remote_check_failed');self.assertIsNotNone(self.memory.completed(self.did))

    def test_size_budget_reported_not_unchanged(self):
        self.done();r,_=self.request(Response(200,self.body),max_bytes=20)
        self.assertEqual(r['status'],'remote_check_failed');self.assertIsNotNone(self.memory.completed(self.did))

    def test_timeout_does_not_drop_known_version(self):
        self.done();r,_=self.request(Response(200,broken=True))
        self.assertEqual(r['status'],'remote_check_failed');self.assertIsNotNone(self.memory.completed(self.did))

    def test_redirect_not_trusted_for_conditional_304(self):
        self.done();r,c=self.request(Response(302,headers={'Location':'/File/Documento/43'}),Response(304))
        self.assertEqual(r['status'],'remote_check_failed');self.assertNotIn('If-None-Match',c.calls[1][1]['headers'])

    def test_shared_hash_not_deleted_for_unread_project(self):
        other=self.ledger.register('other','https://va.mite.gov.it/File/Documento/43','other','pdf')
        self.ledger.persist(other,self.body,'application/pdf');self.memory.complete(self.plan)
        with self.assertRaises(ValueError):self.memory.release(self.did)
        self.assertTrue((self.root/'objects'/(self.sha+'.pdf')).exists())

    def test_receipt_tampering_reported(self):
        self.done();self.ledger.db.execute("UPDATE evidence_receipts SET sources_json='[]'");self.ledger.db.commit()
        self.assertEqual(self.reviews.export()['reviews'][0]['evidence_integrity'],'evidence_unavailable_review_required')

    def test_snapshot_has_no_original_or_full_text(self):
        self.done();out=Path(self.temp.name)/'memory';result=self.memory.snapshot(out)
        self.assertEqual({p.name for p in out.iterdir()},{'audit.sqlite','memory-report.json'})
        self.assertEqual(result['binary_files'],0)
        db=sqlite3.connect(out/'audit.sqlite');ext=json.loads(db.execute('SELECT extraction_json FROM versions').fetchone()[0]);db.close()
        self.assertNotIn('text',ext['pages'][0]);restored=Ledger(out)
        try:
            self.assertEqual(D2(restored,lambda u:None,Client()).acquire(self.did)['status'],'read_memory_reused')
            rr=Reviews(out)
            try:self.assertEqual(rr.import_batch(self.batch),0)
            finally:rr.close()
        finally:restored.db.close()

    def test_pending_doc_stays_pending_without_archive(self):
        out=Path(self.temp.name)/'memory';self.memory.snapshot(out)
        db=sqlite3.connect(out/'audit.sqlite')
        try:
            ext=json.loads(db.execute('SELECT extraction_json FROM versions').fetchone()[0])
            self.assertEqual(ext['status'],'reading_pending_source_not_cached')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM document_read_memory').fetchone()[0],0)
        finally:db.close()

    def test_snapshot_does_not_destroy_existing_destination(self):
        with self.assertRaises(ValueError):self.memory.snapshot(self.root)

    def test_old_review_without_receipt_still_needs_original(self):
        self.done();self.ledger.db.execute('DELETE FROM evidence_receipts');self.ledger.db.commit()
        self.assertEqual(self.reviews.export()['reviews'][0]['evidence_integrity'],'evidence_unavailable_review_required')


if __name__=='__main__':unittest.main()
