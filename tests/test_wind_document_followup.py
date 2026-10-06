"""D7 guards for manually reviewed, version-pinned documents.

These tests check evidence contracts, not semantic truth. The live lifecycle
still validates original hashes, page anchors, receipts and offline restart.
"""
import json
import re
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {'identity', 'power', 'location', 'companies', 'contacts', 'schedule'}
LEGACY_REFS = {'grecale-startup-gantt', 'grecale-commissioning-gantt'}


class FollowupBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = json.loads((ROOT / 'config/wind_document_followup_batch.json').read_text(encoding='utf-8'))
        cls.reviews = cls.batch['reviews']
        cls.index = {r['id']: r for r in cls.reviews}
        cls.plans = cls.batch['documents']

    def test_versioned_nonduplicated_batch(self):
        self.assertEqual(self.batch['schema_version'], '1.0')
        self.assertEqual(self.batch['checkpoint'], 'D7')
        self.assertEqual(len(self.reviews), 20)
        self.assertEqual(len(self.index), len(self.reviews))

    def test_four_distinct_completed_versions(self):
        self.assertEqual(len({(p['doc_id'], p['sha256']) for p in self.plans}), 4)
        self.assertEqual(len({p['project_id'] for p in self.plans}), 4)

    def test_all_twenty_two_pages_explicitly_reviewed(self):
        self.assertEqual(sorted(len(p['pages']) for p in self.plans), [2, 3, 5, 12])
        self.assertEqual(sum(len(p['pages']) for p in self.plans), 22)
        for plan in self.plans:
            pages = plan['pages']
            self.assertEqual([p['page'] for p in pages], list(range(1, len(pages) + 1)))
            for page in pages:
                self.assertEqual(page['mode'], 'text_and_visual')
                self.assertGreaterEqual(len(page['note']), 15)

    def test_all_six_outcomes_and_existing_evidence_references(self):
        for plan in self.plans:
            self.assertEqual(set(plan['outcomes']), FIELDS)
            for outcome in plan['outcomes'].values():
                self.assertIn(outcome['status'], {'recorded', 'not_found_in_document', 'not_applicable', 'conflict_recorded'})
                self.assertGreaterEqual(len(outcome['note']), 10)
                if outcome['status'] in {'recorded', 'conflict_recorded'}:
                    self.assertTrue(outcome.get('review_ids'))
                for rid in outcome.get('review_ids', []):
                    self.assertIn(rid, set(self.index) | LEGACY_REFS)
                    if rid in self.index:
                        self.assertEqual(self.index[rid]['project_id'], plan['project_id'])

    def test_every_source_is_bound_to_its_completed_document(self):
        plans = {p['project_id']: p for p in self.plans}
        for review in self.reviews:
            plan = plans[review['project_id']]
            self.assertTrue(review['evidence'])
            for ev in review['evidence']:
                self.assertRegex(ev['sha256'], r'^[a-f0-9]{64}$')
                self.assertEqual(ev['sha256'], plan['sha256'])
                self.assertTrue(ev['url'].startswith('https://'))
                self.assertTrue(1 <= ev['page'] <= len(plan['pages']))
                self.assertGreaterEqual(len(re.sub(r'\s+', ' ', ev['anchor']).strip()), 8)
                self.assertEqual(ev['reading_mode'], 'text_and_visual')
                self.assertTrue(ev['visual_note'])

    def test_no_execution_awards_from_engineering_or_grid_roles(self):
        roles = {'epc', 'bop_civil', 'bop_electrical', 'foundation_contractor', 'installation_contractor'}
        for review in self.reviews:
            if review['kind'] == 'company_role':
                self.assertNotIn(review['value']['role'], roles)
                self.assertNotEqual(review['value']['relationship'], 'explicit_execution_award')
        self.assertEqual(self.index['tre-d7-enel-grid-scope']['scope'], 'shared_works')
        self.assertEqual(self.index['mercatello-d7-designer']['value']['role'], 'designer')

    def test_only_explicit_corporate_contact_not_procurement(self):
        contacts = [r for r in self.reviews if r['kind'] == 'contact']
        self.assertEqual(len(contacts), 1)
        value = contacts[0]['value']
        self.assertEqual(value['endpoint_scope'], 'corporate')
        self.assertEqual(value['email'], 'rinaconsulting@rina.org')
        self.assertEqual(value['role'], 'corporate_general_contact')

    def test_visible_signatures_are_document_metadata_not_contacts(self):
        signatures = [r for r in self.reviews if r['value'].get('field') == 'document_signature']
        self.assertEqual(len(signatures), 3)
        for row in signatures:
            self.assertEqual(row['kind'], 'attribute')
            self.assertEqual(row['value']['transcription_mode'], 'visual')
            self.assertFalse(row['value']['commercial_contact'])
            self.assertTrue(row['value']['visible_name'])
            self.assertNotIn('email', row['value'])
            self.assertIn('pypdf', row['limits'].lower())

    def test_mercatello_relative_horizon_never_gets_calendar_dates(self):
        value = self.index['mercatello-d7-relative-horizon']['value']
        self.assertEqual(value['basis'], 'document_relative')
        self.assertEqual((value['start_period'], value['end_period']), (1, 22))
        self.assertEqual(value['unit'], 'months')
        self.assertFalse(value.get('start_date'))
        self.assertFalse(value.get('end_date'))
        self.assertIn('not_unconditional', value['qualifier'])

    def test_mercatello_grid_dependency_is_unresolved_not_current_assertion(self):
        value = self.index['mercatello-d7-grid-dependency']['value']
        self.assertEqual(value['party'], 'Terna SpA')
        self.assertFalse(value['dependency_resolution_verified'])
        self.assertIsNone(value['calendar_date'])
        self.assertEqual(len(value['works']), 2)

    def test_grecale_preserves_grid_power_and_distinct_oss_scopes(self):
        value = self.index['grecale-d7-lot-configuration']['value']
        self.assertEqual(value['grid_injection_mw'], 698.25)
        self.assertEqual(value['wtg_count_max'], 45)
        self.assertEqual(value['wtg_unit_mw_max'], 18.8)
        issue = self.index['grecale-d7-oss-scope-dependency']['value']
        self.assertEqual(issue['full_scope_months'], 36)
        self.assertEqual(issue['transport_and_site_installation_months'], 6)
        self.assertFalse(issue['reconciliation_complete'])
        self.assertIsNone(issue['calendar_start'])
        self.assertIsNone(issue['calendar_end'])

    def test_plant_geography_does_not_absorb_access_or_connections(self):
        tre = self.index['tre-d7-identity']['value']
        self.assertEqual(tre['plant_municipalities'], ['Badia Tedalda'])
        self.assertIn('Verghereto', tre['access_road_municipalities'])
        sestino = self.index['sestino-d7-identity']['value']
        self.assertEqual(sestino['plant_municipalities'], ['Sestino'])
        self.assertNotIn('Sestino', sestino['connection_municipalities'])

    def test_dates_are_versioned_and_cover_typo_is_preserved(self):
        for row in self.reviews + self.plans:
            self.assertEqual(row['reviewer'], 'assistant_document_review')
            self.assertEqual(date.fromisoformat(row['reviewed_on']), date(2026, 10, 6))
            if row.get('document_date'):
                date.fromisoformat(row['document_date'])
        value = self.index['mercatello-d7-revision-date']['value']
        self.assertEqual(value['issue_date'], '2024-11-04')
        self.assertEqual(value['cover_date_literal'], '04/11//2024')
        self.assertEqual(value['visible_signature_date'], '2025-02-17')


if __name__ == '__main__':
    unittest.main()
