"""Recover source choices embedded in a question without changing the bank key."""
import re

MARKER = re.compile(r'^[ \t]*\(([A-D])\)[ \t]+', re.MULTILINE)


def presentation(stem, options):
    matches = list(MARKER.finditer(stem or ''))
    labels = [option.get('label') for option in options]
    embedded = {}
    if [match.group(1) for match in matches] == labels:
        embedded = {match.group(1): stem[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(stem)].strip() for i, match in enumerate(matches)}
        if not all(embedded.values()):
            embedded = {}
    output = []
    recovered = False
    for option in options:
        content = str(option.get('content')).strip() if option.get('content') is not None else ''
        placeholder = not content or re.sub(r'[().:\s]', '', content).upper() == option.get('label')
        if placeholder and option.get('label') in embedded:
            content = embedded[option.get('label')]
            recovered = True
        output.append({**option, 'content': content})
    prompt = stem[:matches[0].start()].strip() if recovered else stem
    # If every choice is a real literal letter, retain the original wording.
    return prompt, output
