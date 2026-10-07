"""Bounded animated teaching Reels with bundled CC BY music."""
import hashlib
import json
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw
from social import worker, motion, cinema, storyboard, sound
MAX_VIDEO_BYTES = 8 * 1024 * 1024
FPS = 24
DURATION = 28
AUDIO = Path(__file__).with_name('audio') / 'carefree-28s.mp3'
MANIFEST = AUDIO.with_name('license.json')


def music_credit():
    data = json.loads(MANIFEST.read_text())
    return (f'Music: "{data["title"]}" by {data["artist"]} ({data["source"]}). '
            f'CC BY 4.0: {data["license"]}. Excerpt; volume and fades adjusted. Original synthesized cues by JeeEdge.')


def verified_audio():
    data = json.loads(MANIFEST.read_text())
    if hashlib.sha256(AUDIO.read_bytes()).hexdigest() != data['sha256']:
        raise worker.ServiceError('Bundled licensed audio failed integrity verification.')
    return AUDIO


@lru_cache(maxsize=32)
def face(size, bold=False):
    return worker.font(size, bold)


def text_block(draw, text, y, height, size=34, color='#f6f3ee'):
    while size >= 20:
        font = face(size)
        lines = worker.wrapped(draw, text, font, 570)
        if len(lines)*(size+9) <= height and all(draw.textlength(line, font=font) <= 570 for line in lines):
            for i,line in enumerate(lines):
                draw.text((62,y+i*(size+9)),line,font=font,fill=color)
            return
        size -= 2
    raise worker.ServiceError('Reel text exceeds safe layout.')


def frame(content, copy, seconds):
    plan=(copy or {}).get('storyboard')
    if not storyboard.validate(plan,content):plan=storyboard.fallback(content)
    if (copy or {}).get('hook'):
        plan={**plan, 'hook':copy['hook']}
    return cinema.frame(content,plan,seconds)


def render(content, directory, copy=None):
    started = time.monotonic()
    audio = verified_audio()
    directory = Path(directory)
    plan=(copy or {}).get('storyboard')
    if not storyboard.validate(plan,content):plan=storyboard.fallback(content)
    copy={**(copy or {}),'storyboard':plan}
    effects=sound.render(directory/'effects.wav',plan)
    frames = directory / 'frames'
    frames.mkdir()
    try:
        for index in range(DURATION*FPS):
            if time.monotonic()-started >= 150:
                raise worker.ServiceError('Animation exceeded the rendering time budget.')
            frame(content,copy or {},index/FPS).save(frames / f'{index:04d}.jpg',quality=88)
    except OSError:
        raise worker.ServiceError('Animation frames could not be written.') from None
    output = directory / 'reel.mp4'
    clips = copy.get('voice_clips', [])
    music_volume = '0.07' if clips else '0.24'
    filters = [f'[1:a]volume={music_volume},afade=t=in:d=0.5,afade=t=out:st=26:d=2[m]',
               '[2:a]volume=0.4[fx]']
    labels = '[m][fx]'
    extra_inputs = []
    for index, (path, start, speed) in enumerate(clips):
        extra_inputs += ['-i', str(path)]
        filters.append(f'[{index+3}:a]atempo={speed:.6f},aresample=24000,'
                       f'aformat=channel_layouts=stereo,adelay={round(start*1000)}:all=1[v{index}]')
        labels += f'[v{index}]'
    filters.append(labels+f'amix=inputs={2+len(clips)}:normalize=0,alimiter=limit=0.8[mix]')
    command = ['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
               '-threads','1','-framerate',str(FPS),'-i',str(frames/'%04d.jpg'),
               '-i',str(audio),'-i',str(effects),*extra_inputs,
               '-t',str(DURATION),'-map','0:v:0','-map','[mix]',
               '-filter_complex_threads','1','-filter_complex',';'.join(filters),
               '-c:v','libx264','-threads','1','-filter_threads','1','-preset','veryfast',
               '-crf','26','-pix_fmt','yuv420p','-r','30','-c:a','aac','-ac','2','-b:a','96k',
               '-movflags','+faststart',str(output)]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=max(1, 180-(time.monotonic()-started)))
        probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                                          '-of', 'json', str(output)], check=True,
                                         capture_output=True, timeout=15).stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        raise worker.ServiceError('Reel rendering or validation failed; nothing submitted.') from None
    video = next((s for s in probe['streams'] if s['codec_type'] == 'video'), {})
    if (video.get('codec_name'), video.get('width'), video.get('height')) != ('h264', 720, 1280):
        raise worker.ServiceError('Reel format validation failed.')
    audio = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), {})
    if audio.get('codec_name') != 'aac' or int(audio.get('channels', 0)) != 2:
        raise worker.ServiceError('Reel audio validation failed.')
    if not 27 <= float(probe['format']['duration']) <= 29 or output.stat().st_size > MAX_VIDEO_BYTES:
        raise worker.ServiceError('Reel duration or size exceeds the free-worker budget.')
    return output
