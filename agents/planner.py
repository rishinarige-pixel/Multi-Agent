import json
from .base import Agent


class Planner(Agent):
    def run(self, task):
        result = self.ask('Break the task into 3–5 clear research subtasks. Return ONLY a JSON array of strings.', task)
        try:
            tasks = json.loads(result)
            if not isinstance(tasks, list) or not 3 <= len(tasks) <= 5 or any(
                    not isinstance(t, str) or not t.strip() for t in tasks):
                raise ValueError()
            return tasks
        except (ValueError, TypeError):
            raise RuntimeError('Planner returned invalid JSON; expected 3–5 nonempty subtask strings.')
