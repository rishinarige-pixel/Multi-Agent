import re
from agents.planner import Planner
from agents.writer import Writer
from agents.researcher import Researcher
from agents.reviewer import Reviewer


class Orchestrator:
    def __init__(self, llm, logger, config):
        self.llm, self.logger, self.config = llm, logger, config

    def run(self, task):
        subtasks = Planner(self.llm, self.logger).run(task)
        researcher = Researcher(self.llm, self.logger, self.config)
        notes = [researcher.run(subtask) for subtask in subtasks]
        writer = Writer(self.llm, self.logger)
        reviewer = Reviewer(self.llm, self.logger)
        report = writer.run(task, notes)
        for round_number in range(self.config['max_rounds'] + 1):
            review = reviewer.run(task, report, notes)
            if review['approved']:
                return self.validate_report(writer, task, notes, report)
            if round_number == self.config['max_rounds']:
                self.logger.warning('Revision limit reached: %s', review['feedback'][:1200])
                print('[Reviewer] revision limit reached; feedback retained in log.')
                return self.validate_report(writer, task, notes, report)
            report = writer.run(task, notes, review['feedback'], previous_report=report)

    def validate_report(self, writer, task, notes, report):
        """One bounded Writer repair, then fail before any report file is created."""
        for attempt in range(2):
            has_title = bool(re.search(r'^# +\S.*$', report, re.MULTILINE))
            words = len(report.split())
            if has_title and words >= 200:
                return report
            reason = f'Report needs a title heading (# Title) and at least 200 words; found title={has_title}, words={words}.'
            self.logger.warning('%s', reason)
            if attempt == 0:
                report = writer.run(task, notes, reason, previous_report=report)
        raise RuntimeError('Writer report failed validation after one retry. ' + reason + ' No report saved.')
