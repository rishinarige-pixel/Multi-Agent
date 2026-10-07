from .base import Agent
from .json_utils import extract_json, plan_lines


class Planner(Agent):
    def run(self, task):
        prompt = 'Break the task into exactly 3 clear research subtasks. Return ONLY a JSON array of three strings.'
        result = self.ask(prompt, task)
        for attempt in range(2):
            try:
                tasks = extract_json(result, list)
                if len(tasks) < 3 or any(not isinstance(t, str) or not t.strip() for t in tasks):
                    raise ValueError()
                return [t.strip()[:300] for t in tasks[:3]]
            except (ValueError, TypeError):
                if attempt == 0:
                    result = self.ask('Return exactly ["subtask one", "subtask two", "subtask three"] '
                                      'as valid JSON, replacing examples with relevant subtasks. No prose or fences.', task)
        try:
            return [t[:300] for t in plan_lines(result)]
        except ValueError as exc:
            raise RuntimeError('Planner could not produce three valid subtasks after JSON retry and line fallback.') from exc
