"""Deep Reel selection, immutable working, arithmetic and safe scene layouts."""
from collections import Counter
from datetime import date,timedelta
from fractions import Fraction
import math
from social import advanced,creative,editorial,quality,reel,storyboard


def test_four_reels_use_deep_bank_with_subject_balance_and_no_adjacent_repeat():
    seen=set();previous=set()
    for day in range(16):
        when=(date(2026,10,14)+timedelta(days=day)).isoformat()
        videos=quality.daily_plan(when,12,4)[2::3]
        assert len(videos)==4
        assert all(c['content_tier']==advanced.TIER for c in videos)
        assert set(Counter(c['subject'] for c in videos).values())=={1,2}
        assert {c['story_format'] for c in videos}==set(creative.FORMATS)
        topics={c['topic'] for c in videos}
        assert len(topics)==4 and not topics & previous
        previous=topics;seen|=topics
        assert all(c['journey']=='practice' for c in videos)
    assert seen=={c['topic'] for c in advanced.BANK}
    assert len({advanced.manual('2026-10-14',i)['topic'] for i in range(24)})==24


def test_every_deep_lesson_fits_all_formats_and_keeps_its_three_steps():
    for base in advanced.BANK:
        assert len(base['worked_steps'])==3
        assert len(base['hook'])<=65 and len(base['hook'].split())<=10
        for kind in creative.FORMATS:
            c={**creative.attach(base,'2026-10-14',0),'story_format':kind}
            copy=editorial.authored(c);p=storyboard.plan(c);copy['storyboard']=p
            a,b,d,end=storyboard.beats(p)
            assert 40<=end<=45
            assert c['solution'] in copy['caption']
            assert len(copy['caption']+creative.caption_suffix(c)+reel.music_credit(c))<2200
            for t in (0,a+.5,b+.1,b+(d-b)/2,d-.1,d+.2):
                try:assert reel.frame(c,copy,t).size==(720,1280)
                except Exception as error:raise AssertionError(f"{c['topic']} / {kind} / {t}: {error}") from error


def test_key_multistep_answers_recomputed_independently():
    bank={c['topic']:c for c in advanced.BANK}
    # Mechanics: wedge recoil, total rolling energy and centripetal hinge load.
    wedge=Fraction(1,4)/(1-Fraction(1,4))
    assert bank['Moving wedge constraint']['answer'].startswith(f'g/{wedge.denominator}')
    rolling=Fraction(1,2)+Fraction(1,2)*Fraction(2,5)
    assert bank['Rolling energy and height']['answer']==f'{rolling.numerator}v^2/({rolling.denominator}g)'
    hinge=1+Fraction(3,2)
    assert bank['Falling rod hinge reaction']['answer']==f'{hinge.numerator}mg/{hinge.denominator} upward'
    lost=Fraction(1,2)+Fraction(1,2)*2*Fraction(1,2)**2
    assert bank['Opposed capacitor charge sharing']['answer']==f'{lost.numerator}CV^2/{lost.denominator}'
    assert math.isclose(math.degrees(math.acos(.5)),60)
    # Concentrations and branching: stoichiometry precedes the equilibrium law.
    assert math.sqrt(4/(4+4*3))==float(Fraction(bank['Gas equilibrium dissociation']['answer']))
    assert math.isclose(4e-12/.1**2,4e-10)
    assert f'{5+math.log10((10-5)/(20+5)):.2f}' in bank['Buffer after neutralisation']['answer']
    assert f'{14-(5+math.log10(20/(60-20))):.2f}' in bank['Base buffer after acid']['answer']
    assert math.isclose(.05916/2*math.log10(1/.01),float(bank['Concentration cell polarity']['answer'].split()[0]))
    assert float(bank['Reverse and scale equilibrium']['answer'])==round((100/1000)**2,2)
    association=2*(1-Fraction(100,150))
    assert Fraction(bank['Association apparent molar mass']['answer'])==association
    # Bayes and counting, without using the authored explanatory formulas.
    posterior=Fraction(1,3)/(Fraction(1,3)+Fraction(2,3)*Fraction(1,8))
    assert Fraction(bank['Biased coin Bayes update']['answer'])==posterior
    assert sum((-1)**k*math.comb(4,k)**2 for k in range(5))==int(bank['Alternating binomial square sum']['answer'])
    onto=sum((-1)**k*math.comb(3,k)*(3-k)**5 for k in range(4))
    assert onto==int(bank['Onto function inclusion exclusion']['answer'])
    inverse_second=-Fraction(6,4**3)
    assert Fraction(bank['Inverse function second derivative']['answer'])==inverse_second
