import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import core
from worker import recover_after_restart

class CoreTests(unittest.TestCase):
    def test_job_persists_transitions_and_cancellation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(core, 'DB', Path(tmp)/'data'/'db.sqlite'):
            accepted = core.submit_job('analysis', {'code': 'x=1', 'error': ''})
            self.assertEqual(core.get_job(accepted['job_id'])['state'], 'queued')
            self.assertEqual(core.claim_job(), accepted['job_id'])
            self.assertEqual(core.get_job(accepted['job_id'])['attempts'], 1)
            core.finish_job(accepted['job_id'], 'succeeded', result={'id': 'saved'})
            self.assertEqual(core.get_job(accepted['job_id'])['result'], {'id': 'saved'})
            cancelled = core.submit_job('test_run', {'id': 'session'})
            self.assertEqual(core.cancel_job(cancelled['job_id'])['state'], 'cancelled')
            failed = core.submit_job('analysis', {'code': 'x=1', 'error': ''})
            core.claim_job()
            core.finish_job(failed['job_id'], 'failed', error='model unavailable')
            self.assertEqual(core.get_job(failed['job_id'])['error'], 'model unavailable')

    def test_job_records_survive_database_reopen(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(core, 'DB', Path(tmp)/'jobs.sqlite'):
            job = core.submit_job('analysis', {'code': 'pass', 'error': ''})
            first = core.get_job(job['job_id'])
            second = core.get_job(job['job_id'])
            self.assertEqual(first['created'], second['created'])
            self.assertEqual(second['state'], 'queued')

    def test_worker_restart_requeues_once_then_fails_stale_job(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(core, 'DB', Path(tmp)/'jobs.sqlite'):
            first=core.submit_job('analysis', {'code':'pass','error':''})
            self.assertEqual(core.claim_job(), first['job_id'])
            recover_after_restart()
            self.assertEqual(core.get_job(first['job_id'])['state'], 'queued')
            self.assertEqual(core.claim_job(), first['job_id'])
            recover_after_restart()
            self.assertEqual(core.get_job(first['job_id'])['state'], 'failed')

    def test_invalid_ai_response(self):
        for response in ({}, {'summary':'x','explanation':'x','fixed_code':'def :','tests':'pass'}):
            with self.assertRaises((ValueError, SyntaxError)):
                core.validate_analysis(response)

    def test_sessions_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(core, 'DB', Path(tmp)/'data'/'db.sqlite'):
            payload={'analysis':{'summary':'Empty-input bug'},'review':'pending'}
            session_id=core.save(payload)
            payload['review']='accepted'
            core.save(payload,session_id)
            self.assertEqual(core.get(session_id)['review'],'accepted')
            self.assertEqual(len(core.history()),1)
            with self.assertRaises(ValueError):core.get('missing')

    def test_ai_adapter_and_diff(self):
        response=unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'response':json.dumps({'summary':'Fix zero division','explanation':'Handle empty input','fixed_code':'def average(xs):\n    return sum(xs)/len(xs) if xs else 0\n','tests':'import unittest\nfrom solution import average\nclass Tests(unittest.TestCase):\n    def test_empty(self): self.assertEqual(average([]), 0)\n'})}).encode()
        with tempfile.TemporaryDirectory() as tmp, patch.object(core,'DB',Path(tmp)/'data'/'db.sqlite'),patch.object(core.urllib.request,'urlopen',return_value=response):
            session=core.analyze('def average(xs):\n    return sum(xs)/len(xs)\n','ZeroDivisionError')
            self.assertIn('--- original.py',session['diff'])
            self.assertEqual(core.get(session['id'])['id'],session['id'])

    def test_missing_docker_fails_closed(self):
        with patch.object(core.subprocess,'Popen',side_effect=FileNotFoundError):
            with self.assertRaisesRegex(ValueError,'Docker is required'):
                core.run_code('pass','pass')

if __name__=='__main__':unittest.main()
