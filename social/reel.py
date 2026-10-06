"""Bounded animated teaching Reels with bundled CC BY music."""
import hashlib
import json
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw
from social import worker, motion
MAX_VIDEO_BYTES = 8 * 1024 * 1024
FPS = 12
DURATION = 28
AUDIO = Path(__file__).with_name('audio') / 'carefree-28s.mp3'
MANIFEST = AUDIO.with_name('license.json')


def music_credit():
    data = json.loads(MANIFEST.read_text())
    return (f'Music: "{data["title"]}" by {data["artist"]} ({data["source"]}). '
            f'CC BY 4.0: {data["license"]}. Excerpt; volume and fades adjusted.')


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
    image = Image.new('RGB',(720,1280),'#141519')
    d = ImageDraw.Draw(image)
    d.text((62,150),'JeeEdge / '+content['subject'],font=face(24,True),fill=motion.ORANGE)
    modeled = content.get('topic') in motion.TOPICS
    if seconds < 6:
        label='CAN YOU SPOT THE SHORTCUT?'
        text_block(d,copy.get('hook',content.get('topic','Quick JEE challenge')),300,160,42)
        text_block(d,content['question'],505,340,36)
        d.text((62,950),f'{max(1,6-int(seconds))} seconds to think',font=face(26,True),fill=motion.ORANGE)
    elif seconds < 16:
        label='WATCH THE CONCEPT' if modeled else 'THE RULE + ITS LIMITS'
        if modeled:
            motion.draw_model(image,content,seconds-6)
            text_block(d,motion.caption(content),710,105,27,color=motion.ORANGE)
            text_block(d,content['rule'],830,115,26)
            text_block(d,content['condition'],960,85,21,color=motion.MUTED)
        else:
            text_block(d,content.get('rule',content['answer']),330,310,40)
            # Stage the second block so viewers can follow the rule before its limits.
            if seconds >= 9:
                text_block(d,content.get('condition',content['solution']),700,285,32,color=motion.ORANGE)
    elif seconds < 24:
        label='NOW APPLY IT'
        text_block(d,content['answer'],320,180,46,color=motion.ORANGE)
        if seconds >= 17.5:
            text_block(d,content['solution'],550,390,34)
    else:
        label='SAVE THIS FOR REVISION'
        text_block(d,'Watch out: '+content.get('trap','Check units and signs.'),330,380,38)
        text_block(d,'Follow @jeeedge for more JEE shortcuts',830,120,30,color=motion.ORANGE)
    d.text((62,235),label,font=face(23,True),fill=motion.WHITE)
    d.rounded_rectangle((62,1090,642,1096),radius=3,fill='#34383d')
    d.rectangle((62,1090,62+int(580*seconds/DURATION),1096),fill=motion.ORANGE)
    return image


def render(content, directory, copy=None):
    started = time.monotonic()
    audio = verified_audio()
    directory = Path(directory)
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
    command = ['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
               '-threads','1','-framerate',str(FPS),'-i',str(frames/'%04d.jpg'),
               '-i',str(audio),'-t',str(DURATION),'-map','0:v:0','-map','1:a:0',
               '-af','volume=0.35,afade=t=in:d=0.7,afade=t=out:st=26:d=2',
               '-c:v','libx264','-threads','1','-filter_threads','1','-preset','ultrafast',
               '-crf','26','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','96k',
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
