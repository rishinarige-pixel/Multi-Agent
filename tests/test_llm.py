import logging
from unittest.mock import Mock
import httpx
import pytest
from llm import LLM, ModelError


def config(**kwargs):
    return {'provider': 'ollama', 'model': 'test', 'max_model_calls': 10,
            'timeout_seconds': 1, **kwargs}


def test_retry_and_budget(monkeypatch):
    monkeypatch.setattr('llm.time.sleep', lambda _: None)
    post = Mock(side_effect=httpx.ConnectError('offline'))
    monkeypatch.setattr('llm.httpx.post', post)
    model = LLM(config(max_model_calls=2), logging.getLogger('test'))
    with pytest.raises(ModelError, match='limit'):
        model.complete('system', 'task')
    assert post.call_count == model.calls == 2


def test_three_attempts_then_stop(monkeypatch):
    monkeypatch.setattr('llm.time.sleep', lambda _: None)
    post = Mock(side_effect=httpx.ConnectError('offline'))
    monkeypatch.setattr('llm.httpx.post', post)
    with pytest.raises(ModelError, match='three attempts'):
        LLM(config(), logging.getLogger('test')).complete('s', 'p')
    assert post.call_count == 3


@pytest.mark.parametrize('provider', ['openai', 'ollama'])
def test_provider_transport(monkeypatch, provider):
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-test-key')
    response = Mock()
    response.json.return_value = {'choices': [{'message': {'content': 'ok'}}], 'message': {'content': 'ok'}}
    post = Mock(return_value=response)
    monkeypatch.setattr('llm.httpx.post', post)
    assert LLM(config(provider=provider), logging.getLogger('test')).complete('s', 'p') == 'ok'
    url = post.call_args.args[0]
    assert ('api.openai.com' in url) == (provider == 'openai')


def test_missing_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    with pytest.raises(ModelError, match='OPENAI_API_KEY'):
        LLM(config(provider='openai'), logging.getLogger('test')).complete('s', 'p')


@pytest.mark.parametrize('http_failure', [False, True])
def test_failure_details_and_timing(monkeypatch, capsys, caplog, http_failure):
    monkeypatch.setattr('llm.time.sleep', lambda _: None)
    monkeypatch.setattr('llm.time.perf_counter', Mock(side_effect=[0, 1.25, 2, 3.25, 4, 5.25]))
    if http_failure:
        response = httpx.Response(429, text='rate limit exceeded',
                                  request=httpx.Request('POST', 'https://example.com'))
        error = httpx.HTTPStatusError('failure', request=response.request, response=response)
        expected = 'HTTP 429: rate limit exceeded'
    else:
        error = httpx.ConnectError('connection refused')
        expected = 'ConnectError: connection refused'
    monkeypatch.setattr('llm.httpx.post', Mock(side_effect=error))
    with caplog.at_level(logging.INFO), pytest.raises(ModelError, match=expected):
        LLM(config(), logging.getLogger('test')).complete('s', 'p')
    terminal = capsys.readouterr().out
    assert terminal.count(expected) == 3
    assert terminal.count('took 1.25 seconds') == 3
    assert caplog.text.count(expected) == 3
    assert caplog.text.count('took 1.25 seconds') == 3


def test_success_timing(monkeypatch, capsys, caplog):
    monkeypatch.setattr('llm.time.perf_counter', Mock(side_effect=[10, 12.5]))
    response = Mock()
    response.json.return_value = {'message': {'content': 'ok'}}
    monkeypatch.setattr('llm.httpx.post', Mock(return_value=response))
    with caplog.at_level(logging.INFO):
        assert LLM(config(), logging.getLogger('test')).complete('s', 'p') == 'ok'
    assert 'took 2.50 seconds' in capsys.readouterr().out
    assert 'took 2.50 seconds' in caplog.text


def test_error_redacts_key(monkeypatch, capsys, caplog):
    monkeypatch.setenv('OPENAI_API_KEY', 'secret-test-key')
    monkeypatch.setattr('llm.time.sleep', lambda _: None)
    monkeypatch.setattr('llm.httpx.post', Mock(side_effect=httpx.ConnectError('secret-test-key rejected')))
    with pytest.raises(ModelError) as caught:
        LLM(config(provider='openai'), logging.getLogger('test')).complete('s', 'p')
    assert 'secret-test-key' not in str(caught.value) + capsys.readouterr().out + caplog.text
    assert '[REDACTED]' in str(caught.value)
