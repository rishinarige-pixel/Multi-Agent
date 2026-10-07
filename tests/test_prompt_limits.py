import json
import logging
from unittest.mock import Mock
import pytest
from agents.planner import Planner
from agents.reviewer import Reviewer
from agents.researcher import Researcher
from agents.writer import Writer
from tools.search import Search
from llm import LLM

LOGGER = logging.getLogger('limits')


@pytest.mark.parametrize('response', ['```json\n["A", "B", "C"]\n```',
                                     'Here is the plan: ["A", "B", "C", "D"] Done.'])
def test_wrapped_plan(response):
    llm = Mock(complete=Mock(return_value=response))
    assert Planner(llm, LOGGER).run('task') == ['A', 'B', 'C']
    assert llm.complete.call_count == 1


def test_plan_retry_line_fallback():
    llm = Mock()
    llm.complete.side_effect = ['invalid', '1. A\n2. B\n3. C\n4. D']
    assert Planner(llm, LOGGER).run('task') == ['A', 'B', 'C']
    assert llm.complete.call_count == 2


def test_review_fences_and_fallback():
    llm = Mock()
    llm.complete.side_effect = ['APPROVED\nWell sourced.',
                                'bad json', '- Add citations\n- Explain uncertainty']
    reviewer = Reviewer(llm, LOGGER)
    assert reviewer.run('task', 'report', [])['approved']
    review = reviewer.run('task', 'report', [])
    assert not review['approved'] and 'Add citations' in review['feedback']
    assert llm.complete.call_count == 3


def test_research_limits():
    llm = Mock(complete=Mock(return_value='word ' * 500))
    agent = Researcher(llm, LOGGER, {'search_results': 5})
    assert agent.search.limit == 2
    agent.search.run = Mock(return_value=[{'title': 'title', 'url': f'https://example.com/{i}',
                                         'snippet': 'snippet'} for i in range(5)])
    agent.fetch.run = Mock(return_value='x' * 12000)
    notes = agent.run('task')
    assert agent.fetch.run.call_count == 2
    evidence = json.loads(llm.complete.call_args.args[1])['evidence']
    assert len(evidence) == 2
    assert all(len(e['page_text']) == 1500 for e in evidence)
    assert len(notes['notes'].split()) < 120


def test_writer_limits_with_revision():
    llm = Mock(complete=Mock(return_value='report'))
    notes = [{'subtask': str(i), 'notes': 'x' * 5000,
              'sources': [{'url': f'https://example.com/{i}'}]} for i in range(3)]
    Writer(llm, LOGGER).run('task', notes, 'f' * 2000, previous_report='r' * 10000)
    system, prompt = llm.complete.call_args.args
    data = json.loads(prompt)
    assert '400 words' in system
    assert len(data['notes']) <= 2000
    assert len(data['revision_feedback']) <= 800
    assert data['previous_report'] == 'r' * 10000
    assert 'Return only the full revised report in markdown.' in system
    assert all(f'https://example.com/{i}' in data['notes'] for i in range(3))


def test_ollama_generation_options(monkeypatch):
    response = Mock()
    response.json.return_value = {'message': {'content': 'ok'}}
    post = Mock(return_value=response)
    monkeypatch.setattr('llm.httpx.post', post)
    LLM({'provider': 'ollama', 'model': 'test', 'max_model_calls': 1,
         'timeout_seconds': 60, 'num_ctx': 4096, 'num_predict': 700}, LOGGER).complete('s', 'p')
    assert post.call_args.kwargs['json']['options'] == {'num_ctx': 4096, 'num_predict': 700}
