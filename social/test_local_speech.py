import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
from pathlib import Path
from types import SimpleNamespace
import array
import pytest
from social import advanced, creative, narration, local_speech, speech_audio
from social.test_narration import wav


def test_complete_local_voice_replaces_incomplete_primary_without_mixing_voices(tmp_path):
    content=creative.attach(advanced.BANK[0],'2026-10-15',0);plan=creative.plan(content)
    primary=[];backup=[]
    def fetch(text):primary.append(text);return wav() if len(primary)==1 else None
    def fallback(text):backup.append(text);return wav()
    clips=narration.prepare(content,plan,tmp_path,fetch,fallback=fallback,status=lambda:{'reason':'provider_http_403'})
    assert len(clips)==5 and len(backup)==5 and len(primary)==2
    assert all(path.parent.name=='voice-local' for path,_,_ in clips)
    assert plan['narration']=={'engine':'local','expected':5,'embedded':5,'complete':True,
                              'failures':[{'scene':1,'reason':'provider_http_403'}]}
    assert plan['subtitles']


def test_complete_primary_does_not_spend_cpu_on_local_voice(tmp_path):
    content=creative.attach(advanced.BANK[0],'2026-10-15',0);plan=creative.plan(content)
    clips=narration.prepare(content,plan,tmp_path,lambda _:wav(),fallback=lambda _:pytest.fail('Primary narration is complete'))
    assert len(clips)==5 and plan['narration']['engine']=='groq'


def test_incomplete_backup_cannot_publish_only_a_spoken_misconception(tmp_path):
    content=creative.attach(advanced.BANK[0],'2026-10-15',0);plan=creative.plan(content)
    calls=[]
    def fallback(text):calls.append(text);return wav() if len(calls)==1 else None
    assert narration.prepare(content,plan,tmp_path,lambda _:None,fallback=fallback)==[]
    assert plan['subtitles']==[] and plan['narration']['engine']=='music'
    assert any(f['reason']=='local_unavailable' for f in plan['narration']['failures'])


def test_voice_disable_is_respected_and_missing_key_is_visible(monkeypatch):
    from app.services import social_speech
    calls=[]
    monkeypatch.setattr(social_speech.local_speech,'fetch',lambda text:calls.append(text) or wav())
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    monkeypatch.setenv('SOCIAL_TTS_ENABLED','true');monkeypatch.setenv('SOCIAL_LOCAL_TTS_ENABLED','true')
    assert social_speech.fetch('The force points inward.') is None
    assert social_speech.last_status()['reason']=='missing_groq_key'
    assert social_speech.local_fetch('The force points inward.')==wav()
    monkeypatch.setenv('SOCIAL_TTS_ENABLED','false')
    assert social_speech.fetch('The force points inward.') is None
    assert social_speech.last_status()['reason']=='disabled'
    assert social_speech.local_fetch('The force points inward.') is None and len(calls)==1


def test_local_text_is_never_interpolated_into_shell_or_filter_syntax(monkeypatch):
    text="A -> B: don't read this as 'voice=other'; x < 2."
    def run(args,**kwargs):
        assert not kwargs.get('shell')
        source=args[args.index('-i')+1]
        assert source.startswith('flite=textfile=') and text not in source
        file=source.removeprefix('flite=textfile=').removesuffix(':voice=slt')
        assert Path(file).read_text()==text
        return SimpleNamespace(stdout=wav())
    monkeypatch.setattr(local_speech.subprocess,'run',run)
    assert local_speech.fetch(text)==wav()


def test_actual_offline_voice_is_non_silent_and_every_advanced_script_fits():
    # Real synthesis rather than a tone fixture: validates the deployed engine,
    # every lesson's scene windows and the normal WAV parsing path together.
    for lesson in advanced.BANK:
        content=creative.attach(lesson,'2026-10-15',0)
        for _,window,text in narration.scenes(content,creative.plan(content)):
            data=local_speech.fetch(text)
            assert data, (lesson['topic'],text)
            pcm,_,_,_,metrics=speech_audio.decode(data)
            assert metrics['seconds']/window<=1.3, (lesson['topic'],text,metrics)
            assert max(abs(n) for n in array.array('h',pcm))>100, lesson['topic']
