"""No network fixtures: incremental selection, bounded IO and durable evidence."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import wind_document_fast as f


def packet():
    return {'page_count':1,'pages':[f.page_packet(1,'Proponente Alfa Srl. Potenza 42 MW; comune di Prova. Cronoprogramma 12 mesi.')],
            'unprocessed_pages':[],'native_pages_processed':1,'whole_document_read_complete':False}


class FastTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.ledger=self.root/'input'/'audit.sqlite'
        self.ledger.parent.mkdir();self.ledger.write_bytes(b'untouched-input')
        self.output=self.root/'commercial';self.calls=[]
        self.rows=[{'doc_id':'d1','project_id':'p1','state':'pending_acquisition',
            'url':'https://va.mite.gov.it/File/Documento/1','label':'Relazione generale',
            'sha256':None,'etag':None,'modified':None,'bucket':'canonical','legacy_complete':False,
            'legacy_next_check':None,'stage':'E4','priority':1,'priority_reason':'summary',
            'fingerprint':'metadata-1','metadata':{}}]
        self.module_patch=patch.dict(sys.modules,{'wind_document_audit':types.SimpleNamespace(validate_url=lambda u:None)})
        self.module_patch.start();self.addCleanup(self.module_patch.stop)

    def fake_fetch(self,url,path,old,validate):
        self.calls.append(url);path.write_bytes(b'%PDF-fixture')
        return {'status':'downloaded','sha':'a'*64,'bytes':12,'network_requests':1,'etag':'"a"','modified':''}

    def run_batch(self,**kwargs):
        with patch.object(f,'inventory',return_value=self.rows),patch.object(f,'extract',return_value=packet()) as extracted:
            result=f.run(self.ledger,self.output,fetcher=self.fake_fetch,**kwargs)
            return result,extracted.call_count

    def due(self):
        with sqlite3.connect(self.output/'commercial.sqlite') as db:
            db.execute("UPDATE resources SET next_check='2000-01-01T00:00:00+00:00'")

    def test_cold_then_warm_without_original(self):
        a,n=self.run_batch();b,n2=self.run_batch(offline=True,replay=True)
        self.assertEqual((a['text_extractions'],n),(1,1));self.assertEqual((b['network_requests'],n2),(0,0))
        self.assertEqual(len(self.calls),1);self.assertEqual(b['stored_content_packets'],1)
        self.assertFalse(list(self.output.rglob('*.pdf')))
        self.assertEqual(self.ledger.read_bytes(),b'untouched-input')

    def test_same_hash_200_does_not_extract_again(self):
        self.run_batch();self.due();a,n=self.run_batch()
        self.assertEqual(n,0);self.assertEqual(a['results'][0]['status'],'same_content_reused')

    def test_metadata_change_checks_content_but_does_not_reread_identical(self):
        self.run_batch();self.rows[0]['fingerprint']='new-index-version';a,n=self.run_batch()
        self.assertEqual(a['network_requests'],1);self.assertEqual(n,0)

    def test_changed_content_preserves_previous_packet(self):
        self.run_batch();self.due()
        original=self.fake_fetch
        def changed(*args):return {**original(*args),'sha':'b'*64}
        self.fake_fetch=changed;a,n=self.run_batch()
        self.assertEqual(n,1);self.assertEqual(a['stored_content_packets'],2)

    def test_failure_keeps_information_and_backs_off(self):
        self.run_batch();self.due()
        def failed(*args):return {'status':'error','error':'HTTP 503','bytes':0,'network_requests':1,'text_extractions':0}
        self.fake_fetch=failed;a,n=self.run_batch();b,_=self.run_batch()
        self.assertEqual(a['stored_content_packets'],1);self.assertEqual(a['unresolved_resource_errors'],1)
        self.assertEqual(b['network_requests'],0);self.assertEqual(b['selection_outcomes']['error_retry_not_due'],1)

    def test_one_source_failure_does_not_drop_other_success(self):
        self.rows.append({**self.rows[0],'doc_id':'d2','project_id':'p2','url':self.rows[0]['url']+'2'})
        original=self.fake_fetch
        def mixed(url,*args):
            if url.endswith('12'):return {'status':'error','error':'HTTP 404','bytes':0,'network_requests':1,'text_extractions':0}
            return original(url,*args)
        self.fake_fetch=mixed;a,n=self.run_batch()
        self.assertEqual(a['stored_content_packets'],1);self.assertEqual(len(a['results']),2)

    def test_same_url_downloaded_once_for_two_projects(self):
        self.rows.append({**self.rows[0],'doc_id':'d2','project_id':'p2'})
        a,n=self.run_batch();self.assertEqual((n,len(self.calls)),(1,1))
        with sqlite3.connect(self.output/'commercial.sqlite') as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM links').fetchone()[0],2)

    def test_same_bytes_different_urls_share_one_extraction_not_project_facts(self):
        self.rows.append({**self.rows[0],'doc_id':'d2','project_id':'p2','url':self.rows[0]['url']+'2'})
        a,n=self.run_batch();self.assertEqual((len(self.calls),n),(2,1));self.assertEqual(a['new_verified_facts'],0)

    def test_legacy_completed_reused_without_new_extraction(self):
        self.rows[0].update(legacy_complete=True,sha256='a'*64,legacy_next_check='2099-01-01T00:00:00+00:00')
        a,n=self.run_batch();self.assertEqual((n,len(self.calls)),(0,0))
        self.assertEqual(a['selection_outcomes']['legacy_completed_reused'],1)

    def test_legacy_due_unchanged_skips_extraction(self):
        self.rows[0].update(legacy_complete=True,sha256='a'*64,legacy_next_check='2000-01-01T00:00:00+00:00')
        a,n=self.run_batch();self.assertEqual((n,len(self.calls)),(0,1))

    def test_legacy_changed_gets_targeted_packet_without_completing_it(self):
        self.rows[0].update(legacy_complete=True,sha256='b'*64,legacy_next_check='2000-01-01T00:00:00+00:00')
        a,n=self.run_batch();self.assertEqual(n,1);self.assertEqual(a['new_whole_document_completions'],0)

    def test_specialist_deferred_not_marked_read(self):
        self.rows[0]['priority']=3;a,n=self.run_batch()
        self.assertEqual(n,0);self.assertEqual(a['selection_outcomes']['specialist_deferred'],1)
        self.assertEqual(a['inventory_documents'],1)

    def test_new_document_does_not_restart_old_documents(self):
        self.run_batch();self.rows.append({**self.rows[0],'doc_id':'d2','url':self.rows[0]['url']+'2'})
        a,n=self.run_batch();self.assertEqual(a['network_requests'],1);self.assertEqual(len(self.calls),2)

    def test_scanned_page_is_not_declared_irrelevant(self):
        result=f.page_packet(1,'');self.assertIn('low_native_text_not_empty_page',result['review_flags'])
        self.assertEqual(result['snippets'],{})

    def test_text_passage_never_assigns_epc(self):
        r=f.page_packet(3,'RINA progettista. Affidamento EPC non ancora definito. Durata 24 mesi.')
        self.assertIn('companies_roles',r['snippets']);self.assertNotIn('epc',r)
        self.assertIn('schedule_table_or_scope_review',r['review_flags'])

    def test_priority_does_not_mistake_authority_title_for_authorization(self):
        self.assertGreater(f.classify('Osservazioni REGIONE - SETTORE VALUTAZIONI E AUTORIZZAZIONI AMBIENTALI')[0],0)
        self.assertEqual(f.classify('Carta impianti FER in autorizzazione')[0],3)
        self.assertEqual(f.classify('Cronoprogramma lavori')[0],0)
        self.assertEqual(f.classify('Autorizzazione movimentazione sedimenti marini')[0],3)

    def test_fair_queue_includes_small_project(self):
        rows=[{**self.rows[0],'doc_id':str(i)} for i in range(10)]
        rows.append({**self.rows[0],'doc_id':'other','project_id':'p2','priority':2})
        self.assertEqual({r['project_id'] for r in f.fair_selection(rows,2)},{'p1','p2'})

    def test_lock_rejects_second_writer(self):
        with f.lock(self.output):
            with self.assertRaises(FileExistsError):
                with f.lock(self.output):pass
        self.assertFalse((self.output/'.writer.lock').exists())

    def test_source_memory_path_cannot_be_output(self):
        with self.assertRaises(ValueError):f.run(self.ledger,self.ledger.parent)

    def test_replay_without_previous_run_is_error(self):
        with self.assertRaises(ValueError):self.run_batch(replay=True)

    def test_bad_limits_rejected(self):
        with self.assertRaises(ValueError):self.run_batch(workers=0)
        with self.assertRaises(ValueError):self.run_batch(per_host=3)


class TransferTests(unittest.TestCase):
    class Response:
        def __init__(self,status,body=b'',headers=None):self.status_code=status;self.body=body;self.headers=headers or {}
        def iter_content(self,*args):return iter([self.body])
        def raise_for_status(self):
            if self.status_code>=400:raise ValueError('HTTP '+str(self.status_code))
        def close(self):pass

    def do(self,response,old=None):
        session=types.SimpleNamespace(get=lambda *a,**k:response)
        with tempfile.TemporaryDirectory() as tmp:
            return f.transfer('https://va.mite.gov.it/File/Documento/1',Path(tmp)/'a.pdf',old,lambda u:None,client=session)

    def test_304_does_not_download_or_extract(self):
        r=self.do(self.Response(304,headers={'ETag':'"x"'}),{'sha':'a'*64,'etag':'"x"'})
        self.assertEqual((r['status'],r['bytes'],r['text_extractions']),('not_modified',0,0))

    def test_unsolicited_304_rejected(self):self.assertEqual(self.do(self.Response(304))['status'],'error')
    def test_different_304_etag_rejected(self):
        self.assertEqual(self.do(self.Response(304,headers={'ETag':'"y"'}),{'sha':'a'*64,'etag':'"x"'})['status'],'error')
    def test_html_is_not_a_pdf(self):self.assertEqual(self.do(self.Response(200,b'<html>blocked</html>'))['status'],'error')
    def test_incomplete_response_rejected(self):
        self.assertEqual(self.do(self.Response(200,b'%PDF-test',{'Content-Length':'100'}))['status'],'error')
    def test_pdf_hash_bound(self):
        r=self.do(self.Response(200,b'%PDF-test'));self.assertEqual(r['sha'],hashlib.sha256(b'%PDF-test').hexdigest())


if __name__=='__main__':unittest.main()
