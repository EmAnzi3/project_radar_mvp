#!/usr/bin/env python3
"""Incremental commercial extraction, not whole-dossier certification.

Read the D7 ledger read-only. Prioritize useful documents, persist compact
page-backed leads after every successful file, and never auto-promote facts.
Only new/changed resources are parsed. PDFs live in temporary directories.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager, closing
from datetime import datetime, timedelta, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
import time
from urllib.parse import urlsplit, urljoin

PROFILE = 'commercial-v1'
FIELDS = {
    'identity_power': r'\b(?:[\d.,]+\s*(?:MW|kW|MWh)|aerogenerator\w*|BESS|accumulo)\b',
    'location_area': r'\b(?:comun[ei]|provincia|ubicazion\w*|ettar\w*|superficie|offshore|onshore)\b',
    'companies_roles': r'\b(?:proponente|committente|developer|progettista|appalt\w*|affidament\w*|EPC|BoP|contractor|aggiudic\w*)\b',
    'status': r'\b(?:autorizzazion\w*|decreto|parere|VIA|PAUR|avvio\s+(?:dei\s+)?lavori|in\s+costruzione|diniego|rigett\w*)\b',
    'schedule': r'\b(?:cronoprogramma|Gantt|commissioning|(?-i:COD)(?!\.)|inizio\s+lavori|fine\s+lavori|durata|\d+\s+mes[ei]|\d+\s+settimane)\b',
    'professional_contacts': r'\b(?:contatt\w*|referent\w*|e-?mail|PEC|procurement)\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
    'execution_scope': r'\b(?:battipal\w*|infission\w*|pali\s+di\s+fondazione|fondazion\w*|opere\s+civili|viabilit\w*|piazzol\w*|sollevament\w*|trasport\w*|cavidott\w*)\b',
}
PATTERNS = {key: re.compile(value, re.I) for key, value in FIELDS.items()}
IMPORTANT = re.compile(r'cronoprogramma|cantierizzazion|avviso|sintesi\s+non\s+tecnica|relazione\s+(?:tecnica\s+)?generale|elenco.*elaborati|autorizzazion|decreto|provvedimento|contratt|affidament|aggiudic|comunicato', re.I)
SPECIALIST = re.compile(r'granulometr|sediment|biocenos|benton|fanerogam|avifaun|chirotter|archeolog|acustic|rumore|fotoinser|fotografic|catastal|piano\s+particellare|carta\s+|habitat|geolog|idrolog|idraulic', re.I)
EXECUTION = re.compile(r'fondazion|viabilit|piazzol|logistic|trasport|connession|inquadramento|planimetria\s+generale|progetto\s+del\s+parco', re.I)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else packed(value).encode()).hexdigest()


def classify(label):
    """Metadata prioritization, never a claim that a document has been read."""
    if re.search(r'cronoprogramma|cantierizzazion|contratto|affidamento|aggiudicazione', label, re.I):
        return 0, 'execution_timing_or_decision'
    if SPECIALIST.search(label) or re.search(r'osservazioni.*(?:signor|privat|cittadin)|shadow.flicker|paesaggistic|fotovoltaic|analisi.*acque', label, re.I):
        return 3, 'specialist_deferred_not_discarded'
    if re.search(r'autorizzazione\s+unica|decreto\s+(?:di|VIA|PAUR)|provvedimento\s+(?:di|finale)',label,re.I):
        return 0, 'execution_timing_or_decision'
    if IMPORTANT.search(label) and not re.search(r'osservazioni|parere',label,re.I):
        return 1, 'identity_and_commercial_summary'
    if EXECUTION.search(label):
        return 2, 'execution_support'
    return 2, 'unclassified_requires_discovery'


def inventory(ledger):
    with closing(sqlite3.connect(Path(ledger).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(r) for r in db.execute('''SELECT w.doc_id,w.project_id,w.state,d.url,d.label,h.sha256,
            v.etag,v.modified, rc.next_check AS legacy_next_check, p.bucket,p.inherited_json,
            CASE WHEN m.doc_id IS NOT NULL THEN 1 ELSE 0 END AS legacy_complete
            FROM document_work w JOIN documents d ON d.id=w.doc_id
            LEFT JOIN document_heads h ON h.doc_id=d.id
            LEFT JOIN versions v ON v.doc_id=h.doc_id AND v.sha256=h.sha256
            LEFT JOIN document_read_memory m ON m.doc_id=h.doc_id AND m.sha256=h.sha256
            LEFT JOIN document_remote_checks rc ON rc.doc_id=d.id
            LEFT JOIN projects p ON p.id=w.project_id''')]
        metadata = {}
        for r in db.execute('''SELECT im.doc_id,im.metadata_json FROM inventory_members im
                              JOIN inventory_runs ir ON ir.id=im.run_id ORDER BY ir.started_at'''):
            metadata[r[0]] = json.loads(r[1])
    for r in rows:
        r['metadata'] = metadata.get(r['doc_id'], {})
        r['fingerprint'] = digest({k: r[k] for k in ('url', 'label', 'metadata', 'sha256')})
        r['priority'], r['priority_reason'] = classify(r['label'])
        record = json.loads(r.pop('inherited_json') or '{}').get('record', {})
        r['stage'] = record.get('stage', '')
    return rows


def fair_selection(rows, limit):
    """One per project per round; do not let a 487-attachment dossier monopolize work."""
    groups = defaultdict(deque)
    for r in sorted(rows, key=lambda x: (x['priority'], not (x['stage'] in {'E4','E5','E6','E7'}), x['doc_id'])):
        groups[r['project_id']].append(r)
    selected = []
    while groups and len(selected) < limit:
        order = sorted(groups, key=lambda pid: (groups[pid][0]['priority'], pid))
        for pid in order:
            if len(selected) == limit:
                break
            selected.append(groups[pid].popleft())
            if not groups[pid]:
                del groups[pid]
    return selected


@contextmanager
def lock(root):
    root.mkdir(parents=True, exist_ok=True)
    path = root / '.writer.lock'
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(packed({'pid': os.getpid(), 'started': now()}))
        yield
    finally:
        path.unlink(missing_ok=True)


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.db = sqlite3.connect(self.root / 'commercial.sqlite')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS packets(sha TEXT,profile TEXT,payload TEXT,PRIMARY KEY(sha,profile));
        CREATE TABLE IF NOT EXISTS resources(url TEXT PRIMARY KEY,sha TEXT,etag TEXT,modified TEXT,
            next_check TEXT,status TEXT,checked_at TEXT,error TEXT);
        CREATE TABLE IF NOT EXISTS links(doc_id TEXT PRIMARY KEY,project_id TEXT,url TEXT,fingerprint TEXT);
        CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,created_at TEXT,summary TEXT);
        ''')
        self.db.commit()

    def resource(self, url):
        r = self.db.execute('SELECT * FROM resources WHERE url=?', (url,)).fetchone()
        return dict(r) if r else None

    def save(self, row, result):
        if result['status']=='offline_source_missing':
            return  # No remote observation: do not acknowledge metadata or defer a real retry.
        old = self.resource(row['url']) or {}
        ok = result['status'] in {'targeted_extraction','same_content_reused','not_modified'}
        next_check = (datetime.now(timezone.utc) + timedelta(days=7 if ok else 1)).isoformat(timespec='seconds')
        with self.db:
            if result.get('packet') is not None:
                self.db.execute('INSERT OR IGNORE INTO packets VALUES(?,?,?)', (result['sha'], PROFILE, packed(result['packet'])))
            self.db.execute('INSERT OR REPLACE INTO resources VALUES(?,?,?,?,?,?,?,?)',
                (row['url'], result.get('sha') if ok else old.get('sha'),
                 result.get('etag', old.get('etag')), result.get('modified', old.get('modified')),
                 next_check,result['status'],now(),result.get('error')))
            # Failed acquisition never acknowledges changed index metadata.
            if ok:
                self.db.execute('INSERT OR REPLACE INTO links VALUES(?,?,?,?)',
                                (row['doc_id'],row['project_id'],row['url'],row['fingerprint']))

    def close(self):
        self.db.close()


def page_packet(number, text):
    text = re.sub(r'\s+', ' ', text or '').strip()
    snippets = {}
    for field, pattern in PATTERNS.items():
        found, spans = [], []
        for m in pattern.finditer(text):
            left, right = max(0, m.start()-100), min(len(text), m.end()+230)
            if any(left < b and right > a for a,b in spans):
                continue
            spans.append((left,right));found.append(text[left:right])
            if len(found) == 3:
                break
        if found:
            snippets[field] = found
    flags = []
    if len(text) < 80:
        flags.append('low_native_text_not_empty_page')
    if PATTERNS['schedule'].search(text):
        flags.append('schedule_table_or_scope_review')
    # A native-text pass cannot detect all drawn text, logos or signatures.
    if number == 1:
        flags.append('cover_visual_check_if_identity_or_role_missing')
    return {'page':number,'text_sha256':digest(text.encode()),'characters':len(text),
            'snippets':snippets,'review_flags':flags}


def extract(path, previous=None, budget=60):
    from pypdf import PdfReader
    start = time.monotonic()
    reader = PdfReader(path, strict=False)
    if reader.is_encrypted and not reader.decrypt(''):
        raise ValueError('Encrypted PDF: manual access required')
    old_pages = {p['text_sha256']:p for p in (previous or {}).get('pages', [])}
    pages, skipped, reused = [], [], 0
    retained=Counter(); seen=set(); omitted=Counter()
    for n, page in enumerate(reader.pages, 1):
        if time.monotonic()-start > budget:
            skipped.extend(range(n, len(reader.pages)+1));break
        try:
            text = re.sub(r'\s+', ' ', page.extract_text() or '').strip()
            old = old_pages.get(digest(text.encode()))
            if old:
                pages.append({**old, 'page':n});reused += 1
            else:
                pages.append(page_packet(n,text))
        except Exception:
            skipped.append(n)
    # Rank across the whole native-text pass, not first-hit wins: contents and
    # repeated headers must not crowd out a later power value or works schedule.
    for field in FIELDS:
        candidates=[]; unique=set()
        for pg in pages:
            for excerpt in pg['snippets'].get(field, []):
                if excerpt in unique:continue
                unique.add(excerpt)
                score=0 if re.search(r'\d[\d.,]*\s*(?:MW|kW|MWh|mes[ei]|settimane)|cronoprogramma|committente|proponente|aggiudicat|affidato',excerpt,re.I) else 2
                if re.search(r'\.{3,}',excerpt):score+=5
                candidates.append((score,pg['page'],excerpt))
        chosen={(page,excerpt) for _,page,excerpt in sorted(candidates)[:12]}
        omitted[field]=max(0,len(candidates)-len(chosen))
        for pg in pages:
            kept=[e for e in pg['snippets'].get(field, []) if (pg['page'],e) in chosen]
            if kept:pg['snippets'][field]=kept
            else:pg['snippets'].pop(field,None)
    present=sorted({field for pg in pages for field in pg['snippets']})
    return {'profile':PROFILE,'page_count':len(reader.pages),'pages':pages,'unprocessed_pages':skipped,
        'fields_with_candidate_passages':present,
        'fields_not_established':[field for field in FIELDS if field not in present],
        'page_packets_reused':reused,'native_pages_processed':len(pages),
        'additional_passages_not_retained':dict(omitted),
        'semantics':'candidate_passages_not_verified_facts','whole_document_read_complete':False,
        'coverage':'native_text_only_visual_elements_may_be_missing',
        'guard':'No EPC award, calendar date, contact role, or total MW may be inferred from a keyword hit.'}


def transfer(url, target, old, validate, *, client=None, max_bytes=128*1024**2, budget=120):
    """Conditional public download. No paid services, guessing, or access bypass."""
    import requests
    headers = {'User-Agent':'WindCommercialReader/1.0','Accept-Encoding':'identity'}
    if old and old.get('etag') and not old['etag'].startswith('W/'):
        headers['If-None-Match'] = old['etag']
    elif old and old.get('modified'):
        headers['If-Modified-Since'] = old['modified']
    own = client is None
    client = client or requests.Session()
    response = None;final = url;start = time.monotonic();count = 0;requests_made=0
    try:
        for _ in range(6):
            validate(final)
            requests_made += 1
            response = client.get(final,headers=headers,timeout=(8,30),stream=True,allow_redirects=False)
            if response.status_code not in (301,302,303,307,308):break
            location = response.headers.get('Location');response.close()
            if not location:raise ValueError('Redirect without target')
            final = urljoin(final,location)
            headers.pop('If-None-Match',None);headers.pop('If-Modified-Since',None)
        else:raise ValueError('Redirect limit')
        if response.status_code == 304:
            if not old or not old.get('sha') or not any(k in headers for k in ('If-None-Match','If-Modified-Since')):
                raise ValueError('Unsolicited 304')
            if 'If-None-Match' in headers and response.headers.get('ETag') not in (None, headers['If-None-Match']):
                raise ValueError('Mismatched 304 ETag')
            return {'status':'not_modified','sha':old['sha'],'bytes':0,'network_requests':requests_made,'text_extractions':0}
        response.raise_for_status()
        if response.status_code != 200:raise ValueError('Unexpected partial response')
        if response.headers.get('Content-Encoding','identity') not in ('','identity'):raise ValueError('Encoded body refused')
        size=int(response.headers.get('Content-Length') or 0)
        if size > max_bytes:raise ValueError('Size limit: dedicated large-file lane required')
        sha=hashlib.sha256()
        with open(target,'wb') as f:
            for block in response.iter_content(131072):
                count += len(block)
                if count > max_bytes or time.monotonic()-start > budget:raise ValueError('Transfer budget exceeded')
                sha.update(block);f.write(block)
        if not count or (size and size != count):raise ValueError('Incomplete response')
        with open(target,'rb') as f:
            if b'%PDF-' not in f.read(1024):raise ValueError('Not a PDF; HTML/ZIP/P7M needs its own reader')
        return {'status':'downloaded','sha':sha.hexdigest(),'bytes':count,'network_requests':requests_made,
                'etag':response.headers.get('ETag',''),'modified':response.headers.get('Last-Modified','')}
    except Exception as exc:
        return {'status':'error','error':str(exc)[:400],'bytes':count,
                'network_requests':requests_made,'text_extractions':0}
    finally:
        if response is not None:response.close()
        if own:client.close()


def run(ledger, output, *, limit=50,workers=4,per_host=2,include_deferred=False,
        offline=False,replay=False,local_objects=None,fetcher=transfer,only_ids=None):
    if not (1<=workers<=8 and 1<=per_host<=2 and 0<=limit<=1000):raise ValueError('Invalid bounded batch settings')
    output=Path(output).resolve();ledger=Path(ledger).resolve()
    if output == ledger.parent or output in ledger.parents or ledger in output.parents:
        raise ValueError('Use a separate output directory; never overwrite the source ledger')
    started=time.monotonic();rows=inventory(ledger)
    with lock(output):
        store=Store(output)
        try:
            old_summary=json.loads((output/'summary.json').read_text()) if replay and (output/'summary.json').exists() else None
            if replay and old_summary is None:raise ValueError('Replay needs a prior run')
            replay_ids=set(old_summary['selected_ids']) if old_summary else None
            cached={r['sha']:json.loads(r['payload']) for r in store.db.execute('SELECT * FROM packets WHERE profile=?',(PROFILE,))}
            content_locks=defaultdict(threading.Lock);host_locks=defaultdict(lambda:threading.BoundedSemaphore(per_host))
            linked={r['doc_id']:r['fingerprint'] for r in store.db.execute('SELECT * FROM links')}
            reasons=Counter();candidates=[];reuse=[]
            for row in rows:
                if only_ids is not None and row['doc_id'] not in only_ids:continue
                if row['legacy_complete'] and store.resource(row['url']) is None:
                    with store.db:
                        store.db.execute('INSERT INTO resources VALUES(?,?,?,?,?,?,?,?)',(
                            row['url'],row['sha256'],row['etag'],row['modified'],
                            row['legacy_next_check'] or now(),'legacy_review_reused',now(),None))
                        store.db.execute('INSERT OR REPLACE INTO links VALUES(?,?,?,?)',(
                            row['doc_id'],row['project_id'],row['url'],row['fingerprint']))
                    linked[row['doc_id']]=row['fingerprint']
                if replay_ids is not None and row['doc_id'] not in replay_ids:continue
                old=store.resource(row['url']);changed=old and linked.get(row['doc_id']) != row['fingerprint']
                if old and old['next_check']>now() and (not changed or old['status']=='error'):
                    reason = 'error_retry_not_due' if old['status']=='error' else ('legacy_completed_reused' if row['legacy_complete'] and old['sha']==row['sha256'] else 'memory_reused')
                    reasons[reason]+=1
                    reuse.append(row['doc_id']);continue
                if row['bucket']=='rejected':reasons['excluded_project_retained']+=1;continue
                if row['priority']==3 and not include_deferred and not changed:
                    reasons['specialist_deferred']+=1;continue
                candidates.append({**row,'old':old})
            selected=fair_selection(candidates,limit)
            # Same URL is acquired once; project-specific links remain separate.
            grouped=defaultdict(list)
            for row in selected:grouped[row['url']].append(row)

            def worker(row):
                old=row['old'];url=row['url']
                try:
                    with tempfile.TemporaryDirectory(prefix='wind-commercial-') as temp:
                        path=Path(temp)/'source.pdf';local=None
                        if local_objects and row.get('sha256'):
                            possible=Path(local_objects)/(row['sha256']+'.pdf')
                            if possible.is_file():local=possible
                        if local:
                            with local.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
                            if sha!=row['sha256']:raise ValueError('Local input SHA mismatch')
                            result={'sha':sha,'bytes':0,'network_requests':0,'input_mode':'existing_temporary_file'};path=local
                        elif offline:
                            return {'status':'offline_source_missing','bytes':0,'network_requests':0,'text_extractions':0}
                        else:
                            from wind_document_audit import validate_url
                            with host_locks[urlsplit(url).hostname]:
                                result=fetcher(url,path,old,validate_url)
                            if result['status']!='downloaded':return result
                        sha=result['sha']
                        if row['legacy_complete'] and sha==row['sha256']:
                            return {**result,'status':'same_content_reused','text_extractions':0}
                        with content_locks[sha]:
                            if sha in cached:
                                return {**result,'status':'same_content_reused','text_extractions':0,'packet':cached[sha]}
                            packet=extract(path,cached.get((old or {}).get('sha')))
                            cached[sha]=packet
                        return {**result,'status':'targeted_extraction','text_extractions':1,'packet':packet}
                except Exception as exc:
                    return {'status':'error','error':str(exc)[:400],'bytes':0,'network_requests':int(not offline),'text_extractions':0}

            results=[]
            with ThreadPoolExecutor(max_workers=workers) as pool:
                tasks={pool.submit(worker,group[0]):group for group in grouped.values()}
                for future in as_completed(tasks):
                    group=tasks[future];result=future.result()
                    for row in group:store.save(row,result)
                    compact={k:v for k,v in result.items() if k!='packet'}
                    results.append({**compact,'doc_ids':[r['doc_id'] for r in group],'url':group[0]['url']})
            packets=[{'sha':r['sha'],**json.loads(r['payload'])} for r in store.db.execute('SELECT * FROM packets WHERE profile=?',(PROFILE,))]
            links=[dict(r) for r in store.db.execute('SELECT * FROM links')]
            summary={'profile':PROFILE,'generated_at':now(),'inventory_documents':len(rows),
                'priority_counts':dict(Counter(str(r['priority']) for r in rows)),
                'selection_outcomes':dict(reasons),'eligible_not_selected':max(0,len(candidates)-len(selected)),
                'selected_ids':[r['doc_id'] for r in selected] if not replay else sorted(replay_ids),
                'results':results,'resources_attempted':len(results),'text_extractions':sum(r['text_extractions'] for r in results),
                'network_requests':sum(r.get('network_requests',0) for r in results),
                'bytes_transferred':sum(r.get('bytes',0) for r in results),'elapsed_seconds':round(time.monotonic()-started,3),
                'stored_content_packets':len(packets),'native_pages_processed':sum(p['native_pages_processed'] for p in packets),
                'visual_or_scope_review_pages':sum(bool(p['review_flags']) for d in packets for p in d['pages']),
                'unprocessed_pages':sum(len(p['unprocessed_pages']) for p in packets),
                'unresolved_resource_errors':store.db.execute("SELECT COUNT(*) FROM resources WHERE status='error'").fetchone()[0],
                'new_verified_facts':0,'new_whole_document_completions':0,'canonical_writes':0,
                'sources_stored':0,'guard':'Targeted native-text extraction is not semantic validation or whole-dossier reading.'}
            body={'summary':summary,'links':links,'packets':packets,
                  'plan':[{'doc_id':r['doc_id'],'project_id':r['project_id'],'label':r['label'],
                           'priority':r['priority'],'reason':r['priority_reason'],'legacy_complete':bool(r['legacy_complete'])} for r in rows]}
            for name,value in [('summary.json',summary),('commercial-review.json',body)]:
                temp=output/(name+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,output/name)
            with store.db:store.db.execute('INSERT INTO runs(created_at,summary) VALUES(?,?)',(now(),packed(summary)))
            return summary
        finally:
            store.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ledger',required=True);p.add_argument('--output',required=True)
    p.add_argument('--limit',type=int,default=50);p.add_argument('--workers',type=int,default=4)
    p.add_argument('--per-host',type=int,default=2);p.add_argument('--include-deferred',action='store_true')
    p.add_argument('--no-remote',action='store_true');p.add_argument('--replay',action='store_true')
    p.add_argument('--local-objects');p.add_argument('--only-ids',nargs='*');a=p.parse_args()
    result=run(a.ledger,a.output,limit=a.limit,workers=a.workers,per_host=a.per_host,
        include_deferred=a.include_deferred,offline=a.no_remote,replay=a.replay,local_objects=a.local_objects,only_ids=set(a.only_ids) if a.only_ids is not None else None)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if any(r['status'] in {'error','offline_source_missing'} for r in result['results']):raise SystemExit(2)


if __name__=='__main__':main()
