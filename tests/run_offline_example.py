"""Deterministic full CLI demo; no network, no credentials, no claimed research."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class DemoLLM:
    def complete(self, system, prompt):
        if 'Break the task' in system:
            return json.dumps(['Define Python', 'Explain typical uses', 'Describe limitations'])
        if 'Return notes under 120 words' in system:
            return 'Fixture evidence: Python is a programming language. Source: https://docs.python.org/3/'
        if 'Review the report' in system:
            return 'APPROVED\nThis is explicitly labeled fixture evidence.'
        return ('# Python: offline demonstration\n\n'
                'This report demonstrates the complete agent pipeline using mocked model and web responses; '
                'it is not a live research result.\n\n'
                'Python is a programming language according to the supplied test fixture. '
                '[Source](https://docs.python.org/3/)\n\n'
                'The fixture provides no evidence about history, performance, or specific uses, '
                'so this demonstration makes no claims about those topics.\n' +
                ('This offline demonstration tests message passing, logging, and report saving with '
                 'controlled fixtures. It does not establish any additional real world facts or '
                 'replace a live research run with working web access and a configured model. '
                 'Readers should consult the linked documentation before relying on a factual claim. '
                 'The agents receive only test data and all conclusions remain limited by that evidence. '
                 'The workflow illustrates how planning, research notes, drafting, and review connect '
                 'through the orchestrator while preserving the Writer draft separately from feedback. ') * 2)


if __name__ == '__main__':
    sys.argv = ['main.py', 'Research Python and write a 1-page report']
    with patch.object(main, 'LLM', lambda *args: DemoLLM()), \
         patch('tools.search.Search.execute', return_value=[{
             'title': 'Python documentation', 'url': 'https://docs.python.org/3/',
             'snippet': 'Python is a programming language.'}]), \
         patch('tools.fetch.Fetch.execute', return_value='Python is a programming language.'):
        raise SystemExit(main.main())
