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
                return report
            if round_number == self.config['max_rounds']:
                self.logger.warning('Revision limit reached: %s', review['feedback'][:1200])
                print('[Reviewer] revision limit reached; remaining concerns included in report.')
                return report + '\n\n## Unresolved review concerns\n\n' + review['feedback']
            report = writer.run(task, notes, review['feedback'], previous_report=report)
