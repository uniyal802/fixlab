"""Evaluate FixLab's AI analysis against a labeled bug dataset.

Usage (from the repository root, with Ollama and the Docker runner ready):

    python3 -m evaluation.run_eval --model qwen2.5-coder:7b
    python3 -m evaluation.run_eval --model qwen2.5-coder:1.5b --limit 5 --mutants 0
    python3 -m evaluation.run_eval --check-dataset      # no model needed

For each case the harness asks FixLab for a fix and regression tests, then
measures, using only independent reference tests as ground truth:

  valid_analysis        the model returned usable, syntax-valid JSON fields
  discriminating        generated tests fail on the buggy code AND pass on the fix
  fix_correct           the model's fix passes the reference tests
  verified_fix          fix_correct AND discriminating (a fix FixLab can both
                        repair and demonstrate with its own tests)
  mutation_detection    among mutants of the model's fix that the reference
                        tests catch, the share the generated tests also catch

All execution of AI-generated code goes through backend/core.py:run_code
(Docker, no network). Results are written as JSON and Markdown.
"""
import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))
import core  # noqa: E402
from evaluation.cases import CASES  # noqa: E402
from evaluation.metrics import summarize  # noqa: E402
from evaluation.mutate import mutants as make_mutants  # noqa: E402


def evaluate_case(case, analyze_fn, executor, mutant_limit=6, seed=0):
    """Evaluate one case and return a JSON-serializable result dict.

    analyze_fn(code, error) -> session payload (like core.analyze)
    executor(code, tests)   -> run result (like core.run_code)
    A ValueError from the executor is recorded as `infra_error` so runner or
    Docker problems are never counted as model failures.
    """
    result = {'id': case['id'], 'category': case['category'], 'analysis_valid': False, 'discriminating': False,
              'fix_correct': False, 'verified_fix': False, 'analysis_seconds': None, 'coverage_percent': None, 'mutation': None}
    started = time.monotonic()
    try:
        payload = analyze_fn(case['code'], case['error'])
        result['analysis_seconds'] = round(time.monotonic() - started, 2)
    except ValueError as exc:
        result['analysis_seconds'] = round(time.monotonic() - started, 2)
        result['analysis_error'] = str(exc)[:300]
        return result
    fixed = payload['analysis']['fixed_code']
    generated = payload['analysis']['tests']
    result['analysis_valid'] = True
    result['model_fixed_code'] = fixed
    result['model_tests'] = generated
    try:
        original_run = executor(case['code'], generated)
        fixed_run = executor(fixed, generated)
        reference_run = executor(fixed, case['tests'])
    except ValueError as exc:
        result['infra_error'] = str(exc)[:300]
        return result
    result['original_fails_generated'] = not original_run['passed']
    result['fixed_passes_generated'] = bool(fixed_run['passed'])
    result['discriminating'] = result['original_fails_generated'] and result['fixed_passes_generated']
    result['fix_correct'] = bool(reference_run['passed'])
    result['verified_fix'] = result['fix_correct'] and result['discriminating']
    report = fixed_run.get('report') or {}
    result['coverage_percent'] = report.get('coverage_percent')
    if mutant_limit > 0 and result['fix_correct'] and result['fixed_passes_generated']:
        killable = killed = 0
        try:
            for mutant in make_mutants(fixed, mutant_limit, seed):
                if executor(mutant['code'], case['tests'])['passed']:
                    continue  # reference tests cannot tell it apart: treat as equivalent, ignore
                killable += 1
                if not executor(mutant['code'], generated)['passed']:
                    killed += 1
        except ValueError as exc:
            result['infra_error'] = str(exc)[:300]
            return result
        result['mutation'] = {'killable': killable, 'killed': killed}
    return result


def check_dataset(executor):
    """Verify every case: the buggy code fails its reference tests and the reference fix passes."""
    problems = []
    for case in CASES:
        buggy = executor(case['code'], case['tests'])
        fixed = executor(case['fixed'], case['tests'])
        if buggy['passed'] or not fixed['passed']:
            problems.append({'id': case['id'], 'buggy_passed': buggy['passed'], 'reference_passed': fixed['passed']})
    return problems


def percent(item):
    if item['rate'] is None:
        return 'n/a'
    return '{:.1f}% ({}/{}, 95% CI {:.0f}–{:.0f}%)'.format(100 * item['rate'], item['k'], item['n'], 100 * item['ci_low'], 100 * item['ci_high'])


def render_report(meta, summary, results):
    lines = ['# FixLab evaluation', '',
             'Model: `{model}`  ·  Run: {when}  ·  Commit: `{commit}`  ·  Python {python}'.format(**meta), '',
             'Cases evaluated: {} of {} ({} infrastructure errors excluded). Mutants per case: up to {}.'.format(
                 summary['cases_evaluated'], summary['cases_total'], summary['infra_errors'], meta['mutants']), '',
             '| Metric | Result |', '| --- | --- |']
    rows = [('Valid analysis', summary['valid_analysis']), ('Discriminating generated tests', summary['discriminating_tests']),
            ('Fix correct (reference tests)', summary['fix_correct']), ('Verified fix', summary['verified_fix']),
            ('Mutation detection (generated tests)', summary['mutation_detection'])]
    for name, item in rows:
        lines.append('| {} | {} |'.format(name, percent(item)))
    latency = summary['analysis_seconds']
    if latency['mean'] is not None:
        lines.append('| Analysis latency (s) | mean {:.1f}, median {:.1f}, p95 {:.1f} |'.format(latency['mean'], latency['median'], latency['p95']))
    if summary['mean_statement_coverage_percent'] is not None:
        lines.append('| Mean statement-line coverage of fix | {:.1f}% |'.format(summary['mean_statement_coverage_percent']))
    lines += ['', '## By category', '', '| Category | Cases | Fix correct | Verified fix |', '| --- | --- | --- | --- |']
    for name, bucket in sorted(summary['by_category'].items()):
        lines.append('| {} | {} | {} | {} |'.format(name, bucket['n'], bucket['fix_correct'], bucket['verified_fix']))
    lines += ['', '## Per case', '', '| Case | Valid | Discriminating | Fix correct | Verified | Note |', '| --- | --- | --- | --- | --- | --- |']
    mark = lambda value: 'yes' if value else 'no'
    for r in results:
        note = r.get('infra_error') or r.get('analysis_error') or ''
        lines.append('| {} | {} | {} | {} | {} | {} |'.format(r['id'], mark(r['analysis_valid']), mark(r['discriminating']), mark(r['fix_correct']), mark(r['verified_fix']), note.replace('|', '/')[:80]))
    lines += ['', 'Notes: ground truth is the independent reference test suite per case. Mutation detection ignores mutants the reference tests cannot distinguish (treated as equivalent) and is computed only for fixes that pass the reference tests. A small, hand-written dataset measures relative model differences, not general-purpose debugging ability.', '']
    return '\n'.join(lines)


def git_commit():
    try:
        return subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, timeout=5).stdout.strip() or 'unknown'
    except (OSError, subprocess.TimeoutExpired):
        return 'unknown'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--model', default=os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:7b'))
    parser.add_argument('--ids', help='comma-separated case ids to run')
    parser.add_argument('--limit', type=int, help='run only the first N cases')
    parser.add_argument('--mutants', type=int, default=6, help='max mutants per case (0 disables mutation analysis)')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--out', help='output directory (default evaluation/results/<model>-<timestamp>)')
    parser.add_argument('--check-dataset', action='store_true', help='validate the dataset in Docker and exit; no model needed')
    args = parser.parse_args(argv)

    status = core.health()
    if status['docker'] != 'ready' or not status['runner']:
        sys.exit('Docker and the fixlab-runner:local image are required (docker build -f Dockerfile.runner -t fixlab-runner:local .).')
    if args.check_dataset:
        problems = check_dataset(core.run_code)
        print('Dataset OK: {} cases'.format(len(CASES)) if not problems else json.dumps(problems, indent=2))
        sys.exit(1 if problems else 0)
    os.environ['OLLAMA_MODEL'] = args.model
    status = core.health()
    if status['ai'] != 'ready':
        sys.exit('Model {} is not ready in Ollama (status: {}). Run: ollama pull {}'.format(args.model, status['ai'], args.model))

    selected = [c for c in CASES if not args.ids or c['id'] in args.ids.split(',')]
    if args.limit:
        selected = selected[:args.limit]
    if not selected:
        sys.exit('No matching cases.')
    when = datetime.now(timezone.utc)
    out = Path(args.out) if args.out else ROOT / 'evaluation' / 'results' / '{}-{}'.format(args.model.replace(':', '_').replace('/', '_'), when.strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory() as tmp, patch.object(core, 'DB', Path(tmp) / 'data' / 'eval.db'):
        for index, case in enumerate(selected, 1):
            print('[{}/{}] {}'.format(index, len(selected), case['id']), flush=True)
            results.append(evaluate_case(case, core.analyze, core.run_code, args.mutants, args.seed))
    summary = summarize(results)
    meta = {'model': args.model, 'when': when.isoformat(timespec='seconds'), 'commit': git_commit(), 'python': platform.python_version(), 'mutants': args.mutants, 'seed': args.seed}
    (out / 'results.json').write_text(json.dumps({'meta': meta, 'summary': summary, 'results': results}, indent=2))
    report = render_report(meta, summary, results)
    (out / 'report.md').write_text(report)
    print(report)
    print('Wrote', out)


if __name__ == '__main__':
    main()
