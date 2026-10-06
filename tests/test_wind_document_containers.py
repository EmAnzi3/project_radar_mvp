"""D4 uses generated fixtures: passing tests is not live-project evidence."""
import hashlib,io,json,shutil,sqlite3,stat,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from wind_document_audit import Ledger
from wind_document_containers import Containers,Limits,kind_of,safe_name
from wind_document_queue import Queue


def pdf_bytes():
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    w=PdfWriter();p=w.add_blank_page(width=400,height=400)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    p[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):w._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 300 Td (Synthetic wind document only for tests, never real project evidence.) Tj ET')
    p[NameObject('/Contents')]=w._add_object(stream);b=io.BytesIO();w.write(b);return b.getvalue()


def zipped(entries):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in entries:z.writestr(name,data)
    return b.getvalue()


class ContainerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.ledger=Ledger(self.root);self.addCleanup(self.ledger.db.close)
        self.engine=Containers(self.ledger);self.doc=self.ledger.register('test','https://va.mite.gov.it/File/Documento/1','Fixture','auto')

    def store(self,body):
        sha=hashlib.sha256(body).hexdigest();(self.root/'objects'/(sha+'.bin')).write_bytes(body)
        self.ledger.db.execute('INSERT OR IGNORE INTO versions VALUES(?,?,?,?,?,?,?)',(self.doc,sha,'2026-10-05',len(body),'','',json.dumps({'kind':'binary'})));self.ledger.db.commit();return sha

    def open(self,body):return self.engine.open(self.doc,self.store(body))

    def test_pdf_inside_zip_is_read_with_chain(self):
        result=self.open(zipped([('folder/a.pdf',pdf_bytes())]));self.assertEqual(result['status'],'opened_pending_review')
        row=self.engine.report()['members'][0];self.assertEqual(row['kind'],'pdf');self.assertEqual(row['extraction']['page_count'],1)
        self.assertIn('Synthetic wind',row['extraction']['pages'][0]['text']);self.assertEqual(row['provenance_chain'][0]['member_name'],'folder/a.pdf')
        self.assertEqual(self.engine.report()['complete_dossiers'],0)

    def test_path_traversal_refused(self):
        self.open(zipped([('../outside.pdf',pdf_bytes())]));self.assertEqual(self.engine.report()['members'][0]['status'],'unsafe_member_path')
        self.assertFalse((self.root.parent/'outside.pdf').exists())

    def test_windows_absolute_refused(self):
        for path in ['C:/test.pdf','/test.pdf','..\\test.pdf','a/../b.pdf','a\x00b']:
            self.assertFalse(safe_name(path),path)

    def test_symlink_refused(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            i=zipfile.ZipInfo('link');i.create_system=3;i.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(i,'/etc/passwd')
        self.open(b.getvalue());self.assertEqual(self.engine.report()['members'][0]['status'],'symlink_refused')

    def test_ratio_limit(self):
        self.open(zipped([('bomb.pdf',b'0'*1000000)]));self.assertEqual(self.engine.report()['members'][0]['status'],'compression_ratio_limit')

    def test_size_limit(self):
        self.engine=Containers(self.ledger,Limits(member_bytes=10));self.open(zipped([('large.pdf',pdf_bytes())]))
        self.assertEqual(self.engine.report()['members'][0]['status'],'deferred_member_size')

    def test_member_count_limit(self):
        self.engine=Containers(self.ledger,Limits(members=1));self.open(zipped([('a',b'x'),('b',b'x')]))
        self.assertEqual(self.engine.report()['members'][0]['status'],'deferred_member_count')

    def test_depth_limit_retains_nested_bytes(self):
        self.engine=Containers(self.ledger,Limits(depth=0));self.open(zipped([('nested.zip',zipped([('a.pdf',pdf_bytes())]))]))
        row=self.engine.report()['members'][0];self.assertEqual(row['status'],'deferred_depth_limit');self.assertTrue(row['content_sha'])

    def test_crc_failure_not_read(self):
        data=bytearray(zipped([('a.pdf',pdf_bytes())]));data[50]^=0x5a
        result=self.open(bytes(data));self.assertEqual(result['status'],'partial_or_blocked')

    def test_duplicate_names_do_not_overwrite(self):
        self.open(zipped([('a.txt',b'one'),('A.txt',b'two')]))
        self.assertIn('duplicate_member_path',[r['status'] for r in self.engine.report()['members']])

    def test_unsupported_member_retained(self):
        self.open(zipped([('macro.exe',b'MZ non-executed')]))
        row=self.engine.report()['members'][0];self.assertEqual(row['status'],'unsupported_retained');self.assertTrue(row['content_sha'])

    def test_unchanged_archive_no_duplicate(self):
        data=zipped([('a.pdf',pdf_bytes())]);self.open(data);count=len(self.engine.report()['members']);result=self.open(data)
        self.assertEqual(result['status'],'cached_container_verified');self.assertEqual(count,len(self.engine.report()['members']))

    def test_parent_integrity_checked(self):
        sha=self.store(zipped([('a.pdf',pdf_bytes())]));(self.root/'objects'/(sha+'.bin')).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):self.engine.open(self.doc,sha)

    def test_unknown_parent_rejected(self):
        with self.assertRaises(ValueError):self.engine.open('unknown','a'*64)

    @unittest.skipUnless(shutil.which('openssl'),'OpenSSL missing: live code will report dependency_missing')
    def test_attached_cms_signature_and_nested_zip(self):
        key=self.root/'key.pem';cert=self.root/'cert.pem';plain=self.root/'plain';cms=self.root/'signed.p7m'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-subj','/CN=Synthetic Fixture','-days','1'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
        plain.write_bytes(zipped([('p.pdf',pdf_bytes())]))
        subprocess.run(['openssl','cms','-sign','-binary','-nodetach','-in',str(plain),'-signer',str(cert),'-inkey',str(key),'-outform','DER','-out',str(cms)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
        result=self.open(cms.read_bytes());self.assertEqual(result['status'],'opened_pending_review')
        pdf=next(r for r in self.engine.report()['members'] if r['kind']=='pdf')
        self.assertEqual(len(pdf['provenance_chain']),2);self.assertFalse(pdf['provenance_chain'][0]['certificate_trust_verified'])
        changed=bytearray(cms.read_bytes());changed[-10]^=1
        self.assertEqual(self.open(bytes(changed))['status'],'partial_or_blocked')

    def test_invalid_cms_is_not_read(self):
        data=b'\x30\x80\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x02invalid';self.open(data)
        self.assertEqual(self.engine.report()['members'][0]['status'],'cms_verification_failed_or_detached')


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.l=Ledger(self.tmp.name);self.addCleanup(self.l.db.close);self.q=Queue(self.l)
        for pid,sources in [('a',[{'url':'https://va.mite.gov.it/File/Documento/1'}]),('b',[{'url':'https://unknown.invalid/document.pdf'}]),('c',[{'url':''}])]:
            self.l.db.execute('INSERT INTO projects VALUES(?,?,?,?)',(pid,pid,'canonical',json.dumps({'record':{'sources':sources}})))
        self.l.db.execute('INSERT INTO qualification VALUES(?,?,?)',('RAW-001',None,json.dumps({'source_url':'https://va.mite.gov.it/File/Documento/4'})));self.l.db.commit()

    def test_all_identites_including_missing_and_unapproved_have_tickets(self):
        self.q.seed();r=self.q.export();self.assertEqual(r['projects_with_source_tickets'],3);self.assertEqual(r['qualification_with_source_tickets'],1)
        self.assertIn('missing_reference',r['source_counts']);self.assertIn('host_review_required',r['source_counts'])

    def test_reseed_does_not_clear_pending(self):
        self.q.seed();before=self.q.export();self.q.seed();after=self.q.export();self.assertEqual(before['queue_counts'],after['queue_counts'])

    def test_round_robin_and_cap(self):
        self.q.seed()
        for i in range(10,15):self.l.register('a',f'https://va.mite.gov.it/File/Documento/{i}','cronoprogramma','auto')
        self.q.sync_documents();rows=self.q.candidates(limit=2);self.assertEqual({r['project_id'] for r in rows},{'a','RAW-001'})
        self.assertEqual(len(self.q.candidates(limit=0)),0)

    def test_project_filter(self):
        self.q.seed();self.assertEqual({r['project_id'] for r in self.q.candidates(['a'],100)},{'a'})

    def test_daily_empty_does_not_clear_state(self):
        self.q.seed();row=self.q.candidates(limit=1)[0];self.l.db.execute("UPDATE document_work SET state='text_available_review_pending' WHERE doc_id=?",(row['doc_id'],));self.l.db.commit()
        self.q.seed();self.assertEqual(self.l.db.execute('SELECT state FROM document_work WHERE doc_id=?',(row['doc_id'],)).fetchone()[0],'text_available_review_pending')

    def test_backoff_avoids_repeated_bad_download(self):
        self.q.seed();row=self.q.candidates(limit=1)[0];self.l.db.execute("UPDATE document_work SET state='retry_required',next_retry='2999-01-01' WHERE doc_id=?",(row['doc_id'],));self.l.db.commit()
        self.assertNotIn(row['doc_id'],[r['doc_id'] for r in self.q.candidates(limit=100)])


if __name__=='__main__':unittest.main()
