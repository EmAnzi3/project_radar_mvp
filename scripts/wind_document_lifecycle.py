#!/usr/bin/env python3
"""D5 integration: migrate once, retain lightweight memory, no recurrent PDF pilot.

Cold/migration runs acquire only sources needed to validate existing reviews.
Warm runs use receipts and completed-reading memory. No binary is exported.
"""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from wind_document_audit import Ledger, validate_url
from wind_document_memory import Memory, MemoryD2, MemoryReviews, MemoryQueue, receipt_sources


def run(root, portable, *, repo=Path('.'), seed=True, remote=True):
    root,portable,repo=Path(root),Path(portable),Path(repo)
    root.mkdir(parents=True,exist_ok=True)
    if not (root/'audit.sqlite').exists() and (portable/'audit.sqlite').exists():
        shutil.copyfile(portable/'audit.sqlite',root/'audit.sqlite')
    ledger=Ledger(root);summary={'source_reads':[], 'currentness_checks':[], 'complete_dossiers':0, 'canonical_writes':0}
    try:
        if seed:
            ledger.seed(repo);ledger.import_qualification(repo/'config/wind_document_qualification_seed.json')
        memory=Memory(ledger);engine=MemoryD2(ledger,validate_url);queue=MemoryQueue(ledger)
        store=MemoryReviews(root)
        try:
            # Sources of reviewed facts must be verified once before issuing receipts.
            # We do NOT mark the remaining pages as read just because a claim exists.
            for file in ['wind_document_review_pilot.json','wind_document_memory_reviews.json']:
                batch=json.loads((repo/'config'/file).read_text(encoding='utf-8'))
                for entry in batch['reviews']:
                    if receipt_sources(store.db,entry) is not None:continue
                    for evidence in entry['evidence']:
                        did=ledger.register(entry['project_id'],evidence['url'],'Reviewed source','pdf')
                        original=root/'objects'/(evidence['sha256']+'.pdf')
                        if not original.is_file():
                            summary['source_reads'].append(engine.acquire(did,render_limit=0))
                store.import_batch(batch)
            first=store.export()
            completed=json.loads((repo/'config/wind_document_completed_pilot.json').read_text(encoding='utf-8'))
            for plan in completed['documents']:
                memory.complete(plan);memory.release(plan['doc_id'],plan['sha256'])
                if memory.completed(plan['doc_id']):
                    reuse=engine.acquire(plan['doc_id'],render_limit=0)
                    assert reuse['status']=='read_memory_reused' and reuse['text_extractions']==0
                if remote and memory.completed(plan['doc_id']):
                    summary['currentness_checks'].append(memory.check_remote(plan['doc_id']))
            queue.seed()
            before=queue.export();queue.seed();after=queue.export()
            assert before['queue_counts']==after['queue_counts']
            summary['review_count']=store.export()['review_count']
            summary['queue_counts']=after['queue_counts']
            summary['registry_counts']=dict(ledger.db.execute('SELECT bucket,COUNT(*) FROM projects GROUP BY bucket'))
            summary['qualification_records']=ledger.db.execute('SELECT COUNT(*) FROM qualification').fetchone()[0]
            # Snapshot is rebuilt only in its own dedicated output directory.
            if portable.exists():
                allowed={'audit.sqlite','memory-report.json','review-report.json','review-report.html','D5-summary.json'}
                assert all(p.is_file() and p.name in allowed for p in portable.iterdir()), 'Unexpected content in memory output; not removing it'
                for p in portable.iterdir():p.unlink()
            summary['snapshot']=memory.snapshot(portable)
            remembered=MemoryReviews(portable)
            try:
                for file in ['wind_document_review_pilot.json','wind_document_memory_reviews.json']:
                    assert remembered.import_batch(json.loads((repo/'config'/file).read_text(encoding='utf-8')))==0
                report=remembered.export()
                assert report['review_count']==first['review_count']
                assert report['complete_dossiers']==0
            finally:remembered.close()
            # Original-free snapshot must also support the next reading decision.
            warm=Ledger(portable)
            try:
                for plan in completed['documents']:
                    if Memory(warm).completed(plan['doc_id']):
                        reused=MemoryD2(warm,validate_url).acquire(plan['doc_id'])
                        assert reused['status']=='read_memory_reused' and reused['bytes_transferred']==0
                summary['completed_document_versions']=Memory(warm).export()['completed_document_versions']
                summary['persisted_queue_counts']=dict(warm.db.execute('SELECT state,COUNT(*) FROM document_work GROUP BY state'))
            finally:warm.db.close()
            (portable/'objects').rmdir()  # empty directory created by Ledger, never an archive
            summary['binary_files_exported']=sum(1 for p in portable.rglob('*') if p.is_file() and p.suffix.lower() in {'.pdf','.bin','.png','.zip','.p7m'})
            assert summary['binary_files_exported']==0
            (portable/'D5-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(summary,ensure_ascii=False,indent=2))
            return summary
        finally:store.close()
    finally:ledger.db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--memory',required=True)
    p.add_argument('--repo',default='.');p.add_argument('--no-seed',action='store_true');p.add_argument('--no-remote',action='store_true')
    a=p.parse_args();run(a.output,a.memory,repo=Path(a.repo),seed=not a.no_seed,remote=not a.no_remote)


if __name__=='__main__':main()
