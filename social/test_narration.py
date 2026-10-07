import io
import wave
from social import narration, lessons, storyboard


def wav(seconds=1):
    out=io.BytesIO()
    with wave.open(out,'wb') as f:
        f.setparams((1,2,24000,0,'NONE','not compressed'))
        f.writeframes(b'\0\0'*int(seconds*24000))
    return out.getvalue()


def test_all_scripts_fit_api_and_scenes():
    for i in range(12):
        c=lessons.visual_lesson('2026-10-07',i)
        for pace in ('steady','brisk'):
            plan={**storyboard.fallback(c),'pace':pace}
            scenes=narration.scenes(c,plan)
            assert len(scenes)==2
            assert all(len(text)<=200 and window>0 for _,window,text in scenes)
            assert scenes[1][0]+scenes[1][1]<17.1


def test_audio_fallback_and_timing(tmp_path):
    c=lessons.visual_lesson('2026-10-07',0);plan=storyboard.fallback(c)
    assert narration.prepare(c,plan,tmp_path,lambda _:None)==[]
    assert narration.prepare(c,plan,tmp_path,lambda _:b'bad wav')==[]
    assert narration.prepare(c,plan,tmp_path,lambda _:wav(20))==[]
    clips=narration.prepare(c,plan,tmp_path,lambda _:wav())
    assert len(clips)==2
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


def test_durable_reuse_failure_and_disabled(monkeypatch):
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
        calls.append(kwargs)
        return wav()
    monkeypatch.setattr(speech.worker,'request',request)
    assert speech.fetch('Hello')==wav()
    assert speech.fetch('Hello')==wav()
    assert len(calls)==1
    def failed(*args,**kwargs):
        calls.append(kwargs)
        raise speech.worker.ServiceError('unavailable')
    monkeypatch.setattr(speech.worker,'request',failed)
    assert speech.fetch('Another line') is None
    assert speech.fetch('Another line') is None
    assert len(calls)==2
    monkeypatch.setenv('SOCIAL_TTS_ENABLED','false')
    assert speech.fetch('Hello') is None
    assert len(calls)==2


def test_real_voice_mix(tmp_path):
    import shutil
    import pytest
    from social import reel
    if not shutil.which('ffmpeg'):
        pytest.skip('FFmpeg unavailable')
    content=lessons.visual_lesson('2026-10-07',0)
    plan=storyboard.fallback(content)
    clips=narration.prepare(content,plan,tmp_path,lambda _:wav())
    output=reel.render(content,tmp_path,{'storyboard':plan,'voice_clips':clips})
    assert output.stat().st_size>1000
