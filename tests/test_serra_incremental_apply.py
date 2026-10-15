import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from apply_serra_review import apply
ROOT=Path(__file__).resolve().parents[1]
class IncrementalApplyTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
  (self.root/'config').mkdir();(self.root/'docs/wind/data').mkdir(parents=True)
  self.r=json.loads((ROOT/'config/wind_serra_review.json').read_text())
  current=json.loads((ROOT/'docs/wind/data/projects-1.json').read_text())
  self.p=next(x for x in current if x['id']=='serra-giannina')
  self.old={'reviewed_on':'previous','marker':'source-backed-baseline'}
  self.p['documentary']=self.old
  self.r['previous_documentary_sha256']=hashlib.sha256(json.dumps(self.old,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  self.other={'id':'other-project','mw':13,'documentary':{'unchanged':True}}
  self.config=self.root/'config/wind_serra_review.json';self.data=self.root/'docs/wind/data/projects-1.json'
 def write(self):
  self.config.write_text(json.dumps(self.r));self.data.write_text(json.dumps([self.p,self.other]))
 def test_incremental_apply_and_idempotence(self):
  self.write();apply(self.root);after=json.loads(self.data.read_text())
  self.assertEqual(after[1],self.other);self.assertEqual(after[0]['documentary'],self.r['documentary'])
  raw=self.data.read_bytes();self.assertTrue(apply(self.root)['reused_without_writes']);self.assertEqual(raw,self.data.read_bytes())
 def test_reject_newer_review_without_writes(self):
  self.p['documentary']['reviewed_on']='newer';self.write();raw=self.data.read_bytes()
  with self.assertRaises(ValueError):apply(self.root)
  self.assertEqual(raw,self.data.read_bytes())
 def test_reject_source_replacement_without_writes(self):
  self.p['sources'][0]['id']=self.r['sources_added'][0]['id'];self.p['sources'][0]['url']='https://invalid.test'
  self.write();raw=self.data.read_bytes()
  with self.assertRaises(ValueError):apply(self.root)
  self.assertEqual(raw,self.data.read_bytes())
if __name__=='__main__':unittest.main()
