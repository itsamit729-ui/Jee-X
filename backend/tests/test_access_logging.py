import logging
from app.access_logging import HealthProbeFilter


def test_health_filter_retains_failures_and_media():
    f=HealthProbeFilter()
    for path,status,expected in [('/health',200,False),('/health?probe=1',200,False),('/health',503,True),('/api/social/assets/a.mp4',206,True),('/api/social/trigger',202,True)]:
        record=logging.LogRecord('uvicorn.access',20,'',0,'%s %s %s %s %s',('client','GET',path,'1.1',status),None)
        assert f.filter(record)==expected
    assert f.filter(logging.LogRecord('uvicorn.access',20,'',0,'unexpected format',(),None))
