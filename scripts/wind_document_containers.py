#!/usr/bin/env python3
"""D4: bounded ZIP/CMS opening with immutable parent-to-child provenance.

Opening a signed envelope is not a qualified-signature/legal validation. Files
are stored under hashes, never under archive paths. No embedded code executes.
"""
from __future__ import annotations
import hashlib
import json
import re
import shutil
import stat
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

from wind_document_inventory import D2, extract_file, file_hash, stamp


@dataclass(frozen=True)
class Limits:
    members: int = 200
    member_bytes: int = 128 * 1024**2
    total_bytes: int = 512 * 1024**2
    ratio: int = 200
    depth: int = 3
    seconds: int = 90


def safe_name(name):
    name = name.replace('\\', '/')
    return bool(name) and not (name.startswith('/') or ':' in name or '\x00' in name or
        any(p in {'', '.', '..'} for p in name.rstrip('/').split('/')) or
        any(ord(c) < 32 for c in name))


def kind_of(path, label=''):
    with Path(path).open('rb') as f:
        prefix = f.read(1024)
    if prefix.startswith((b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')):
        return 'zip'
    if b'%PDF-' in prefix:
        return 'pdf'
    # CMS signedData object identifier 1.2.840.113549.1.7.2, not mere .p7m name.
    if b'\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x02' in prefix[:40] or prefix.startswith(b'-----BEGIN CMS'):
        return 'cms'
    if re.search(r'\.p7[m,s](?:$|[?#])', label, re.I):
        return 'cms'
    return 'unsupported'


class Containers:
    def __init__(self, ledger, limits=None):
        self.ledger, self.db, self.root = ledger, ledger.db, ledger.root
        self.limits = limits or Limits()
        if min(self.limits.members,self.limits.member_bytes,self.limits.total_bytes,self.limits.ratio,self.limits.seconds) < 1 or self.limits.depth < 0:
            raise ValueError('Positive budgets required')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS container_attempts(
          id INTEGER PRIMARY KEY,doc_id TEXT,parent_sha TEXT,checked_at TEXT,result_json TEXT);
        CREATE TABLE IF NOT EXISTS visual_queue(doc_id TEXT,sha256 TEXT,page INTEGER,path TEXT,
          render_sha256 TEXT,status TEXT,detail TEXT,PRIMARY KEY(doc_id,sha256,page));
        CREATE TABLE IF NOT EXISTS container_runs(
          id TEXT PRIMARY KEY,doc_id TEXT,parent_sha TEXT,checked_at TEXT,status TEXT,detail TEXT,
          UNIQUE(doc_id,parent_sha));
        CREATE TABLE IF NOT EXISTS container_members(
          id TEXT PRIMARY KEY,run_id TEXT,parent_member TEXT,ordinal INTEGER,name TEXT,
          content_sha TEXT,kind TEXT,byte_count INTEGER,status TEXT,detail TEXT,
          extraction_json TEXT,chain_json TEXT);
        ''')
        self.db.commit()

    def _row(self, run, parent, ordinal, name, sha, kind, size, status, detail, extraction, chain):
        identity = json.dumps([run,parent,ordinal,name], ensure_ascii=False)
        mid = hashlib.sha256(identity.encode()).hexdigest()[:32]
        self.db.execute('INSERT OR REPLACE INTO container_members VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (mid,run,parent,ordinal,name,sha,kind,size,status,detail,json.dumps(extraction,ensure_ascii=False),json.dumps(chain,ensure_ascii=False)))
        self.db.commit()
        return mid

    def _budget(self, count=0):
        if time.monotonic()-self.started > self.limits.seconds:
            raise ValueError('time_budget')
        if self.used + count > self.limits.total_bytes:
            raise ValueError('expanded_size_budget')

    def _store(self, path):
        sha = file_hash(path)
        target = self.root / 'objects' / (sha + '.bin')
        if not target.exists(): shutil.copyfile(path,target)
        elif file_hash(target) != sha: raise ValueError('stored_object_corrupt')
        return sha

    def _cms(self, source, out):
        executable = shutil.which('openssl')
        if not executable: return 'dependency_missing', 'OpenSSL unavailable'
        with source.open('rb') as f: prefix = f.read(50)
        fmt = 'PEM' if prefix.startswith(b'-----BEGIN') else 'DER'
        # -noverify disables certificate-chain trust checks, NOT content signature checks.
        command = [executable,'cms','-verify','-binary','-inform',fmt,'-in',str(source),
                   '-noverify','-out',str(out)]
        with tempfile.TemporaryFile() as err:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=err)
            try:
                while process.poll() is None:
                    self._budget()
                    if out.exists() and out.stat().st_size > self.limits.member_bytes:
                        raise ValueError('cms_output_size_budget')
                    time.sleep(0.03)
                if process.returncode != 0:
                    err.seek(0)
                    return 'cms_verification_failed_or_detached',err.read(2048).decode(errors='replace')[-1000:]
                if not out.exists() or not out.stat().st_size:
                    return 'cms_no_embedded_content','No embedded bytes were returned'
                if out.stat().st_size > self.limits.member_bytes:
                    return 'deferred_size_limit','CMS output exceeds member limit'
                return 'content_signature_verified_trust_unchecked','Certificate trust, revocation and qualified-signature validity NOT checked'
            except Exception as exc:
                return 'deferred_budget',str(exc)
            finally:
                if process.poll() is None: process.kill(); process.wait()

    def _walk(self, source, run, parent, chain, depth):
        kind = kind_of(source)
        if depth > self.limits.depth:
            return 'deferred_depth_limit'
        self._budget()
        if kind == 'cms':
            with tempfile.TemporaryDirectory(dir=self.root) as tmp:
                output=Path(tmp)/'content'
                status,note=self._cms(source,output)
                if status != 'content_signature_verified_trust_unchecked':
                    self._row(run,parent,0,'CMS embedded content',None,'cms',0,status,note,{},chain)
                    return 'partial_or_blocked'
                provenance={'container':'cms','parent_sha256':file_hash(source),'signature_status':status,'certificate_trust_verified':False}
                return self._child(output,run,parent,0,'CMS embedded content',chain+[provenance],depth)
        if kind != 'zip': return 'unsupported_container'
        outcomes=[]
        try:
            with zipfile.ZipFile(source) as archive:
                entries=archive.infolist()
                if len(entries)>self.limits.members:
                    self._row(run,parent,0,'ZIP central directory',None,'zip',0,'deferred_member_count',f'{len(entries)} entries; limit {self.limits.members}',{},chain)
                    return 'partial_or_blocked'
                used_names=set()
                for index,info in enumerate(entries):
                    name=info.filename; normalized=name.replace('\\','/').casefold()
                    detail=None
                    if not safe_name(name): detail='unsafe_member_path'
                    elif normalized in used_names: detail='duplicate_member_path'
                    elif stat.S_ISLNK(info.external_attr >> 16): detail='symlink_refused'
                    elif info.flag_bits & 1: detail='encrypted_member'
                    elif info.file_size > self.limits.member_bytes: detail='deferred_member_size'
                    elif info.file_size > max(info.compress_size,1)*self.limits.ratio: detail='compression_ratio_limit'
                    used_names.add(normalized)
                    if detail:
                        self._row(run,parent,index,name,None,'unknown',info.file_size,detail,detail,{},chain);outcomes.append('blocked');continue
                    if info.is_dir(): continue
                    try:
                        self._budget(info.file_size)
                        with tempfile.TemporaryDirectory(dir=self.root) as tmp:
                            path=Path(tmp)/'member'; size=0
                            with archive.open(info) as src,path.open('wb') as dst:
                                while block:=src.read(128*1024):
                                    size+=len(block);self._budget(size)
                                    if size>self.limits.member_bytes: raise ValueError('actual_member_size_limit')
                                    dst.write(block)
                            if size != info.file_size: raise ValueError('zip_size_mismatch')
                            provenance={'container':'zip','parent_sha256':file_hash(source),'member_index':index,'member_name':name,'crc32':f'{info.CRC:08x}'}
                            outcomes.append(self._child(path,run,parent,index,name,chain+[provenance],depth))
                    except Exception as exc:
                        self._row(run,parent,index,name,None,'unknown',info.file_size,'member_failed',str(exc),{},chain);outcomes.append('blocked')
        except (zipfile.BadZipFile,ValueError,OSError) as exc:
            self._row(run,parent,0,'ZIP',None,'zip',0,'container_failed',str(exc),{},chain)
            return 'partial_or_blocked'
        return 'opened_pending_review' if all(x=='opened_pending_review' for x in outcomes) else 'partial_or_blocked'

    def _child(self,path,run,parent,index,name,chain,depth):
        size=path.stat().st_size;self._budget(size);self.used+=size
        if size>self.limits.member_bytes: raise ValueError('member_size_limit')
        sha=self._store(path);kind=kind_of(path,name)
        self.nodes+=1
        if self.nodes>self.limits.members:
            self._row(run,parent,index,name,sha,kind,size,'deferred_tree_member_limit','Nested member count limit',{},chain)
            return 'partial_or_blocked'
        extraction={};status='unsupported_retained'
        if kind=='pdf':
            target=self.root/'objects'/(sha+'.pdf')
            if not target.exists():shutil.copyfile(path,target)
            # D2 parser runs in a subprocess so an individual PDF cannot stall the queue indefinitely.
            with tempfile.TemporaryDirectory(dir=self.root) as tmp:
                result=Path(tmp)/'extraction.json'
                try:
                    import sys
                    cmd=[sys.executable,str(Path(__file__).resolve()),'--extract',str(target),'--result',str(result)]
                    subprocess.run(cmd,check=True,timeout=max(1,min(30,self.limits.seconds)),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    extraction=json.loads(result.read_text(encoding='utf-8'))
                    status=extraction.get('status','extraction_failed')
                except Exception as exc:status='extraction_failed';extraction={'error':str(exc),'pages':[]}
        elif kind in {'zip','cms'}:status='nested_container'
        mid=self._row(run,parent,index,name,sha,kind,size,status,'',extraction,chain)
        if kind=='pdf' and extraction.get('pages'):
            D2.render(self,mid,sha,self.root/'objects'/(sha+'.pdf'),extraction,1)
        if kind in {'zip','cms'}:
            nested=self._walk(path,run,mid,chain,depth+1)
            self.db.execute('UPDATE container_members SET status=? WHERE id=?',(nested,mid));self.db.commit();return nested
        return 'opened_pending_review' if kind=='pdf' and extraction.get('pages') else 'partial_or_blocked'

    def open(self,did,sha):
        self.started,self.used,self.nodes=time.monotonic(),0,0
        source=self.root/'objects'/(sha+'.bin')
        record=self.db.execute('SELECT 1 FROM versions WHERE doc_id=? AND sha256=?',(did,sha)).fetchone()
        if not record or not source.is_file() or file_hash(source)!=sha:raise ValueError('Original container version missing/corrupt')
        run=hashlib.sha256((did+'|'+sha).encode()).hexdigest()[:32]
        cached=self.db.execute('SELECT status FROM container_runs WHERE id=?',(run,)).fetchone()
        # Explicit retries allowed on blocked/partial runs; successful runs require every stored child to remain intact.
        children=self.db.execute('SELECT content_sha FROM container_members WHERE run_id=? AND content_sha IS NOT NULL',(run,)).fetchall()
        if cached and cached[0]=='opened_pending_review' and children and all((self.root/'objects'/(r[0]+'.bin')).is_file() and file_hash(self.root/'objects'/(r[0]+'.bin'))==r[0] for r in children):
            return {'status':'cached_container_verified','run_id':run}
        self.db.execute('INSERT OR REPLACE INTO container_runs VALUES(?,?,?,?,?,?)',(run,did,sha,stamp(),'in_progress',''));self.db.commit()
        self.db.execute('DELETE FROM container_members WHERE run_id=?',(run,));self.db.commit()
        try:status=self._walk(source,run,None,[],0);detail=''
        except Exception as exc:status='partial_or_blocked';detail=str(exc)
        self.db.execute('UPDATE container_runs SET status=?,detail=? WHERE id=?',(status,detail,run));self.db.commit()
        result={'status':status,'run_id':run,'expanded_bytes':self.used,'nodes':self.nodes,'detail':detail}
        snapshot={'result':result,'members':[dict(r) for r in self.db.execute('SELECT * FROM container_members WHERE run_id=?',(run,))]}
        self.db.execute('INSERT INTO container_attempts(doc_id,parent_sha,checked_at,result_json) VALUES(?,?,?,?)',(did,sha,stamp(),json.dumps(snapshot,ensure_ascii=False)));self.db.commit()
        return result

    def report(self):
        runs=[dict(r) for r in self.db.execute('SELECT * FROM container_runs ORDER BY checked_at,id')]
        members=[]
        for r in self.db.execute('SELECT * FROM container_members ORDER BY run_id,id'):
            row=dict(r);row['extraction']=json.loads(row.pop('extraction_json'));row['provenance_chain']=json.loads(row.pop('chain_json'));members.append(row)
        return {'container_runs':runs,'members':members,'legal_signature_validation':False,'complete_dossiers':0}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--extract',required=True);p.add_argument('--result',required=True);a=p.parse_args()
    Path(a.result).write_text(json.dumps(extract_file(a.extract),ensure_ascii=False),encoding='utf-8')
