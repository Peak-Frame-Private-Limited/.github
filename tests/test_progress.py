import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('progress', Path(__file__).resolve().parents[1] / 'scripts/update_progress.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ProgressTests(unittest.TestCase):
    def test_private_forks_and_profile_excluded(self):
        good = {'name': 'app', 'private': False, 'fork': False, 'archived': False}
        self.assertTrue(p.eligible(good))
        for change in ({'private': True}, {'name': '.github'}, {'archived': True}, {'fork': True}):
            self.assertFalse(p.eligible(good | change))

    def test_milestone_zero_is_not_fake_completion(self):
        self.assertIsNone(p.completion({'open': 0, 'closed': 0}))
        self.assertEqual(p.completion({'open': 1, 'closed': 3}), 75)

    def test_marker_edit_preserves_brand_content(self):
        text = 'Brand\n<!-- PROGRESS:START -->\nold\n<!-- PROGRESS:END -->\nContact'
        self.assertEqual(p.replace_block(text, 'new'), text.replace('old', 'new'))
        with self.assertRaises(ValueError):
            p.replace_block('No markers', 'new')

    def test_empty_snapshot_is_honest_and_valid_svg(self):
        s = {'updated': '2026-10-29T00:00:00Z', 'org': 'Peak-Frame-Private-Limited', 'repos': [], 'milestones': [], 'releases': []}
        self.assertIn('No public project repositories', p.markdown(s))
        ET.fromstring(p.svg(s))

    def test_title_cannot_inject_markup(self):
        label = p.link('name | <script>\n[trick]', 'https://github.com/org/repo')
        self.assertNotIn('<script>', label)
        self.assertIn('\\|', label)
        with self.assertRaises(ValueError):
            p.link('x', 'javascript:alert(1)')

    def test_pagination(self):
        with patch.object(p, 'api', side_effect=[list(range(100)), [100]]) as api:
            self.assertEqual(len(list(p.pages('/items?state=open'))), 101)
            self.assertIn('page=2', api.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
