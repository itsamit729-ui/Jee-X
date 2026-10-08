import io
import os
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')
import wave
from social import narration, lessons, storyboard


def wav(seconds=1):
    out=io.BytesIO()
    with wave.open(out,'wb') as f:
        f.setparams((1,2,24000,0,'NONE','not compressed'))
        f.writeframes(b'\0\0'*int(seconds*24000))
    return out.getvalue()


def test_all_scripts_fit_api_and_scenes():
    for i in range(lessons.TOTAL):
        c=lessons.visual_lesson('2026-10-07',i)
        for pace in ('steady','brisk'):
            plan={**storyboard.fallback(c),'pace':pace}
            scenes=narration.scenes(c,plan)
            assert len(scenes) in (3,4)
            assert all(len(text)<=200 and window>0 for _,window,text in scenes)
            assert scenes[1][0]+scenes[1][1]<17.1


def test_audio_fallback_and_timing(tmp_path):
    c=lessons.visual_lesson('2026-10-07',0);plan=storyboard.fallback(c)
    assert narration.prepare(c,plan,tmp_path,lambda _:None)==[]
    assert narration.prepare(c,plan,tmp_path,lambda _:b'bad wav')==[]
    assert narration.prepare(c,plan,tmp_path,lambda _:wav(20))==[]
    clips=narration.prepare(c,plan,tmp_path,lambda _:wav())
    assert len(clips)==len(narration.scenes(c,plan))
    assert all(path.exists() and speed==1 for path,_,speed in clips)


def test_tts_budget_is_separate(monkeypatch):
    from app.services import social_budget as b
    calls=[]
    monkeypatch.setattr(b,'reserve',lambda service,**kw:calls.append((service,kw)))
    b.before(narration.URL,{'input':'Hello'})
    assert calls==[('groq_tts',{'tokens':37})]
    monkeypatch.setattr(b,'cache',lambda *args:calls.append(args))
    b.limited(narration.URL,100)
    assert calls[-1][0]=='cooldown:groq_tts'


def test_durable_reuse_failure_and_disabled(monkeypatch, caplog):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    from app.models.social_job import SocialSpeech, SocialQuotaLock, SocialUsage, SocialCache
    from app.services import social_speech as speech, social_budget as budget
    engine=create_engine('sqlite://')
    Base.metadata.create_all(engine,tables=[c.__table__ for c in (SocialSpeech,SocialQuotaLock,SocialUsage,SocialCache)])
    factory=sessionmaker(bind=engine)
    monkeypatch.setattr(speech,'SessionLocal',factory)
    monkeypatch.setattr(budget,'SessionLocal',factory)
    monkeypatch.setenv('GROQ_API_KEY','test')
    monkeypatch.setenv('SOCIAL_TTS_ENABLED','true')
    calls=[]
    def request(*args,**kwargs):
        from social.test_speech_audio import streamed
        calls.append(kwargs)
        return streamed(wav(), metadata=True)
    monkeypatch.setattr(speech.worker,'request',request)
    assert speech.fetch('Hello')==wav()
    assert speech.fetch('Hello')==wav()
    assert len(calls)==1
    def failed(*args,**kwargs):
        calls.append(kwargs)
        return wav(21)
    monkeypatch.setattr(speech.worker,'request',failed)
    assert speech.fetch('Another line') is None
    assert speech.fetch('Another line') is None
    assert len(calls)==2
    assert 'stage=audio_validation reason=duration_out_of_bounds' in caplog.text
    from datetime import datetime,timedelta
    with factory() as db:
        failed_row=db.query(SocialSpeech).filter(SocialSpeech.audio.is_(None)).one()
        failed_row.created_at=datetime.utcnow()-timedelta(minutes=31)
        db.commit()
    monkeypatch.setattr(speech.worker,'request',request)
    assert speech.fetch('Another line')==wav()
    assert len(calls)==3
    assert speech.fetch('Another line')==wav()
    monkeypatch.setenv('SOCIAL_TTS_ENABLED','false')
    assert speech.fetch('Hello') is None
    assert len(calls)==3


def test_real_voice_mix(tmp_path):
    import shutil
    import pytest
    from social import reel
    if not shutil.which('ffmpeg'):
        pytest.skip('FFmpeg unavailable')
    content=lessons.visual_lesson('2026-10-07',0)
    plan=storyboard.fallback(content)
    # Model the provider's streamed header using a known non-silent test signal.
    import math,struct,array,subprocess
    from social.test_speech_audio import streamed
    out=io.BytesIO()
    with wave.open(out,'wb') as f:
        f.setparams((1,2,24000,0,'NONE','not compressed'))
        f.writeframes(b''.join(struct.pack('<h',int(8000*math.sin(2*math.pi*1000*i/24000))) for i in range(24000)))
    clips=narration.prepare(content,plan,tmp_path,lambda _:streamed(out.getvalue(),metadata=True))
    assert len(clips)==len(narration.scenes(content,plan))
    output=reel.render(content,tmp_path,{'storyboard':plan,'voice_clips':clips})
    assert output.stat().st_size>1000
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(output),'-ss','0.6','-t','0.4',
        '-vn','-f','s16le','-ac','1','-ar','8000','-'])
    values=array.array('h',raw)
    real=sum(x*math.cos(2*math.pi*1000*i/8000) for i,x in enumerate(values))
    imag=sum(x*math.sin(2*math.pi*1000*i/8000) for i,x in enumerate(values))
    # Confirms that narration, not just the licensed music, reached the AAC track.
    assert 2*math.hypot(real,imag)/len(values)>2000
