import os
os.environ.setdefault('DATABASE_URL','mysql+pymysql://test:test@localhost/unused')
import hashlib
import pytest
from app.services import social_pipeline as pipeline
from test_social_slots import setup


def test_every_checkpoint_key_fits_the_actual_mysql_column_and_preserves_valid_legacy_keys():
    day='2026-10-15:s08'
    for prefix in ['prepared','progress','delivery','confirmation','youtube-channel','youtube-confirmation','youtube-caption-repair','x'*200]:
        result=pipeline.key(prefix,day)
        assert len(result)<=48
        assert result==pipeline.key(prefix,day)
        assert result!=pipeline.key(prefix,'2026-10-15:s09')
        if len(prefix)<=15:assert result==prefix+':'+hashlib.sha256(day.encode()).hexdigest()[:32]
    assert pipeline.key('youtube-caption-repair',day)!=pipeline.key('youtube-caption-other',day)


def test_invalid_explicit_cache_names_fail_before_the_database_write(setup):
    _,factory,_,_=setup
    with factory() as db:
        with pytest.raises(ValueError,match='48-character storage limit'):
            pipeline.write(db,'x'*49,{'post_id':'existing'})
        assert pipeline.read(db,'x'*49) is None
