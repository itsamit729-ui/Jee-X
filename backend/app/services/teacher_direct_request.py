"""Conservative parsing for clear paper requests; unfamiliar constraints go to AI."""
import re

SUBJECTS={'PHY':r'\bphysics\b','CHEM':r'\bchemistry\b','MATH':r'\bmath(?:ematics|s)?\b','ENG':r'\benglish\b','LR':r'\blogical reasoning\b'}


def direct_request(prompt, exam, catalog):
    from app.services.teacher_ai import AIPlan, AISection
    turns=[t.split('\nassistant:',1)[0].strip().lower() for t in re.split(r'(?:^|\n)teacher:\s*',prompt) if t.strip()]
    text=' '.join(turns)
    if not re.search(r'\b(create|generate|make|build|prepare|want|need)\b',text) or not re.search(r'\b(paper|test|mock|questions?|mcqs?|omr)\b',text):return None
    # These require relational/semantic interpretation; never silently drop them.
    if re.search(r'\b(except|exclude|excluding|without|avoid|not|only|or|each|respectively|shift|year|similar|original|previous|numerical|integer|multiple|taught|unseen|title|named|called|percent|ratio|hours?)\b|%|\b20\d{2}\b|per subject',text):return None
    chapters=catalog.get('chapters',[])
    scope_ids=[];subjects=[];scope=False
    # The latest scope clarification replaces the earlier scope.
    for turn in reversed(turns):
        found=[]
        for chapter in chapters:
            aliases={chapter['name'].lower(),chapter.get('slug','').replace('-',' ').replace('_',' ').lower()}
            for alias in aliases:
                if len(alias)<4:continue
                pattern=r'\b'+re.escape(alias)+r's?\b'
                if alias.endswith('s'):pattern=r'\b'+re.escape(alias[:-1])+r's?\b'
                if re.search(pattern,turn):found.append(chapter);break
        sub=[code for code,pattern in SUBJECTS.items() if re.search(pattern,turn)]
        if found or sub or re.search(r'\bfull syllabus\b',turn):
            scope_ids=list(dict.fromkeys(c['id'] for c in found));subjects=sub or sorted({c['subject'] for c in found});scope=True;break
    # A known chapter in an old turn is still a recognised word after a correction.
    cleaned=text
    for chapter in chapters:
        for alias in {chapter['name'].lower(),chapter.get('slug','').replace('-',' ').replace('_',' ').lower()}:
            if len(alias)>=4:cleaned=re.sub(r'\b'+re.escape(alias.rstrip('s'))+r's?\b',' ',cleaned)
    for pattern in SUBJECTS.values():cleaned=re.sub(pattern,' ',cleaned)
    cleaned=re.sub(r'\bmht[\s-]*cet\b|\bbitsat\b|\bjee[\s-]*(?:mains?|adv(?:anced)?)\b',' ',cleaned)
    # A small grammar makes this path deliberately conservative. Unknown topic
    # names or constraints fall through to AI instead of being ignored.
    allowed=set('create generate make build prepare want need i an a b the level paper papers test mock with questions question mcq mcqs on from of and or balanced difficulty easy foundation hard challenging minutes minute min mins for two 2 one 1 single shuffled shuffle sets set standard award mark marks per correct answer answers no negative marking give me matching omr pdf pdfs both download downloads please full syllabus in actually change to use now it at'.split())
    if any(word not in allowed and not word.isdigit() for word in re.findall(r'[a-z]+|\d+',cleaned)):return None
    # Subject quotas and format counts are left to the AI path above.
    counts=re.findall(r'\b(\d+)\s*(?:questions?|mcqs?)\b',text)
    durations=re.findall(r'\b(\d+)\s*min(?:ute)?s?\b',text)
    if len(set(re.findall(r'\b(\d+)\s*(?:questions?|mcqs?)\b',turns[-1])))>1:return None
    count=int(counts[-1]) if counts else None
    duration=int(durations[-1]) if durations else None
    # A bare answer belongs only to the field the preceding follow-up asked for.
    followup=re.search(r'\nassistant:([^\n]+)\nteacher:\s*(\d+)\s*$',prompt,re.I)
    if followup:
        question=followup.group(1).lower()
        asks_count=bool(re.search(r'how many|number of questions|question count',question))
        asks_duration=bool(re.search(r'duration|minutes|how long',question))
        if asks_count and not asks_duration:count=int(followup.group(2))
        elif asks_duration and not asks_count:duration=int(followup.group(2))
        else:return None
    if count is not None and not 1<=count<=200:return AIPlan(intent='needs_details',clarification='Choose between 1 and 200 questions.')
    if duration is not None and not 1<=duration<=240:return AIPlan(intent='needs_details',clarification='Choose a duration between 1 and 240 minutes.')
    levels=re.findall(r'\b(easy|foundation|balanced|hard|challenging)\b',text)
    if len(set(re.findall(r'\b(easy|foundation|balanced|hard|challenging)\b',turns[-1])))>1:return None
    level={'foundation':'easy','challenging':'hard'}.get(levels[-1],levels[-1]) if levels else 'balanced'
    marking=r'\b(?:award\s+)?(\d+)\s*marks?\s*(?:per|for\s+(?:each|every))\s*correct\s*answer'
    corrects=re.findall(marking,text)
    wrong=0 if re.search(r'\bno negative marking\b',text) else None
    # Other marking expressions must not be discarded.
    if 'negative' in text and wrong is None:return None
    correct=int(corrects[-1]) if corrects else None
    other_marking=re.sub(marking,' ',text)
    other_marking=re.sub(r'\bno negative marking\b',' ',other_marking)
    if re.search(r'\bmarks?|marking\b',other_marking):return None
    if correct is not None and not 1<=correct<=10:return None
    if any(int(n) not in (1,2) for n in re.findall(r'\b(\d+)\s+(?:shuffled\s+)?sets?\b',text)):return None
    sets=True if re.search(r'\b(?:two|2)\s+(?:shuffled\s+)?sets?\b|\bsets? a and b\b',text) else None
    if sets is None and re.search(r'\bsets?\b',text):
        if re.search(r'\b(?:one|1|single)\s+set\b',text):sets=False
        else:return None
    sections=[]
    if count and subjects:
        if len(subjects)>count:return None
        sections=[AISection(subject=s,count=count//len(subjects)+(i<count%len(subjects)),
                   chapter_ids=[c['id'] for c in chapters if c['id'] in scope_ids and c['subject']==s]) for i,s in enumerate(subjects)]
    return AIPlan(intent='paper',scope_specified=scope,count=count,duration_minutes=duration,
                  chapter_ids=scope_ids,sections=sections,level=level,marks_correct=correct,marks_wrong=wrong,sets_enabled=sets)
