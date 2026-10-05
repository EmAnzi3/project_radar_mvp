#!/usr/bin/env python3
"""Read once per reviewed version; persist lightweight memory, never PDF archives.

The portable database is authoritative. Runs work in a temporary directory,
validate a staged memory snapshot, then replace the database atomically. A
failed run cannot delete the last good memory or silently relabel partial work.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

REVIEW_FILES = ('wind_document_review_pilot.json', 'wind_document_memory_reviews.json',
                'wind_document_read_once_reviews.json')
COMPLETION_FILES = ('wind_document_completed_pilot.json', 'wind_document_read_once_completed.json')
ALLOWED_MEMORY_FILES = {'audit.sqlite', 'memory-report.json', 'review-report.json',
                        'review-report.html', 'D5-summary.json'}


def validate_locations(root, portable):
    root, portable = Path(root).resolve(), Path(portable).resolve()
    if root == portable or root.is_relative_to(portable) or portable.is_relative_to(root):
        raise ValueError('Working and memory directories must be separate, non-nested paths')
    if portable.exists() and (not portable.is_dir() or any(
            p.is_symlink() or not p.is_file() or p.name not in ALLOWED_MEMORY_FILES
            for p in portable.iterdir())):
        raise ValueError('Unexpected file in memory destination; nothing will be deleted')
    return root, portable


@contextmanager
def memory_lock(portable):
    """No concurrent writers. An abandoned lock requires explicit inspection."""
    portable = Path(portable)
    portable.parent.mkdir(parents=True, exist_ok=True)
    path = portable.parent / (portable.name + '.lock')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'memory': str(portable)}))
        yield
    finally:
        path.unlink(missing_ok=True)


def copy_database(source, destination):
    """Use SQLite backup so journal/WAL state is not lost by copying one file."""
    source = Path(source)
    with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)


def publish_memory(stage, portable):
    """Commit the authoritative DB first. Derived reports are regenerable."""
    stage, portable = Path(stage), Path(portable)
    if {p.name for p in stage.iterdir()} - ALLOWED_MEMORY_FILES:
        raise ValueError('Staged memory contains unexpected files')
    if any(not p.is_file() or p.is_symlink() for p in stage.iterdir()):
        raise ValueError('Staged memory must contain only regular lightweight files')
    with closing(sqlite3.connect((stage / 'audit.sqlite').resolve().as_uri() + '?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Staged database failed integrity check')
    portable.mkdir(parents=True, exist_ok=True)
    # Same-parent temporary directory ensures same filesystem for atomic replace.
    os.replace(stage / 'audit.sqlite', portable / 'audit.sqlite')
    for path in stage.iterdir():
        os.replace(path, portable / path.name)


def _load(repo, names, key):
    values = []
    for name in names:
        body = json.loads((repo / 'config' / name).read_text(encoding='utf-8'))
        values.extend(body[key])
    return values


def run(root, portable, *, repo=Path('.'), seed=True, remote=True):
    # Lazy imports also let storage-safety tests run without PDF dependencies.
    from wind_document_audit import Ledger, validate_url
    from wind_document_memory import Memory, MemoryD2, MemoryReviews, MemoryQueue, receipt_sources

    root, portable = validate_locations(root, portable)
    repo = Path(repo)
    root.mkdir(parents=True, exist_ok=True)
    with memory_lock(portable), tempfile.TemporaryDirectory(prefix='reading-', dir=root) as tmp:
        scratch = Path(tmp)
        # A stale old working directory must never overwrite newer portable memory.
        source = portable / 'audit.sqlite' if (portable / 'audit.sqlite').is_file() else root / 'audit.sqlite'
        if source.is_file():
            copy_database(source, scratch / 'audit.sqlite')
        ledger = Ledger(scratch)
        summary = {'source_reads': [], 'currentness_checks': [], 'complete_dossiers': 0,
                   'canonical_writes': 0, 'storage_policy': 'memory_only_temporary_sources'}
        store = None
        try:
            if seed:
                ledger.seed(repo)
                ledger.import_qualification(repo / 'config/wind_document_qualification_seed.json')
            memory, engine = Memory(ledger), MemoryD2(ledger, validate_url)
            queue, store = MemoryQueue(ledger), MemoryReviews(scratch)
            entries = _load(repo, REVIEW_FILES, 'reviews')
            plans = _load(repo, COMPLETION_FILES, 'documents')
            seen = set()

            def ensure_source(pid, url, sha):
                did = ledger.register(pid, url, 'Reviewed source', 'pdf')
                target = scratch / 'objects' / (sha + '.pdf')
                if target.is_file():
                    return did
                if did in seen:
                    raise ValueError('Acquired source does not match the reviewed version: ' + url)
                seen.add(did)
                # The old D1-D4 working file may be reused once; no new archive.
                old = root / 'objects' / (sha + '.pdf')
                if old.is_file():
                    import hashlib
                    with old.open('rb') as stream:
                        if hashlib.file_digest(stream, 'sha256').hexdigest() != sha:
                            raise ValueError('Migration original hash mismatch: ' + url)
                    staged_original = scratch / ('migration-' + sha + '.pdf')
                    shutil.copyfile(old, staged_original)
                    meta = ledger.db.execute('SELECT etag,modified FROM versions WHERE doc_id=? AND sha256=?', (did, sha)).fetchone()
                    result = engine.ingest_transfer(did, {'path': str(staged_original), 'sha256': sha,
                        'bytes': old.stat().st_size, 'final_url': url,
                        'etag': meta[0] if meta else '', 'modified': meta[1] if meta else ''}, render_limit=0)
                    summary['source_reads'].append({**result, 'status': 'migration_file_reused',
                                                    'bytes_transferred': 0})
                else:
                    if not remote:
                        raise ValueError('Offline run needs missing reviewed source: ' + url)
                    result = engine.acquire(did, render_limit=0)
                    summary['source_reads'].append(result)
                if not target.is_file():
                    raise ValueError('Source unavailable or version changed; pending review retained: ' + url)
                return did

            for entry in entries:
                if receipt_sources(store.db, entry) is None:
                    for ev in entry['evidence']:
                        ensure_source(entry['project_id'], ev['url'], ev['sha256'])
            store.import_batch({'schema_version': '1.0', 'reviews': entries})

            for plan in plans:
                if memory.completed(plan['doc_id'], plan['sha256']) is None:
                    doc = ledger.db.execute('SELECT url FROM documents WHERE id=?', (plan['doc_id'],)).fetchone()
                    if doc is None:
                        raise ValueError('Completion refers to unregistered source')
                    ensure_source(plan['project_id'], doc[0], plan['sha256'])
                memory.complete(plan)
                memory.release(plan['doc_id'], plan['sha256'])
            # Check every currently completed document, not only the hardcoded pilot.
            if remote:
                ids = ledger.db.execute('SELECT DISTINCT doc_id FROM document_read_memory').fetchall()
                for row in ids:
                    if memory.completed(row[0]):
                        summary['currentness_checks'].append(memory.check_remote(row[0]))
            queue.seed()
            before = queue.export()
            queue.seed()
            assert before['queue_counts'] == queue.export()['queue_counts'], 'Seed reset work'
            summary['review_count'] = store.export()['review_count']
            summary['registry_counts'] = dict(ledger.db.execute('SELECT bucket,COUNT(*) FROM projects GROUP BY bucket'))
            summary['qualification_records'] = ledger.db.execute('SELECT COUNT(*) FROM qualification').fetchone()[0]
            # Stage and validate everything before touching the previous good DB.
            with tempfile.TemporaryDirectory(prefix=portable.name + '-stage-', dir=portable.parent) as st:
                stage = Path(st)
                summary['snapshot'] = memory.snapshot(stage)
                staged_reviews = MemoryReviews(stage)
                try:
                    assert staged_reviews.import_batch({'schema_version': '1.0', 'reviews': entries}) == 0
                    report = staged_reviews.export()
                    assert report['review_count'] == summary['review_count']
                finally:
                    staged_reviews.close()
                restored = Ledger(stage)
                try:
                    mm = Memory(restored)
                    for plan in plans:
                        if mm.completed(plan['doc_id']):
                            result = MemoryD2(restored, validate_url).acquire(plan['doc_id'])
                            assert result['status'] == 'read_memory_reused' and result['bytes_transferred'] == 0
                    summary['completed_document_versions'] = mm.export()['completed_document_versions']
                    summary['persisted_queue_counts'] = dict(restored.db.execute('SELECT state,COUNT(*) FROM document_work GROUP BY state'))
                    summary['queue_counts'] = summary['persisted_queue_counts']
                finally:
                    restored.db.close()
                (stage / 'objects').rmdir()
                summary['binary_files_exported'] = 0
                (stage / 'D5-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
                publish_memory(stage, portable)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return summary
        finally:
            if store is not None:
                store.close()
            ledger.db.close()
        # TemporaryDirectory removes originals/renders even after a failed run.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--memory', required=True)
    parser.add_argument('--repo', default='.')
    parser.add_argument('--no-seed', action='store_true')
    parser.add_argument('--no-remote', action='store_true')
    args = parser.parse_args()
    run(args.output, args.memory, repo=Path(args.repo), seed=not args.no_seed, remote=not args.no_remote)


if __name__ == '__main__':
    main()
