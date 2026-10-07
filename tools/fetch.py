import ipaddress
import socket
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from .base import Tool


def validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Only public HTTP(S) URLs without credentials are supported')
    if parsed.port not in (None, 80, 443):
        raise ValueError('Nonstandard web ports are blocked')
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80))
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Private, loopback and reserved addresses are blocked')


class Fetch(Tool):
    def execute(self, url):
        validate_url(url)
        # Do not follow redirects into internal networks or download unbounded bodies.
        with httpx.stream('GET', url, timeout=20, follow_redirects=False) as response:
            response.raise_for_status()
            if 'text/html' not in response.headers.get('content-type', '') and 'text/plain' not in response.headers.get('content-type', ''):
                raise ValueError('Only HTML and plain text are supported')
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 1_000_000:
                    raise ValueError('Page exceeds 1 MB')
        soup = BeautifulSoup(bytes(body), 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer']):
            tag.decompose()
        return soup.get_text(' ', strip=True)[:12000]
