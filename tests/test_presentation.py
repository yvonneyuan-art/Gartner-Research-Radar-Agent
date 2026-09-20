import copy
import tempfile
import unittest
from pathlib import Path
from radar.runner import load, save, render, decorate, ROOT
from radar.presentation import notebook, prose


class PresentationTests(unittest.TestCase):
    def test_cleanup_preserves_numbers_links_and_escaping(self):
        self.assertEqual(prose('本周AI支出2026年增49.5%[citation:abc123]。'),
                         '本周 AI 支出 2026 年增 49.5%。')
        self.assertEqual(prose('https://example.com/AI2026'), 'https://example.com/AI2026')

    def test_modules_merge_updates_and_preserve_source_links(self):
        old = load(ROOT / 'bootstrap/2026-09-18.json', {})
        new = copy.deepcopy(old)
        new['end'] = '2026-09-25'
        new['initial'] = False
        new['records'] = [copy.deepcopy(old['records'][0])]
        new['records'][0]['id'] = 'alternate-id'
        new['records'][0]['summary'] = '新增AI摘要2026年[citation:internal]。'
        new['records'][0]['status'] = '本周更新'
        new['analysis']['core'] = [{'text': '本周AI变化[citation:internal]', 'sources': ['alternate-id']}]
        result = notebook([decorate(old), decorate(new)])
        self.assertEqual(len(result['records']), len(old['records']))
        self.assertEqual(result['aliases']['alternate-id'], old['records'][0]['id'])
        self.assertFalse(any(r['is_new'] for r in result['records']))
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            save(data / 'reports/2026-09-18.json', old)
            render(new, data / 'site')
            html = (data / 'site/index.html').read_text()
            self.assertNotIn('[citation:', html)
            self.assertNotIn('<table', html)
            self.assertEqual(html.count('<h2>研究汇总</h2>'), 1)
            self.assertEqual(html.count('<article '), len(old['records']))
            self.assertIn('新增 AI 摘要 2026 年', html)
            self.assertIn('href="#r-' + old['records'][0]['id'] + '"', html)
            self.assertNotIn('研究类型：', html)
            self.assertNotIn('本期新增', html)
