from collections import Counter
from datetime import date
from social import art_direction as art, quality, lessons, editorial, storyboard, narration


def test_each_day_has_all_four_styles_in_each_media_kind():
    for d in range(8,18):
        plan=quality.daily_plan(f'2026-10-{d:02}',12,4)
        assert Counter(art.style(c) for i,c in enumerate(plan) if i%3==2)==dict.fromkeys(art.STYLES,1)
        assert Counter(art.style(c) for i,c in enumerate(plan) if i%3!=2)==dict.fromkeys(art.STYLES,2)
        for i,c in enumerate(plan):
            assert c['design_version']==3
            assert art.style(c)==art.style(dict(c))


def test_every_lesson_fits_every_art_direction(tmp_path):
    for i in range(lessons.TOTAL):
        base=quality.enrich(lessons.lesson('2026-10-08',i))
        for kind in art.STYLES:
            c={**base,'art_direction':kind};copy=editorial.authored(c)
            out=tmp_path/str(i)/kind;out.mkdir(parents=True)
            paths=art.carousel(c,copy,out)
            assert len(paths)=={'notebook':5,'casefile':4,'poster':4,'comparison':6}[kind]
            plan={**storyboard.fallback(c),'hook':copy['hook']}
            for t in (0,5,18,25):
                assert art.reel_frame(c,plan,t).size==(720,1280)


def test_caption_modes_change_structure_without_changing_math():
    original=quality.enrich(lessons.lesson('2026-10-08',30))
    values=[art.caption({**original,'art_direction':k}) for k in art.STYLES]
    assert len(set(values))==4
    assert values[0].startswith(original['question'])
    assert original['solution'] in values[0]
    assert values[1].startswith('My brain:')
    assert values[3].startswith(original['transfer_question'])
    assert all(original['condition'] in x for x in values)
    assert all('Applies when:' not in x and 'Check your reasoning:' not in x for x in values)


def test_teacher_can_accept_caption_without_topic_prefix(monkeypatch):
    c={**quality.enrich(lessons.lesson('2026-10-08',30)),'art_direction':'notebook'}
    draft={'hooks':['Double speed. How much braking distance?']*3,'caption':art.caption(c)}
    responses=iter([draft,{'approved':True,'chosen':0,'clarity':5,'educational_value':5,'hook_specificity':5,'payoff':5}])
    monkeypatch.setattr(editorial,'call',lambda *a,**k:next(responses))
    result=editorial.package(c,'reel')
    assert result['editorial_source']=='groq_reviewed'
    assert not result['caption'].startswith(c['topic'])


def test_every_lesson_has_an_original_joke_and_comic_audio_is_complete(tmp_path):
    from social.test_narration import wav
    for i in range(lessons.TOTAL):
        c={**quality.enrich(lessons.lesson('2026-10-08',i)),'art_direction':'casefile'}
        assert c['topic'] in art.HUMOR
        brain,reality=art.joke(c)
        plan=storyboard.fallback(c)
        scenes=narration.scenes(c,plan)
        assert len(scenes)==4
        assert scenes[0][2]==brain and scenes[1][2]==reality
        assert all(len(text)<=200 for _,_,text in scenes)
    calls=[]
    def partial(text):
        calls.append(text)
        return wav() if len(calls)==1 else None
    assert narration.prepare(c,plan,tmp_path,partial)==[]
    assert plan['subtitles']==[]
