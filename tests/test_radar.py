import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from radar.research import canonical, clean_record, classify, synthesize
from radar.runner import generate, notify, load, save, ROOT
from radar.delivery import check, signature
from radar.network import ServiceError, call

class RadarTests(unittest.TestCase):
    def setUp(self):
        self.config = load(ROOT / 'config.json', {})
        self.fixture = load(ROOT / 'tests' / 'sample.json', {})
        self.record = clean_record(self.fixture['hit'], self.fixture['extraction'], self.config['topics'])

    def test_canonical_document_id_and_host_boundary(self):
        a = canonical('https://www.gartner.com/en/documents/123/slug?utm_source=a#x')
        b = canonical('https://www.gartner.com/documents/123?ref=b')
        self.assertEqual(a, b)
        for url in ['javascript:alert(1)', 'https://gartner.com.evil.org/documents/123', 'http://www.gartner.com/documents/1', 'https://evil.org@www.gartner.com/documents/1']:
            with self.assertRaises(ValueError):
                canonical(url)

    def test_missing_proof_cannot_create_metadata(self):
        obj = copy.deepcopy(self.fixture['extraction'])
        obj['analysts'] = [{'value': 'Invented Person', 'quote': 'Tony Harvey'}]
        obj['published'] = {'value': '2026-09-18', 'quote': '14 September 2026'}
        obj['access'] = {'value': 'paid', 'quote': 'Magic Quadrant'}
        r = clean_record(self.fixture['hit'], obj, self.config['topics'])
        self.assertEqual(r['analysts'], [])
        self.assertIsNone(r['published'])
        self.assertEqual(r['access'], '未知')

    def test_week_window_and_semantic_dedup(self):
        r = self.record
        state = classify(r, None, date(2026,9,12), date(2026,9,18))
        self.assertEqual(r['status'], '本周新增')
        r['summary'] = 'Completely different generated paraphrase'
        classify(r, state, date(2026,9,19), date(2026,9,25))
        self.assertEqual(r['status'], '已收录')
        r['updated'] = '2026-09-21'
        classify(r, state, date(2026,9,19), date(2026,9,25))
        self.assertEqual(r['status'], '本周更新')

    def test_unknown_future_and_background(self):
        for published, status in [(None, '首次发现·日期未知'), ('2026-09-01', '补充背景'), ('2026-10-01', '未来日期·待核实')]:
            r = dict(self.record, published=published)
            classify(r, None, date(2026,9,12), date(2026,9,18))
            self.assertEqual(r['status'], status)

    def test_no_fabricated_citations_or_single_source_cross_theme(self):
        answer = {'core': [{'text': 'Fake fact', 'sources': ['nonexistent']}],
                  'themes': {}, 'signals': [{'text': 'Too broad', 'sources': [self.record['id']]}]}
        with patch('radar.research.llm', return_value=answer):
            result = synthesize([self.record], self.config)
        self.assertEqual(result['core'], [])
        self.assertEqual(result['signals'], [])

    def test_offline_render_idempotency_and_html_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            first = generate(self.config, date(2026,9,18), data, True)
            second = generate(self.config, date(2026,9,18), data, True)
            self.assertEqual(first, second)
            self.assertTrue((data / 'site/index.html').exists())
            from radar.runner import render
            first['records'][0]['title'] = '<script>alert(1)</script>'
            render(first, data / 'site')
            html = (data / 'site/index.html').read_text()
            self.assertNotIn('<script>', html)
            self.assertIn('&lt;script&gt;', html)
            with self.assertRaises(ServiceError):
                notify(data, '2026-09-18', 'https://example.com', 'webhook')

    def test_failed_send_not_recorded_and_success_is_deduped(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            report = generate(self.config, date(2026,9,18), data, True)
            report['demo'] = False
            save(data / 'reports/2026-09-18.json', report)
            with patch('radar.delivery.webhook', side_effect=ServiceError('failure')):
                with self.assertRaises(ServiceError):
                    notify(data, '2026-09-18', 'https://example.com', 'webhook')
            self.assertEqual(load(data / 'state.json', {})['deliveries'], {})
            with patch('radar.delivery.webhook') as send:
                notify(data, '2026-09-18', 'https://example.com', 'webhook')
                notify(data, '2026-09-18', 'https://example.com', 'webhook')
                self.assertEqual(send.call_count, 1)

    def test_feishu_http_success_but_api_failure(self):
        check({'code': 0})
        check({'StatusCode': 0})
        for response in [{'code': 19021}, {}, {'StatusCode': 1}]:
            with self.assertRaises(ServiceError):
                check(response)
        self.assertEqual(len(signature('test-only-secret', '1700000000')), 44)

    def test_total_discovery_failure_preserves_previous_state(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            save(data / 'state.json', {'records': {'old': {}}, 'deliveries': {}, 'demo': False})
            before = (data / 'state.json').read_bytes()
            with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-placeholder'}), patch('radar.runner.discover', side_effect=ServiceError('failure')):
                with self.assertRaises(ServiceError):
                    generate(self.config, date(2026,9,18), data)
            self.assertEqual(before, (data / 'state.json').read_bytes())
            self.assertFalse((data / 'site').exists())

    def test_network_redacts_secrets(self):
        import requests
        with patch('requests.request', side_effect=requests.RequestException('SECRET-WEBHOOK-URL')):
            with self.assertRaises(ServiceError) as exc:
                call('test', 'POST', 'https://example.com/secret', retries=0)
            self.assertNotIn('SECRET', str(exc.exception))

    def test_live_search_contract_and_canonical_dedup(self):
        from radar.research import discover
        config = dict(self.config, topics={'Virtualization': 'server virtualization'})
        reply = {'results': [{'url': self.record['url'] + '?utm_source=x',
                              'title': self.record['title'], 'content': 'public snippet',
                              'raw_content': None}]}
        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test-only'}), patch('radar.research.call', return_value=reply) as api:
            hits, errors, stats = discover(config, date(2026,9,18), {})
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['level'], '搜索摘要')
        self.assertEqual(errors, [])
        self.assertEqual(stats['queries'], 2)
        self.assertEqual(api.call_args_list[0].kwargs['json']['start_date'], '2026-09-12')
        self.assertEqual(api.call_args_list[0].kwargs['json']['end_date'], '2026-09-19')

    def test_app_upload_then_file_message(self):
        from radar.delivery import app_file
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.html'
            path.write_text('<html>test</html>')
            env = {'FEISHU_APP_ID': 'test-id', 'FEISHU_APP_SECRET': 'test-secret', 'FEISHU_CHAT_ID': 'test-chat'}
            responses = [{'code': 0, 'tenant_access_token': 'test-token'},
                         {'code': 0, 'data': {'file_key': 'test-file'}}, {'code': 0}]
            with patch.dict('os.environ', env), patch('radar.delivery.call', side_effect=responses) as api:
                app_file(path, '2026-09-18')
            self.assertEqual(api.call_count, 3)
            self.assertEqual(api.call_args_list[1].kwargs['data']['file_type'], 'stream')
            message = api.call_args_list[2].kwargs['json']
            self.assertEqual(message['receive_id'], 'test-chat')
            self.assertEqual(json.loads(message['content']), {'file_key': 'test-file'})

    def test_monthly_first_window_then_weekly_append(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            first = generate(self.config, date(2026,9,18), data, True)
            self.assertEqual(first['start'], '2026-08-19')
            second = generate(self.config, date(2026,9,25), data, True)
            self.assertEqual(second['start'], '2026-09-19')
            self.assertFalse(second['initial'])
            html = (data / 'site/index.html').read_text()
            self.assertIn('id="edition-2026-09-18"', html)
            self.assertIn('id="edition-2026-09-25"', html)
            self.assertLess(html.index('id="edition-2026-09-25"'), html.index('id="edition-2026-09-18"'))
            self.assertEqual(len(list((data / 'site').glob('*.html'))), 1)
            self.assertEqual(second['new_count'], 0)
            from radar.runner import decorate
            self.assertEqual(decorate(second)['active_topics'], [])
            self.assertNotIn('<h3>HCI', html)
            self.assertIn('未检出可确认', html)
            generate(self.config, date(2026,9,18), data, True)
            self.assertEqual((data / 'site/index.html').read_text(), html)

    def test_background_does_not_create_topic_box(self):
        from radar.runner import decorate
        report = {'initial': False, 'topics': ['Virtualization', 'HCI'], 'records': [dict(self.record, status='补充背景')]}
        self.assertEqual(decorate(report)['active_topics'], [])

    def test_bootstrap_import_persists_dedup_and_stable_link(self):
        from radar.runner import import_report
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            imported = import_report(ROOT / 'bootstrap/2026-09-18.json', data)
            self.assertEqual(len(imported['records']), 11)
            self.assertEqual(len(load(data / 'state.json', {})['records']), 11)
            with self.assertRaises(ServiceError):
                import_report(ROOT / 'bootstrap/2026-09-18.json', data)
            with patch('radar.delivery.webhook') as send:
                notify(data, '2026-09-18', 'https://example.com/radar', 'webhook')
                self.assertEqual(send.call_args.args[1], 'https://example.com/radar/index.html#edition-2026-09-18')

    def test_calendar_month_boundary_and_gap_catchup(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            first = generate(self.config, date(2026,3,31), data, True)
            self.assertEqual(first['start'], '2026-03-01')
            second = generate(self.config, date(2026,4,15), data, True)
            self.assertEqual(second['start'], '2026-04-01')

    def test_metadata_order_and_missing_fields_do_not_create_updates(self):
        r = self.record
        state = classify(r, None, date(2026,9,12), date(2026,9,18))
        r['analysts'].reverse()
        r['research_type'] = '未知'
        r['published'] = None
        classify(r, state, date(2026,9,19), date(2026,9,25))
        self.assertEqual(r['status'], '已收录')

    def test_deepseek_endpoint_key_and_json_contract(self):
        from radar.research import llm
        reply = {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"ok":true}'}}]}
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-deepseek', 'DEEPSEEK_MODEL': 'deepseek-flash'}, clear=True), patch('radar.research.call', return_value=reply) as api:
            self.assertEqual(llm('Return JSON', {}, self.config), {'ok': True})
            self.assertEqual(api.call_args.args[2], 'https://api.deepseek.com/chat/completions')
            self.assertEqual(api.call_args.kwargs['headers']['Authorization'], 'Bearer test-deepseek')
            request = api.call_args.kwargs['json']
            self.assertEqual(request['model'], 'deepseek-flash')
            self.assertEqual(request['response_format'], {'type': 'json_object'})
            self.assertEqual(request['thinking'], {'type': 'disabled'})

    def test_incomplete_or_empty_deepseek_output_rejected(self):
        from radar.research import llm
        for reason, content in [('length', '{"ok":true}'), ('stop', ''), ('stop', '[]')]:
            reply = {'choices': [{'finish_reason': reason, 'message': {'content': content}}]}
            with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-only'}, clear=True), patch('radar.research.call', return_value=reply):
                with self.assertRaises(ServiceError):
                    llm('Return JSON', {}, self.config)
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(ServiceError, 'DEEPSEEK_API_KEY'):
                llm('Return JSON', {}, self.config)

if __name__ == '__main__':
    unittest.main()
