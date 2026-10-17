"""Interpret common paper requests locally; preserve unfamiliar constraints for AI."""
import re

SUBJECTS = {'PHY': r'\bphysics\b', 'CHEM': r'\bchemistry\b', 'MATH': r'\bmathematics\b',
            'ENG': r'\benglish\b', 'LR': r'\blogical reasoning\b'}
SMALL = dict(zip('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(), range(20)))
TENS = dict(zip('twenty thirty forty fifty sixty seventy eighty ninety'.split(), range(20, 100, 10)))
UNIT = '(?:' + '|'.join(SMALL) + ')'
TEN = '(?:' + '|'.join(TENS) + ')'
NUMBER_WORDS = re.compile(r'\b(?:(?:one|two) hundred(?:[ -]+(?:and[ -]+)?(?:' + TEN + r'(?:[ -]+' + UNIT + r')?|' + UNIT + r'))?|' + TEN + r'(?:[ -]+' + UNIT + r')?|' + UNIT + r')\b')


def normalize(text):
    text = text.lower().replace('−', '-').replace('–', '-').replace('’', "'")
    def number(match):
        words = match.group().replace('-', ' ').split()
        value = 0
        for word in words:
            if word == 'hundred': value *= 100
            else: value += SMALL.get(word, TENS.get(word, 0))
        return str(value)
    text = NUMBER_WORDS.sub(number, text)
    text = re.sub(r'(?<=\d)(?=[a-z])', ' ', text)
    replacements = [(r'\b(?:phy|phys)\b', 'physics'), (r'\bchem\b', 'chemistry'),
                    (r'\b(?:math|maths|mth|mths)\b', 'mathematics'),
                    (r'\bpcm\b', 'physics chemistry mathematics'),
                    (r'\b(?:q|qns?|qs|ques)\b', 'questions'),
                    (r'\b(?:mins?|minutes?)\b', 'minutes'),
                    (r'\b(?:moderate|medium)\b', 'balanced'),
                    (r'\b(?:without|no)\s+(?:any\s+)?(?:negative|neg|-ve)(?:\s+(?:marking|marks))?\b', 'no negative marking'),
                    (r'\b(single|multi|multiple)-(correct|choice)\b', r'\1 \2'),
                    (r'\bmht[ -]*cet\b', 'mht cet'), (r'\bjee[ -]*mains?\b', 'jee main')]
    for pattern, value in replacements: text = re.sub(pattern, value, text)
    text = re.sub(r'\b(\d+)-(?=questions?|mcqs?)', r'\1 ', text)
    text = re.sub(r'\bhalf an hour\b', '30 minutes', text)
    text = re.sub(r'\b(?:a\s+)?couple\s+(?:of\s+)?questions\b', '2 questions', text)
    text = re.sub(r'\b(\d+)\s*(?:hours?|hrs?|h)\s*(?:and\s*)?(\d+)\s*minutes\b',
                  lambda m: f'{int(m[1])*60+int(m[2])} minutes', text)
    text = re.sub(r'\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b',
                  lambda m: f'{float(m[1])*60:g} minutes', text)
    return text


def teacher_turns(prompt):
    return [normalize(turn.split('\nassistant:', 1)[0].strip())
            for turn in re.split(r'(?:^|\n)teacher:\s*', prompt) if turn.strip()]


def unrelated(turn):
    return bool(re.fullmatch(r'(?:hi+|hello|hey|thanks|thank you|good morning|good evening)[!., ]*',turn)
                or re.search(r'\b(jokes?|weather|recipe|website|poem|essay|movie|song|translate)\b',turn)
                or (re.search(r'\b(explain|teach|solve|what is|why|who is|tell me about|how does)\b',turn)
                    and not re.search(r'\b(papers?|tests?|mocks?|questions?|mcqs?|omr)\b',turn)))


def direct_request(prompt, exam, catalog):
    from app.services.teacher_ai import AIPlan, AISection
    turns = teacher_turns(prompt)
    latest = turns[-1] if turns else ''
    # Unrelated turns never consume provider quota, including within an old request.
    if unrelated(latest): return AIPlan(intent='unrelated')
    turns = [turn for turn in turns if not unrelated(turn)]
    text = ' '.join(turns)
    chapters = catalog.get('chapters', [])
    has_paper = bool(re.search(r'\b(papers?|tests?|mocks?|questions?|mcqs?|omr)\b', text))
    has_subject = any(re.search(pattern, text) for pattern in SUBJECTS.values())
    has_exam = bool(exam or re.search(r'\b(mht cet|jee main|jee advanced|bitsat)\b', text))
    if not has_paper and not has_subject and not has_exam:
        return AIPlan(intent='unrelated')

    def ask(question):
        from fastapi import HTTPException
        raise HTTPException(422, question)

    # Keep unknown words: a known subject must never conceal an unknown topic.
    cleaned = text
    scope_ids, subjects, scope = [], [], False
    for turn in reversed(turns):
        explicit = [code for code, pattern in SUBJECTS.items() if re.search(pattern, turn)]
        found, other_subjects = [], set()
        for chapter in chapters:
            aliases = {chapter['name'].lower(), chapter.get('slug', '').replace('-', ' ').replace('_', ' ').lower()}
            if any(len(alias) >= 4 and re.search(r'\b' + re.escape(alias[:-1] if alias.endswith('s') else alias) + r's?\b', turn) for alias in aliases):
                if explicit and chapter['subject'] not in explicit: other_subjects.add(chapter['subject'])
                else: found.append(chapter)
        if other_subjects and not found:
            return ask('That chapter does not belong to the requested subject. Please choose the matching subject or a different chapter.')
        if found or explicit or re.search(r'\b(?:full|complete|entire) syllabus\b', turn):
            scope_ids = list(dict.fromkeys(c['id'] for c in found))
            subjects = explicit or sorted({c['subject'] for c in found})
            scope = True
            break
    for chapter in chapters:
        for alias in {chapter['name'].lower(), chapter.get('slug', '').replace('-', ' ').replace('_', ' ').lower()}:
            if len(alias) >= 4:
                cleaned = re.sub(r'\b' + re.escape(alias[:-1] if alias.endswith('s') else alias) + r's?\b', ' ', cleaned)

    # Subject quotas work without a model, including a total derived from "2 each".
    subject_pattern = '(?:physics|chemistry|mathematics|english|logical reasoning)'
    quota_pattern = r'\b(\d+)\s*(?:questions?\s+(?:in|from|of|for)\s+)?(' + subject_pattern + r')\b'
    quotas = {}
    for number, name in re.findall(quota_pattern, text):
        code = next(code for code, pattern in SUBJECTS.items() if re.search(pattern, name))
        quotas[code] = int(number)
    each = re.findall(r'\b(\d+)\s*(?:questions?\s*)?(?:each|per subject)\b', text)
    if each:
        if not subjects:
            subjects = ['PHY','CHEM','MATH','ENG','LR'] if exam=='bitsat' else ['PHY','CHEM','MATH'] if exam else []
        if subjects: quotas = {subject: int(each[-1]) for subject in subjects}; scope = True
    count_text = re.sub(quota_pattern, ' ', text)
    count_text = re.sub(r'\b\d+\s*(?:questions?\s*)?(?:each|per subject)\b', ' ', count_text)
    question_count = (r'\b(\d+)\s*(?:(?:balanced|easy|hard|challenging|foundation)\s+)?'
                      r'(?:(?:jee[ -]*(?:main|advanced)|mht cet|bitsat)(?:[ -]*level)?\s*)?'
                      r'(?:(?:physics|chemistry|mathematics|english|logical reasoning|and|,)\s+)*'
                      r'(?:questions?|mcqs?)\b')
    counts = re.findall(question_count+r'|\b(?:question count|questions|count)\s*[:=]\s*(\d+)\b', count_text)
    counts = [a or b for a, b in counts]
    if re.search(r'(?<!\w)-\s*'+question_count, text) or re.search(question_count.replace(r'(\d+)',r'\d+\.\d+'),text):
        return ask('Use a whole number between 1 and 200 for the question count.')
    count = int(counts[-1]) if counts else sum(quotas.values()) if quotas else None
    durations = re.findall(r'\b(\d+(?:\.\d+)?)\s*minutes\b', text)
    latest_durations = re.findall(r'\b(\d+(?:\.\d+)?)\s*minutes\b', latest)
    if len(set(latest_durations)) > 1: return ask('You gave more than one duration. How many minutes should the paper last?')
    duration_value = float(durations[-1]) if durations else None
    if duration_value is not None and duration_value != int(duration_value):
        return ask('Please use a whole number of minutes for the duration.')
    duration = int(duration_value) if duration_value is not None else None
    # Only infer a bare number when the preceding question asks for one field.
    replies = re.findall(r'\nassistant:([^\n]+)\nteacher:\s*([^\n]+)', prompt, re.I)
    if replies and re.fullmatch(r'\d+[.! ]*', latest):
        previous = replies[-1][0].lower()
        asks_count = bool(re.search(r'how many|number of questions|question count', previous))
        asks_time = bool(re.search(r'duration|minutes|how long', previous))
        if asks_count and not asks_time: count = int(re.search(r'\d+', latest)[0])
        elif asks_time and not asks_count: duration = int(re.search(r'\d+', latest)[0])
        else: return ask('Does that number mean questions or minutes? Please include the unit, for example “2 questions, 10 minutes”.')
    if count is not None and not 1 <= count <= 200: return ask('Choose between 1 and 200 questions.')
    if duration is not None and not 1 <= duration <= 240: return ask('Choose a duration between 1 and 240 minutes.')
    if quotas and count != sum(quotas.values()): return ask('The subject counts do not add up to the total. Please give the total and the count for each subject.')
    if any(not 1 <= value <= 200 for value in quotas.values()): return ask('Each requested subject needs between 1 and 200 questions.')
    if count and subjects and len(subjects) > count: return ask(f'A {count}-question paper cannot include all {len(subjects)} subjects. Choose fewer subjects or increase the question count.')

    levels = re.findall(r'\b(easy|foundation|balanced|hard|challenging)\b', text)
    level = {'foundation': 'easy', 'challenging': 'hard'}.get(levels[-1], levels[-1]) if levels else 'balanced'
    marking = r'\b(?:award\s+)?(\d+)\s*marks?(?:\s*(?:per|for\s+(?:each|every))\s*correct\s*answer)?'
    if re.search(r'\b\d+\.\d+\s*marks?|\+\d+\.\d+', text):
        return ask('This builder uses whole-number marks. Please specify a whole-number score and deduction.')
    ambiguous_marking = bool(re.search(r'-\s*\d+\s*marks?\b', text))
    correct_matches = list(re.finditer(marking, text))
    pair_matches = list(re.finditer(r'\+(\d+)\s*(?:/|,)\s*-(\d+)\b', text))
    pair = [match.groups() for match in pair_matches]
    ambiguous_marking |= 'negative' in text and 'no negative marking' not in text and not pair
    wrong_values = [(match.start(),0) for match in re.finditer(r'\bno negative marking\b',text)] + [(match.start(),int(match[2])) for match in pair_matches]
    correct_values = [(match.start(),int(match[1])) for match in correct_matches + pair_matches]
    wrong = max(wrong_values)[1] if wrong_values else None
    correct = max(correct_values)[1] if correct_values else None
    if correct is not None and not 1 <= correct <= 10: return ask('Correct answers can carry 1–10 marks. Which value should I use?')
    if wrong is not None and not 0 <= wrong <= 10: return ask('The deduction per incorrect answer must be 0–10 marks.')
    set_counts = [int(n) for n in re.findall(r'\b(\d+)\s*(?:shuffled?\s*)?sets?\b', text)]
    if any(n not in (1, 2) for n in set_counts): return ask('I can prepare one paper or two shuffled sets, A and B. Which do you want?')
    sets = set_counts[-1] == 2 if set_counts else True if re.search(r'\bsets?\s*(?:a|1)\s*(?:and|/|&)\s*(?:set\s*)?(?:b|2)\b', text) else False if re.search(r'\bsingle\s+set\b', text) else None
    if re.search(r'\b(single set|single paper|no sets|only 1 paper)\b',latest): sets=False
    if sets is None and re.search(r'\bsets?\b',text): return ask('Would you like a single paper or two shuffled sets, A and B?')
    types = re.findall(r'\b(single correct|multiple choice|mcqs?|numerical|multi correct|multiple correct)\b', text)
    kinds = {'single correct': 'single_correct', 'multiple choice': 'single_correct', 'mcq': 'single_correct', 'mcqs': 'single_correct', 'numerical': 'numerical', 'multi correct': 'multi_correct', 'multiple correct': 'multi_correct'}
    question_types = {kinds[k] for k in types}
    question_type = next(iter(question_types)) if len(question_types) == 1 else None
    if question_type and count and not subjects:
        subjects = sorted({c['subject'] for c in chapters})[:count]
    sections = []
    if count and subjects:
        sections = [AISection(subject=s, count=quotas.get(s, count // len(subjects) + (i < count % len(subjects))),
                    chapter_ids=[c['id'] for c in chapters if c['id'] in scope_ids and c['subject'] == s], type=question_type)
                    for i, s in enumerate(subjects)]
    plan = AIPlan(intent='paper', scope_specified=scope, count=count, duration_minutes=duration,
                  chapter_ids=scope_ids, sections=sections, level=level, marks_correct=correct, marks_wrong=wrong, sets_enabled=sets)

    # Remove only grammar we can represent; unfamiliar requirements still need AI.
    cleaned = re.sub(marking, ' ', cleaned)
    cleaned = re.sub(r'\+\d+\s*(?:/|,)\s*-\d+\b', ' ', cleaned)
    for pattern in SUBJECTS.values(): cleaned = re.sub(pattern, ' ', cleaned)
    cleaned = re.sub(r'\bmht cet\b|\bbitsat\b|\bjee[ -]*(?:main|adv(?:anced)?)\b', ' ', cleaned)
    filler = set("create generate make build prepare give want need i i'd would like can could you me my us an a b the level pattern paper papers test tests mock mocks with using exam questions question count q mcq mcqs on from of and balanced difficulty easy foundation hard challenging minutes time duration for within shuffled shuffle sets set standard award per correct answer answers no negative marking matching omr pdf pdfs both download downloads please pls full complete entire syllabus in actually change to use now it at about based chapter chapters topic topics covering include including each subject only single multiple choice numerical multi just as well thanks thank let's lets we our there should be have has this that is are total all do questionpaper questionpapers also then ready together same yes ok okay bank available published quick short small practice quiz .".split())
    words = re.findall(r'[a-z]+', cleaned)
    unknown = [word for word in words if word not in filler]
    relational = bool(re.search(r'\b(except|exclude|excluding|without|avoid|not|or|respectively|shift|year|similar|original|previous|taught|unseen|title|named|called|percent|ratio)\b|\bno\s+(?!negative marking\b|sets?\b)|%|\b20\d{2}\b', text))
    ambiguous = ambiguous_marking or len(question_types) > 1 or len(set(re.findall(r'\b(easy|foundation|balanced|hard|challenging)\b', latest))) > 1
    if unknown or relational or ambiguous:
        # Follow-ups for missing basics are local even when the eventual request
        # contains a complex constraint. The full conversation is kept for later.
        if catalog.get('paper_defaults', {}).get('require_details') and (not exam or count is None or not scope or duration is None):
            plan.intent = 'needs_details'
            return plan
        return None
    return plan
