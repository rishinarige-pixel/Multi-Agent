import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
import yaml
from dotenv import load_dotenv
from llm import LLM
from orchestrator import Orchestrator

ROOT = Path(__file__).resolve().parent


def load_config():
    config = yaml.safe_load((ROOT / 'config.yaml').read_text())
    if config['provider'] not in ('openai', 'ollama'):
        raise ValueError('provider must be openai or ollama')
    for key, minimum, maximum in [('max_rounds', 0, 2), ('max_model_calls', 1, 100),
                                  ('search_results', 1, 5), ('timeout_seconds', 1, 1800)]:
        if type(config[key]) is not int or not minimum <= config[key] <= maximum:
            raise ValueError(f'Invalid {key}: expected {minimum}–{maximum}')
    for key, default, maximum in [('num_ctx', 4096, 4096), ('num_predict', 700, 2048)]:
        value = config.get(key, default)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError(f'Invalid {key}: expected 1–{maximum}')
    if not isinstance(config['model'], str) or not config['model'].strip():
        raise ValueError('model must be a nonempty string')
    output = (ROOT / config['output_folder']).resolve()
    if not output.is_relative_to(ROOT / 'output'):
        raise ValueError('output_folder must be inside ./output')
    return config, output


def main():
    parser = argparse.ArgumentParser(description='Collaborative research and Markdown reports')
    parser.add_argument('task')
    args = parser.parse_args()
    logger = logging.getLogger('multi_agent')
    try:
        load_dotenv(ROOT / '.env')
        config, output = load_config()
        logs = ROOT / 'logs'
        if logs.is_symlink():
            raise ValueError('logs must not be a symlink')
        logs.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
        logging.basicConfig(filename=logs / f'run_{stamp}.log', level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s')
        report = Orchestrator(LLM(config, logger), logger, config).run(args.task)
        output.mkdir(parents=True, exist_ok=True)
        path = output / f'report_{stamp}.md'
        with path.open('x', encoding='utf-8') as handle:
            handle.write(report)
        print(f'Report saved: {path}')
        return 0
    except (RuntimeError, ValueError, OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        logger.error('%s', exc)
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
