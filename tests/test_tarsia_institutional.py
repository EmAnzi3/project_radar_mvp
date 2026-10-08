"""Tarsia regional source and P.IVA integrity regressions."""
import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TarsiaInstitutional(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  rows=json.loads((ROOT/'docs/wind/data/projects-2.json').read_text(encoding='utf-8'))
  cls.p=next(x for x in rows if x['id']=='tarsia-ovest')
  cls.review=json.loads((ROOT/'config/wind_tarsia_review.json').read_text(encoding='utf-8'))
 def test_source_generator_coherence(self):
  self.assertEqual(self.p['documentary'],self.review['documentary'])
 def test_identity_and_power_not_falsified(self):
  self.assertEqual((self.p['wtg'],self.p['mw']),(3,12.9))
  self.assertIn('soltanto T1, T5 e T6',next(x for x in self.p['configs'] if x['source_id']=='tars-reg-old')['note'])
 def test_official_sources_accessible_as_references(self):
  urls={s['id']:s['url'] for s in self.p['sources']}
  for i in ('tars-reg-old','tars-reg-voltura-2025','tars-reg-variante-2026','tars-reg-sia-2020','tars-reg-elec-2020'):
   self.assertTrue(urls[i].startswith('https://www.regione.calabria.it/'))
 def test_vat_numbers_are_limited_to_verified_roles(self):
  companies={r['company']:r for r in self.p['documentary']['company_registry']}
  self.assertEqual(companies['Eni Plenitude Renewables Italy S.p.A.']['vat_id'],'09722790962')
  self.assertEqual(companies['PLC System S.r.l.']['vat_id'],'03242081218')
  self.assertEqual(companies['Idoka Costruzioni S.r.l.']['vat_id'],'01903670766')
  self.assertEqual(companies['PLT Engineering S.r.l.']['vat_id'],'05857900723')
  self.assertIsNone(companies['Delta S.r.l.']['vat_id'])
  self.assertIsNone(companies['Michelangelo Mammana S.r.l. (denominazione PLC)']['vat_id'])
  for v in companies.values():
   if v['vat_id']:self.assertRegex(v['vat_id'],r'^\d{11})
 def test_unfinished_census_explicit(self):
  self.assertFalse(self.p['documentary']['whole_dossier_complete'])
  self.assertEqual(self.p['documentary']['paid_model_calls'],0)
  missing=next(x for x in self.p['documentary']['dossier_coverage'] if 'SUAP' in x['group'])
  self.assertEqual(missing['status'],'allegati_non_acquisiti')
 def test_anchored_fields_and_company_links(self):
  ids={s['id'] for s in self.p['sources']}
  for row in self.p['documentary']['fields']+self.p['documentary']['contacts']+self.p['documentary']['company_registry']+self.p['documentary']['dossier_coverage']:
   self.assertTrue(set(row.get('source_ids',[])) <= ids)
if __name__ == '__main__':unittest.main()
)
 def test_unfinished_census_explicit(self):
  self.assertFalse(self.p['documentary']['whole_dossier_complete'])
  self.assertEqual(self.p['documentary']['paid_model_calls'],0)
  missing=next(x for x in self.p['documentary']['dossier_coverage'] if 'SUAP' in x['group'])
  self.assertEqual(missing['status'],'allegati_non_acquisiti')
 def test_anchored_fields_and_company_links(self):
  ids={s['id'] for s in self.p['sources']}
  for row in self.p['documentary']['fields']+self.p['documentary']['contacts']+self.p['documentary']['company_registry']+self.p['documentary']['dossier_coverage']:
   self.assertTrue(set(row.get('source_ids',[])) <= ids)
if __name__ == '__main__':unittest.main()
