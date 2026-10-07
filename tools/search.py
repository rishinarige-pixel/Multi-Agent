from ddgs import DDGS
from .base import Tool


class Search(Tool):
    def __init__(self, logger, limit=3):
        super().__init__(logger)
        self.limit = min(limit, 2)

    def execute(self, query):
        results = DDGS(timeout=20).text(query, max_results=self.limit, backend='duckduckgo')
        return [{'title': r['title'], 'url': r['href'], 'snippet': r['body']}
                for r in results][:self.limit]
