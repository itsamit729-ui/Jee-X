from collections import Counter
from datetime import date,timedelta
from social import lessons, quality, storyboard, editorial, worker


def test_daily_plan_balanced_unique_and_no_next_day_repeat():
    previous=set()
    for delta in range(40):
        day=(date(2026,10,7)+timedelta(days=delta)).isoformat()
        plan=quality.daily_plan(day,12,4)
        topics={c['topic'] for c in plan}
        assert len(topics)==12 and not topics & previous
        assert Counter(c['subject'] for c in plan)=={'PHYSICS':4,'CHEMISTRY':4,'MATHS':4}
        assert all(plan[i]['topic'] in storyboard.VISUAL_TOPICS for i in (2,5,8,11))
        previous=topics
        for total in range(1,13):
            for reels in range(min(4,total)+1):
                items=quality.daily_plan(day,total,reels)
                assert len({c['topic'] for c in items})==total


def test_all_authored_content_and_renders(tmp_path):
    for i in range(lessons.TOTAL):
        c=quality.enrich(lessons.lesson('2026-10-07',i))
        assert c['why'] and c['transfer_question'] and c['transfer_answer']
        copy=editorial.authored(c)
        assert len(copy['caption']) < 1200
        paths=worker.render(c,copy,tmp_path/str(i))
        assert len(paths)==6


def test_repeated_captions_ignore_tracking_numbers_and_music():
    text=editorial.authored(quality.daily_plan('2026-10-07',12,4)[0])['caption']
    assert editorial.repeated(text,[text+'\n\nMusic: a credit\nJeeEdge daily 2026-10-07 / s00'])
    assert editorial.repeated('Compute 2 plus 3 using addition.', ['Compute 20 plus 30 using addition.'])
    assert not editorial.repeated(text,['A completely unrelated educational topic with no matching content.'])


def test_richer_reel_reasoning_fits_every_visual_topic():
    from social import cinema
    for i in range(lessons.TOTAL):
        c=quality.enrich(lessons.lesson('2026-10-07',i))
        if c['topic'] in storyboard.VISUAL_TOPICS:
            for pace in ('brisk','steady'):
                plan={**storyboard.fallback(c),'pace':pace}
                for seconds in (11,14,16,25):
                    assert cinema.frame(c,plan,seconds).size==(720,1280)
