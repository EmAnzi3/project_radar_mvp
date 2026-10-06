#!/usr/bin/env python3
"""D4: persistent, fair document work queue for every registered project.

Source references are not read dossiers. Unapproved/missing URLs and unfinished
indexes remain work tickets; zero daily discoveries never clears this queue.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import datetime,timedelta,timezone
from html import escape
from pathlib import Path
from urllib.parse import urljoin,urlsplit

from wind_document_audit import Ledger,validate_url
from wind_document_inventory import D2,file_hash,stamp
from wind_document_containers import Containers,kind_of


def asset_url(url):
    return bool(re.search(r'\.(pdf|zip|p7m)(?:$|[?#])|/File/Documento/\d+',url,re.I))


def priority(label):
    return 10 if re.search(r'cronoprogramma|relazione.*generale|sintesi.*tecnica|avviso|elenco.*elaborati',label,re.I) else 30


class Queue:
    def __init__(self,ledger):
        self.ledger,self.db,self.root=ledger,ledger.db,ledger.root
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS source_work(
          id TEXT PRIMARY KEY,project_id TEXT,url TEXT,label TEXT,state TEXT,detail TEXT,checked_at TEXT);
        CREATE TABLE IF NOT EXISTS document_work(
          doc_id TEXT PRIMARY KEY,project_id TEXT,priority INTEGER,state TEXT,
          attempts INTEGER DEFAULT 0,next_retry TEXT,last_result TEXT);
        CREATE TABLE IF NOT EXISTS document_work_history(
          id INTEGER PRIMARY KEY,doc_id TEXT,checked_at TEXT,result_json TEXT);
        ''')
        self.db.commit()

    def seed(self):
        for p in self.db.execute('SELECT * FROM projects').fetchall():
            record=json.loads(p['inherited_json']).get('record',{})
            sources=record.get('sources') or []
            if not sources:self._source(p['id'],'','No source reference in registry')
            for source in sources:
                if isinstance(source,dict):self._source(p['id'],source.get('url') or '',source.get('title') or source.get('publisher') or 'Registry source')
        for p in self.db.execute('SELECT * FROM qualification').fetchall():
            row=json.loads(p['inherited_json']);self._source(p['id'],row.get('source_url') or '',f"Qualification {p['id']}")
        self.sync_documents()

    def _source(self,pid,url,label):
        sid=hashlib.sha256(json.dumps([pid,url,label],ensure_ascii=False).encode()).hexdigest()[:32]
        state='source_pending';detail=''
        if not url:state='missing_reference';detail='Registry has no downloadable URL; uploaded/original document must be located'
        else:
            try:validate_url(url,resolve=False)
            except ValueError as exc:state='host_review_required';detail=str(exc)
        self.db.execute('INSERT OR IGNORE INTO source_work VALUES(?,?,?,?,?,?,?)',(sid,pid,url,label,state,detail,None));self.db.commit()
        if state=='source_pending' and asset_url(url):
            self.ledger.register(pid,url,label,'auto')
            self.db.execute("UPDATE source_work SET state='asset_queued' WHERE id=? AND state='source_pending'",(sid,));self.db.commit()
        return sid

    def sync_documents(self):
        rows=self.db.execute('SELECT * FROM documents').fetchall()
        for row in rows:
            if not asset_url(row['url']):continue
            self.db.execute('INSERT OR IGNORE INTO document_work(doc_id,project_id,priority,state) VALUES(?,?,?,?)',
                (row['id'],row['project_id'],priority(row['label']), 'pending_acquisition'))
            old=self.db.execute('SELECT v.sha256,v.extraction_json FROM versions v JOIN document_heads h ON v.doc_id=h.doc_id AND v.sha256=h.sha256 WHERE v.doc_id=?',(row['id'],)).fetchone()
            if old:
                extraction=json.loads(old['extraction_json']); original=self.root/'objects'/(old['sha256']+'.pdf')
                if extraction.get('pages') and original.is_file() and file_hash(original)==old['sha256']:
                    status='text_available_review_pending' if any(p.get('text_characters',0)>=40 for p in extraction['pages']) else 'visual_reading_required'
                    self.db.execute("UPDATE document_work SET state=? WHERE doc_id=? AND state IN ('pending_acquisition','retry_required')",(status,row['id']))
        self.db.commit()

    def expand(self,projects,*,index_limit=2,page_limit=100,d2=None):
        d2=d2 or D2(self.ledger,validate_url)
        # Limit work, not registration. Every observed procedure index is kept as a source ticket.
        for pid in projects:
            sources=self.db.execute("SELECT * FROM source_work WHERE project_id=? AND state='source_pending' ORDER BY id",(pid,)).fetchall()
            remaining=index_limit
            for source in sources:
                url=source['url']
                if re.search(r'/Oggetti/Documentazione/\d+/\d+',url):
                    if remaining<=0:continue
                    remaining-=1
                    result=d2.inventory(pid,url,page_limit=page_limit)
                    self.db.execute('UPDATE source_work SET state=?,detail=?,checked_at=? WHERE id=?',
                        (result['status'],json.dumps(result,ensure_ascii=False),stamp(),source['id']));self.db.commit();continue
                did=self.ledger.register(pid,url,source['label'],'auto')
                status=self.ledger.fetch(did)
                version=self.db.execute('SELECT v.extraction_json FROM versions v JOIN document_heads h ON h.doc_id=v.doc_id AND h.sha256=v.sha256 WHERE v.doc_id=?',(did,)).fetchone()
                result=json.loads(version[0]) if version else {}
                self.db.execute('UPDATE source_work SET state=?,detail=?,checked_at=? WHERE id=?',(status,'Not an exhaustive attachment inventory',stamp(),source['id']));self.db.commit()
                if status != 'html_read_inventory_unconfirmed' or result.get('kind')!='html':continue
                object_match=re.search(r'/Oggetti/Info/(\d+)',url)
                for href,label in result.get('links',[]):
                    link=urljoin(url,href)
                    if urlsplit(link).hostname != urlsplit(url).hostname:continue
                    docmatch=re.search(r'/Oggetti/Documentazione/(\d+)/(\d+)',link)
                    if docmatch and object_match and docmatch[1]==object_match[1]:
                        sid=self._source(pid,link,label or 'Observed MASE procedure index')
                        current=self.db.execute('SELECT state FROM source_work WHERE id=?',(sid,)).fetchone()[0]
                        if current=='source_pending' and remaining>0:
                            remaining-=1;inv=d2.inventory(pid,link,page_limit=page_limit)
                            self.db.execute('UPDATE source_work SET state=?,detail=?,checked_at=? WHERE id=?',
                                (inv['status'],json.dumps(inv,ensure_ascii=False),stamp(),sid));self.db.commit()
        self.sync_documents()

    def candidates(self,projects=None,limit=6):
        now=stamp();rows=self.db.execute("""SELECT w.*,d.url,d.label FROM document_work w JOIN documents d ON d.id=w.doc_id
            WHERE w.state IN ('pending_acquisition','retry_required') AND (w.next_retry IS NULL OR w.next_retry<=?)
            ORDER BY w.attempts,w.priority,w.project_id,w.doc_id""",(now,)).fetchall()
        groups={}
        for row in rows:
            if projects and row['project_id'] not in projects:continue
            groups.setdefault(row['project_id'],[]).append(dict(row))
        selected=[]
        while groups and len(selected)<limit:
            for pid in list(groups):
                if len(selected)>=limit:break
                selected.append(groups[pid].pop(0))
                if not groups[pid]:groups.pop(pid)
        return selected

    def acquire(self,projects=None,limit=6,d2=None):
        d2=d2 or D2(self.ledger,validate_url);containers=Containers(self.ledger);results=[]
        for row in self.candidates(projects,limit):
            did=row['doc_id'];result=d2.acquire(did,max_bytes=128*1024**2,render_limit=1)
            state='retry_required'
            if result.get('sha256'):
                sha=result['sha256'];binary=self.root/'objects'/(sha+'.bin');pdf=self.root/'objects'/(sha+'.pdf')
                if pdf.is_file():
                    version=self.db.execute('SELECT extraction_json FROM versions WHERE doc_id=? AND sha256=?',(did,sha)).fetchone()
                    ext=json.loads(version[0]) if version else {}
                    if ext.get('pages'):
                        state='text_available_review_pending' if any(p.get('text_characters',0)>=40 for p in ext['pages']) else 'visual_reading_required'
                    else:state='unsupported_or_unreadable'
                elif binary.is_file() and kind_of(binary,row['url']) in {'cms','zip'}:
                    result['container']=containers.open(did,sha)
                    state='container_opened_review_pending' if result['container']['status'] in {'opened_pending_review','cached_container_verified'} else 'container_partial_or_blocked'
                else:state='unsupported_or_unreadable'
            next_retry=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat(timespec='seconds') if state=='retry_required' else None
            self.db.execute('UPDATE document_work SET state=?,attempts=attempts+1,next_retry=?,last_result=? WHERE doc_id=?',
                (state,next_retry,json.dumps(result,ensure_ascii=False),did))
            self.db.execute('INSERT INTO document_work_history(doc_id,checked_at,result_json) VALUES(?,?,?)',(did,stamp(),json.dumps(result,ensure_ascii=False)));self.db.commit()
            results.append({'project_id':row['project_id'],'doc_id':did,'url':row['url'],'state':state,'result':result})
            print(json.dumps(results[-1],ensure_ascii=False),flush=True)
        return results

    def export(self):
        work=[dict(r) for r in self.db.execute('SELECT w.*,d.label,d.url FROM document_work w JOIN documents d ON d.id=w.doc_id ORDER BY w.project_id,w.priority,w.doc_id')]
        sources=[dict(r) for r in self.db.execute('SELECT * FROM source_work ORDER BY project_id,id')]
        counts=dict(self.db.execute('SELECT state,COUNT(*) FROM document_work GROUP BY state'))
        sources_count=dict(self.db.execute('SELECT state,COUNT(*) FROM source_work GROUP BY state'))
        containers=Containers(self.ledger).report()
        report={'generated_at':stamp(),'queue_counts':counts,'source_counts':sources_count,'projects_with_source_tickets':len({r['project_id'] for r in sources if not r['project_id'].startswith('RAW-')}),'qualification_with_source_tickets':len({r['project_id'] for r in sources if r['project_id'].startswith('RAW-')}),'work':work,'sources':sources,'containers':containers,'complete_dossiers':0,'canonical_writes':0,
            'guard':'Download, estrazione e apertura contenitori non equivalgono a lettura/validazione integrale. La coda non si azzera con un report giornaliero vuoto.'}
        (self.root/'queue-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        lines=['# D4 — coda documentale persistente',report['guard'],'',json.dumps(counts,ensure_ascii=False),'',f"Identità con riferimenti: {report['projects_with_source_tickets']}; record di qualificazione: {report['qualification_with_source_tickets']}"]
        (self.root/'queue-report.md').write_text('\n'.join(lines),encoding='utf-8')
        def table(rows,fields):
            return '<table><thead><tr>'+''.join('<th>'+escape(f)+'</th>' for f in fields)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(str(r.get(f) or ''))+'</td>' for f in fields)+'</tr>' for r in rows)+'</tbody></table>'
        html='<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wind D4 — coda documentale</title><style>body{font:15px/1.5 system-ui;margin:30px auto;padding:20px;max-width:1200px;color:#173038;background:#f5f7f8}table{border-collapse:collapse;width:100%;background:white;table-layout:fixed}td,th{padding:10px;border-bottom:1px solid #ccd6d8;vertical-align:top;overflow-wrap:anywhere;text-align:left}pre{white-space:pre-wrap}h2{margin-top:30px}</style><h1>Coda documentale Wind</h1><p>'+escape(report['guard'])+'</p><pre>'+escape(json.dumps(counts,ensure_ascii=False,indent=2))+'</pre><h2>Fonti e impedimenti</h2>'+table(sources,['project_id','label','state','detail'])+'<h2>Allegati</h2>'+table(work,['project_id','label','state','url'])+'</html>'
        (self.root/'queue-report.html').write_text(html,encoding='utf-8');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--plan');p.add_argument('--seed-only',action='store_true');p.add_argument('--max-assets',type=int,default=6);a=p.parse_args()
    if a.max_assets<0:p.error('max-assets cannot be negative')
    ledger=Ledger(a.output)
    try:
        queue=Queue(ledger);queue.seed();plan=json.loads(Path(a.plan).read_text(encoding='utf-8')) if a.plan else {}
        if not a.seed_only:
            queue.expand(plan.get('expand_projects',[]),index_limit=plan.get('index_limit_per_project',1),page_limit=plan.get('page_limit',100))
            queue.acquire(plan.get('acquire_projects'),a.max_assets)
        report=queue.export();print(json.dumps({'queue_counts':report['queue_counts'],'complete_dossiers':0},ensure_ascii=False))
    finally:ledger.db.close()


if __name__=='__main__':main()
