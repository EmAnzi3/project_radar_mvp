"""Regressions for source-backed Serra Giannina enrichment only."""
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SerraReviewTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=json.loads((ROOT/'config/wind_serra_review.json').read_text(encoding='utf-8'))
  m=json.loads((ROOT/'docs/wind/data/projects.json').read_text(encoding='utf-8'))
  cls.projects=[p for f in m['chunks'] for p in json.loads((ROOT/'docs/wind/data'/f).read_text(encoding='utf-8'))]
  cls.p=next(x for x in cls.projects if x['id']=='serra-giannina')
  cls.d=cls.p['documentary']
 def test_canonical_count_preserved(self):
  self.assertEqual(len(self.projects),51)
  self.assertAlmostEqual(sum(p['mw'] for p in self.projects),11202.52,places=2)
  self.assertEqual((self.p['mw'],self.p['wtg'],self.p['stage']),(42,6,'E7'))
 def test_tarsia_unmodified_and_two_panels_only(self):
  self.assertEqual([p['id'] for p in self.projects if p.get('documentary')],['serra-giannina','tarsia-ovest'])
 def test_source_of_truth_persisted(self):
  self.assertEqual(self.d,self.r['documentary'])
  self.assertFalse(self.d['whole_dossier_complete'])
  self.assertEqual(self.d['paid_model_calls'],0)
 def test_no_execution_awards_invented(self):
  self.assertIn('Civil BoP',self.p['gaps'])
  confirmed=[x for x in self.p['relations'] if x['status']=='confirmed']
  self.assertEqual(len(confirmed),1)
  self.assertEqual(confirmed[0]['company'],'EGM Project')
  self.assertIn('Progettista',confirmed[0]['role'])
  self.assertFalse(any(x['role'] in ('epc','bop_civil','bop_electrical') for x in confirmed))
 def test_vat_and_contacts_exact(self):
  a={x['company']:x for x in self.d['company_registry']}
  self.assertEqual(a['RWE Renewables Italia S.r.l.']['vat_id'],'06400370968')
  self.assertEqual(a['EGM Project S.r.l.']['vat_id'],'02094310766')
  em=self.d['contacts'][0]
  self.assertEqual(em['email'],'info@egmproject.it')
  self.assertEqual(em['phone'],'+39 0971 1790116')
  self.assertNotIn('procurement',em['role'].lower())
 def test_source_pages_and_sha(self):
  ids={x['id'] for x in self.p['sources']}
  self.assertEqual(len(ids),len(self.p['sources']))
  for x in self.d['evidence']:
   self.assertIn(x['source_id'],ids)
   self.assertGreater(x['page'],0)
   self.assertRegex(x['sha256'],r'^[0-9a-f]{64}$')
  for x in self.d['fields']+self.d['contacts']+self.d['company_registry']+self.d['dossier_coverage']:
   self.assertTrue(set(x.get('source_ids',[]))<=ids)
 def test_inventoried_not_read(self):
  cov={x['group']:x for x in self.d['dossier_coverage']}
  self.assertEqual(len(cov),4)
  metrics=self.d['document_metrics']
  self.assertEqual(metrics['indexed_references'],279)
  self.assertEqual(metrics['acquired_references'],32)
  self.assertEqual(metrics['acquired_unique_sha256'],30)
  self.assertEqual(metrics['targeted_analyzed_unique_sha256'],30)
  self.assertEqual(metrics['pending_acquisition_references'],247)
  self.assertIn('3_allegati_censiti_non_acquisiti',cov['MASE – procedura 15213 (indice 19356)']['status'])
 def test_commercial_contacts_pinned_to_pages(self):
  contact=next(x for x in self.d['contacts'] if x['email']=='antonia.raino@rwe.com')
  self.assertEqual(contact['phone'],'+39 349 9341765')
  self.assertEqual(contact['page_refs'],[{'source_id':'sg-mase-arpab-aug','page':14}])
  for item in self.d['fields']+self.d['contacts']+self.d['company_registry']:
   for ref in item.get('page_refs',[]):
    self.assertIn(ref['source_id'],item['source_ids'])
    self.assertGreater(ref['page'],0)
 def test_successive_lots_and_persistent_memory(self):
  load=lambda p:json.loads((ROOT/p).read_text())
  a=load('config/wind_serra_mase_priority.json')
  b=load('config/serra_secondo_lotto_config.json')
  c=load('config/serra_terzo_lotto_config.json')
  urls=lambda x:{s['url'] for s in x['sources']}
  self.assertEqual((len(urls(a)),len(urls(b)),len(urls(c))),(8,24,24))
  self.assertFalse(urls(a)&urls(b) or urls(c)&(urls(a)|urls(b)))
  inv=load('docs_admin/wind-research/serra-inventory.json')
  indexed={r['url'] for p in inv['procedures'] for r in p['rows']}
  self.assertEqual(len(indexed),279)
  self.assertTrue((urls(a)|urls(b)|urls(c))<=indexed)
  ledger=load('docs_admin/wind-research/serra-acquisition-ledger.json')
  memory=load('docs_admin/wind-research/serra-document-memory.json')
  self.assertEqual(len(ledger['resources']),32)
  self.assertEqual(len(memory['documents']),30)
  self.assertEqual({r['sha256'] for r in ledger['resources'].values()},set(memory['documents']))
  for sha,review in memory['documents'].items():
   self.assertEqual(review['sha256'],sha)
   self.assertEqual(review['analysis_status'],'targeted_reviewed')
 def test_schedule_is_relative(self):
  sched=next(x for x in self.d['fields'] if x['label']=='Cronoprogramma')
  self.assertIn('senza data iniziale',sched['value'])
  self.assertNotIn('COD documentato',sched['value'])
if __name__=='__main__':unittest.main()
