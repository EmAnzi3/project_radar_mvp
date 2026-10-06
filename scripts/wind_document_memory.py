#!/usr/bin/env python3
"""D5: read once per version, keep evidence not a permanent document archive.

PDFs/renders are working files. Only an explicit whole-document review closes a
version. Conditional HTTP checks and hashes reopen it on content change, never
on a network error. A completed document is not a completed project dossier.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

FIELDS = {'identity', 'power', 'location', 'companies', 'contacts', 'schedule'}
OUTCOMES = {'recorded', 'not_found_in_document', 'not_applicable', 'conflict_recorded'}


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def tables(db):
    return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def schema(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS evidence_receipts(
      review_id TEXT PRIMARY KEY, body_sha TEXT NOT NULL, sources_json TEXT NOT NULL,
      receipt_sha TEXT NOT NULL, recorded_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS document_read_memory(
      doc_id TEXT, sha256 TEXT, completion_json TEXT NOT NULL, completed_at TEXT NOT NULL,
      released_at TEXT, PRIMARY KEY(doc_id,sha256));
    CREATE TABLE IF NOT EXISTS document_remote_checks(
      doc_id TEXT PRIMARY KEY, sha256 TEXT, etag TEXT, modified TEXT,
      last_checked TEXT, next_check TEXT, last_status TEXT);
    CREATE TABLE IF NOT EXISTS document_memory_events(
      id INTEGER PRIMARY KEY, doc_id TEXT, checked_at TEXT, result_json TEXT);
    ''')
    db.commit()


def receipt_sources(db, entry):
    """Only an identical, previously validated interpretation can use its receipt."""
    if 'evidence_receipts' not in tables(db):
        return None
    row = db.execute('SELECT * FROM evidence_receipts WHERE review_id=?', (entry['id'],)).fetchone()
    if row is None or row['body_sha'] != fingerprint(entry):
        return None
    sources = json.loads(row['sources_json'])
    check(fingerprint({'body_sha': row['body_sha'], 'sources': sources}) == row['receipt_sha'], 'Receipt integrity mismatch')
    result = []
    for source in sources:
        s = dict(source)
        r = db.execute('SELECT project_id,url FROM documents WHERE id=?', (s['doc_id'],)).fetchone()
        check(r is not None and r['project_id'] == entry['project_id'] and r['url'] == s['url'], 'Receipt project/source mismatch')
        h = db.execute('SELECT sha256 FROM document_heads WHERE doc_id=?', (s['doc_id'],)).fetchone()
        s['head_matches_reviewed_version'] = h is not None and h[0] == s['sha256']
        s['provenance_mode'] = 'recorded_page_evidence'
        result.append(s)
    return result


def make_receipt(db, entry, sources):
    """Called only after D3 has validated the original and interpretation schema."""
    compact = []
    for source, evidence in zip(sources, entry['evidence']):
        r = db.execute('SELECT extraction_json FROM versions WHERE doc_id=? AND sha256=?',
                       (source['doc_id'], source['sha256'])).fetchone()
        pages = json.loads(r[0]).get('pages', [])
        text = next(p.get('text', '') for p in pages if p['page'] == source['page'])
        normalized = re.sub(r'\s+', ' ', text).strip()
        anchor = re.sub(r'\s+', ' ', evidence['anchor']).strip()
        offset = normalized.casefold().find(anchor.casefold())
        check(offset >= 0, 'Cannot record a missing page anchor')
        compact.append({**source, 'page_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'excerpt': normalized[max(0, offset-160):offset+len(anchor)+240],
            'anchor': anchor, 'original_verified_at': stamp()})
    body_sha = fingerprint(entry)
    return (entry['id'], body_sha, canonical(compact),
            fingerprint({'body_sha': body_sha, 'sources': compact}), stamp())


class Memory:
    def __init__(self, ledger):
        self.ledger, self.root, self.db = ledger, ledger.root, ledger.db
        schema(self.db)

    def completed(self, did, sha=None):
        if sha is None:
            h = self.db.execute('SELECT sha256 FROM document_heads WHERE doc_id=?', (did,)).fetchone()
            if h is None:
                return None
            sha = h[0]
        return self.db.execute('SELECT * FROM document_read_memory WHERE doc_id=? AND sha256=?', (did, sha)).fetchone()

    def complete(self, plan):
        """Semantic/visual completion is an explicit attestation, not auto-detection."""
        check(plan.get('schema_version') == '1.0', 'Versioned completion plan required')
        did, sha = plan['doc_id'], plan['sha256']
        old = self.completed(did, sha)
        if old:
            check(old['completion_json'] == canonical(plan), 'Immutable completion changed')
            return 'already_completed'
        row = self.db.execute('SELECT v.* FROM versions v JOIN documents d ON d.id=v.doc_id WHERE v.doc_id=? AND v.sha256=? AND d.project_id=?',
                              (did, sha, plan['project_id'])).fetchone()
        check(row is not None, 'Unknown project/version')
        h = self.db.execute('SELECT sha256 FROM document_heads WHERE doc_id=?', (did,)).fetchone()
        check(h is not None and h[0] == sha, 'Only the acquired current version may be completed')
        ext = json.loads(row['extraction_json'])
        check(ext.get('kind') == 'pdf' and ext.get('page_count', 0) > 0, 'Readable PDF required')
        original = self.root/'objects'/(sha+'.pdf')
        check(original.is_file(), 'Original needed for first completion')
        with original.open('rb') as f:
            check(hashlib.file_digest(f, 'sha256').hexdigest() == sha, 'Original hash mismatch')
        pages = plan.get('pages', [])
        check(len(pages) == ext['page_count'] and {p['page'] for p in pages} == set(range(1,ext['page_count']+1)), 'All PDF pages must be explicitly reviewed')
        for page in pages:
            check(page.get('mode') == 'text_and_visual' and len(page.get('note','')) >= 15, 'Page reading/visual attestation missing')
        check(plan.get('reviewer') == 'assistant_document_review', 'Reviewer provenance missing')
        date.fromisoformat(plan['reviewed_on'])
        outcomes = plan.get('outcomes', {})
        check(set(outcomes) == FIELDS, 'Every required field needs a recorded outcome')
        for outcome in outcomes.values():
            check(outcome.get('status') in OUTCOMES and len(outcome.get('note','')) >= 10, 'Invalid field outcome')
            if outcome['status'] in {'recorded', 'conflict_recorded'}:
                check(outcome.get('review_ids'), 'Recorded field needs evidence review IDs')
            for rid in outcome.get('review_ids', []):
                rr = self.db.execute('SELECT body_json FROM documentary_reviews WHERE review_id=?', (rid,)).fetchone()
                check(rr is not None, 'Referenced review absent')
                entry = json.loads(rr[0]);sources = receipt_sources(self.db, entry)
                check(sources and any(s['doc_id']==did and s['sha256']==sha for s in sources), 'Referenced review has no receipt for this version')
        with self.db:
            self.db.execute('INSERT INTO document_read_memory VALUES(?,?,?,?,NULL)', (did,sha,canonical(plan),stamp()))
            self.db.execute('INSERT OR REPLACE INTO document_remote_checks VALUES(?,?,?,?,?,?,?)',
                (did,sha,row['etag'] or '',row['modified'] or '',None,stamp(),'not_checked_since_reading'))
            if 'document_work' in tables(self.db):
                self.db.execute("UPDATE document_work SET state='read_complete',next_retry=NULL WHERE doc_id=?", (did,))
        return 'completed'

    def release(self, did, sha=None):
        memory = self.completed(did, sha)
        check(memory is not None, 'Do not release an incomplete reading as completed')
        sha = memory['sha256']
        # Shared hashes cannot be deleted while another use still needs review.
        refs = self.db.execute('SELECT doc_id FROM versions WHERE sha256=?', (sha,)).fetchall()
        check(all(self.completed(r[0],sha) for r in refs), 'Shared content has unreviewed uses')
        if 'container_members' in tables(self.db):
            check(not self.db.execute('SELECT 1 FROM container_members WHERE content_sha=?', (sha,)).fetchone(), 'Container child needs explicit chain completion first')
        # Persist minimal page fingerprints first; the operation is crash-retry safe.
        with self.db:
            for r in refs:
                row = self.db.execute('SELECT extraction_json FROM versions WHERE doc_id=? AND sha256=?',(r[0],sha)).fetchone()
                ext=json.loads(row[0]);ext=thin_extraction(ext, completed=True)
                self.db.execute('UPDATE versions SET extraction_json=? WHERE doc_id=? AND sha256=?', (canonical(ext),r[0],sha))
                self.db.execute('DELETE FROM observations WHERE doc_id=? AND sha256=?',(r[0],sha))
            if 'visual_queue' in tables(self.db):
                self.db.execute("UPDATE visual_queue SET path=NULL,status='reviewed_binary_released' WHERE sha256=?",(sha,))
        removed=0
        for suffix in ('.pdf','.bin'):
            p=self.root/'objects'/(sha+suffix)
            if p.is_file():removed+=p.stat().st_size;p.unlink()
        renders=self.root/'renders'/sha
        if renders.exists():shutil.rmtree(renders)
        with self.db:
            self.db.execute('UPDATE document_read_memory SET released_at=? WHERE sha256=?',(stamp(),sha))
        return removed

    def check_remote(self, did, *, session=None, validate=None, force=False, interval_days=7,
                     max_bytes=256*1024**2, budget=120):
        from wind_document_audit import validate_url
        validate=validate or validate_url
        old=self.completed(did)
        check(old is not None, 'Remote reuse requires completed current version')
        remote=self.db.execute('SELECT * FROM document_remote_checks WHERE doc_id=?',(did,)).fetchone()
        check(remote is not None and remote['sha256']==old['sha256'], 'Missing version-bound remote validators')
        if not force and remote['next_check'] and remote['next_check'] > stamp():
            return {'status':'check_not_due','doc_id':did,'sha256':old['sha256'],'bytes_transferred':0,'text_extractions':0}
        doc=self.db.execute('SELECT * FROM documents WHERE id=?',(did,)).fetchone()
        headers={'User-Agent':'WindDocumentMemory/0.5','Accept-Encoding':'identity'}
        # Strong ETag preferred. A weak ETag is not a byte-identity proof.
        tag=remote['etag'] or ''
        if tag and not tag.startswith('W/'):
            headers['If-None-Match']=tag
        elif remote['modified']:
            headers['If-Modified-Since']=remote['modified']
        own=session is None;client=session or requests.Session();response=None
        result={'doc_id':did,'sha256':old['sha256'],'bytes_transferred':0,'text_extractions':0}
        final=doc['url'];start=time.monotonic();temp=None
        try:
            for _ in range(6):
                validate(final)
                response=client.get(final,headers=headers,timeout=(6,25),stream=True,allow_redirects=False)
                code=response.status_code;result['http_status']=code
                if code in (301,302,303,307,308):
                    target=response.headers.get('Location');response.close();check(target,'Redirect without Location')
                    final=urljoin(final,target)
                    # Validators bind the original resource, not a different target.
                    headers.pop('If-None-Match',None);headers.pop('If-Modified-Since',None)
                    continue
                break
            else:raise ValueError('Redirect limit exceeded')
            if code==304:
                check('If-None-Match' in headers or 'If-Modified-Since' in headers, 'Unexpected 304 without conditional request')
                if 'If-None-Match' in headers and response.headers.get('ETag'):
                    check(response.headers['ETag'] == headers['If-None-Match'], '304 carries a different version ETag')
                result['status']='unchanged_by_server'
            elif code==200:
                size=response.headers.get('Content-Length')
                check(not size or int(size)<=max_bytes,'Download exceeds configured comparison limit')
                if response.headers.get('Content-Encoding','identity') not in ('','identity'):
                    raise ValueError('Encoded comparison response not supported')
                with tempfile.NamedTemporaryFile(dir=self.root,suffix='.compare',delete=False) as f:
                    temp=Path(f.name);sha=hashlib.sha256()
                    for block in response.iter_content(131072):
                        result['bytes_transferred']+=len(block)
                        check(result['bytes_transferred']<=max_bytes,'Comparison byte budget exceeded')
                        check(time.monotonic()-start<=budget,'Comparison time budget exceeded')
                        sha.update(block);f.write(block)
                check(result['bytes_transferred']>0,'Empty comparison response')
                check(not size or int(size)==result['bytes_transferred'],'Incomplete response body')
                current=sha.hexdigest()
                if current==old['sha256']:
                    result['status']='unchanged_by_hash'
                else:
                    d2=MemoryD2(self.ledger,validate,session=client)
                    transfer={'path':str(temp),'sha256':current,'bytes':result['bytes_transferred'],
                        'etag':response.headers.get('ETag',''),'modified':response.headers.get('Last-Modified',''),
                        'final_url':final}
                    result['text_extractions']=1
                    acquired=d2.ingest_transfer(did,transfer,render_limit=0)
                    h=self.db.execute('SELECT sha256 FROM document_heads WHERE doc_id=?',(did,)).fetchone()
                    check(h is not None and h[0]==current,'Changed response was not a readable new version')
                    result.update(status='content_changed_review_required',sha256=current,text_extractions=1,acquisition=acquired)
                    if 'document_work' in tables(self.db):
                        self.db.execute("UPDATE document_work SET state='text_available_review_pending',next_retry=NULL WHERE doc_id=?",(did,));self.db.commit()
            else:
                result.update(status='remote_check_failed',detail='HTTP '+str(code))
            if result['status'] in {'unchanged_by_server','unchanged_by_hash'}:
                with self.db:
                    # Only store validators received on a full, hash-matched representation.
                    self.db.execute('UPDATE document_remote_checks SET etag=?,modified=? WHERE doc_id=?',
                        ((response.headers.get('ETag','') if code==200 else remote['etag']),
                         (response.headers.get('Last-Modified','') if code==200 else remote['modified']),did))
        except Exception as exc:
            result.update(status='remote_check_failed',detail=str(exc)[:400])
        finally:
            if temp:temp.unlink(missing_ok=True)
            if response is not None:response.close()
            if own:client.close()
        days=interval_days if result['status']!='remote_check_failed' else 1
        next_time=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat(timespec='seconds')
        with self.db:
            self.db.execute('UPDATE document_remote_checks SET last_checked=?,next_check=?,last_status=? WHERE doc_id=?',(stamp(),next_time,result['status'],did))
            self.db.execute('INSERT INTO document_memory_events(doc_id,checked_at,result_json) VALUES(?,?,?)',(did,stamp(),canonical(result)))
        return result

    def export(self):
        completed=[dict(r) for r in self.db.execute('SELECT m.*,d.project_id,d.url,h.sha256 AS head_sha FROM document_read_memory m JOIN documents d ON d.id=m.doc_id LEFT JOIN document_heads h ON h.doc_id=m.doc_id')]
        for r in completed:r['completion']=json.loads(r.pop('completion_json'))
        result={'completed_document_versions':len(completed),'documents':completed,
            'receipts':self.db.execute('SELECT COUNT(*) FROM evidence_receipts').fetchone()[0],
            'checks':[dict(r) for r in self.db.execute('SELECT * FROM document_remote_checks')],
            'events':[json.loads(r[0]) for r in self.db.execute('SELECT result_json FROM document_memory_events')],
            'complete_dossiers':0,'canonical_writes':0,
            'guard':'Memoria delle letture e dei riscontri; non archivio di originali. Completato documento non significa completato fascicolo.'}
        (self.root/'memory-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result

    def snapshot(self, destination):
        """Portable memory only: never copy PDF, renders, containers or full text."""
        destination=Path(destination)
        check(destination.resolve()!=self.root.resolve(),'Snapshot must not overwrite the working ledger')
        destination.mkdir(parents=True,exist_ok=True)
        check(not any(destination.iterdir()),'Snapshot destination must be empty')
        self.db.commit();target=sqlite3.connect(destination/'audit.sqlite')
        try:
            self.db.backup(target)
            with target:
                for did,sha,body in target.execute('SELECT doc_id,sha256,extraction_json FROM versions').fetchall():
                    completed=target.execute('SELECT 1 FROM document_read_memory WHERE doc_id=? AND sha256=?',(did,sha)).fetchone() is not None
                    target.execute('UPDATE versions SET extraction_json=? WHERE doc_id=? AND sha256=?',(canonical(thin_extraction(json.loads(body),completed)),did,sha))
                if 'document_work' in tables(target):
                    target.execute("UPDATE document_work SET state='review_pending_source_not_cached' WHERE state IN ('text_available_review_pending','visual_reading_required')")
                target.execute('DELETE FROM observations')  # unvalidated regex mentions are not durable facts
                if 'container_members' in tables(target):
                    for mid,body in target.execute('SELECT id,extraction_json FROM container_members').fetchall():
                        target.execute('UPDATE container_members SET extraction_json=? WHERE id=?',(canonical(thin_extraction(json.loads(body or '{}'))),mid))
                if 'visual_queue' in tables(target):
                    target.execute("UPDATE visual_queue SET path=NULL,status=CASE WHEN status='reviewed_binary_released' THEN status ELSE 'source_needed_for_pending_visual_review' END")
            target.execute('VACUUM')  # do not leave deleted page text in SQLite free pages
        finally:target.close()
        report=self.export();(destination/'memory-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return {'memory_bytes':sum(p.stat().st_size for p in destination.iterdir()),'binary_files':0,'full_documents_stored':0}


def thin_extraction(ext, completed=False):
    return {'kind':ext.get('kind'),'status':'read_complete' if completed else 'reading_pending_source_not_cached',
        'page_count':ext.get('page_count',len(ext.get('pages',[]))),
        'pages':[{'page':p['page'],'text_characters':p.get('text_characters',0),
            'page_text_sha256':hashlib.sha256(p['text'].encode()).hexdigest() if 'text' in p else p.get('page_text_sha256'),
            'needs_visual_review':not completed} for p in ext.get('pages',[])],
        'text_released':True,'fascicolo_complete':False}



from wind_document_inventory import D2
from wind_document_review import Reviews
from wind_document_queue import Queue


class MemoryReviews(Reviews):
    """D3 evidence rules retained; validated receipts survive intentional release."""
    def __init__(self, root):
        super().__init__(root)
        schema(self.db)

    def validate(self, entry):
        if isinstance(entry, dict) and entry.get('id'):
            sources=receipt_sources(self.db,entry)
            if sources is not None:return sources
        return super().validate(entry)

    def import_batch(self, batch):
        check(batch.get('schema_version')=='1.0' and batch.get('reviews'),'Versioned review batch required')
        entries=batch['reviews'];check(len({e['id'] for e in entries})==len(entries),'Duplicate review IDs')
        prepared=[];receipts=[]
        for entry in entries:
            sources=self.validate(entry);body=canonical(entry);sha=fingerprint(entry)
            old=self.db.execute('SELECT body_sha256 FROM documentary_reviews WHERE review_id=?',(entry['id'],)).fetchone()
            check(old is None or old[0]==sha,'Immutable review changed')
            if receipt_sources(self.db,entry) is None:receipts.append(make_receipt(self.db,entry,sources))
            prepared.append((entry['id'],entry['project_id'],sha,body,stamp()))
        before=self.db.total_changes
        with self.db:
            self.db.executemany('INSERT OR IGNORE INTO documentary_reviews VALUES(?,?,?,?,?)',prepared)
            inserted=self.db.total_changes-before
            self.db.executemany('INSERT OR IGNORE INTO evidence_receipts VALUES(?,?,?,?,?)',receipts)
        return inserted

    def export(self):
        report=super().export()
        for row in report['reviews']:
            if row['evidence_integrity']=='pinned_evidence_available' and all(s.get('provenance_mode')=='recorded_page_evidence' for s in row['sources']):
                row['evidence_integrity']='recorded_page_evidence'
        (self.root/'review-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        from html import escape
        cards=[]
        for r in report['reviews']:
            links=''.join('<li><a href="'+escape(s['url'],quote=True)+'">Fonte</a> · p. '+str(s['page'])+' · SHA '+s['sha256'][:12]+'</li>' for s in r['sources'])
            cards.append('<article><h2>'+escape(r['project_id'])+'</h2><p><b>'+escape(r['statement'])+'</b></p><pre>'+escape(json.dumps(r['value'],ensure_ascii=False,indent=2))+'</pre><p>'+escape(r['limits'])+'</p><p>Provenienza: '+escape(r['evidence_integrity'])+'</p><ul>'+links+'</ul></article>')
        html='<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wind — memoria documentale</title><style>body{font:16px/1.5 system-ui;max-width:1050px;margin:30px auto;padding:0 20px;background:#f4f7f6;color:#162c33}article{background:white;padding:20px;border:1px solid #ccd8d7;border-radius:12px;margin:15px 0}pre,li{white-space:pre-wrap;overflow-wrap:anywhere}h2{font-size:20px}a{color:#087766}</style><h1>Wind — memoria delle informazioni</h1><p>Riscontri e riferimenti restano disponibili senza conservare gli originali. Un documento completato non certifica tutto il fascicolo.</p>'+''.join(cards)+'</html>'
        (self.root/'review-report.html').write_text(html,encoding='utf-8')
        return report


class MemoryD2(D2):
    def acquire(self,did,*,max_bytes=256*1024**2,render_limit=4,refresh=False):
        memory=Memory(self.ledger);read=memory.completed(did)
        if read:
            if refresh:return memory.check_remote(did,session=self.session,validate=self.validate,force=True,max_bytes=max_bytes)
            return {'status':'read_memory_reused','doc_id':did,'sha256':read['sha256'],'bytes_transferred':0,'text_extractions':0}
        old=self.db.execute('SELECT v.* FROM versions v JOIN document_heads h ON v.doc_id=h.doc_id AND v.sha256=h.sha256 WHERE v.doc_id=?',(did,)).fetchone()
        from wind_document_inventory import file_hash,stream_download
        if old and not refresh:
            ext=json.loads(old['extraction_json']);path=self.root/'objects'/(old['sha256']+'.pdf')
            if path.is_file() and not ext.get('text_released') and file_hash(path)==old['sha256']:
                self.render(did,old['sha256'],path,ext,render_limit)
                return {'status':'cached_verified','doc_id':did,'sha256':old['sha256']}
        doc=self.db.execute('SELECT * FROM documents WHERE id=?',(did,)).fetchone()
        transfer=stream_download(doc['url'],self.root/'transfers'/did,validate=self.validate,session=self.session,max_bytes=max_bytes)
        self.attempt(did,transfer)
        if transfer['status']!='downloaded':return transfer
        return self.ingest_transfer(did,transfer,render_limit=render_limit)

    def ingest_transfer(self,did,transfer,*,render_limit=0):
        from wind_document_inventory import extract_file
        source=Path(transfer['path']);sha=transfer['sha256'];ext=extract_file(source)
        target=self.root/'objects'/(sha+('.pdf' if ext['kind']=='pdf' else '.bin'))
        shutil.copyfile(source,target);source.unlink(missing_ok=True)
        self.db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?) ON CONFLICT(doc_id,sha256) DO UPDATE SET extraction_json=excluded.extraction_json,etag=excluded.etag,modified=excluded.modified',
            (did,sha,stamp(),transfer['bytes'],transfer.get('etag'),transfer.get('modified'),canonical(ext)))
        if ext.get('pages') and ext['status'] not in ('not_a_pdf','invalid_pdf','encrypted'):
            self.db.execute('INSERT INTO document_heads VALUES(?,?) ON CONFLICT(doc_id) DO UPDATE SET sha256=excluded.sha256',(did,sha))
        from wind_document_audit import power_mentions
        for page in ext.get('pages',[]):
            for item in power_mentions(page.get('text','')):
                self.db.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?)',(did,sha,page['page'],canonical(item)))
        self.db.commit();self.attempt(did,{'status':ext['status'],'sha256':sha,'final_url':transfer['final_url']})
        if ext['kind']=='pdf' and ext.get('pages'):self.render(did,sha,target,ext,render_limit)
        return {'status':ext['status'],'doc_id':did,'sha256':sha,'bytes':transfer['bytes'],'pages':ext.get('page_count')}


class MemoryQueue(Queue):
    def sync_documents(self):
        super().sync_documents();memory=Memory(self.ledger)
        for row in self.db.execute('SELECT doc_id FROM document_work').fetchall():
            if memory.completed(row[0]):
                self.db.execute("UPDATE document_work SET state='read_complete',next_retry=NULL WHERE doc_id=?",(row[0],))
        self.db.commit()

    def acquire(self,projects=None,limit=6,d2=None):
        from wind_document_audit import validate_url
        return super().acquire(projects,limit,d2=d2 or MemoryD2(self.ledger,validate_url))

def main():
    from wind_document_audit import Ledger
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--complete');p.add_argument('--check',action='store_true');p.add_argument('--force-check',action='store_true');p.add_argument('--snapshot')
    a=p.parse_args();ledger=Ledger(a.output)
    try:
        m=Memory(ledger)
        if a.complete:
            for plan in json.loads(Path(a.complete).read_text(encoding='utf-8'))['documents']:
                print(m.complete(plan));print('Bytes released:',m.release(plan['doc_id'],plan['sha256']))
        if a.check:
            for row in ledger.db.execute('SELECT doc_id FROM document_read_memory GROUP BY doc_id').fetchall():
                if m.completed(row[0]):print(json.dumps(m.check_remote(row[0],force=a.force_check),ensure_ascii=False))
        if a.snapshot:print(json.dumps(m.snapshot(a.snapshot)))
        print(json.dumps({'completed_document_versions':m.export()['completed_document_versions'],'complete_dossiers':0}))
    finally:ledger.db.close()


if __name__=='__main__':main()
