import json
import math
import shutil
import subprocess
from pathlib import Path
import pytest
from social import lessons, motion, reel, worker


def test_projectiles_share_range_but_not_flight_height():
    low=motion.projectile_points(30); high=motion.projectile_points(60)
    assert low[-1][0] == pytest.approx(high[-1][0])
    assert low[-1][1] == pytest.approx(0,abs=1e-9)
    assert high[-1][1] == pytest.approx(0,abs=1e-9)
    assert max(y for _,y in high) > max(y for _,y in low)


def test_all_lesson_layouts_and_motion():
    for index in range(lessons.TOTAL):
        c=lessons.lesson('2026-10-06',index)
        for second in (0,6,10,15,18,25):
            assert reel.frame(c,{'hook':c['topic']},second).size == (720,1280)
        if c['topic'] in motion.TOPICS:
            assert reel.frame(c,{},7).tobytes() != reel.frame(c,{},10).tobytes()


def test_audio_tampering_holds_render(tmp_path,monkeypatch):
    p=tmp_path/'bad.mp3';p.write_bytes(b'unapproved audio')
    monkeypatch.setattr(reel,'AUDIO',p)
    with pytest.raises(worker.ServiceError,match='integrity'):
        reel.render(lessons.lesson('2026-10-06',0),tmp_path)
    assert not (tmp_path/'reel.mp4').exists()


@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg not installed')
def test_real_reel_has_audible_licensed_music(tmp_path):
    content=next(lessons.lesson('2026-10-06',i) for i in range(lessons.TOTAL)
                 if lessons.lesson('2026-10-06',i)['topic']=='Projectile range')
    output=reel.render(content,tmp_path)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(output)]))
    assert {s['codec_type'] for s in probe['streams']} == {'audio','video'}
    # Decode actual output samples: an AAC track alone would also allow silent audio.
    import array
    pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(output),'-map','0:a:0','-f','s16le','-ac','1','-ar','8000','-'])
    values=array.array('h',pcm)
    assert math.sqrt(sum(x*x for x in values)/len(values)) > 100
    assert output.stat().st_size < reel.MAX_VIDEO_BYTES
    assert 'Kevin MacLeod' in reel.music_credit()
    assert 'https://creativecommons.org/licenses/by/4.0/' in reel.music_credit()
