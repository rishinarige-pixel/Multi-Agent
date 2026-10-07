import json
import logging
from unittest.mock import Mock
import pytest
import main
from agents.reviewer import Reviewer
from agents.writer import Writer
from orchestrator import Orchestrator
from test_orchestrator import setup_web, write_config, responses

VALID = '# Final title\n\n' + 'Evidence ' * 200


@pytest.mark.parametrize('invalid', ['Actionable corrections: Add sources.',
                                     'No heading ' + 'word ' * 210,
                                     '# Too short\nOnly a few words.'])
def test_validation_repairs_once(invalid):
    writer = Mock()
    writer.run.return_value = VALID
    orchestrator = Orchestrator(None, logging.getLogger('test'), {})
    assert orchestrator.validate_report(writer, 'task', [], invalid) == VALID
    assert writer.run.call_count == 1
    assert writer.run.call_args.kwargs['previous_report'] == invalid


def test_valid_draft_needs_no_retry():
    writer = Mock()
    assert Orchestrator(None, logging.getLogger('test'), {}).validate_report(writer, 'task', [], VALID) == VALID
    writer.run.assert_not_called()


def test_bad_cli_report_never_saved(monkeypatch, tmp_path, capsys):
    setup_web(monkeypatch)
    write_config(tmp_path, max_rounds=0)
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    monkeypatch.setattr('sys.argv', ['main.py', 'task'])
    llm = Mock()
    llm.complete.side_effect = [json.dumps(['A', 'B', 'C'])] + ['notes'] * 3 + [
        'Actionable corrections: cite sources', 'APPROVED', '# Still short']
    monkeypatch.setattr(main, 'LLM', lambda *args: llm)
    assert main.main() == 1
    assert 'failed validation after one retry' in capsys.readouterr().err
    assert not list(tmp_path.glob('output/**/*.md'))
    assert llm.complete.call_count == 7


def test_final_saved_file_is_latest_writer_not_feedback(monkeypatch, tmp_path, caplog, capsys):
    setup_web(monkeypatch)
    write_config(tmp_path)
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    monkeypatch.setattr('sys.argv', ['main.py', 'task'])
    llm = Mock()
    llm.complete.side_effect = responses([False, False, False])
    monkeypatch.setattr(main, 'LLM', lambda *args: llm)
    with caplog.at_level(logging.INFO):
        assert main.main() == 0
    report = next((tmp_path / 'output').glob('*.md')).read_text()
    assert report.startswith('# Python report 2')
    assert 'Explain uses clearly.' not in report
    assert 'Explain uses clearly.' in caplog.text
    assert 'Explain uses clearly.' not in capsys.readouterr().out


def test_reviewer_explicit_verdict_and_strict_retry():
    llm = Mock()
    llm.complete.side_effect = ['APPROVED-ish', 'REVISE\nActionable corrections: add a source.']
    review = Reviewer(llm, logging.getLogger('test')).run('task', VALID, [])
    assert not review['approved']
    assert review['feedback'] == 'Actionable corrections: add a source.'
    assert llm.complete.call_count == 2


def test_revision_prompt_keeps_full_draft_and_feedback():
    llm = Mock(complete=Mock(return_value=VALID))
    previous = VALID + 'More evidence ' * 400
    Writer(llm, logging.getLogger('test')).run('task', [], 'Add a source.', previous_report=previous)
    system, prompt = llm.complete.call_args.args
    data = json.loads(prompt)
    assert data['previous_report'] == previous
    assert data['revision_feedback'] == 'Add a source.'
    assert 'Return only the full revised report in markdown.' in system
