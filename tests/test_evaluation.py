"""Tests for the evaluation harness. Model output is stubbed and execution uses
the trusted local executor; no Ollama or Docker is needed."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from evaluation.cases import CASES
from evaluation.local_exec import run_trusted_local
from evaluation.metrics import percentile, summarize, wilson
from evaluation.mutate import mutants
import core
from evaluation import run_eval
from evaluation.run_eval import check_dataset, evaluate_case, render_report

BY_ID = {c['id']: c for c in CASES}
CASE = BY_ID['median_even']


def stub(fixed, tests):
    return lambda code, error: {'analysis': {'fixed_code': fixed, 'tests': tests}}


class DatasetTests(unittest.TestCase):
    def test_ids_are_unique_and_fields_present(self):
        self.assertEqual(len({c['id'] for c in CASES}), len(CASES))
        for c in CASES:
            for key in ('id', 'category', 'error', 'code', 'fixed', 'tests'):
                self.assertTrue(c[key].strip(), (c['id'], key))

    def test_buggy_fails_and_reference_fix_passes(self):
        self.assertEqual(check_dataset(run_trusted_local), [])


class MutationTests(unittest.TestCase):
    def test_deterministic_distinct_and_valid(self):
        source = CASE['fixed']
        first = mutants(source, 6, seed=1)
        self.assertEqual(first, mutants(source, 6, seed=1))
        codes = [m['code'] for m in first]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(0 < len(first) <= 6)
        for code in codes:
            compile(code, '<m>', 'exec')

    def test_limit_and_empty(self):
        self.assertLessEqual(len(mutants(CASE['fixed'], 2)), 2)
        self.assertEqual(mutants('x = "text"\n', 5), [])


class MetricTests(unittest.TestCase):
    def test_wilson(self):
        self.assertEqual(wilson(0, 0), (0.0, 0.0))
        low, high = wilson(10, 20)
        self.assertAlmostEqual(low, 0.299, places=2)
        self.assertAlmostEqual(high, 0.701, places=2)
        self.assertEqual(wilson(20, 20)[1], 1.0)

    def test_percentile(self):
        self.assertIsNone(percentile([], 95))
        self.assertEqual(percentile([1, 2, 3, 4], 50), 2)
        self.assertEqual(percentile([1, 2, 3, 4], 95), 4)


class EvaluateCaseTests(unittest.TestCase):
    def run_case(self, analyze, executor=run_trusted_local, mutant_limit=0):
        return evaluate_case(CASE, analyze, executor, mutant_limit)

    def test_good_fix_and_good_tests_are_verified(self):
        result = self.run_case(stub(CASE['fixed'], CASE['tests']))
        self.assertTrue(result['analysis_valid'] and result['discriminating'] and result['fix_correct'] and result['verified_fix'])
        self.assertIsNotNone(result['coverage_percent'])

    def test_unchanged_buggy_code_is_not_a_correct_fix(self):
        result = self.run_case(stub(CASE['code'], CASE['tests']))
        self.assertFalse(result['fix_correct'])
        self.assertFalse(result['verified_fix'])

    def test_weak_tests_that_pass_on_buggy_code_are_not_discriminating(self):
        weak = 'import unittest\nfrom solution import median\nclass T(unittest.TestCase):\n    def test_odd(self): self.assertEqual(median([1, 2, 3]), 2)\n'
        result = self.run_case(stub(CASE['fixed'], weak))
        self.assertTrue(result['fix_correct'])
        self.assertFalse(result['discriminating'])
        self.assertFalse(result['verified_fix'])

    def test_invalid_analysis_is_a_model_failure_not_infra(self):
        def failing(code, error):
            raise ValueError('AI analysis unavailable or invalid.')
        result = self.run_case(failing)
        self.assertFalse(result['analysis_valid'])
        self.assertNotIn('infra_error', result)
        self.assertIn('analysis_error', result)

    def test_executor_failure_is_recorded_as_infra_error(self):
        def broken(code, tests):
            raise ValueError('Docker runner unavailable.')
        result = self.run_case(stub(CASE['fixed'], CASE['tests']), executor=broken)
        self.assertIn('infra_error', result)
        summary = summarize([result])
        self.assertEqual((summary['cases_evaluated'], summary['infra_errors']), (0, 1))

    def test_mutation_detection_strong_versus_trivial_tests(self):
        strong = self.run_case(stub(CASE['fixed'], CASE['tests']), mutant_limit=6)
        self.assertGreater(strong['mutation']['killable'], 0)
        self.assertEqual(strong['mutation']['killed'], strong['mutation']['killable'])
        trivial = 'import unittest\nclass T(unittest.TestCase):\n    def test_nothing(self): self.assertTrue(True)\n'
        weak = self.run_case(stub(CASE['fixed'], trivial), mutant_limit=6)
        self.assertEqual(weak['mutation']['killed'], 0)

    def test_mutation_skipped_when_fix_is_wrong(self):
        result = self.run_case(stub(CASE['code'], CASE['tests']), mutant_limit=6)
        self.assertIsNone(result['mutation'])


class ReportTests(unittest.TestCase):
    def test_summary_and_report_render(self):
        good = evaluate_case(CASE, stub(CASE['fixed'], CASE['tests']), run_trusted_local, 3)
        bad = evaluate_case(BY_ID['clamp_swapped'], stub(BY_ID['clamp_swapped']['code'], BY_ID['clamp_swapped']['tests']), run_trusted_local, 0)
        summary = summarize([good, bad])
        self.assertEqual(summary['verified_fix']['k'], 1)
        self.assertEqual(summary['verified_fix']['n'], 2)
        self.assertEqual(summary['fix_correct']['rate'], 0.5)
        meta = {'model': 'stub', 'when': 'now', 'commit': 'abc', 'python': '3', 'mutants': 3}
        report = render_report(meta, summary, [good, bad])
        self.assertIn('Verified fix', report)
        self.assertIn('median_even', report)


class CliTests(unittest.TestCase):
    def test_main_writes_json_and_markdown_reports(self):
        by_code = {c['code']: c for c in CASES}
        def fake_analyze(code, error):
            return {'analysis': {'fixed_code': by_code[code]['fixed'], 'tests': by_code[code]['tests']}}
        ready = {'model': 'stub', 'ai': 'ready', 'docker': 'ready', 'runner': True}
        with tempfile.TemporaryDirectory() as out, patch.object(core, 'health', return_value=ready), \
                patch.object(core, 'analyze', fake_analyze), patch.object(core, 'run_code', run_trusted_local):
            run_eval.main(['--model', 'stub', '--limit', '2', '--mutants', '2', '--out', out])
            data = json.loads((Path(out) / 'results.json').read_text())
            self.assertEqual(data['summary']['cases_evaluated'], 2)
            self.assertEqual(data['summary']['verified_fix']['k'], 2)
            self.assertEqual(data['meta']['model'], 'stub')
            self.assertIn('Verified fix', (Path(out) / 'report.md').read_text())

    def test_exits_when_docker_runner_missing(self):
        missing = {'model': 'stub', 'ai': 'ready', 'docker': 'unavailable', 'runner': False}
        with patch.object(core, 'health', return_value=missing), self.assertRaises(SystemExit):
            run_eval.main(['--limit', '1'])


if __name__ == '__main__':
    unittest.main()
