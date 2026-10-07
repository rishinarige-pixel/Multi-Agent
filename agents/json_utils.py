"""Decode fenced/prose-wrapped JSON and conservative line fallbacks."""
import json
import re


def extract_json(text, expected):
    decoder = json.JSONDecoder()
    opener = '[' if expected is list else '{'
    for index, char in enumerate(text):
        if char == opener:
            try:
                value, _ = decoder.raw_decode(text[index:])
                if isinstance(value, expected):
                    return value
            except ValueError:
                pass
    raise ValueError('No JSON value found')


def plan_lines(text):
    lines = []
    for line in text.splitlines():
        match = re.match(r'^\s*(?:[-*•]|\d+[.)])\s+(.+)', line)
        if match:
            lines.append(match.group(1).strip())
    if not lines:
        lines = [line.strip() for line in text.splitlines()
                 if line.strip() and not line.strip().startswith('```')]
    if len(lines) < 3:
        raise ValueError('Need three subtask lines')
    return lines[:3]


def review_lines(text):
    # Never infer approval from free-form prose or a malformed review.
    feedback = '\n'.join(line.strip() for line in text.splitlines()
                         if line.strip() and not line.strip().startswith('```'))
    if not feedback:
        raise ValueError('Empty review')
    return {'approved': False, 'feedback': 'Review could not be parsed; address these comments: ' + feedback[:800]}
