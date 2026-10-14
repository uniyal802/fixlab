import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import core

class CoreTests(unittest.TestCase):
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
