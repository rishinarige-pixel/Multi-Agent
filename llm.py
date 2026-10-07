"""The only model transport. Every attempt counts toward the run budget."""
import os
import time
import httpx


class ModelError(RuntimeError):
    pass


class LLM:
    def __init__(self, config, logger):
        self.config, self.logger, self.calls = config, logger, 0

    def complete(self, system, prompt):
        for attempt in range(3):
            if self.calls >= self.config['max_model_calls']:
                raise ModelError('Total model-call limit reached.')
            self.calls += 1
            started = time.perf_counter()
            key = None
            try:
                messages = [{'role': 'system', 'content': system},
                            {'role': 'user', 'content': prompt}]
                provider = self.config['provider']
                if provider == 'openai':
                    key = os.getenv('OPENAI_API_KEY')
                    if not key:
                        raise ModelError('Set OPENAI_API_KEY in your environment or .env.')
                    url = 'https://api.openai.com/v1/chat/completions'
                    headers = {'Authorization': f'Bearer {key}'}
                else:
                    url, headers = 'http://localhost:11434/api/chat', {}
                payload = {'model': self.config['model'], 'messages': messages}
                if provider == 'ollama':
                    payload['stream'] = False
                response = httpx.post(url, headers=headers, json=payload,
                                      timeout=self.config['timeout_seconds'])
                response.raise_for_status()
                data = response.json()
                result = (data['choices'][0]['message']['content'] if provider == 'openai'
                          else data['message']['content'])
                if not isinstance(result, str) or not result.strip():
                    raise ValueError('Empty model response')
                return result
            except ModelError:
                raise
            except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
                if isinstance(exc, httpx.HTTPStatusError):
                    detail = f'HTTP {exc.response.status_code}: {exc.response.text}'
                else:
                    detail = f'{type(exc).__name__}: {exc}'
                if key:
                    detail = detail.replace(key, '[REDACTED]')
                message = f'Model call {self.calls} (attempt {attempt + 1}/3) failed: {detail}'
                print(f'[LLM] {message}', flush=True)
                self.logger.warning('%s', message)
                if attempt == 2:
                    raise ModelError(f'Model request failed after three attempts: {detail}') from exc
            finally:
                elapsed = time.perf_counter() - started
                message = f'Model call {self.calls} took {elapsed:.2f} seconds'
                print(f'[LLM] {message}', flush=True)
                self.logger.info('%s', message)
            time.sleep(2 ** attempt)
