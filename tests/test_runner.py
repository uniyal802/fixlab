"""Real Docker integration tests; intentionally skipped when Docker is absent."""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import core

def available():
    if not shutil.which('docker'): return False
    try:
        return subprocess.run(['docker','image','inspect','fixlab-runner:local'],capture_output=True,timeout=5).returncode==0
    except (OSError,subprocess.TimeoutExpired):return False

@unittest.skipUnless(available(),'Build Docker runner to execute integration tests')
class RunnerTests(unittest.TestCase):
    tests='import unittest\nfrom solution import average\nclass TestAverage(unittest.TestCase):\n    def test_empty(self): self.assertEqual(average([]),0)\n    def test_normal(self): self.assertEqual(average([2,4]),3)\n'
    def test_regression_workflow(self):
        original=core.run_code('def average(xs):\n    return sum(xs)/len(xs)\n',self.tests)
        fixed=core.run_code('def average(xs):\n    return sum(xs)/len(xs) if xs else 0\n',self.tests)
        self.assertFalse(original['passed'])
        self.assertTrue(fixed['passed'])
        self.assertEqual(fixed['report']['tests_run'],2)
        self.assertGreater(fixed['report']['coverage_percent'],0)
    def test_empty_suite_rejected(self):
        self.assertFalse(core.run_code('pass','pass')['passed'])
    def test_network_isolation(self):
        tests='import unittest, socket\nclass TestNetwork(unittest.TestCase):\n    def test_blocked(self):\n        with self.assertRaises(OSError): socket.create_connection(("1.1.1.1",443),timeout=1)\n'
        self.assertTrue(core.run_code('pass',tests)['passed'])
