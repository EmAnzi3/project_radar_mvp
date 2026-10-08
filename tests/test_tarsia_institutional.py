"""Integrity tests for the Tarsia institutional-document update."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TarsiaInstitutional(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = json.loads((ROOT / 'docs/wind/data/projects-2.json').read_text(encoding='utf-8'))
        cls.p = next(x for x in rows if x['id'] == 'tarsia-ovest')
        cls.review = json.loads((ROOT / 'config/wind_tarsia_review.json').read_text(encoding='utf-8'))

    def test_generator_source_matches_materialized_record(self):
        self.assertEqual(self.p['documentary'], self.review['documentary'])

    def test_current_configuration_kept_separate_from_historical(self):
        self.assertEqual((self.p['wtg'], self.p['mw']), (3, 12.9))
        old = next(x for x in self.p['configs'] if x['source_id'] == 'tars-reg-old')
        self.assertIn('soltanto T1, T5 e T6', old['note'])

    def test_official_source_links_are_bound_to_tarsia(self):
        links = {s['id']: s['url'] for s in self.p['sources']}
        for key in ('tars-reg-old', 'tars-reg-voltura-2025', 'tars-reg-variante-2026',
                    'tars-reg-sia-2020', 'tars-reg-elec-2020'):
            self.assertTrue(links[key].startswith('https://www.regione.calabria.it/'))

    def test_company_vat_verified_or_explicitly_unresolved(self):
        companies = {x['company']: x for x in self.p['documentary']['company_registry']}
        self.assertEqual(companies['Eni Plenitude Renewables Italy S.p.A.']['vat_id'], '09722790962')
        self.assertEqual(companies['PLT Engineering S.r.l.']['vat_id'], '05857900723')
        self.assertEqual(companies['PLC System S.r.l.']['vat_id'], '03242081218')
        self.assertEqual(companies['Idoka Costruzioni S.r.l.']['vat_id'], '01903670766')
        self.assertIsNone(companies['Delta S.r.l.']['vat_id'])
        self.assertIsNone(companies['Michelangelo Mammana S.r.l. (denominazione PLC)']['vat_id'])
        for x in companies.values():
            if x['vat_id'] is not None:
                self.assertRegex(x['vat_id'], r'^\d{11}$')

    def test_unresolved_suap_documentation_never_closed(self):
        self.assertFalse(self.p['documentary']['whole_dossier_complete'])
        self.assertEqual(self.p['documentary']['paid_model_calls'], 0)
        suap = next(x for x in self.p['documentary']['dossier_coverage'] if 'SUAP' in x['group'])
        self.assertEqual(suap['status'], 'allegati_non_acquisiti')

    def test_all_source_ids_exist(self):
        ids = {s['id'] for s in self.p['sources']}
        d = self.p['documentary']
        for row in d['fields'] + d['contacts'] + d['company_registry'] + d['dossier_coverage']:
            self.assertTrue(set(row.get('source_ids', [])) <= ids)

if __name__ == '__main__':
    unittest.main()
