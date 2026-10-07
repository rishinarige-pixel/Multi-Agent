class Agent:
    def __init__(self, llm, logger):
        self.llm, self.logger = llm, logger

    def ask(self, system, prompt):
        name = type(self).__name__
        print(f'[{name}] working…', flush=True)
        self.logger.info('%s input: %s', name, prompt[:1200])
        result = self.llm.complete(system, prompt)
        self.logger.info('%s output: %s', name, result[:1200])
        return result
