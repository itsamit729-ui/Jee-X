"""One original carousel daily. Credentials never leave environment variables.

Media and the durable submission ledger live on a separate public media branch.
No comments, DMs, or artificial engagement are sent by this worker.
"""
import base64
import io
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / 'output'
MEDIA_BRANCH = 'jeeedge-social-media'
REPO = os.getenv('GITHUB_REPOSITORY', 'itsamit729-ui/Jee-X')
HANDLE = 'jeeedge'
SITE = 'https://jee-edge.onrender.com/'


class ServiceError(RuntimeError):
    pass


def request(url, method='GET', body=None, headers=None, missing_ok=False, binary=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read()
            return raw if binary else json.loads(raw)
    except urllib.error.HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        # Do not expose remote bodies, URLs, headers, tokens or prompts in logs.
        raise ServiceError(f'Service returned HTTP {error.code}; no paid fallback.') from None
    except (urllib.error.URLError, TimeoutError):
        raise ServiceError('Network request failed; next scheduled run will retry safely.') from None


def github(path, **kwargs):
    return request(f'https://api.github.com/repos/{REPO}/{path}',
                   headers={'Authorization': f'Bearer {os.environ["GITHUB_TOKEN"]}',
                            'Accept': 'application/vnd.github+json'}, **kwargs)


def ensure_media_branch():
    if github(f'git/ref/heads/{MEDIA_BRANCH}', missing_ok=True) is None:
        base = github('git/ref/heads/main')['object']['sha']
        github('git/refs', method='POST', body={'ref': f'refs/heads/{MEDIA_BRANCH}', 'sha': base})


def load_file(path):
    return github(f'contents/{path}?ref={MEDIA_BRANCH}', missing_ok=True)


def save_file(path, content):
    previous = load_file(path)
    payload = {'message': f'JeeEdge automation: {path}', 'branch': MEDIA_BRANCH,
               'content': base64.b64encode(content).decode()}
    if previous:
        payload['sha'] = previous['sha']
    return github(f'contents/{path}', method='PUT', body=payload)


def buffer(query, variables=None):
    result = request('https://api.buffer.com', method='POST',
                     body={'query': query, 'variables': variables or {}},
                     headers={'Authorization': f'Bearer {os.environ["BUFFER_API_KEY"]}'})
    if result.get('errors') or not result.get('data'):
        raise ServiceError('Buffer query failed. Check API permissions and connection.')
    return result['data']


def find_channel():
    orgs = buffer('{ account { organizations { id } } }')['account']['organizations']
    matches = []
    for org in orgs:
        channels = buffer('query($input: ChannelsInput!) { channels(input:$input) '
                          '{ id name displayName service isQueuePaused } }',
                          {'input': {'organizationId': org['id']}})['channels']
        for channel in channels:
            names = [str(channel.get(k, '')).lower().lstrip('@') for k in ('name', 'displayName')]
            if channel['service'].lower() == 'instagram' and HANDLE in names:
                matches.append((org['id'], channel))
    if len(matches) != 1:
        raise ServiceError('Expected exactly one Instagram channel named jeeedge. Check Buffer.')
    if matches[0][1]['isQueuePaused']:
        raise ServiceError('The Buffer channel is paused.')
    return matches[0]


def posts(org, channel, start):
    result = buffer('query($input:PostsInput!) { posts(first:100,input:$input) '
                    '{ edges { node { id text status } } pageInfo { hasNextPage } } }',
                    {'input': {'organizationId': org, 'filter': {
                        'channelIds': [channel], 'startDate': start}}})['posts']
    if result['pageInfo']['hasNextPage']:
        raise ServiceError('Post history needs pagination; stopping to protect against duplicates.')
    return [edge['node'] for edge in result['edges']]


def problem(day):
    """Original, parametrized problems; never labelled as actual exam PYQs."""
    rng = random.Random(day)
    n = rng.randint(2, 9)
    kind = datetime.fromisoformat(day).toordinal() % 6
    if kind == 0:
        return {'subject': 'PHYSICS', 'topic': 'Current electricity',
                'question': f'Two {n} ohm resistors are connected in parallel. What is the equivalent resistance?',
                'answer': f'{n / 2:g} ohm',
                'solution': f'1/R = 1/{n} + 1/{n} = 2/{n}.\nSo R = {n}/2 = {n / 2:g} ohm.\nFor two identical resistors in parallel, the resistance halves.'}
    if kind == 1:
        return {'subject': 'MATHS', 'topic': 'Differentiation',
                'question': f'If f(x) = x^2 + {n}x, what is the value of f\'(2)?',
                'answer': str(4 + n), 'solution': f'f\'(x) = 2x + {n}.\nAt x = 2: f\'(2) = 4 + {n} = {4 + n}.\nDifferentiate first, then substitute.'}
    if kind == 2:
        return {'subject': 'CHEMISTRY', 'topic': 'Mole concept',
                'question': f'A sample contains {18 * n} g of pure water. How many moles of water are present? Use molar mass = 18 g/mol.',
                'answer': f'{n} mol', 'solution': f'Moles = mass / molar mass.\nn = {18 * n}/18 = {n} mol.\nKeep the mass and molar mass units consistent.'}
    if kind == 3:
        return {'subject': 'PHYSICS', 'topic': 'Work and energy',
                'question': f'A {n} kg object moves at 4 m/s. Calculate its kinetic energy.',
                'answer': f'{8 * n} J', 'solution': f'K = (1/2)mv^2.\nK = (1/2) x {n} x 4^2 = {8 * n} J.\nThe speed is squared, not multiplied by two.'}
    if kind == 4:
        return {'subject': 'MATHS', 'topic': 'Probability',
                'question': f'A bag has {n} red balls and {2 * n} blue balls. One ball is drawn at random, with every ball equally likely. What is the probability of red?',
                'answer': '1/3', 'solution': f'P(red) = red balls / total balls.\nP(red) = {n}/({n} + {2 * n}) = {n}/{3 * n} = 1/3.\nCount all equally likely outcomes in the denominator.'}
    return {'subject': 'CHEMISTRY', 'topic': 'Concentration',
            'question': f'{n} mol of solute is dissolved to make 2 L of solution. What is its molarity?',
            'answer': f'{n / 2:g} mol/L', 'solution': f'Molarity = moles / solution volume in litres.\nM = {n}/2 = {n / 2:g} mol/L.\nUse the final solution volume, not solvent volume.'}


def ai_copy(content, history):
    prompt = ('Write an Instagram hook and caption for JeeEdge, for JEE students. English, friendly, concise. '
              'Return JSON with only hook (max 75 characters) and caption (max 1000 characters). '
              'Do not give the answer in either field, claim this is a PYQ, invent facts, mention rankings, '
              'promise marks or guaranteed results, or add URLs. Encourage solving then swiping. '
              'Do not change or generate the problem or solution. Use recent performance where available. '
              + json.dumps({'problem': content, 'recent_performance': history}))
    model = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
    if not re.fullmatch(r'gemini-[a-zA-Z0-9.\-]+', model):
        raise ServiceError('Invalid Gemini model name.')
    result = request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                     method='POST', headers={'x-goog-api-key': os.environ['GEMINI_API_KEY']},
                     body={'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {
                         'responseMimeType': 'application/json', 'maxOutputTokens': 1600}})
    try:
        text = ''.join(p.get('text', '') for p in result['candidates'][0]['content']['parts'])
        copy = json.loads(text)
        for key, limit in [('hook', 75), ('caption', 1000)]:
            if not isinstance(copy[key], str) or not 1 <= len(copy[key]) <= limit:
                raise ValueError()
        if re.search(r'https?://|guarantee|\bPYQ\b|100%|AIR\s*1', copy['hook'] + ' ' + copy['caption'], re.I):
            raise ValueError()
        return copy
    except (KeyError, IndexError, ValueError, TypeError):
        raise ServiceError('AI copy did not pass validation; holding publication.') from None


def font(size, bold=False):
    suffix = '-Bold' if bold else ''
    return ImageFont.truetype(f'/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf', size)


def wrapped(draw, text, face, width):
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            test = f'{line} {word}'.strip()
            if draw.textlength(test, font=face) > width and line:
                lines.append(line)
                line = word
            else:
                line = test
        lines.append(line)
    return lines


def render(content, copy):
    OUT.mkdir(parents=True, exist_ok=True)
    cards = [('30-SECOND WARM-UP', copy['hook'], 'Swipe for the question'),
             (content['topic'].upper(), content['question'], 'Solve first. Then swipe.'),
             ('THE BREAKDOWN', content['answer'] + '\n\n' + content['solution'], 'Save this for revision'),
             ('YOUR NEXT STEP', 'Turn one question\ninto a practice habit.', 'Visit JeeEdge through the link in our bio')]
    paths = []
    for index, (label, body, footer) in enumerate(cards):
        img = Image.new('RGB', (1080, 1350), '#141519')
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((64, 70, 230, 126), radius=16, fill='#ff8547')
        draw.text((82, 82), 'JeeEdge', font=font(27, True), fill='#141519')
        draw.text((845, 88), f'0{index + 1} / 04', font=font(23), fill='#93969f')
        draw.line((64, 190, 1016, 190), fill='#36383f', width=2)
        draw.text((66, 247), label, font=font(24, True), fill='#ff8547')
        size = 72 if index in (0, 3) else 49
        while size >= 28:
            face = font(size, index in (0, 3))
            lines = wrapped(draw, body, face, 930)
            if len(lines) * (size + 18) <= 770 and all(draw.textlength(line, font=face) <= 930 for line in lines):
                break
            size -= 2
        else:
            raise ServiceError('Card text exceeds layout; holding publication.')
        y = 345
        for line in lines:
            draw.text((66, y), line, font=face, fill='#f6f3ee')
            y += size + 18
        draw.line((64, 1155, 1016, 1155), fill='#36383f', width=2)
        draw.text((66, 1194), footer, font=font(27), fill='#f6f3ee')
        draw.text((66, 1254), '@jeeedge  /  ORIGINAL PRACTICE', font=font(21), fill='#93969f')
        path = OUT / f'{index + 1}.png'
        img.save(path)
        paths.append(path)
    return paths


def summarize_history(history):
    reports = []
    for item in history[-7:]:
        if not item.get('post_id'):
            continue
        try:
            report = buffer('query($id:PostId!) { post(input:{id:$id}) '
                            '{ status metrics { name type value unit } metricsUpdatedAt } }',
                            {'id': item['post_id']})['post']
            reports.append({'topic': item.get('topic'), 'report': report})
        except ServiceError:
            # Analytics availability must not prevent content publication.
            reports.append({'topic': item.get('topic'), 'report': 'metrics unavailable'})
    return reports


def main():
    now = datetime.now(timezone.utc)
    day = now.astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat()
    preview = os.getenv('PREVIEW_ONLY') == 'true'
    offline = '--offline-preview' in sys.argv
    required = [] if offline else ['BUFFER_API_KEY', 'GEMINI_API_KEY'] + ([] if preview else ['GITHUB_TOKEN'])
    if any(not os.getenv(key) for key in required):
        raise ServiceError('Required repository secrets are missing.')
    content = problem(day)
    ledger = {'history': []}
    state_path = 'state/ledger.json'
    marker = f'JeeEdge daily {day}'
    if not offline:
        org, channel = find_channel()
        recent = posts(org, channel['id'], (now - timedelta(days=3)).isoformat())
        found = next((p for p in recent if marker in p['text']), None)
        if found:
            print(f'Today already has a Buffer post; status: {found["status"]}. No duplicate created.')
            return
        if sum(p['status'] in ('scheduled', 'sending') for p in recent) >= 9:
            raise ServiceError('Buffer queue near free-plan capacity; waiting.')
    if not preview and not offline:
        ensure_media_branch()
        saved = load_file(state_path)
        if saved:
            ledger = json.loads(base64.b64decode(saved['content']))
        existing = next((item for item in ledger['history'] if item['day'] == day), None)
        if existing:
            raise ServiceError('Today has a submission record. Check Buffer before any manual retry.')
    metrics = [] if offline or preview else summarize_history(ledger['history'])
    copy = {'hook': 'Can you solve this before you swipe?',
            'caption': 'A quick original warm-up. Solve it first, then swipe for the breakdown.'} if offline else ai_copy(content, metrics)
    images = render(content, copy)
    caption = copy['caption'] + '\n\nOriginal practice question. More practice via the link in our bio.\n#JEE #JEEPreparation #JeeEdge\n' + marker
    (OUT / 'preview.json').write_text(json.dumps({'problem': content, 'copy': copy, 'caption': caption,
                                                'recent_metrics': metrics}, indent=2))
    if preview or offline:
        print('Preview generated. Nothing uploaded or posted.')
        return
    urls = []
    for image in images:
        result = save_file(f'media/{day}/{image.name}', image.read_bytes())
        urls.append(f'https://raw.githubusercontent.com/{REPO}/{result["commit"]["sha"]}/media/{day}/{image.name}')
    for url in urls:
        raw = request(url, binary=True)
        with Image.open(io.BytesIO(raw)) as image:
            if image.size != (1080, 1350):
                raise ServiceError('Public media verification failed.')
    record = {'day': day, 'topic': content['topic'], 'state': 'submitting', 'urls': urls}
    ledger['history'].append(record)
    save_file(state_path, json.dumps(ledger, indent=2).encode())
    # The ledger is committed BEFORE the non-idempotent publishing mutation.
    # On an ambiguous timeout, never submit again automatically.
    payload = {'text': caption, 'channelId': channel['id'], 'schedulingType': 'automatic',
               'mode': 'customScheduled', 'dueAt': (now + timedelta(minutes=30)).isoformat(),
               'assets': [{'image': {'url': url}} for url in urls]}
    result = buffer('mutation($input:CreatePostInput!) { createPost(input:$input) '
                    '{ ... on PostActionSuccess { post { id status } } '
                    '... on MutationError { message } } }', {'input': payload})['createPost']
    if not result.get('post'):
        raise ServiceError('Buffer rejected submission. Check the saved ledger and Buffer dashboard.')
    record.update({'state': 'scheduled', 'post_id': result['post']['id']})
    save_file(state_path, json.dumps(ledger, indent=2).encode())
    print('Carousel scheduled successfully for @jeeedge. See Buffer for publishing status.')


if __name__ == '__main__':
    try:
        main()
    except ServiceError as error:
        print(f'Automation paused: {error}', file=sys.stderr)
        sys.exit(1)
