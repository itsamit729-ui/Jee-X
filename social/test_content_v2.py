"""Contracts that protect content diversity, correct answers and hook delivery."""
from datetime import date, timedelta
from fractions import Fraction
import math
from social import lessons, quality, editorial, storyboard, narration, reel


def test_full_five_day_bank_without_repetition():
    topics=[]
    for day in range(5):
        plan=quality.daily_plan((date(2026,10,7)+timedelta(days=day)).isoformat(),12,4)
        topics.extend(c['topic'] for c in plan)
    assert len(topics)==len(set(topics))==60


def test_reviewed_hook_reaches_pixels_and_speech():
    c=quality.enrich(lessons.lesson('2026-10-07',30))
    plan=storyboard.fallback(c)
    hook='Double speed. Four times the stopping distance?'
    a=reel.frame(c,{'storyboard':plan,'hook':hook},0)
    b=reel.frame(c,{'storyboard':plan,'hook':'A different opening'},0)
    assert a.crop((54,175,624,340)).tobytes()!=b.crop((54,175,624,340)).tobytes()
    assert narration.scenes(c,{**plan,'hook':hook})[0][2]==hook
    assert storyboard.beats(plan)[0]==4


def test_original_answer_calculations():
    bank={c['topic']:c for c in lessons.EXTRA}
    # Independent recomputation of especially easy-to-misstate examples.
    assert Fraction(sum(Fraction(1,k*(k+1)) for k in range(1,11))) == Fraction(bank['Telescoping sum']['answer'])
    outcomes=['HH','HT','TH','TT'];remaining=[x for x in outcomes if 'H' in x]
    assert Fraction(sum(x=='HH' for x in remaining),len(remaining)) == Fraction(bank['Conditional probability']['answer'])
    assert math.comb(5,2)*2**2 == int(bank['Binomial coefficients']['answer'])
    assert abs((3+4j)**2) == float(bank['Complex modulus']['answer'])
    assert (100**2-60**2)/(4*100) == float(bank['Lens displacement']['answer'].split()[0])
    assert 10*(20/10)**2 == float(bank['Stopping distance']['answer'].split()[0])
    assert -0.05916/2*math.log10(10) == float(bank['Nernst shift']['answer'].split()[0])
    assert 1+.8 == float(bank['Colligative dissociation']['answer'])
    acid=(-1e-5+math.sqrt(1e-10+4*1e-5*.001))/2
    assert round(-math.log10(acid),2)==4.02


def test_tts_reservation_fits_existing_free_budget():
    for d in range(7,12):
        plan=quality.daily_plan(f'2026-10-{d:02}',12,4)
        scripts=[text for c in plan[2::3] for _,_,text in narration.scenes(c,storyboard.fallback(c))]
        assert len(scripts)==12
        assert all(len(text)<=200 for text in scripts)
        assert sum(len(text.encode())+32 for text in scripts)<3200


def test_three_voice_scenes_have_measured_subtitles(tmp_path):
    from social.test_narration import wav
    c=quality.enrich(lessons.lesson('2026-10-07',30));plan=storyboard.fallback(c)
    assert len(narration.prepare(c,plan,tmp_path,lambda _:wav(2)))==3
    cues=plan['subtitles']
    assert all(x['start']<x['end']<=28 for x in cues)
    assert all(a['end']<=b['start']+1e-8 for a,b in zip(cues,cues[1:]))
    assert ' '.join(x['text'] for x in cues)==' '.join(t for _,_,t in narration.scenes(c,plan))


def test_generic_hook_review_score_falls_back(monkeypatch):
    c=quality.enrich(lessons.lesson('2026-10-07',30))
    values=iter([{'hooks':['A generic shortcut','Try this now','Learn a concept'],'caption':editorial.authored(c)['caption']},
        {'approved':True,'chosen':0,'clarity':5,'educational_value':5,'hook_specificity':2,'payoff':5}])
    monkeypatch.setattr(editorial,'call',lambda *a,**kw:next(values))
    assert editorial.package(c,'reel')==editorial.authored(c)
