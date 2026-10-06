"""Bounded template Reel rendering without paid media services."""
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from social import worker
MAX_VIDEO_BYTES = 8 * 1024 * 1024


def render(content, directory):
    directory = Path(directory)
    frames = directory / 'frames'
    frames.mkdir()
    scenes = [('QUICK JEE CHALLENGE', content['question'], 'Think it through', 10),
              ('THE ANSWER', content['answer'], 'Here is why', 4),
              ('THE BREAKDOWN', content['solution'], 'Pause to read', 10),
              ('KEEP YOUR MOMENTUM', 'One question today.\nA stronger habit tomorrow.', 'Practice at JeeEdge — link in bio', 4)]
    index = 0
    for label, text, footer, duration in scenes:
        for second in range(duration):
            image = Image.new('RGB', (720, 1280), '#141519')
            draw = ImageDraw.Draw(image)
            draw.text((62, 155), 'JeeEdge / ' + content['subject'], font=worker.font(24, True), fill='#ff8547')
            draw.text((62, 235), label, font=worker.font(23, True), fill='#f6f3ee')
            size = 40
            while size >= 24:
                face = worker.font(size, label == 'THE ANSWER')
                lines = worker.wrapped(draw, text, face, 580)
                if len(lines) * (size + 12) <= 560 and all(draw.textlength(line, font=face) <= 580 for line in lines):
                    break
                size -= 2
            else:
                raise worker.ServiceError('Reel text exceeds safe layout.')
            for line_no, line in enumerate(lines):
                draw.text((62, 340 + line_no * (size + 12)), line, font=face, fill='#f6f3ee')
            draw.text((62, 960), footer, font=worker.font(24), fill='#ff8547')
            if label == 'QUICK JEE CHALLENGE':
                draw.text((62, 1020), str(duration-second) + ' seconds', font=worker.font(30, True), fill='#f6f3ee')
            draw.rectangle((62, 1100, 62 + int(580 * (index+1)/28), 1105), fill='#ff8547')
            image.save(frames / f'{index:03d}.png')
            index += 1
    output = directory / 'reel.mp4'
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
               '-threads', '1', '-framerate', '1', '-i', str(frames / '%03d.png'),
               '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', '28',
               '-c:v', 'libx264', '-threads', '1', '-filter_threads', '1', '-preset', 'ultrafast',
               '-crf', '25', '-pix_fmt', 'yuv420p', '-r', '30', '-c:a', 'aac',
               '-b:a', '64k', '-movflags', '+faststart', str(output)]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=180)
        probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                                          '-of', 'json', str(output)], check=True,
                                         capture_output=True, timeout=15).stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        raise worker.ServiceError('Reel rendering or validation failed; nothing submitted.') from None
    video = next((s for s in probe['streams'] if s['codec_type'] == 'video'), {})
    if (video.get('codec_name'), video.get('width'), video.get('height')) != ('h264', 720, 1280):
        raise worker.ServiceError('Reel format validation failed.')
    if not 27 <= float(probe['format']['duration']) <= 29 or output.stat().st_size > MAX_VIDEO_BYTES:
        raise worker.ServiceError('Reel duration or size exceeds the free-worker budget.')
    return output
