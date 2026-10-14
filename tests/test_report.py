"""Validate runner reporting using only fixed, trusted repository fixtures."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
RUNNER=Path(__file__).resolve().parents[1]/'backend'/'runner.py'

class ReportTests(unittest.TestCase):
    def run_fixture(self,code,tests):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'solution.py').write_text(code)
            Path(tmp,'test_solution.py').write_text(tests)
            response=subprocess.run([sys.executable,'-B',str(RUNNER)],cwd=tmp,capture_output=True,text=True,timeout=5)
            line=next(line for line in response.stdout.splitlines() if line.startswith('FIXLAB_REPORT='))
            return response.returncode,json.loads(line.split('=',1)[1])
    def test_failure_and_success_have_coverage_reports(self):
        tests='import unittest\nfrom solution import average\nclass T(unittest.TestCase):\n    def test_empty(self): self.assertEqual(average([]),0)\n    def test_normal(self): self.assertEqual(average([2,4]),3)\n'
        failed,report=self.run_fixture('def average(xs):\n    return sum(xs)/len(xs)\n',tests)
        self.assertEqual(failed,1);self.assertEqual(report['errors'],1)
        passed,report=self.run_fixture('def average(xs):\n    if not xs:\n        return 0\n    return sum(xs)/len(xs)\n',tests)
        self.assertEqual(passed,0);self.assertEqual(report['tests_run'],2)
        self.assertEqual(report['coverage_percent'],100.0)
    def test_no_tests_and_all_skipped_fail(self):
        self.assertEqual(self.run_fixture('pass','pass')[0],1)
        tests='import unittest\nclass T(unittest.TestCase):\n    @unittest.skip("skip")\n    def test_empty(self): pass\n'
        self.assertEqual(self.run_fixture('pass',tests)[0],1)
