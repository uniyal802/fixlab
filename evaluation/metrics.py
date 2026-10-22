"""Aggregation of per-case evaluation results into reportable metrics."""
import math


def wilson(k, n, z=1.96):
    """95% Wilson score interval for a proportion k/n. Returns (low, high)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def rate(k, n):
    low, high = wilson(k, n)
    return {'k': k, 'n': n, 'rate': (k / n) if n else None, 'ci_low': low, 'ci_high': high}


def percentile(values, q):
    """Nearest-rank percentile (q in 0..100); None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(q / 100 * len(ordered)) - 1))
    return ordered[index]


def summarize(results):
    """Summarize a list of per-case result dicts (see run_eval.evaluate_case).

    Cases with `infra_error` (Docker/runner problems, not model behavior) are
    excluded from every denominator and counted separately.
    """
    eligible = [r for r in results if not r.get('infra_error')]
    n = len(eligible)

    def count(key):
        return sum(1 for r in eligible if r.get(key) is True)

    mutation_cases = [r for r in eligible if r.get('mutation') and r['mutation']['killable'] > 0]
    killable = sum(r['mutation']['killable'] for r in mutation_cases)
    killed = sum(r['mutation']['killed'] for r in mutation_cases)
    latencies = [r['analysis_seconds'] for r in eligible if r.get('analysis_seconds') is not None]
    coverage = [r['coverage_percent'] for r in eligible if r.get('coverage_percent') is not None]

    categories = {}
    for r in eligible:
        bucket = categories.setdefault(r['category'], {'n': 0, 'fix_correct': 0, 'verified_fix': 0})
        bucket['n'] += 1
        bucket['fix_correct'] += 1 if r.get('fix_correct') is True else 0
        bucket['verified_fix'] += 1 if r.get('verified_fix') is True else 0

    return {
        'cases_total': len(results),
        'cases_evaluated': n,
        'infra_errors': len(results) - n,
        'valid_analysis': rate(count('analysis_valid'), n),
        'discriminating_tests': rate(count('discriminating'), n),
        'fix_correct': rate(count('fix_correct'), n),
        'verified_fix': rate(count('verified_fix'), n),
        'mutation_detection': dict(rate(killed, killable), cases=len(mutation_cases)),
        'analysis_seconds': {
            'mean': (sum(latencies) / len(latencies)) if latencies else None,
            'median': percentile(latencies, 50),
            'p95': percentile(latencies, 95),
        },
        'mean_statement_coverage_percent': (sum(coverage) / len(coverage)) if coverage else None,
        'by_category': categories,
    }
