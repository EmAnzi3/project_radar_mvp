import json,unittest,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TarsiaEnrichment(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  m=json.loads((ROOT/'docs/wind/data/projects.json').read_text(encoding='utf-8'))
  cls.projects=[p for f in m['chunks'] for p in json.loads((ROOT/'docs/wind/data'/f).read_text(encoding='utf-8'))]
  cls.p=next(p for p in cls.projects if p['id']=='tarsia-ovest');cls.d=cls.p['documentary']
 def test_counts_power(self):
  self.assertEqual(len(self.projects),51);self.assertAlmostEqual(sum(p['mw'] for p in self.projects),11202.52,2)
 def test_only_target_has_panel(self):self.assertEqual([p['id'] for p in self.projects if p.get('documentary')],['tarsia-ovest'])
 def test_eight_requested_areas(self):
  self.assertEqual(len(self.d['fields']),6);self.assertTrue(self.d['contacts']);self.assertTrue(self.d['gaps'])
 def test_power_preserved(self):self.assertEqual(self.p['mw'],12.9);self.assertEqual(self.p['wtg'],3)
 def test_not_total_completion(self):self.assertFalse(self.d['whole_dossier_complete']);self.assertEqual(self.d['paid_model_calls'],0)
 def test_contacts_roles(self):
  c=self.d['contacts'];self.assertEqual(len(c),4)
  self.assertEqual(c[0]['email'],'commerciale.system@plc-spa.com');self.assertIsNone(c[0]['phone'])
  self.assertEqual(c[1]['company'],'PLC S.p.A.');self.assertIn('Centralino',c[1]['role'])
  self.assertIn('non commerciale',c[3]['role'])
 def test_no_unqualified_names_or_wrong_entity_contacts(self):
  raw=json.dumps(self.d,ensure_ascii=False)
  for invalid in ('Stefano Rossi','2222999','stefano.rossi@','info@gruppomammana','info@mammanamichelangelo'):
   self.assertNotIn(invalid,raw)
  self.assertIn('Delta S.r.l.',[r['company'] for r in self.p['relations']])
  self.assertNotIn('Delta Costruzioni',[r['company'] for r in self.p['relations']])
 def test_source_references(self):
  ids={s['id'] for s in self.p['sources']}
  for r in self.d['fields']+self.d['contacts']:
   self.assertTrue(r['source_ids']);self.assertTrue(set(r['source_ids'])<=ids)
 def test_no_fake_byte_provenance(self):
  ev=self.d['evidence'];self.assertEqual(ev[0]['page'],1);self.assertRegex(ev[0]['sha256'],r'^[0-9a-f]{64}$')
  for x in ev[1:]:self.assertEqual(x['capture'],'web_reader_fallback');self.assertIsNone(x['sha256'])
 def test_render_dependency_order(self):
  html=(ROOT/'docs/wind/index.html').read_text(encoding='utf-8')
  self.assertLess(html.index('assets/documentary-summary.js'),html.index('assets/app.js'))
 def test_renderer_empty_for_other_projects_and_escapes(self):
  js=ROOT/'docs/wind/assets/documentary-summary.js'
  code="global.window={};require("+json.dumps(str(js))+");const r=window.WindDocumentary.render; if(r({id:'other'})!=='')throw Error('Other project changed'); const x=r({id:'x',sources:[],documentary:{reviewed_on:'today',method:'<script>bad</script>',fields:[],contacts:[],gaps:[]}});if(x.includes('<script>'))throw Error('XSS');"
  subprocess.run(['node','-e',code],check=True,capture_output=True)
if __name__=='__main__':unittest.main()
