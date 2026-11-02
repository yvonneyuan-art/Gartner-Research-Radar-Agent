import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from radar.publishing import public_url

class PublishingTests(unittest.TestCase):
    def test_cloudflare_verifies_content_without_leaking_token(self):
        env = {'HOSTING_PROVIDER':'cloudflare', 'CLOUDFLARE_ACCOUNT_ID':'a'*32,
               'CLOUDFLARE_PROJECT_NAME':'research-weekly', 'CLOUDFLARE_API_TOKEN':'test-token'}
        metadata = Mock()
        metadata.json.return_value = {'success':True,'result':{'subdomain':'research-weekly.pages.dev'}}
        stale = Mock(status_code=200, content=b'old')
        current = Mock(status_code=200, content=b'new')
        get = Mock(side_effect=[metadata, stale, current])
        with tempfile.TemporaryDirectory() as directory:
            site=Path(directory)
            (site/'index.html').write_bytes(b'new')
            self.assertEqual(public_url(env, site, get, Mock()), 'https://research-weekly.pages.dev')
        self.assertEqual(get.call_count, 3)
        self.assertNotIn('headers', get.call_args_list[1].kwargs)
        self.assertNotIn('headers', get.call_args_list[2].kwargs)

    def test_github_remains_default_until_switch(self):
        get=Mock()
        self.assertEqual(public_url({'GITHUB_PAGES_URL':'https://example.github.io/report/'}, get=get),
                         'https://example.github.io/report/')
        get.assert_not_called()
