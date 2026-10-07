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
