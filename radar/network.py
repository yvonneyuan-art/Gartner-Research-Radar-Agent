"""Bounded requests; never echo response bodies, request URLs or secrets on errors."""
import time
import requests

class ServiceError(RuntimeError):
    pass

def call(service, method, url, *, retries=2, **kwargs):
    for attempt in range(retries + 1):
        try:
            response = requests.request(method, url, timeout=(15, 120), allow_redirects=False, **kwargs)
        except requests.RequestException:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise ServiceError(f'{service}: network error; credentials and payload redacted') from None
        if (response.status_code == 429 or response.status_code >= 500) and attempt < retries:
            time.sleep(2 ** attempt)
            continue
        if not 200 <= response.status_code < 300:
            raise ServiceError(f'{service}: HTTP {response.status_code}; details redacted')
        try:
            return response.json()
        except ValueError:
            raise ServiceError(f'{service}: invalid JSON') from None
