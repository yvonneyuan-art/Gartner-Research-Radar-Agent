"""Resolve the public report URL; verify Cloudflare before sending notifications."""
import os
import re
import time
from pathlib import Path
import requests


def public_url(env, site=Path('.runtime/site'), get=requests.get, pause=time.sleep):
    if env.get('HOSTING_PROVIDER') != 'cloudflare':
        url = env.get('GITHUB_PAGES_URL', '')
        if not url.startswith('https://') or '\n' in url:
            raise ValueError('Missing deployed GitHub Pages URL')
        return url
    account = env['CLOUDFLARE_ACCOUNT_ID']
    project = env['CLOUDFLARE_PROJECT_NAME']
    if not re.fullmatch(r'[a-fA-F0-9]{32}', account) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,57}', project):
        raise ValueError('Invalid Cloudflare account or project configuration')
    response = get(f'https://api.cloudflare.com/client/v4/accounts/{account}/pages/projects/{project}',
                   headers={'Authorization': 'Bearer ' + env['CLOUDFLARE_API_TOKEN']}, timeout=30)
    response.raise_for_status()
    metadata = response.json()
    if not metadata.get('success'):
        raise ValueError('Cloudflare project lookup failed')
    host = metadata['result']['subdomain']
    if not re.fullmatch(r'[a-z0-9-]+\.pages\.dev', host):
        raise ValueError('Unexpected Cloudflare public hostname')
    url = 'https://' + host
    expected = (site / 'index.html').read_bytes()
    for attempt in range(12):
        try:
            # Credentials are sent only to the Cloudflare API, never to the public site.
            page = get(url + '/index.html', params={'verify': str(time.time_ns())}, timeout=30)
            if page.status_code == 200 and page.content == expected:
                return url
        except requests.RequestException:
            pass
        if attempt < 11:
            pause(5)
    raise ValueError('Cloudflare page is not yet serving the new report; notification skipped')


def main():
    try:
        url = public_url(os.environ)
    except (requests.RequestException, ValueError, KeyError, OSError):
        raise SystemExit('Public report verification failed. Check Cloudflare configuration and deployment; no notification sent.')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('url=' + url + '\n')
    print('Public report verified: ' + url)


if __name__ == '__main__':
    main()
