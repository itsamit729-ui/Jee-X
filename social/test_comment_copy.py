import pytest
from social import comment_copy


def test_public_reply_requires_review(monkeypatch):
    results=iter([{'action':'reply','reply':'At fixed mass, energy scales with speed squared.','reason':''},{'approved':False}])
    monkeypatch.setattr(comment_copy,'call',lambda *a:next(results))
    assert comment_copy.decide({'rule':'K proportional to v squared'},'Why?',[])[0]=='review'


def test_links_never_published(monkeypatch):
    monkeypatch.setattr(comment_copy,'call',lambda *a:{'action':'reply','reply':'Visit https://example.com','reason':''})
    assert comment_copy.decide({},'Hi',[])[0]=='review'


def test_review_can_resume_without_new_draft(monkeypatch):
    calls=[]
    def call(system,data,schema):calls.append(data);return {'approved':True}
    monkeypatch.setattr(comment_copy,'call',call)
    assert comment_copy.decide({},'Thanks',[],candidate='Glad it helped!')[0]=='reply'
    assert len(calls)==1
