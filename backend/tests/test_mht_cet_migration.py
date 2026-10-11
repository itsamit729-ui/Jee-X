"""Guard upgrades from both divergent branches and repeat deployment startup."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://test:test@localhost/unused')


def load_migration():
    path = Path(__file__).resolve().parents[1] / 'scripts/add_mht_cet.py'
    spec = importlib.util.spec_from_file_location('mht_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('existing', ['bitsat', 'mht_cet', None])
def test_upgrade_preserves_both_exam_branches(monkeypatch, existing):
    migration = load_migration()
    inspector = MagicMock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{'name': 'in_main'}]
    def checks(table):
        if existing is None:
            return []
        column, name = ('exam', 'ck_questions_exam') if table == 'questions' else ('pattern', 'ck_tests_pattern')
        return [{'name': name, 'sqltext': f"{column} IN ('jee_main','jee_advanced','{existing}')"}]
    inspector.get_check_constraints.side_effect = checks
    engine = MagicMock()
    monkeypatch.setattr(migration, 'engine', engine)
    monkeypatch.setattr(migration, 'inspect', lambda _: inspector)
    monkeypatch.setattr('sys.argv', ['add_mht_cet.py'])
    migration.main()
    engine.begin.assert_not_called()  # dry run cannot mutate
    monkeypatch.setattr('sys.argv', ['add_mht_cet.py', '--apply'])
    migration.main()
    statements = [str(c.args[0]) for c in engine.begin.return_value.__enter__.return_value.execute.call_args_list]
    assert len(statements) == 3
    assert 'ADD COLUMN in_mht_cet BOOLEAN NOT NULL DEFAULT 0' in statements[0]
    for statement in statements[1:]:
        assert all(f"'{exam}'" in statement for exam in ('jee_main', 'jee_advanced', 'bitsat', 'mht_cet'))
        assert 'ADD CONSTRAINT' in statement
        assert 'DROP TABLE' not in statement and 'DELETE' not in statement
    # Model constraint and migration accept the same values.
    from app import models
    from sqlalchemy.schema import CreateTable
    from sqlalchemy.dialects.mysql import dialect
    for model in (models.Question, models.Test):
        ddl = str(CreateTable(model.__table__).compile(dialect=dialect()))
        assert all(f"'{exam}'" in ddl for exam in migration.QUESTION_EXAMS)


def test_current_schema_is_noop(monkeypatch):
    migration = load_migration()
    inspector = MagicMock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{'name': 'in_mht_cet'}]
    inspector.get_check_constraints.side_effect = lambda table: [{
        'name': 'ck_questions_exam' if table == 'questions' else 'ck_tests_pattern',
        'sqltext': "exam IN ('jee_main','jee_advanced','bitsat','mht_cet')"}]
    engine = MagicMock()
    monkeypatch.setattr(migration, 'engine', engine)
    monkeypatch.setattr(migration, 'inspect', lambda _: inspector)
    monkeypatch.setattr('sys.argv', ['add_mht_cet.py', '--apply'])
    migration.main()
    engine.begin.assert_not_called()
