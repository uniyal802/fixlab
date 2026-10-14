"""Container-only regression runner with structured results and line coverage."""
import ast
import io
import json
import os
import sys
import trace
import unittest
sys.path.insert(0, os.getcwd())

output = io.StringIO()
runner = unittest.TextTestRunner(stream=output, verbosity=2)
tracer = trace.Trace(count=True, trace=False)
result = None
error = None
try:
    def execute():
        suite = unittest.defaultTestLoader.discover('.', pattern='test_solution.py')
        return runner.run(suite)
    result = tracer.runfunc(execute)
except BaseException as exc:
    error = str(exc)

source = os.path.abspath('solution.py')
# Statement-line coverage, explicitly excluding blank lines and comments.
try:
    tree = ast.parse(open(source).read())
    executable = {node.lineno for node in ast.walk(tree) if isinstance(node, ast.stmt)}
except (OSError, SyntaxError):
    executable = set()
hits = {line for (filename, line), count in tracer.results().counts.items() if os.path.abspath(filename) == source and count > 0}
covered = executable & hits
report = {
    'tests_run': result.testsRun if result else 0,
    'failures': len(result.failures) if result else 0,
    'errors': len(result.errors) if result else 1,
    'skipped': len(result.skipped) if result else 0,
    'coverage_percent': round(100 * len(covered) / len(executable), 1) if executable else None,
    'covered_lines': sorted(covered),
    'missing_lines': sorted(executable - hits),
    'coverage_kind': 'Python statement-line coverage',
}
print(output.getvalue()[:24000])
if error:
    print(error)
print('FIXLAB_REPORT=' + json.dumps(report), flush=True)
sys.exit(0 if result and result.testsRun > 0 and result.testsRun > len(result.skipped) and result.wasSuccessful() else 1)
