import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import worker


class WorkerTests(unittest.TestCase):
    def test_calculated_problem_answers(self):
        import random
        start = date(2026, 1, 1)
        for offset in range(366):
            day = (start + timedelta(days=offset)).isoformat()
            n = random.Random(day).randint(2, 9)
            item = worker.problem(day)
            expected = [f'{n / 2:g} ohm', str(4 + n), f'{n} mol',
                        f'{8 * n} J', '1/3', f'{n / 2:g} mol/L'][date.fromisoformat(day).toordinal() % 6]
            self.assertEqual(item['answer'], expected)

    def test_all_templates_render(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(worker, 'OUT', Path(directory)):
            for offset in range(6):
                day = (date(2026, 10, 6) + timedelta(days=offset)).isoformat()
                paths = worker.render(worker.problem(day), {'hook': 'Could this tiny mistake cost you marks?'})
                self.assertEqual(len(paths), 4)
                for path in paths:
                    with worker.Image.open(path) as image:
                        self.assertEqual(image.size, (1080, 1350))

    def test_ai_copy_rejects_false_pyq_claim(self):
        result = {'candidates': [{'content': {'parts': [{'text': json.dumps({
            'hook': 'Actual PYQ', 'caption': 'Try it'})}]}}]}
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), patch.object(worker, 'request', return_value=result):
            with self.assertRaises(worker.ServiceError):
                worker.ai_copy(worker.problem('2026-10-06'), [])

    def test_ambiguous_submission_records_before_mutation(self):
        writes = []
        def save(path, data):
            if path == 'state/ledger.json':
                writes.append(json.loads(data))
            return {'commit': {'sha': 'test'}}
        def mutation(*args, **kwargs):
            self.assertEqual(writes[-1]['history'][-1]['state'], 'submitting')
            raise worker.ServiceError('timeout')
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test', 'BUFFER_API_KEY': 'test', 'GEMINI_API_KEY': 'test', 'PREVIEW_ONLY': 'false'
        }), patch.object(worker, 'OUT', Path(directory)), patch.object(worker, 'find_channel', return_value=('org', {'id': 'channel'})), patch.object(worker, 'posts', return_value=[]), patch.object(worker, 'ensure_media_branch'), patch.object(worker, 'load_file', return_value=None), patch.object(worker, 'save_file', side_effect=save), patch.object(worker, 'ai_copy', return_value={'hook': 'Try this', 'caption': 'Solve and swipe'}), patch.object(worker, 'request') as request, patch.object(worker, 'buffer', side_effect=mutation):
            import io
            raw = io.BytesIO()
            worker.Image.new('RGB', (1080, 1350)).save(raw, format='PNG')
            request.return_value = raw.getvalue()
            with self.assertRaises(worker.ServiceError):
                worker.main()
            self.assertEqual(len(writes), 1)

    def test_unresolved_record_never_resubmits(self):
        day = worker.datetime.now(worker.ZoneInfo('Asia/Kolkata')).date().isoformat()
        ledger = {'history': [{'day': day, 'state': 'submitting'}]}
        saved = {'content': worker.base64.b64encode(json.dumps(ledger).encode()).decode()}
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test', 'BUFFER_API_KEY': 'test', 'GEMINI_API_KEY': 'test', 'PREVIEW_ONLY': 'false'}), patch.object(worker, 'find_channel', return_value=('org', {'id': 'channel'})), patch.object(worker, 'posts', return_value=[]), patch.object(worker, 'ensure_media_branch'), patch.object(worker, 'load_file', return_value=saved), patch.object(worker, 'buffer') as buffer:
            with self.assertRaises(worker.ServiceError):
                worker.main()
            buffer.assert_not_called()


if __name__ == '__main__':
    unittest.main()
