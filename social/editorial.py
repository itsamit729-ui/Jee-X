"""Groq proposes and reviews packaging; authored mathematics remains immutable."""
import json
import os
import re
from social import worker


def call(prompt, schema):
    result = worker.request('https://api.groq.com/openai/v1/chat/completions', method='POST',
        headers={'Authorization': 'Bearer ' + os.environ['GROQ_API_KEY']},
        body={'model': 'openai/gpt-oss-120b', 'messages': [{'role':'user', 'content':prompt}],
              'response_format': {'type':'json_schema', 'json_schema':{'name':'jeeedge_editorial','strict':True,'schema':schema}},
              'reasoning_effort':'low', 'max_completion_tokens':1536})
    choice = result['choices'][0]
    if choice.get('finish_reason') != 'stop':
        raise ValueError('Incomplete editorial response')
    return json.loads(choice['message']['content'])


def package(content, kind):
    fallback = {'hook': 'A useful check for ' + content['topic'].lower(),
                'caption': 'Learn the rule, check when it applies, and try the example. Save this for your next revision session.'}
    try:
        context = {k: content[k] for k in ('subject','topic','rule','condition','trap')}
        draft = call('Create three distinct English hooks (each <=65 characters) and one caption (<=350 characters) '
            'for an original JEE ' + kind + '. No URLs, link-in-bio, website launch claims, PYQ claims, '
            'score guarantees, invented statistics or example answers. Use one save or follow CTA. '
            'Do not alter the rule or hide its conditions. Only output JSON. Lesson: ' + json.dumps(context),
            {'type':'object','properties':{'hooks':{'type':'array','items':{'type':'string'}},'caption':{'type':'string'}},
             'required':['hooks','caption'],'additionalProperties':False})
        hooks, caption = draft['hooks'], draft['caption']
        if len(hooks) != 3 or any(not isinstance(h,str) or not 1 <= len(h.strip()) <= 65 for h in hooks):
            raise ValueError('Invalid hooks')
        if not isinstance(caption,str) or not 1 <= len(caption.strip()) <= 350:
            raise ValueError('Invalid caption')
        if re.search(r'https?://|www\.|link in|bio|website|guarantee|\bPYQ\b|100%|AIR\s*1', ' '.join(hooks)+caption, re.I):
            raise ValueError('Unsupported promotion')
        review = call('Review this JEE packaging against the supplied authoritative rule and conditions. '
            'Approve only if accurate, no invented claims or answers, no website/bio promotion, '
            'and useful for revision. Select the strongest hook index (0,1,2). '
            'Output JSON with approved boolean and chosen integer. '
            + json.dumps({'lesson':context,'draft':draft}),
            {'type':'object','properties':{'approved':{'type':'boolean'},'chosen':{'type':'integer','enum':[0,1,2]}},
             'required':['approved','chosen'],'additionalProperties':False})
        if review['approved'] is not True or type(review['chosen']) is not int or review['chosen'] not in range(3):
            raise ValueError('Review rejected')
        return {'hook':hooks[review['chosen']].strip(), 'caption':caption.strip()}
    except (worker.ServiceError, ValueError, TypeError, KeyError, IndexError):
        # Quota limits reduce AI use, not mathematical integrity; never buy a fallback.
        print('Using authored lesson packaging; editorial unavailable or not approved.', flush=True)
        return fallback
