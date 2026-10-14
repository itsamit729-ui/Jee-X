"""New visual scenes, exact maths, complete narration and immutable legacy plans."""
import copy
from collections import Counter
from social import advanced,creative,editorial,narration,reel,retention,storyboard


def test_all_advanced_lessons_fit_every_cut_with_every_story_and_complete_working():
    assert set(retention.BRIEFS)=={c['topic'] for c in advanced.BANK}
    assert max(b-a for a,b in zip(retention.CUTS,retention.CUTS[1:]))<=8
    for base in advanced.BANK:
        original=copy.deepcopy(base)
        for kind in creative.FORMATS:
            c={**creative.attach(base,'2026-10-15',0),'story_format':kind}
            p=storyboard.plan(c);draft={**editorial.authored(c),'storyboard':p}
            assert storyboard.beats(p)==(8,22,36,40)
            for t in (0,3.5,8.5,15.5,22.5,30.5,33.5,36.5):
                try:assert reel.frame(c,draft,t).size==(720,1280)
                except Exception as error:raise AssertionError((base['topic'],kind,t,str(error))) from error
            lines=narration.scenes(c,p)
            assert len(lines)==5
            assert tuple(text for _,_,text in lines[1:4])==retention.brief(c)['voice']
            assert all(0<len(text)<=200 and at+window<36 for at,window,text in lines)
            assert sum(len(text.encode())+32 for _,_,text in lines)<=700
            assert c['question'] in draft['caption'] and c['solution'] in draft['caption']
        assert original==base


def test_new_visual_models_change_between_frames_and_legacy_plan_keeps_its_renderer():
    for base in advanced.BANK:
        c=creative.attach(base,'2026-10-15',0);draft={**editorial.authored(c),'storyboard':storyboard.plan(c)}
        if retention.brief(c)['visual'] not in ('algebra','discriminant'):
            first=reel.frame(c,draft,.4).crop((70,395,625,700)).tobytes()
            later=reel.frame(c,draft,8.4 if retention.brief(c)['visual']=='capacitors' else 1.1).crop((70,395,625,700)).tobytes()
            assert first!=later,base['topic']
    legacy={**creative.attach(advanced.BANK[0],'2026-10-15',0)}
    legacy.pop('story_engine')
    assert 'engine' not in storyboard.plan(legacy)
    assert storyboard.beats(storyboard.plan(legacy))==creative.DEEP_TIMINGS[legacy['story_format']]
    assert len(narration.scenes(legacy,storyboard.plan(legacy)))==3


def test_chart_values_and_worked_voice_follow_the_authored_calculation():
    from fractions import Fraction
    def values(topic):return [Fraction(v).limit_denominator(24) for _,v in retention.BRIEFS[topic][3]]
    assert sum(values('Rolling energy and height')[:2])==values('Rolling energy and height')[2]
    assert sum(values('Parallel first order pathways'))==1
    assert sum(values('Alternating binomial square sum'))==6
    assert sum(values('Onto function inclusion exclusion')[:3])==150
    assert sum(values('Gas equilibrium dissociation')[:2])==values('Gas equilibrium dissociation')[2]
    weights=values('Biased coin Bayes update')
    assert weights[0]/sum(weights)==Fraction(4,5)


def test_narration_cannot_leave_only_a_misconception_and_four_videos_fit_local_tts_tokens(tmp_path):
    from social.test_narration import wav
    c=creative.attach(advanced.BANK[0],'2026-10-15',0);p=storyboard.plan(c);calls=[]
    def partial(text):
        calls.append(text)
        return wav(1) if len(calls)<5 else None
    assert narration.prepare(c,p,tmp_path,partial)==[]
    assert p['subtitles']==[]
    full=storyboard.plan(c)
    assert len(narration.prepare(c,full,tmp_path,lambda text:wav(1)))==5
    assert full['subtitles']
    # The local ledger reserves UTF-8 bytes + 32, not guessed provider tokens.
    maximum=max(sum(len(line.encode())+32 for _,_,line in retention.scenes(
        creative.attach(base,'2026-10-15',0),storyboard.plan(creative.attach(base,'2026-10-15',0)))) for base in advanced.BANK)
    assert maximum*4<3200


def test_optional_five_reel_plan_stays_distinct_and_within_authored_daily_voice_budget():
    from datetime import date,timedelta
    from social import quality
    for offset in range(32):
        day=(date(2026,10,15)+timedelta(days=offset)).isoformat()
        lessons=[c for i,c in enumerate(quality.daily_plan(day,12,5)) if (i+1)*5//12>i*5//12]
        assert len(lessons)==5 and len({c['topic'] for c in lessons})==5
        assert set(Counter(c['subject'] for c in lessons).values())=={1,2}
        # Allow the maximum reviewed English hook length instead of our shorter opening.
        budget=sum(sum(len(text.encode())+32 for _,_,text in retention.scenes(c,{**storyboard.plan(c),'hook':'X'*65})) for c in lessons)
        assert budget<=3200
