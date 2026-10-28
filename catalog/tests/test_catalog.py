import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('shared_catalog', ROOT / 'catalog/manage.py')
catalog = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(catalog)

class Catalog(unittest.TestCase):
    def setUp(self): self.registry = catalog.read_registry()

    def test_current_inventory_and_generated_view_match(self):
        catalog.validate(self.registry)
        for name, body in catalog.projections(self.registry).items():
            self.assertEqual(body, (catalog.GENERATED / name).read_bytes())

    def test_new_source_cannot_be_silently_omitted(self):
        actual = catalog.inventory() | {'systems/fictional-new-app'}
        with self.assertRaisesRegex(ValueError, 'CATALOG_DRIFT missing=systems/fictional-new-app'):
            catalog.validate(self.registry, actual)

    def test_removed_source_and_duplicate_entry_are_refused(self):
        bad = copy.deepcopy(self.registry); bad['components'].append(bad['components'][0])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_COMPONENT'): catalog.validate(bad)
        with self.assertRaisesRegex(ValueError, 'CATALOG_DRIFT'):
            catalog.validate(self.registry, set())

    def test_requirements_package_and_evidence_are_required(self):
        for field, value in [('requirements', ''), ('package', 'wrong-family'), ('examples', []), ('validation', 'missing.md')]:
            bad = copy.deepcopy(self.registry); bad['components'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): catalog.validate(bad)

    def test_new_registered_app_is_source_only_until_packaged(self):
        bad = copy.deepcopy(self.registry)
        entry = copy.deepcopy(next(c for c in bad['components'] if c['kind'] == 'system'))
        entry.update(id='fictional-new-app', path='systems/fictional-new-app', title='Fictional new app')
        bad['components'].append(entry)
        actual = catalog.inventory() | {entry['path']}
        with patch.object(catalog, 'inventory', return_value=actual): data = catalog.model(bad)
        self.assertIn(entry['path'], data['pending_packaging'])
        fresh = next(c for c in data['tools'] if c['id'] == entry['id'])
        self.assertFalse(fresh['released']); self.assertIn('/blob/main/', fresh['guide'])
        self.assertIn('next package pending', catalog.render(data))

    def test_render_escapes_metadata_and_keeps_workshops(self):
        bad = copy.deepcopy(self.registry); bad['components'][0]['purpose'] = '<img src=x onerror=bad>'
        text = catalog.render(catalog.model(bad))
        self.assertNotIn('<img src=x', text); self.assertIn('&lt;img', text)
        self.assertEqual(8, text.count('Five-minute workshop'))

    def test_draft_release_and_missing_assets_cannot_activate(self):
        with patch.object(catalog, 'fetch', return_value=json.dumps({'draft': True, 'tag_name': 'toolkit-v0.2.0'}).encode()):
            with self.assertRaisesRegex(ValueError, 'PUBLISHED_RELEASE_REQUIRED'):
                catalog.verify_release('toolkit-v0.2.0')

    def test_focused_versions_have_distinct_download_start_demo_and_methodology(self):
        data = catalog.model(self.registry); text = catalog.render(data)
        for app in ('local-site-builder', 'resource-monitor'):
            entry = next(c for c in data['tools'] if c['id'] == app)
            release = entry['focused_release']
            self.assertIn('/blob/' + release['tag'] + '/', entry['guide'])
            self.assertIn('/download/' + release['tag'] + '/' + release['filename'], text)
            self.assertIn(entry['path'] + '/START-HERE.md', text)
            self.assertIn(entry['path'] + '/docs/PROVENANCE.md', text)
        bad = copy.deepcopy(self.registry)
        next(c for c in bad['components'] if c['id'] == 'resource-monitor')['focused_release']['filename'] = '../bad.zip'
        with self.assertRaisesRegex(ValueError, 'FOCUSED_RELEASE_INVALID'): catalog.validate(bad)
        responses = [json.dumps({'draft': False, 'tag_name': 'toolkit-v0.2.0', 'assets': []}).encode(),
                     json.dumps({'tag': 'toolkit-v0.2.0', 'downloads': [{'filename': 'outlands-complete-0.2.0.zip',
                       'url': 'https://github.com/' + catalog.OWNER + '/releases/download/toolkit-v0.2.0/outlands-complete-0.2.0.zip', 'bytes': 1}]}).encode()]
        with patch.object(catalog, 'fetch', side_effect=responses):
            with self.assertRaisesRegex(ValueError, 'RELEASE_ASSET_MISSING'):
                catalog.verify_release('toolkit-v0.2.0')

if __name__ == '__main__': unittest.main()
