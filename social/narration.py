"""Short authored English narration. No extra LLM calls or paid-provider fallback."""
import io
import wave
from pathlib import Path
from social import storyboard

MODEL = 'canopylabs/orpheus-v1-english'
VOICE = 'troy'
URL = 'https://api.groq.com/openai/v1/audio/speech'
MAX_BYTES = 1024 * 1024
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
    if topic not in RULES:
        return []
    reveal = storyboard.beats(plan)[0]
    return [(0.4, reveal - 0.8, storyboard.HOOKS[topic][plan['hook_index']]),
            (reveal + 0.2, 16.8 - reveal, RULES[topic])]


def duration(data):
    if len(data) > MAX_BYTES:
        raise ValueError('Speech too large')
    with wave.open(io.BytesIO(data), 'rb') as audio:
        if audio.getcomptype() != 'NONE' or audio.getnchannels() not in (1, 2):
            raise ValueError('Unsupported speech WAV')
        seconds = audio.getnframes() / audio.getframerate()
        if not 0.1 <= seconds <= 20:
            raise ValueError('Speech duration out of bounds')
        if len(audio.readframes(audio.getnframes())) != audio.getnframes()*audio.getnchannels()*audio.getsampwidth():
            raise ValueError('Truncated speech')
        return seconds


def prepare(content, plan, directory, fetch):
    clips = []
    for index, (start, window, text) in enumerate(scenes(content, plan)):
        data = fetch(text)
        if not data:
            continue
        try:
            seconds = duration(data)
            speed = max(1.0, seconds / window)
            if speed > 1.3:  # Never cut off a sentence or rush an explanation.
                continue
            path = Path(directory) / f'voice-{index}.wav'
            path.write_bytes(data)
            clips.append((path, start, speed))
        except (ValueError, wave.Error, EOFError, OSError):
            continue
    return clips
