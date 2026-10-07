import time


class Tool:
    """Read-only tools expose run(value); failures return None after retries."""
    def __init__(self, logger):
        self.logger = logger

    def run(self, value):
        name = type(self).__name__
        self.logger.info('%s input: %s', name, str(value)[:500])
        for attempt in range(3):
            try:
                result = self.execute(value)
                self.logger.info('%s output: %s', name, str(result)[:1200])
                return result
            except Exception as exc:
                self.logger.warning('%s attempt %s failed (%s)', name, attempt + 1, type(exc).__name__)
                if attempt < 2:
                    time.sleep(2 ** attempt)
        return None
