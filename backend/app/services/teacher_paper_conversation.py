"""Reduce one teacher reply into bounded, explicit request fields.

This is untrusted request data, not a saved/authorized plan. ai_draft always
resolves it against the current published bank and validates the final plan.
No IDs, question content, or permissions are accepted from conversation state.
"""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from app.services.teacher_direct_request import normalize, unrelated, SUBJECTS, REQUEST_GRAMMAR
from app.services.teacher_paper_language import scope_matches

Slot = Literal['exam', 'count', 'quotas', 'scope', 'duration', 'difficulty', 'correct_marks', 'wrong_marks', 'sets', 'type', 'source', 'reference', 'title']


class PaperConversation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: Literal[1] = 1
    slots: dict[Slot, str] = Field(default_factory=dict, max_length=14)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    question: str = Field('', max_length=2000)

    @field_validator('slots', 'constraints')
    @classmethod
    def bounded_text(cls, values):
        texts = values.values() if isinstance(values, dict) else values
        if any(len(value) > 1800 or '\n' in value for value in texts):
            raise ValueError('Conversation fields must be single-line text of at most 1800 characters.')
        return values

    def canonical(self):
        return ', '.join([self.slots[key] for key in Slot.__args__ if self.slots.get(key)] + self.constraints)


def advance(previous, reply, chapters):
    state = previous.model_copy(deep=True)
    text = re.sub(r'\s+', ' ', normalize(reply.strip()))
    if unrelated(text): return state, text
    if re.fullmatch(r'\d+[.! ]*', text):
        question = state.question.lower()
        count = bool(re.search(r'how many|number of questions|question count', question))
        duration = bool(re.search(r'duration|minutes|how long', question))
        if count != duration:
            text = re.search(r'\d+', text)[0] + (' questions' if count else ' minutes')
        else:
            state.question = 'Does that number mean questions or minutes? Include the unit, for example “2 questions, 10 minutes”.'
            return state, None

    consumed = set()
    def consume(start, end): consumed.update(range(start, end))
    def extract(slot, pattern):
        matches = list(re.finditer(pattern, text))
        if not matches: return False
        # Keep contradictions within a reply visible to validation. Across replies
        # replace just this field, including invalid earlier values.
        state.slots[slot] = ' '.join(match[0] for match in matches)
        for match in matches: consume(*match.span())
        return True

    scope_spans = [(a, b) for a, b, _ in scope_matches(text, chapters)]
    has_chapter = bool(scope_spans)
    scope_spans += [match.span() for pattern in SUBJECTS.values() for match in re.finditer(pattern, text)]
    scope_spans += [match.span() for match in re.finditer(r'\b(?:full|complete|entire) syllabus\b', text)]
    extract('exam', r'\b(?:jee[ -]*(?:main|advanced)|mht cet|bitsat|neet|upsc)\b')
    extract('duration', r'(?<!\w)-?\d+(?:\.\d+)?\s*minutes\b')
    extract('difficulty', r'\b(?:(?:not|avoid|without)\s+)?(?:easy|balanced|hard)\b')
    # Separate positive/negative values so an updated duration or score cannot
    # erase an earlier explicit no-negative-marking instruction.
    pairs = list(re.finditer(r'\+(\d+)\s*(?:/|,)\s*-(\d+)\b', text))
    for match in pairs:
        state.slots['correct_marks'] = match[1] + ' marks'
        state.slots['wrong_marks'] = 'no negative marking' if match[2] == '0' else 'deduct %s for incorrect answers' % match[2]
        consume(*match.span())
    if not pairs:
        extract('correct_marks', r'\b\d+(?:\.\d+)?\s*marks?(?:\s*(?:per|for\s+(?:each|every))\s*correct\s*answer)?')
    extract('wrong_marks', r'\bno negative marking\b')
    extract('sets', r'\b(?:\d+\s*(?:shuffled?\s*)?sets?|single set|single paper|no sets|only 1 paper|sets?\s*a\s*(?:and|/|&)\s*(?:set\s*)?b)\b')
    extract('type', r'\b(?:(?:no|not|without|exclude|excluding|avoid)\s+)?(?:single correct|multiple choice|mcqs?|numerical|multi correct|multiple correct)\b')
    # Preserve these as independent fields too, so a later correction replaces
    # its earlier reference/title/source rather than accumulating both.
    extract('source', r'\b(?:pyqs?|previous year questions|original questions|all sources)\b')
    extract('reference', r'\b(?:from|similar to|exact|entire|original)\s+(?:the\s+)?(?:20\d{2}(?:[-/]\d{1,2}){0,2}(?:\s*(?:[- ]?shift[- ]?\d+))?(?:\s+paper)?|(?:original\s+)?paper)\b')
    extract('title', r'\b(?:title|named|called)\s+[^,;.]+')

    subject_pattern = '(?:physics|chemistry|mathematics|english|logical reasoning)'
    quotas = list(re.finditer(r'\b\d+\s*(?:questions?\s+(?:in|from|of|for)\s+)?' + subject_pattern + r'\b|\b\d+\s*(?:questions?\s*)?(?:each|per subject)\b', text))
    count_matches = list(re.finditer(r'(?<!\w)-?\d+(?:\.\d+)?\s*(?:(?:balanced|easy|hard)\s+)?(?:(?:jee[ -]*(?:main|advanced)|mht cet|bitsat)\s+)?(?:(?:' + subject_pattern + r'|and|,)\s+)*(?:questions?|mcqs?|pyqs?|previous year questions?)\b|\b(?:question count|questions|count)\s*[:=]\s*\d+\b', text))
    totals = [match for match in count_matches if not any(q.start() <= match.start() < q.end() for q in quotas)]
    # "2 Physics questions" is one subject quota and also defines the total.
    if quotas:
        state.slots['quotas'] = ', '.join(match[0] for match in quotas)
        for match in quotas: consume(*match.span())
        if not totals: state.slots.pop('count', None)
    if totals:
        value = re.search(r'-?\d+(?:\.\d+)?', totals[-1][0])[0]
        state.slots['count'] = value + ' questions'
    for match in count_matches: consume(*match.span())

    # Topic clauses preserve unknown names as scope. Correcting the topic then
    # replaces that field instead of leaving the misspelling in old history.
    masked = ''.join(' ' if i in consumed else char for i, char in enumerate(text))
    for match in re.finditer(r'\b(?:on|chapters?|topics?|covering)\s+([^,;.]+)', masked):
        if re.search(r'[a-z]', match[1]): scope_spans.append(match.span())
    if scope_spans:
        if not quotas: state.slots.pop('quotas', None)
        # Retain scope relationships; exclusions must reach the planner intact.
        start, end = min(a for a, _ in scope_spans), max(b for _, b in scope_spans)
        prefix = re.search(r'\b(?:no|not|except|without|exclude|excluding|avoid)\s*$', text[:start])
        if prefix: start = prefix.start(); scope_spans.append((start, end))
        scope = ''.join(' ' if i in consumed and not any(a <= i < b for a,b in scope_spans) else char for i,char in enumerate(text))[start:end]
        if state.question.startswith('Which chapter do you mean:') and not has_chapter and previous.slots.get('scope'):
            scope = scope + ' ' + previous.slots['scope']
        state.slots['scope'] = re.sub(r'\s+', ' ', scope).strip()
        for a, b in scope_spans: consume(a, b)
        for match in re.finditer(r'\b(?:exclude|excluding|except|without|avoid|not|or)\b', text[start:end]):
            consume(start + match.start(), start + match.end())

    # Never silently discard unfamiliar constraints, names, fractions or units.
    residue = ''.join(' ' if i in consumed else char for i,char in enumerate(text))
    tokens = re.findall(r'[a-z]+|\d+(?:\.\d+)?|[%+/-]', residue)
    if any(token not in REQUEST_GRAMMAR for token in tokens):
        residue = residue.strip(' ,;.')
        if residue and residue not in state.constraints:
            if len(state.constraints) >= 20:
                from fastapi import HTTPException
                raise HTTPException(422, 'There are too many unresolved requirements. Start a new request with the complete paper requirements.')
            state.constraints.append(residue)
    # Bound even server-produced state before returning it to the browser.
    try:
        state = PaperConversation.model_validate(state.model_dump())
    except ValidationError:
        from fastapi import HTTPException
        raise HTTPException(422, 'A requirement is too long. Please shorten it or start a new request.') from None
    canonical = state.canonical()
    if len(canonical) > 6000:
        from fastapi import HTTPException
        raise HTTPException(422, 'This request is too long. Start a new request with the complete paper requirements.')
    return state, canonical or text
