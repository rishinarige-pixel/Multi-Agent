import logging
from unittest.mock import Mock
import pytest
from tools.fetch import validate_url, Fetch
from tools.base import Tool


@pytest.mark.parametrize('url', ['file:///etc/passwd', 'http://user:pass@example.com', 'http://example.com:8080'])
def test_unsafe_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_private_address(monkeypatch):
    monkeypatch.setattr('tools.fetch.socket.getaddrinfo', lambda *args: [(2, 1, 6, '', ('127.0.0.1', 80))])
    with pytest.raises(ValueError, match='Private'):
        validate_url('http://localhost')


def test_fetch_strips_scripts(monkeypatch):
    monkeypatch.setattr('tools.fetch.validate_url', lambda _: None)
    response = Mock(headers={'content-type': 'text/html'})
    response.iter_bytes.return_value = [b'<h1>Facts</h1><script>bad()</script><p>Evidence</p>']
    context = Mock()
    context.__enter__ = Mock(return_value=response)
    context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr('tools.fetch.httpx.stream', lambda *a, **kw: context)
    assert Fetch(logging.getLogger('test')).execute('https://example.com') == 'Facts Evidence'


def test_tool_retries(monkeypatch):
    monkeypatch.setattr('tools.base.time.sleep', lambda _: None)
    tool = Tool(logging.getLogger('test'))
    tool.execute = Mock(side_effect=ValueError('failed'))
    assert tool.run('query') is None
    assert tool.execute.call_count == 3
