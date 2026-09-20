"""Presentation-only cleanup; original research and provenance remain intact."""
import re
from markupsafe import Markup
from .research import canonical

TITLE = 'Gartner 周报：虚拟化、私有云、容器、AI'


def prose(value):
    if isinstance(value, Markup) or not isinstance(value, str) or value.startswith(('https://', 'http://')):
        return value
    value = re.sub(r'\[citation\s*:[^\]]*\]', '', value, flags=re.I)
    value = re.sub(r'(?<=[\u3400-\u9fff])(?=[A-Za-z0-9])', ' ', value)
    value = re.sub(r'(?<=[A-Za-z0-9%％])(?=[\u3400-\u9fff])', ' ', value)
    return value


def notebook(editions):
    """Merge documents across editions; append analysis within each module."""
    records, aliases, cores, signals, themes = {}, {}, [], [], {}
    seen = {}
    latest = editions[-1]['end']

    def points(items, module):
        result = []
        for point in items:
            text = prose(point['text']).strip()
            key = (text, tuple(sorted(point.get('sources', []))))
            if key not in seen.setdefault(module, set()):
                seen[module].add(key)
                result.append(dict(point, text=text))
        return result

    for edition in editions:
        end = edition['end']
        for record in edition['records']:
            key = canonical(record['url'])
            previous = records.get(key)
            merged = dict(previous or {})
            merged.update({k: v for k, v in record.items() if v or k not in merged})
            merged['first_seen'] = previous['first_seen'] if previous else end
            merged['anchor'] = previous['anchor'] if previous else record['id']
            merged['is_new'] = merged['first_seen'] == latest
            records[key] = merged
            aliases[record['id']] = merged['anchor']
        cores.append({'date': end, 'points': points(edition['analysis']['core'], 'core')})
        signal_points = points(edition['analysis']['signals'], 'signals')
        if signal_points:
            signals.append({'date': end, 'points': signal_points})
        for topic in edition['active_topics']:
            topic_points = points(edition['analysis']['themes'].get(topic, []), topic)
            if topic_points:
                themes.setdefault(topic, []).append({'date': end, 'points': topic_points})
    ordered = sorted(records.values(), key=lambda r: (r.get('published') or r['first_seen'], r['first_seen'], r['title']), reverse=True)
    return dict(title=TITLE, records=ordered, aliases=aliases, cores=cores[::-1],
                signals=signals[::-1], themes={topic: blocks[::-1] for topic, blocks in themes.items()},
                latest=editions[-1], editions=editions[::-1])
