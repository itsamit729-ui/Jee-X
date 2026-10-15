"""Offline speech using FFmpeg/libflite; no network, API key or paid service."""
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from social import speech_audio


def fetch(text):
    if not text or len(text)>200:return None
    # Use a text file: user/lesson text must never become shell or filter code.
    try:
        with TemporaryDirectory(prefix='jeeedge-voice-') as directory:
            source=Path(directory)/'speech.txt';source.write_text(text,encoding='utf-8')
            result=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin',
                '-threads','1','-filter_threads','1','-f','lavfi','-i',f'flite=textfile={source}:voice=slt',
                '-ac','1','-ar','24000','-c:a','pcm_s16le','-f','wav','pipe:1'],
                check=True,capture_output=True,timeout=10)
            return speech_audio.normalize(result.stdout)[0]
    except (OSError,subprocess.SubprocessError,ValueError):return None
