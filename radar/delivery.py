import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from urllib.parse import urlsplit
from .network import call, ServiceError
from .presentation import prose, TITLE


def required(name):
    value = os.environ.get(name)
    if not value:
        raise ServiceError(f'{name} is required')
    return value


def signature(secret, timestamp):
    return base64.b64encode(hmac.new(f'{timestamp}\n{secret}'.encode(), b'', hashlib.sha256).digest()).decode()


def check(result):
    code = result.get('code', result.get('StatusCode'))
    if code != 0:
        raise ServiceError(f'Feishu: API rejected request (code={code}); details redacted')
    return result


def webhook(report, link):
    url = required('FEISHU_WEBHOOK_URL')
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname != 'open.feishu.cn' or not p.path.startswith('/open-apis/bot/v2/hook/'):
        raise ServiceError('Expected official Feishu custom-bot HTTPS webhook')
    points = '\n'.join('• ' + prose(x['text']) for x in report['analysis']['core'])
    payload = {'msg_type': 'text', 'content': {'text':
        f"{TITLE} | {report['start']} — {report['end']}\n"
        f"新增/更新 {report['new_count']} 项 · 本期收录 {len(report['records'])} 项\n"
        f"{report['quality']}\n{points[:1800]}\nGartner 周报：{link}"}}
    secret = os.environ.get('FEISHU_WEBHOOK_SECRET')
    if secret:
        payload['timestamp'] = str(int(time.time()))
        payload['sign'] = signature(secret, payload['timestamp'])
    # Webhook has no idempotency key: do not retry ambiguous sends automatically.
    check(call('Feishu webhook', 'POST', url, retries=0, json=payload))


def app_file(report_path, issue_id):
    root = 'https://open.feishu.cn/open-apis'
    token = check(call('Feishu token', 'POST', root + '/auth/v3/tenant_access_token/internal',
        json={'app_id': required('FEISHU_APP_ID'), 'app_secret': required('FEISHU_APP_SECRET')}))['tenant_access_token']
    headers = {'Authorization': f'Bearer {token}'}
    with report_path.open('rb') as file:
        upload = check(call('Feishu upload', 'POST', root + '/im/v1/files', retries=0,
            headers=headers, data={'file_type': 'stream', 'file_name': report_path.name},
            files={'file': (report_path.name, file, 'text/html')}))
    key = upload['data']['file_key']
    chat = required('FEISHU_CHAT_ID')
    message = {'receive_id': chat, 'msg_type': 'file',
               'content': json.dumps({'file_key': key}),
               'uuid': str(uuid.uuid5(uuid.NAMESPACE_URL, f'gartner:{chat}:{issue_id}'))}
    check(call('Feishu message', 'POST', root + '/im/v1/messages?receive_id_type=chat_id',
               headers=headers, retries=0, json=message))
