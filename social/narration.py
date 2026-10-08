"""Short authored English narration. No extra LLM calls or paid-provider fallback."""
import io
import logging
import wave
from pathlib import Path
from social import storyboard, speech_audio, hooks, art_direction

log = logging.getLogger('uvicorn.error')

MODEL = 'canopylabs/orpheus-v1-english'
VOICE = 'troy'
URL = 'https://api.groq.com/openai/v1/audio/speech'
MAX_BYTES = speech_audio.MAX_BYTES
# Spoken forms avoid ambiguous readings of mathematical notation.
RULES = {
    'Projectile range': 'With equal launch and landing heights and no air drag, complementary angles give equal ranges at the same speed.',
    'Vertical throw': 'At the top, vertical velocity is zero. Gravity is still acting downward. Zero velocity does not mean zero acceleration.',
    'Uniform circular motion': 'At the same radius, doubling speed makes centripetal acceleration four times larger. Its direction is toward the centre.',
    'Wave speed': 'Wave speed equals frequency times wavelength. Convert centimetres to metres before multiplying.',
    'Kinetic energy scaling': 'Keep mass fixed. Triple the speed, and kinetic energy becomes nine times larger. Square the speed multiplier.',
    'Dilution': 'Adding only solvent keeps solute moles fixed. Multiply initial concentration by initial volume, then divide by final volume.',
    'First-order half-life': 'For a first order reaction, halve what remains each time. After three half lives, one eighth of the original amount remains.',
    'Odd-function integral': 'An odd function has cancelling signed areas across symmetric bounds, provided the integral exists. The integral is zero.',
    'Even-function integral': 'For an integrable even function on symmetric bounds, integrate from zero to the positive bound, then double the result.',
    'Derivative at a point': 'Differentiate the function first. Then substitute the point. Substituting first loses the slope information.',
    'Difference of squares': 'Subtracting two squares equals the difference of the numbers times their sum. Move the pieces to see the rectangle.',
    'Limiting reagent': 'Use a balanced reaction. Divide each amount in moles by its coefficient. The smaller ratio identifies the limiting reagent.',
}


def scenes(content, plan):
    topic = content['topic']
    opening = plan.get('hook') or hooks.opening(content)
    rule = RULES.get(topic,content.get('why',content['rule']))
    # Authored speech explains the worked example or a labelled mistake.
    # The carousel also carries the more demanding transfer question.
    example = content.get('spoken_example') or content.get('spoken_takeaway') or ('Avoid this mistake: ' + content['trap'])
    if art_direction.style(content)=='casefile':
        brain,reality=art_direction.joke(content)
        return [(0.2,3.6,brain),(4.2,4.5,reality),(9.2,7.4,rule),(17.2,10.4,example)]
    return [(0.2, 3.6, opening), (4.2, 12.4, rule), (17.2, 10.4, example)]


def duration(data):
    return speech_audio.duration(data)


def prepare(content, plan, directory, fetch):
    clips = []
    plan["subtitles"] = []
    for index, (start, window, text) in enumerate(scenes(content, plan)):
        data = fetch(text)
        if not data:
            log.info('JeeEdge TTS scene=%d skipped: no audio available.', index)
            continue
        try:
            data, metrics = speech_audio.normalize(data)
            seconds = duration(data)
            speed = max(1.0, seconds / window)
            if speed > 1.3:  # Never cut off a sentence or rush an explanation.
                log.warning('JeeEdge TTS scene=%d skipped: speech=%.2fs window=%.2fs required_speed=%.2f', index, seconds, window, speed)
                continue
            path = Path(directory) / f'voice-{index}.wav'
            path.write_bytes(data)
            clips.append((path, start, speed))
            words = text.split()
            chunks = [' '.join(words[j:j+7]) for j in range(0,len(words),7)]
            actual = seconds / speed
            total = sum(len(x.split()) for x in chunks)
            offset = start
            for chunk in chunks:
                end = offset + actual * len(chunk.split()) / total
                plan['subtitles'].append({'start':offset,'end':end,'text':chunk})
                offset = end
        except (ValueError, wave.Error, EOFError, OSError) as error:
            log.warning('JeeEdge TTS scene=%d skipped: invalid audio or file error (%s).', index, type(error).__name__)
            continue
    if art_direction.style(content)=='casefile' and len(clips)!=len(scenes(content,plan)):
        # Do not leave only a spoken misconception when its correction failed.
        log.warning('JeeEdge comic narration incomplete; using the complete visual joke with music.')
        plan['subtitles']=[]
        return []
    return clips
