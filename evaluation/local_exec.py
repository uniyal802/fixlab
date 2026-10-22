"""Trusted-code-only local executor.

WARNING: this runs code directly on the host with no isolation. It exists
only for repository-authored, trusted inputs: validating the bundled dataset
and unit-testing the evaluation harness with stubbed model output. Never pass
it AI-generated code. Real evaluation runs use backend/core.py:run_code,
which executes inside the locked-down Docker runner.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / 'backend' / 'runner.py'


def run_trusted_local(code, tests, timeout=20):
    """Same result shape as core.run_code, without Docker."""
    with tempfile.TemporaryDirectory(prefix='fixlab-trusted-') as folder:
        (Path(folder) / 'solution.py').write_text(code)
        (Path(folder) / 'test_solution.py').write_text(tests)
        started = time.monotonic()
        try:
            process = subprocess.run([sys.executable, '-B', str(RUNNER)], cwd=folder, capture_output=True, timeout=timeout, text=True, errors='replace')
        except subprocess.TimeoutExpired:
            return {'passed': False, 'exit_code': None, 'output': 'Execution timed out', 'timed_out': True}
    text = (process.stdout or '') + (process.stderr or '')
    report = None
    for line in text.splitlines():
        if line.startswith('FIXLAB_REPORT='):
            try:
                report = json.loads(line[len('FIXLAB_REPORT='):])
            except json.JSONDecodeError:
                pass
    passed = process.returncode == 0 and report is not None and report.get('tests_run', 0) > 0
    return {'passed': passed, 'exit_code': process.returncode, 'output': text[:32000], 'timed_out': False, 'duration_seconds': round(time.monotonic() - started, 2), 'report': report}
