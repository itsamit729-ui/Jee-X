from unittest.mock import patch
import pytest
from social import editorial, lessons, worker


def test_editorial_selects_reviewed_hook_without_changing_lesson():
    content=lessons.lesson('2026-10-06',0)
    before=dict(content)
    with patch.object(editorial,'call',side_effect=[{'hooks':['Try this shortcut','A useful check','Avoid this trap'],
         'caption':editorial.authored(content)['caption']},{'approved':True,'chosen':2,'clarity':4,'educational_value':5,'hook_specificity':5,'payoff':5}]):
        assert editorial.package(content,'reel')['hook']=='Avoid this trap'
    assert content==before


@pytest.mark.parametrize('failure',[worker.ServiceError('quota'), ValueError('bad JSON')])
def test_editorial_falls_back_without_paid_provider(failure):
    with patch.object(editorial,'call',side_effect=failure):
        result=editorial.package(lessons.lesson('2026-10-06',1),'reel')
    assert 'bio' not in result['caption'] and 'http' not in result['caption']


def test_rejected_editorial_is_not_published():
    with patch.object(editorial,'call',side_effect=[{'hooks':['Try it','Check it','Save it'],'caption':'Save this rule.'},
                                                  {'approved':False,'chosen':0}]):
        result=editorial.package(lessons.lesson('2026-10-06',1),'carousel')
    assert result == editorial.authored(lessons.lesson('2026-10-06',1))


def test_low_quality_ai_falls_back_to_specific_lesson():
    content=lessons.lesson('2026-10-06',0)
    draft={'hooks':['Understand the rule','Check this condition','Reason through it'],'caption':editorial.authored(content)['caption']}
    with patch.object(editorial,'call',side_effect=[draft,{'approved':True,'chosen':0,'clarity':3,'educational_value':5,'hook_specificity':5,'payoff':5}]):
        assert editorial.package(content,'carousel')==editorial.authored(content)
