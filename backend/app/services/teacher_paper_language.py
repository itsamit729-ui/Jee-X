"""Versioned language mappings, resolved against this teacher's live bank.

IDs never belong in a mapping file: different installations import different IDs.
Typo suggestions require a reply; they must never widen a teacher's scope.
"""
import json
import re
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def mappings():
    return json.loads(Path(__file__).with_name('teacher_paper_mappings.json').read_text())


def phrase(value):
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


def normalize_terms(text):
    # One substitution pass prevents chained aliases (e.g. logical reasoning).
    aliases = {alias: canonical for canonical, values in mappings()['terms'].items() for alias in [canonical, *values]}
    pattern = r'(?<!\w)(?:' + '|'.join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)) + r')(?!\w)'
    return re.sub(pattern, lambda match: aliases[match[0]], text)


def chapter_aliases(chapters):
    result = {}
    for chapter in chapters:
        names = {phrase(chapter['name']), phrase(chapter.get('slug', ''))}
        for entry in mappings()['chapters']:
            if chapter['subject'] == entry['subject'] and chapter.get('slug') in entry['slugs']:
                names.update(phrase(alias) for alias in entry['aliases'])
        names.update(name[:-1] for name in list(names) if len(name) > 5 and name.endswith('s'))
        for name in names:
            if name: result.setdefault(name, []).append(chapter)
    return result


def scope_matches(text, chapters):
    """Longest non-overlapping aliases; ambiguous matches remain ambiguous."""
    aliases = chapter_aliases(chapters)
    matches, occupied = [], []
    for alias in sorted(aliases, key=len, reverse=True):
        # Permit punctuation between words without changing positions in text.
        pattern = r'\b' + r'[\W_]+'.join(re.escape(w) for w in alias.split()) + r'\b'
        for match in re.finditer(pattern, text):
            if any(match.start() < end and start < match.end() for start, end in occupied): continue
            occupied.append(match.span())
            matches.append((match.start(), match.end(), aliases[alias]))
    return sorted(matches)


def expand_chapter_aliases(text, chapters):
    from app.services.teacher_direct_request import SUBJECTS
    subjects = {code for code, pattern in SUBJECTS.items() if re.search(pattern, text)}
    for start, end, targets in reversed(scope_matches(text, chapters)):
        if subjects: targets = [target for target in targets if target['subject'] in subjects]
        ids = {target['id'] for target in targets}
        if len(ids) == 1:
            text = text[:start] + targets[0]['slug'].replace('-', ' ').replace('_', ' ') + text[end:]
    return text


def topic_question(text, chapters):
    """Resolve ambiguities before a provider can guess or discard a topic."""
    from app.services.teacher_direct_request import SUBJECTS
    subjects = {code for code, pattern in SUBJECTS.items() if re.search(pattern, text)}
    relevant = [c for c in chapters if not subjects or c['subject'] in subjects]
    for _, _, targets in scope_matches(text, relevant):
        if len({c['id'] for c in targets}) > 1:
            names = ', '.join(dict.fromkeys(c['name'] + ' (' + c['subject'] + ')' for c in targets))
            return f'Which chapter do you mean: {names}?'
    # Only suggest a typo in an explicit topic clause, not arbitrary prose.
    for match in re.finditer(r'\b(?:on|chapter[s]?|topic[s]?)\s+([a-z][a-z &-]{2,100})', text):
        candidate = re.split(r'\b(?:for|with|balanced|easy|hard|questions?|minutes|sets?)\b', match[1])[0].strip(' -')
        if not candidate or candidate in ('full syllabus', 'the full syllabus'): continue
        remaining = candidate
        for start, end, _ in reversed(scope_matches(candidate, relevant)):
            remaining = remaining[:start] + ' ' * (end-start) + remaining[end:]
        for pattern in SUBJECTS.values(): remaining = re.sub(pattern, ' ', remaining)
        remaining = re.sub(r'\b(?:the|and|only|chapter[s]?|topic[s]?|include|including|except|exclude|excluding|without|not|or)\b', ' ', remaining)
        remaining = phrase(remaining)
        if not remaining: continue
        aliases = chapter_aliases(relevant)
        close = get_close_matches(remaining, list(aliases), n=3, cutoff=.78)
        if close:
            names = list(dict.fromkeys(c['name'] for alias in close for c in aliases[alias]))
            return 'I could not match “' + candidate + '” exactly. Did you mean ' + ' or '.join(names) + '? Reply with the chapter name.'
        choices = ', '.join(dict.fromkeys(c['name'] for c in relevant[:6]))
        return f'I could not find “{remaining}” in the published chapter catalog for this exam. Please give a listed chapter name' + (f', such as {choices}.' if choices else ', or choose another exam.')
    return None
