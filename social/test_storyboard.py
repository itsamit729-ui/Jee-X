import pytest
from social import storyboard,lessons,editorial,cinema


def content(topic='Projectile range'):
 return next(lessons.lesson('2026-10-07',i) for i in range(lessons.TOTAL) if lessons.lesson('2026-10-07',i)['topic']==topic)


def test_invalid_ai_plan_falls_back_without_changing_math(monkeypatch):
 c=content();before=c.copy()
 monkeypatch.setattr(editorial,'call',lambda *a,**k:{'format':'run_python','code':'do something'})
 assert storyboard.plan(c)==storyboard.fallback(c)
 assert c==before


def test_visual_direction_does_not_spend_an_extra_ai_call(monkeypatch):
 def forbidden(*a,**kw):raise AssertionError('No cosmetic AI request')
 monkeypatch.setattr(editorial,'call',forbidden)
 c=content()
 assert storyboard.plan(c)==storyboard.fallback(c)
 assert storyboard.beats(storyboard.plan(c))==(4,17,23,28)


def test_all_visual_topics_and_story_variants_fit():
 for topic in storyboard.VISUAL_TOPICS:
  c=content(topic)
  for form in storyboard.FORMATS:
   for hook in range(3):
    plan={**storyboard.fallback(c),'format':form,'hook_index':hook}
    for t in (0,4.5,10.5,18,21,25):
     assert cinema.frame(c,plan,t).size==(720,1280)


def test_visual_reel_pool_has_no_daily_repeats():
 for day in ('2026-10-07','2026-10-08','2026-10-09'):
  topics=[lessons.visual_lesson(day,i)['topic'] for i in range(10)]
  assert len(set(topics))==10
  assert set(topics)<=set(storyboard.VISUAL_TOPICS)


def test_animation_changes_inside_diagram():
 for topic in storyboard.VISUAL_TOPICS:
  c=content(topic);plan=storyboard.fallback(c)
  a=cinema.frame(c,plan,1).crop((65,380,640,850))
  b=cinema.frame(c,plan,3.5).crop((65,380,640,850))
  assert a.tobytes()!=b.tobytes(),topic
