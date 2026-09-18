import argparse
import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .network import ServiceError
from .research import discover, llm, clean_record, classify, synthesize, EXTRACT
from . import delivery

ROOT = Path(__file__).resolve().parent.parent


def load(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def generate(config, end, data, demo=False):
    site = data / 'site'
    report_path = data / 'reports' / f'{end}.json'
    # A completed edition is reused after deployment or notification failure.
    if report_path.exists():
        report = load(report_path, {})
        if report['demo'] != demo:
            raise ServiceError('Demo and live data must use separate directories')
        render(report, site)
        return report
    state = load(data / 'state.json', {'schema': 1, 'records': {}, 'deliveries': {}, 'demo': demo})
    if state.get('demo') != demo:
        raise ServiceError('Demo and live state must use separate directories')
    start = end - timedelta(days=config['window_days'] - 1)
    errors, records, all_count = [], [], 0
    if demo:
        fixture = load(ROOT / 'tests' / 'sample.json', {})
        hits = [fixture['hit']]
        stats = {'queries': 0, 'discovered': 1, 'processed': 1}
    else:
        if not os.environ.get('OPENAI_API_KEY'):
            raise ServiceError('OPENAI_API_KEY is required; use --demo for an offline sample')
        hits, errors, stats = discover(config, end, state['records'])
    next_records = dict(state['records'])
    failures = 0
    for hit in hits:
        try:
            obj = fixture['extraction'] if demo else llm(EXTRACT, {
                'topics': list(config['topics']), 'source': hit}, config)
            record = clean_record(hit, obj, config['topics'])
            if not record:
                continue
            all_count += 1
            prior = state['records'].get(record['url'])
            next_records[record['url']] = classify(record, prior, start, end)
            # Already-seen unchanged records do not reappear in subsequent editions.
            if record['status'] != '已收录':
                records.append(record)
        except (ServiceError, ValueError, TypeError, AttributeError, KeyError):
            failures += 1
            errors.append(f"元数据提取失败：{hit['url']}")
    if hits and failures == len(hits):
        raise ServiceError('All document extraction failed; previous state preserved')
    rank = {'本周新增': 0, '本周更新': 1, '元数据变化·待核实': 2,
            '首次发现·日期未知': 3, '补充背景': 4, '未来日期·待核实': 5}
    records.sort(key=lambda r: (rank[r['status']], r['title']))
    if demo:
        analysis = {'core': [{'text': '验证样例：公开摘要显示，服务器虚拟化选型正在重新受到关注。此页仅验证展示流程，不代表完成七个主题的本周检索。',
                              'sources': [records[0]['id']] if records else []}],
                    'themes': {t: [] for t in config['topics']}, 'signals': []}
    else:
        try:
            analysis = synthesize(records, config)
        except (ServiceError, TypeError, ValueError, AttributeError):
            errors.append('趋势综合失败；保留已提取的逐条摘要，不生成无证据结论')
            analysis = {'core': [], 'themes': {t: [] for t in config['topics']}, 'signals': []}
    quality = ('验证样例 · 非完整周报' if demo else
               '部分失败 · 本期覆盖不完整' if errors else '公开检索完成 · 不保证穷尽全部研究')
    report = {'start': str(start), 'end': str(end), 'demo': demo, 'topics': list(config['topics']),
              'created': datetime.now(ZoneInfo(config['timezone'])).isoformat(), 'records': records,
              'analysis': analysis, 'errors': errors, 'stats': stats, 'quality': quality,
              'new_count': sum(r['status'] in ['本周新增', '本周更新'] for r in records),
              'unchanged_count': all_count - len(records)}
    render(report, site)
    save(report_path, report)
    state['records'] = next_records
    save(data / 'state.json', state)
    save(data / 'latest.json', report)
    return report


def render(report, site):
    env = Environment(loader=FileSystemLoader(str(ROOT / 'radar' / 'templates')),
                      autoescape=select_autoescape(['html']))
    output = env.get_template('report.html').render(report=report)
    site.mkdir(parents=True, exist_ok=True)
    (site / f"{report['end']}.html").write_text(output, encoding='utf-8')
    issues = sorted((p.name for p in site.glob('????-??-??.html')), reverse=True)
    (site / 'index.html').write_text(env.get_template('index.html').render(issues=issues), encoding='utf-8')
    (site / '.nojekyll').touch()


def notify(data, issue, base_url, mode):
    report = load(data / 'reports' / f'{issue}.json', None)
    if not report or report['demo']:
        raise ServiceError('Only a completed live report can be delivered')
    state = load(data / 'state.json', {})
    from urllib.parse import urlsplit
    import hashlib
    destination = os.environ.get('FEISHU_WEBHOOK_URL' if mode == 'webhook' else 'FEISHU_CHAT_ID', '')
    key = f"{issue}:{mode}:" + hashlib.sha256(destination.encode()).hexdigest()[:12]
    if key in state.get('deliveries', {}):
        print('Already delivered; skipped')
        return
    if mode == 'webhook':
        p = urlsplit(base_url)
        if p.scheme != 'https' or not p.hostname or p.username or p.password or p.query or p.fragment:
            raise ServiceError('A deployed HTTPS base URL is required')
        delivery.webhook(report, base_url.rstrip('/') + f'/{issue}.html')
    else:
        delivery.app_file(data / 'site' / f'{issue}.html', issue)
    state.setdefault('deliveries', {})[key] = datetime.now().isoformat()
    save(data / 'state.json', state)
    print('Delivery accepted by Feishu')


def main():
    parser = argparse.ArgumentParser(description='Gartner public research weekly radar')
    parser.add_argument('command', choices=['generate', 'notify'])
    parser.add_argument('--config', type=Path, default=ROOT / 'config.json')
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data')
    parser.add_argument('--as-of', type=date.fromisoformat)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--base-url', default='')
    parser.add_argument('--mode', choices=['webhook', 'app'], default='webhook')
    args = parser.parse_args()
    config = load(args.config, None)
    try:
        if not config:
            raise ServiceError('Missing config.json')
        end = args.as_of or datetime.now(ZoneInfo(config['timezone'])).date()
        if args.command == 'generate':
            report = generate(config, end, args.data_dir, args.demo)
            print(f"Generated {report['end']}: {len(report['records'])} records; {report['quality']}")
        else:
            notify(args.data_dir, str(end), args.base_url, args.mode)
    except ServiceError as exc:
        parser.exit(1, str(exc) + '\n')

if __name__ == '__main__':
    main()
