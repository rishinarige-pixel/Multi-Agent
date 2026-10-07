import json
import logging
from unittest.mock import Mock
import pytest
from orchestrator import Orchestrator
from agents.planner import Planner
import main


def setup_web(monkeypatch):
    monkeypatch.setattr('tools.search.Search.run', lambda self, q: [
        {'title': 'Python', 'url': 'https://docs.python.org/3/', 'snippet': 'Python documentation'}])
    monkeypatch.setattr('tools.fetch.Fetch.run', lambda self, url: 'Python is a programming language.')


def responses(reviews):
    values = [json.dumps(['History', 'Features', 'Uses'])] + ['Notes https://docs.python.org/3/'] * 3
    for index, approved in enumerate(reviews):
        values += [f'# Python report {index}\nSource: https://docs.python.org/3/',
                   json.dumps({'approved': approved, 'feedback': '' if approved else 'Explain uses clearly.'})]
    return values


@pytest.mark.parametrize('reviews, calls', [([True], 6), ([False, True], 8), ([False]*3, 10)])
def test_revision_rounds(monkeypatch, reviews, calls):
    setup_web(monkeypatch)
    llm = Mock()
    llm.complete.side_effect = responses(reviews)
    report = Orchestrator(llm, logging.getLogger('test'), {'max_rounds': 2, 'search_results': 1}).run('Research Python')
    assert llm.complete.call_count == calls
    assert ('Unresolved review concerns' in report) == (not reviews[-1])


def test_invalid_plan():
    with pytest.raises(RuntimeError, match='Planner'):
        Planner(Mock(complete=Mock(return_value='["one"]')), logging.getLogger('test')).run('task')


def test_cli_writes_report_and_log(monkeypatch, tmp_path):
    setup_web(monkeypatch)
    (tmp_path / 'config.yaml').write_text((main.ROOT / 'config.yaml').read_text())
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    monkeypatch.setattr('sys.argv', ['main.py', 'Research Python and write a 1-page report'])
    llm = Mock()
    llm.complete.side_effect = responses([True])
    monkeypatch.setattr(main, 'LLM', lambda *args: llm)
    # pytest installs handlers; remove them temporarily so basicConfig exercises file logging.
    root_logger = logging.getLogger()
    old_handlers = root_logger.handlers[:]
    root_logger.handlers = []
    try:
        assert main.main() == 0
        reports = list((tmp_path / 'output').glob('report_*.md'))
        assert len(reports) == 1 and '# Python' in reports[0].read_text()
        log = next((tmp_path / 'logs').glob('run_*.log')).read_text()
        assert 'Planner input:' in log and 'Reviewer output:' in log
    finally:
        for handler in root_logger.handlers:
            handler.close()
        root_logger.handlers = old_handlers


def test_no_evidence(monkeypatch):
    monkeypatch.setattr('tools.search.Search.run', lambda *args: None)
    llm = Mock()
    llm.complete.side_effect = [json.dumps(['A', 'B', 'C']), '# Evidence unavailable',
                               '{"approved": true, "feedback": ""}']
    report = Orchestrator(llm, logging.getLogger('test'), {'max_rounds': 0, 'search_results': 1}).run('task')
    assert 'unavailable' in report and llm.complete.call_count == 3


def test_output_escape(monkeypatch, tmp_path):
    config = (main.ROOT / 'config.yaml').read_text().replace('output_folder: output', 'output_folder: ../escape')
    (tmp_path / 'config.yaml').write_text(config)
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='inside'):
        main.load_config()
