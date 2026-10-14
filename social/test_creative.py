"""New-story contracts: variety, immutable teaching, timing and free fallback."""
from array import array
from collections import Counter
from datetime import date, timedelta
import wave
from social import creative, editorial, lessons, narration, quality, reel, sound, storyboard


def test_smaller_schedules_reach_the_whole_bank_and_reels_span_subjects():
    topics=[]
    for offset in range(15):
        day=(date(2026,10,12)+timedelta(days=offset)).isoformat()
        topics.extend(c['topic'] for c in quality.daily_plan(day,4,0))
        reels=quality.daily_plan(day,12,4)[2::3]
        assert {c['story_format'] for c in reels} == set(creative.FORMATS)
        assert len({creative.plan(c)['soundtrack'] for c in reels}) == 4
        assert set(Counter(c['subject'] for c in reels).values()) == {1,2}
    assert len(topics)==len(set(topics))==60


def test_every_example_fits_each_story_without_changing_answers():
    for i in range(lessons.TOTAL):
        base=quality.enrich(lessons.lesson('2026-10-12',i))
        assert base['topic'] in creative.HOOKS
        captions=[]
        for j,kind in enumerate(creative.FORMATS):
            c={**creative.attach(base,'2026-10-12',j),'story_format':kind}
            assert all(c[k]==base[k] for k in ('question','answer','solution','condition','why'))
            copy=editorial.authored(c);p=storyboard.plan(c);copy['storyboard']=p
            captions.append(copy['caption'])
            assert c['question'] in copy['caption'] and c['solution'] in copy['caption']
            assert len(copy['caption']+creative.caption_suffix(c)+reel.music_credit(c))<2200
            assert storyboard.validate(p,c)
            a,b,d,end=storyboard.beats(p)
            for t in (0,.6,a+.5,a+3,b+.6,d+.6):
                assert reel.frame(c,copy,t).size==(720,1280)
            assert all(len(text)<=200 and at+window<d for at,window,text in narration.scenes(c,p))
        assert len(set(captions))==4


def test_new_audio_has_distinct_non_silent_beds_and_matching_lengths(tmp_path):
    samples=[]
    for index,kind in enumerate(creative.FORMATS):
        c={**creative.attach(quality.enrich(lessons.lesson('2026-10-12',0)),'2026-10-12',index),
           'story_format':kind,'creative_seed':index}
        p=storyboard.plan(c);path=sound.bed(tmp_path/f'{index}.wav',p)
        with wave.open(str(path)) as wav:
            assert wav.getnframes()/wav.getframerate()==creative.TIMINGS[kind][-1]
            values=array('h',wav.readframes(wav.getnframes()))
            assert max(values)>500 and min(values)<-500
            assert max(abs(v) for v in values)<32767
            samples.append(values[:48000].tobytes())
    assert len(set(samples))==4


def test_legacy_snapshot_keeps_timeline_and_license():
    c=quality.enrich(lessons.lesson('2026-10-12',0))
    assert not creative.active(c)
    assert storyboard.beats(storyboard.plan(c))==(4,17,23,28)
    assert 'Kevin MacLeod' in reel.music_credit(c)


def test_partial_voice_falls_back_as_a_complete_story(tmp_path):
    from social.test_narration import wav
    c=creative.attach(quality.enrich(lessons.lesson('2026-10-12',0)),'2026-10-12',0)
    p=storyboard.plan(c);calls=[]
    def fetch(text):
        calls.append(text)
        return wav(1) if len(calls)==1 else None
    assert narration.prepare(c,p,tmp_path,fetch)==[]
    assert p['subtitles']==[]
    full=storyboard.plan(c)
    assert len(narration.prepare(c,full,tmp_path,lambda _:wav(1)))==3
    assert all(x['start']<x['end']<creative.TIMINGS[full['format']][2] for x in full['subtitles'])


def test_promotion_does_not_confuse_caption_repetition():
    c=quality.daily_plan('2026-10-12',4,2)[0]
    caption=editorial.authored(c)['caption']
    assert editorial.repeated(caption,[caption+creative.caption_suffix(c)+'\n\n'+reel.music_credit(c)+'\n\nJeeEdge daily 2026-10-12 / s00'])
