"""Storage guards for read-once memory: no loss, no implicit network/archives."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from wind_document_lifecycle import validate_locations, memory_lock, copy_database, publish_memory


class LifecycleStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.memory = self.base / 'memory'
        self.stage = self.base / 'stage'
        self.work = self.base / 'work'

    def db(self, parent, value):
        parent.mkdir(exist_ok=True)
        with sqlite3.connect(parent/'audit.sqlite') as db:
            db.execute('CREATE TABLE marker(value)')
            db.execute('INSERT INTO marker VALUES(?)', (value,))

    def value(self, parent):
        with sqlite3.connect(parent/'audit.sqlite') as db:
            return db.execute('SELECT value FROM marker').fetchone()[0]

    def test_distinct_sibling_paths(self):
        self.assertEqual(validate_locations(self.work, self.memory), (self.work, self.memory))

    def test_same_directory_rejected(self):
        with self.assertRaises(ValueError): validate_locations(self.memory, self.memory)

    def test_nested_memory_rejected(self):
        with self.assertRaises(ValueError): validate_locations(self.work, self.work/'memory')

    def test_nested_work_rejected(self):
        with self.assertRaises(ValueError): validate_locations(self.memory/'work', self.memory)

    def test_unexpected_user_file_not_removed(self):
        self.memory.mkdir(); p=self.memory/'user-notes.txt';p.write_text('keep')
        with self.assertRaises(ValueError): validate_locations(self.work,self.memory)
        self.assertEqual(p.read_text(),'keep')

    def test_lock_blocks_concurrent_writer(self):
        with memory_lock(self.memory):
            with self.assertRaises(FileExistsError):
                with memory_lock(self.memory): pass
        self.assertFalse((self.base/'memory.lock').exists())

    def test_exception_releases_own_lock(self):
        with self.assertRaises(RuntimeError):
            with memory_lock(self.memory): raise RuntimeError('test')
        self.assertFalse((self.base/'memory.lock').exists())

    def test_abandoned_lock_not_silently_removed(self):
        p=self.base/'memory.lock';p.write_text('another owner')
        with self.assertRaises(FileExistsError):
            with memory_lock(self.memory): pass
        self.assertEqual(p.read_text(),'another owner')

    def test_sqlite_backup_preserves_committed_wal(self):
        self.memory.mkdir(); db=sqlite3.connect(self.memory/'audit.sqlite')
        try:
            db.execute('PRAGMA journal_mode=WAL');db.execute('CREATE TABLE marker(value)')
            db.execute('INSERT INTO marker VALUES(7)');db.commit()
            self.stage.mkdir();copy_database(self.memory/'audit.sqlite',self.stage/'audit.sqlite')
            self.assertEqual(self.value(self.stage),7)
        finally: db.close()

    def test_atomic_publish_and_reports(self):
        self.db(self.memory,1);self.db(self.stage,2)
        (self.stage/'D5-summary.json').write_text(json.dumps({'complete_dossiers':0}))
        publish_memory(self.stage,self.memory)
        self.assertEqual(self.value(self.memory),2)
        self.assertTrue((self.memory/'D5-summary.json').is_file())

    def test_failed_commit_preserves_previous_database(self):
        self.db(self.memory,1);self.db(self.stage,2)
        with patch('wind_document_lifecycle.os.replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):publish_memory(self.stage,self.memory)
        self.assertEqual(self.value(self.memory),1)
        self.assertEqual(self.value(self.stage),2)

    def test_corrupt_stage_never_replaces_good_memory(self):
        self.db(self.memory,1);self.stage.mkdir();(self.stage/'audit.sqlite').write_bytes(b'corrupt')
        with self.assertRaises(sqlite3.DatabaseError):publish_memory(self.stage,self.memory)
        self.assertEqual(self.value(self.memory),1)

    def test_stage_with_pdf_rejected(self):
        self.db(self.memory,1);self.db(self.stage,2);(self.stage/'source.pdf').write_bytes(b'%PDF')
        with self.assertRaises(ValueError):publish_memory(self.stage,self.memory)
        self.assertEqual(self.value(self.memory),1)

    def test_stage_with_directory_rejected(self):
        self.db(self.memory,1);self.db(self.stage,2);(self.stage/'objects').mkdir()
        with self.assertRaises(ValueError):publish_memory(self.stage,self.memory)
        self.assertEqual(self.value(self.memory),1)

    def test_missing_source_not_created_as_empty_database(self):
        with self.assertRaises(sqlite3.OperationalError):
            copy_database(self.base/'missing.sqlite',self.base/'target.sqlite')
        self.assertFalse((self.base/'missing.sqlite').exists())


if __name__ == '__main__': unittest.main()
