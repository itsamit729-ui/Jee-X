"""Groq proposes and reviews packaging; authored mathematics remains immutable."""
import json
import os
import re
from social import worker, hooks, art_direction


def call(prompt, schema, max_tokens=1536, reasoning_effort="low"):
    result = worker.request('https://api.groq.com/openai/v1/chat/completions', method='POST',
        headers={'Authorization': 'Bearer ' + os.environ['GROQ_API_KEY']},
        body={'model': 'openai/gpt-oss-120b', 'messages': [{'role':'user', 'content':prompt}],
              'response_format': {'type':'json_schema', 'json_schema':{'name':'jeeedge_editorial','strict':True,'schema':schema}},
              'reasoning_effort':reasoning_effort, 'max_completion_tokens':max_tokens})
    choice = result['choices'][0]
    if choice.get('finish_reason') != 'stop':
        raise ValueError('Incomplete editorial response')
    return json.loads(choice['message']['content'])


def authored(content):
    return {'hook':art_direction.joke(content)[0] if art_direction.style(content)=='casefile' else hooks.opening(content), 'editorial_source':'authored',
            'caption':art_direction.caption(content)}


def normalized_caption(value):
    value = value.split('\n\nMusic:', 1)[0]
    value = re.sub(r'JeeEdge daily \d{4}-\d{2}-\d{2} / s\d{2}', '', value)
    return ' '.join(re.findall(r'[a-z]+', value.lower()))


def repeated(caption, recent):
    from difflib import SequenceMatcher
    candidate = normalized_caption(caption)
    return any(SequenceMatcher(None, candidate, normalized_caption(old), autojunk=False).ratio() >= 0.82
               for old in recent if old)


def package(content, kind, recent=()):
    fallback = authored(content)
    direction = art_direction.style(content)
    lower, upper = art_direction.CAPTION_LIMITS[direction]
    try:
        context = {k: content[k] for k in ('subject','topic','rule','condition','trap','question','answer','solution',
                   'why','transfer_question','transfer_answer','hook','level') if k in content}
        if direction=='casefile':
            context['original_joke'] = dict(zip(('brain','reality'),art_direction.joke(content)))
        draft = call('Create three distinct English hooks (each <=65 characters) and one educational caption '
            f'({lower} to {upper} characters) for an original JEE ' + kind + '. '
            + art_direction.BRIEFS[direction] + ' '
            'Open a concrete curiosity gap: a choice, surprising constraint, calculation or plausible wrong answer. '
            'Make the payoff specific and deliverable from this lesson. No generic learn-this or spot-the-trap hooks. '
            'For reels keep each hook to at most 10 spoken words and 65 characters. '
            'Write naturally and specifically. Do not begin with a chapter label or always end with a question. '
            'Avoid stock phrases: unlock, master, ace, game-changer, did you know, test your knowledge, '
            'check your reasoning, applies when, and here is the secret. No invented personal anecdotes. '
            'Include the reasoning and essential condition in natural prose. Use only the supplied facts. '
            'Use a closing question only if the assigned format benefits from one. No save/follow/comment/tag/share requests, hashtags, '
            'URLs, website/bio promotion, invented facts, exam-year/PYQ claims, rank or score promises. '
            'Avoid generic filler and copying earlier captions. Math and calculated examples are immutable. '
            + json.dumps({'lesson':context,'recent_captions':[x[:180] for x in recent[:4]]}),
            {'type':'object','properties':{'hooks':{'type':'array','items':{'type':'string'}},'caption':{'type':'string'}},
             'required':['hooks','caption'],'additionalProperties':False}, max_tokens=1536)
        hooks, caption = draft['hooks'], draft['caption']
        if len(hooks) != 3 or any(not isinstance(h,str) or not 1 <= len(h.strip()) <= 65 for h in hooks):
            raise ValueError('Invalid hooks')
        if kind == 'reel' and any(len(h.split()) > 10 for h in hooks):
            raise ValueError('Opening too long for its scene')
        if not isinstance(caption,str) or not lower <= len(caption.strip()) <= upper:
            raise ValueError('Invalid caption')
        if re.search(r'\b(unlock|game.changer|ace your|did you know|test your knowledge|check your reasoning|applies when)\b',caption,re.I):
            raise ValueError('Stock caption phrasing')
        if re.search(r'https?://|www\.|link in|\bbio\b|website|guarantee|\bPYQ\b|100%|AIR\s*1|#|@|\b(save|follow|comment|tag|share|viral)\b', ' '.join(hooks)+caption, re.I):
            raise ValueError('Unsupported promotion')
        if repeated(caption, recent):
            raise ValueError('Repeated caption')
        review = call('Act as a strict JEE teacher. Review the draft against the authoritative lesson. '
            'Approve only when the caption explains the reasoning, includes the applicable conditions, '
            'adds no unsupported facts, and makes sense without the images. Score clarity and educational '
            'value from 1 to 5; 4 means specific, clear and useful, 5 means exceptionally concise teaching. '
            'Also score hook_specificity and payoff from 1 to 5: the chosen hook must ask a concrete '
            'topic-specific question or make a precise contrast whose answer the lesson actually delivers. '
            'Reject generic filler, altered math, misleading hooks and engagement requests. '
            'Judge whether the caption sounds like a specific tutor note instead of a stock social template. '
            'The assigned editorial direction is: '+art_direction.BRIEFS[direction]+' '
            'Reject hooks that could be pasted onto another topic unchanged. Select strongest hook index (0,1,2). '
            + json.dumps({'lesson':context,'draft':draft}),
            {'type':'object','properties':{'approved':{'type':'boolean'},'chosen':{'type':'integer','enum':[0,1,2]},
              'clarity':{'type':'integer','enum':[1,2,3,4,5]},'educational_value':{'type':'integer','enum':[1,2,3,4,5]},
              'hook_specificity':{'type':'integer','enum':[1,2,3,4,5]}, 'payoff':{'type':'integer','enum':[1,2,3,4,5]}},
             'required':['approved','chosen','clarity','educational_value','hook_specificity','payoff'],'additionalProperties':False}, max_tokens=1024, reasoning_effort='medium')
        if (review['approved'] is not True or type(review['chosen']) is not int or review['chosen'] not in range(3)
                or type(review['clarity']) is not int or review['clarity'] < 4
                or type(review['educational_value']) is not int or review['educational_value'] < 4
                or any(type(review.get(k)) is not int or review[k]<4 for k in ('hook_specificity','payoff'))):
            raise ValueError('Review rejected')
        return {'hook':art_direction.joke(content)[0] if direction=='casefile' else hooks[review['chosen']].strip(), 'caption':caption.strip(), 'editorial_source':'groq_reviewed'}
    except (worker.ServiceError, ValueError, TypeError, KeyError, IndexError):
        print('Using authored teaching caption; editorial unavailable or quality gate not met.', flush=True)
        return fallback
