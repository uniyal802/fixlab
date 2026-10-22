"""Labeled bug cases for evaluating FixLab.

Each case has:
  id        stable identifier
  category  bug class (used for per-category reporting)
  error     the bug report shown to the model (symptom + expected behavior)
  code      the buggy module given to the model
  fixed     an independent reference solution (never shown to the model)
  tests     independent reference tests (never shown to the model)

Invariants, enforced by tests/test_evaluation.py:
  * `tests` FAIL against `code`
  * `tests` PASS against `fixed`

Cases are original to this repository; they are small by design so that a
7B or smaller local model has a realistic chance, which keeps the benchmark
sensitive to model differences instead of saturating at 0% or 100%.
"""

CASES = []


def case(id, category, error, code, fixed, tests):
    CASES.append({'id': id, 'category': category, 'error': error, 'code': code, 'fixed': fixed, 'tests': tests})


case('average_empty', 'empty-input',
     "ZeroDivisionError: division by zero from average([]). Expected: average([]) returns 0.0.",
     '''def average(xs):
    return sum(xs) / len(xs)
''',
     '''def average(xs):
    if not xs:
        return 0.0
    return sum(xs) / len(xs)
''',
     '''import unittest
from solution import average

class T(unittest.TestCase):
    def test_empty(self): self.assertEqual(average([]), 0.0)
    def test_values(self): self.assertEqual(average([2, 4]), 3)
    def test_single(self): self.assertEqual(average([5]), 5)
''')

case('fizzbuzz_range', 'off-by-one',
     "fizzbuzz(5) returned ['1', '2', 'Fizz', '4'] but should also include 5 -> 'Buzz'. The last number n is missing.",
     '''def fizzbuzz(n):
    out = []
    for i in range(1, n):
        if i % 15 == 0:
            out.append('FizzBuzz')
        elif i % 3 == 0:
            out.append('Fizz')
        elif i % 5 == 0:
            out.append('Buzz')
        else:
            out.append(str(i))
    return out
''',
     '''def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append('FizzBuzz')
        elif i % 3 == 0:
            out.append('Fizz')
        elif i % 5 == 0:
            out.append('Buzz')
        else:
            out.append(str(i))
    return out
''',
     '''import unittest
from solution import fizzbuzz

class T(unittest.TestCase):
    def test_five(self): self.assertEqual(fizzbuzz(5), ['1', '2', 'Fizz', '4', 'Buzz'])
    def test_fifteen(self): self.assertEqual(fizzbuzz(15)[-1], 'FizzBuzz')
    def test_zero(self): self.assertEqual(fizzbuzz(0), [])
    def test_length(self): self.assertEqual(len(fizzbuzz(3)), 3)
''')

case('mutable_default', 'shared-state',
     "Calling add_item('a') and then add_item('b') returns ['a', 'b'] on the second call. Each call without an explicit list must start from a new empty list.",
     '''def add_item(item, items=[]):
    items.append(item)
    return items
''',
     '''def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
''',
     '''import unittest
from solution import add_item

class T(unittest.TestCase):
    def test_fresh_list_each_call(self):
        add_item('a')
        self.assertEqual(add_item('b'), ['b'])
    def test_explicit_list_is_extended(self):
        lst = ['x']
        result = add_item('y', lst)
        self.assertEqual(lst, ['x', 'y'])
        self.assertIs(result, lst)
''')

case('palindrome_normalize', 'string-handling',
     "is_palindrome('A man, a plan, a canal: Panama') returns False. Expected True: ignore case and non-alphanumeric characters.",
     '''def is_palindrome(s):
    return s == s[::-1]
''',
     '''def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]
''',
     '''import unittest
from solution import is_palindrome

class T(unittest.TestCase):
    def test_sentence(self): self.assertTrue(is_palindrome('A man, a plan, a canal: Panama'))
    def test_not(self): self.assertFalse(is_palindrome('hello'))
    def test_empty(self): self.assertTrue(is_palindrome(''))
    def test_case(self): self.assertTrue(is_palindrome('Racecar'))
    def test_quotes(self): self.assertTrue(is_palindrome("No 'x' in Nixon"))
''')

case('clamp_swapped', 'wrong-operator',
     "clamp(5, 0, 10) returns 10 but should return 5. Values already inside [lo, hi] must be unchanged; values outside move to the nearest bound.",
     '''def clamp(x, lo, hi):
    return max(hi, min(x, lo))
''',
     '''def clamp(x, lo, hi):
    return max(lo, min(x, hi))
''',
     '''import unittest
from solution import clamp

class T(unittest.TestCase):
    def test_inside(self): self.assertEqual(clamp(5, 0, 10), 5)
    def test_below(self): self.assertEqual(clamp(-3, 0, 10), 0)
    def test_above(self): self.assertEqual(clamp(42, 0, 10), 10)
    def test_bounds(self):
        self.assertEqual(clamp(0, 0, 10), 0)
        self.assertEqual(clamp(10, 0, 10), 10)
''')

case('binary_search_bound', 'off-by-one',
     "binary_search([4], 4) returns -1 instead of 0, and binary_search([1, 3, 5, 7], 7) returns -1 instead of 3. The function returns the index of target in a sorted list, or -1 if absent.",
     '''def binary_search(xs, target):
    lo, hi = 0, len(xs) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] == target:
            return mid
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
     '''def binary_search(xs, target):
    lo, hi = 0, len(xs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if xs[mid] == target:
            return mid
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
     '''import unittest
from solution import binary_search

class T(unittest.TestCase):
    def test_single(self): self.assertEqual(binary_search([4], 4), 0)
    def test_last(self): self.assertEqual(binary_search([1, 3, 5, 7], 7), 3)
    def test_first(self): self.assertEqual(binary_search([1, 3, 5, 7], 1), 0)
    def test_middle(self): self.assertEqual(binary_search([1, 3, 5, 7], 5), 2)
    def test_missing(self): self.assertEqual(binary_search([1, 3, 5, 7], 4), -1)
    def test_empty(self): self.assertEqual(binary_search([], 1), -1)
''')

case('count_words_whitespace', 'string-handling',
     "count_words('hello   world') returns 4 but should return 2, and count_words('') returns 1 but should return 0. Words are separated by any amount of whitespace.",
     '''def count_words(text):
    return len(text.split(' '))
''',
     '''def count_words(text):
    return len(text.split())
''',
     '''import unittest
from solution import count_words

class T(unittest.TestCase):
    def test_multiple_spaces(self): self.assertEqual(count_words('hello   world'), 2)
    def test_empty(self): self.assertEqual(count_words(''), 0)
    def test_blank(self): self.assertEqual(count_words('  '), 0)
    def test_mixed_whitespace(self): self.assertEqual(count_words('one two\\tthree\\nfour'), 4)
    def test_single(self): self.assertEqual(count_words('single'), 1)
''')

case('median_even', 'wrong-algorithm',
     "median([1, 2, 3, 4]) returns 3 but should return 2.5. For an even number of items use the mean of the two middle values. median([]) should raise ValueError.",
     '''def median(xs):
    s = sorted(xs)
    return s[len(s) // 2]
''',
     '''def median(xs):
    if not xs:
        raise ValueError('median of empty list')
    s = sorted(xs)
    mid = len(s) // 2
    if len(s) % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2
''',
     '''import unittest
from solution import median

class T(unittest.TestCase):
    def test_even(self): self.assertEqual(median([1, 2, 3, 4]), 2.5)
    def test_even_unsorted(self): self.assertEqual(median([4, 1, 3, 2]), 2.5)
    def test_odd(self): self.assertEqual(median([3, 1, 2]), 2)
    def test_single(self): self.assertEqual(median([5]), 5)
    def test_empty(self):
        with self.assertRaises(ValueError):
            median([])
''')

case('flatten_nested', 'recursion',
     "flatten([1, [2, [3, [4]]]]) returns [1, 2, [3, [4]]]. It must flatten lists nested to any depth, preserving order.",
     '''def flatten(items):
    out = []
    for item in items:
        if isinstance(item, list):
            out.extend(item)
        else:
            out.append(item)
    return out
''',
     '''def flatten(items):
    out = []
    for item in items:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out
''',
     '''import unittest
from solution import flatten

class T(unittest.TestCase):
    def test_deep(self): self.assertEqual(flatten([1, [2, [3, [4]]]]), [1, 2, 3, 4])
    def test_empty(self): self.assertEqual(flatten([]), [])
    def test_empty_nested(self): self.assertEqual(flatten([[], [[]]]), [])
    def test_flat(self): self.assertEqual(flatten([1, 2]), [1, 2])
    def test_two_level(self): self.assertEqual(flatten([[1, 2], [3]]), [1, 2, 3])
''')

case('unique_order', 'wrong-algorithm',
     "unique([3, 1, 3, 2, 1]) returns items in a different order. It must keep the first occurrence of each item and preserve the original order: [3, 1, 2].",
     '''def unique(xs):
    return list(set(xs))
''',
     '''def unique(xs):
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
''',
     '''import unittest
from solution import unique

class T(unittest.TestCase):
    def test_order(self): self.assertEqual(unique([3, 1, 3, 2, 1]), [3, 1, 2])
    def test_empty(self): self.assertEqual(unique([]), [])
    def test_all_same(self): self.assertEqual(unique([5, 5, 5]), [5])
    def test_descending(self): self.assertEqual(unique([9, 8, 7]), [9, 8, 7])
''')

case('max_subarray_negative', 'boundary',
     "max_subarray([-3, -1, -2]) returns 0 but should return -1 (the best non-empty subarray sum). max_subarray([]) should raise ValueError.",
     '''def max_subarray(xs):
    best = 0
    current = 0
    for x in xs:
        current = max(x, current + x)
        best = max(best, current)
    return best
''',
     '''def max_subarray(xs):
    if not xs:
        raise ValueError('empty input')
    best = current = xs[0]
    for x in xs[1:]:
        current = max(x, current + x)
        best = max(best, current)
    return best
''',
     '''import unittest
from solution import max_subarray

class T(unittest.TestCase):
    def test_all_negative(self): self.assertEqual(max_subarray([-3, -1, -2]), -1)
    def test_mixed(self): self.assertEqual(max_subarray([1, -2, 3, 4, -1]), 7)
    def test_classic(self): self.assertEqual(max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]), 6)
    def test_single(self): self.assertEqual(max_subarray([5]), 5)
    def test_empty(self):
        with self.assertRaises(ValueError):
            max_subarray([])
''')

case('chunk_tail', 'off-by-one',
     "chunk([1, 2, 3, 4, 5], 2) returns [[1, 2], [3, 4]] but should return [[1, 2], [3, 4], [5]]: the final partial chunk is dropped. chunk(xs, n) with n <= 0 should raise ValueError.",
     '''def chunk(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs) - n, n)]
''',
     '''def chunk(xs, n):
    if n <= 0:
        raise ValueError('n must be positive')
    return [xs[i:i + n] for i in range(0, len(xs), n)]
''',
     '''import unittest
from solution import chunk

class T(unittest.TestCase):
    def test_partial_tail(self): self.assertEqual(chunk([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])
    def test_exact(self): self.assertEqual(chunk([1, 2, 3, 4], 2), [[1, 2], [3, 4]])
    def test_empty(self): self.assertEqual(chunk([], 3), [])
    def test_larger_than_list(self): self.assertEqual(chunk([1, 2], 5), [[1, 2]])
    def test_bad_size(self):
        for n in (0, -1):
            with self.assertRaises(ValueError):
                chunk([1, 2, 3], n)
''')

case('word_frequency_case', 'string-handling',
     "word_frequency('The cat the CAT') returns {'The': 1, 'cat': 1, 'the': 1, 'CAT': 1}. Counting must be case-insensitive with lowercase keys, and leading/trailing punctuation (. , ! ?) must be stripped: {'the': 2, 'cat': 2}. Tokens that are empty after stripping are ignored.",
     '''def word_frequency(text):
    counts = {}
    for word in text.split():
        counts[word] = counts.get(word, 0) + 1
    return counts
''',
     '''def word_frequency(text):
    counts = {}
    for word in text.split():
        word = word.strip('.,!?').lower()
        if word:
            counts[word] = counts.get(word, 0) + 1
    return counts
''',
     '''import unittest
from solution import word_frequency

class T(unittest.TestCase):
    def test_case(self): self.assertEqual(word_frequency('The cat the CAT'), {'the': 2, 'cat': 2})
    def test_punctuation(self): self.assertEqual(word_frequency('Hello, world! hello.'), {'hello': 2, 'world': 1})
    def test_empty(self): self.assertEqual(word_frequency(''), {})
    def test_only_punctuation(self): self.assertEqual(word_frequency('!!! ...'), {})
''')

case('parse_int_sign', 'boundary',
     "parse_int('-42') returns None but should return -42. A leading '+' or '-' sign is allowed. Surrounding whitespace is ignored. Invalid strings such as '4x2', '-' or '' return None.",
     '''def parse_int(s):
    s = s.strip()
    if s.isdigit():
        return int(s)
    return None
''',
     '''import re


def parse_int(s):
    s = s.strip()
    if re.fullmatch(r'[+-]?[0-9]+', s):
        return int(s)
    return None
''',
     '''import unittest
from solution import parse_int

class T(unittest.TestCase):
    def test_plain(self): self.assertEqual(parse_int('42'), 42)
    def test_whitespace(self): self.assertEqual(parse_int(' 7 '), 7)
    def test_negative(self): self.assertEqual(parse_int('-42'), -42)
    def test_plus(self): self.assertEqual(parse_int('+5'), 5)
    def test_invalid(self):
        for s in ('4x2', '', '-', '--3'):
            self.assertIsNone(parse_int(s))
''')

case('merge_intervals_sort', 'wrong-algorithm',
     "merge_intervals([[5, 8], [1, 3], [2, 6]]) returns [[5, 8]] but should return [[1, 8]]. Intervals may arrive in any order; overlapping or touching intervals are merged.",
     '''def merge_intervals(intervals):
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
''',
     '''def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
''',
     '''import unittest
from solution import merge_intervals

class T(unittest.TestCase):
    def test_unsorted(self): self.assertEqual(merge_intervals([[5, 8], [1, 3], [2, 6]]), [[1, 8]])
    def test_disjoint(self): self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])
    def test_touching(self): self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])
    def test_empty(self): self.assertEqual(merge_intervals([]), [])
    def test_contained(self): self.assertEqual(merge_intervals([[1, 10], [2, 3]]), [[1, 10]])
''')

case('rotate_left_wrap', 'boundary',
     "rotate_left([1, 2, 3], 4) returns [1, 2, 3] but should return [2, 3, 1]: k can exceed the list length and must wrap around. rotate_left([], 5) must return [].",
     '''def rotate_left(xs, k):
    return xs[k:] + xs[:k]
''',
     '''def rotate_left(xs, k):
    if not xs:
        return []
    k %= len(xs)
    return xs[k:] + xs[:k]
''',
     '''import unittest
from solution import rotate_left

class T(unittest.TestCase):
    def test_wrap(self): self.assertEqual(rotate_left([1, 2, 3], 4), [2, 3, 1])
    def test_full_turn(self): self.assertEqual(rotate_left([1, 2, 3], 3), [1, 2, 3])
    def test_one(self): self.assertEqual(rotate_left([1, 2, 3, 4], 1), [2, 3, 4, 1])
    def test_empty(self): self.assertEqual(rotate_left([], 5), [])
    def test_negative(self): self.assertEqual(rotate_left([1, 2, 3], -1), [3, 1, 2])
    def test_zero(self): self.assertEqual(rotate_left([1, 2, 3], 0), [1, 2, 3])
''')

case('leap_year_rules', 'wrong-algorithm',
     "is_leap_year(1900) returns True but 1900 is not a leap year, while 2000 is. Gregorian rule: divisible by 4, except century years that are not divisible by 400.",
     '''def is_leap_year(y):
    return y % 4 == 0
''',
     '''def is_leap_year(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
''',
     '''import unittest
from solution import is_leap_year

class T(unittest.TestCase):
    def test_leap(self):
        for y in (2000, 2024, 2400):
            self.assertTrue(is_leap_year(y), y)
    def test_not_leap(self):
        for y in (1900, 2023, 2100):
            self.assertFalse(is_leap_year(y), y)
''')

case('moving_average_window', 'off-by-one',
     "moving_average([1, 2, 3, 4], 2) returns [1.5, 2.5] but should return [1.5, 2.5, 3.5]: the last full window is missing. If window is larger than the list return []. window <= 0 raises ValueError.",
     '''def moving_average(xs, window):
    return [sum(xs[i:i + window]) / window for i in range(len(xs) - window)]
''',
     '''def moving_average(xs, window):
    if window <= 0:
        raise ValueError('window must be positive')
    return [sum(xs[i:i + window]) / window for i in range(len(xs) - window + 1)]
''',
     '''import unittest
from solution import moving_average

class T(unittest.TestCase):
    def test_basic(self): self.assertEqual(moving_average([1, 2, 3, 4], 2), [1.5, 2.5, 3.5])
    def test_full_window(self): self.assertEqual(moving_average([1, 2, 3], 3), [2.0])
    def test_window_too_large(self): self.assertEqual(moving_average([1, 2], 5), [])
    def test_single(self): self.assertEqual(moving_average([4], 1), [4.0])
    def test_bad_window(self):
        for w in (0, -1):
            with self.assertRaises(ValueError):
                moving_average([1, 2], w)
''')

case('merge_counts_sum', 'shared-state',
     "merge_counts({'x': 1}, {'x': 2, 'y': 3}) returns {'x': 2, 'y': 3} but should sum shared keys: {'x': 3, 'y': 3}. The input dictionaries must not be modified.",
     '''def merge_counts(a, b):
    merged = a
    merged.update(b)
    return merged
''',
     '''def merge_counts(a, b):
    merged = dict(a)
    for key, value in b.items():
        merged[key] = merged.get(key, 0) + value
    return merged
''',
     '''import unittest
from solution import merge_counts

class T(unittest.TestCase):
    def test_sum(self): self.assertEqual(merge_counts({'x': 1}, {'x': 2, 'y': 3}), {'x': 3, 'y': 3})
    def test_inputs_unchanged(self):
        a, b = {'x': 1}, {'x': 2}
        merge_counts(a, b)
        self.assertEqual(a, {'x': 1})
        self.assertEqual(b, {'x': 2})
    def test_empty(self): self.assertEqual(merge_counts({}, {}), {})
    def test_disjoint(self): self.assertEqual(merge_counts({'a': 1}, {'b': 2}), {'a': 1, 'b': 2})
''')

case('transpose_rectangular', 'wrong-algorithm',
     "transpose([[1, 2, 3], [4, 5, 6]]) returns [[1, 4], [2, 5]] but should return [[1, 4], [2, 5], [3, 6]]. Non-square matrices must work. transpose([]) returns [].",
     '''def transpose(matrix):
    n = len(matrix)
    return [[matrix[r][c] for r in range(n)] for c in range(n)]
''',
     '''def transpose(matrix):
    if not matrix:
        return []
    return [[row[c] for row in matrix] for c in range(len(matrix[0]))]
''',
     '''import unittest
from solution import transpose

class T(unittest.TestCase):
    def test_wide(self): self.assertEqual(transpose([[1, 2, 3], [4, 5, 6]]), [[1, 4], [2, 5], [3, 6]])
    def test_tall(self): self.assertEqual(transpose([[1], [2], [3]]), [[1, 2, 3]])
    def test_square(self): self.assertEqual(transpose([[1, 2], [3, 4]]), [[1, 3], [2, 4]])
    def test_empty(self): self.assertEqual(transpose([]), [])
    def test_single(self): self.assertEqual(transpose([[7]]), [[7]])
''')

case('second_largest_distinct', 'boundary',
     "second_largest([5, 5, 3]) returns 5 but should return 3 (the second largest distinct value). With fewer than two distinct values return None.",
     '''def second_largest(xs):
    return sorted(xs)[-2]
''',
     '''def second_largest(xs):
    distinct = sorted(set(xs))
    if len(distinct) < 2:
        return None
    return distinct[-2]
''',
     '''import unittest
from solution import second_largest

class T(unittest.TestCase):
    def test_duplicates(self): self.assertEqual(second_largest([5, 5, 3]), 3)
    def test_basic(self): self.assertEqual(second_largest([1, 2, 3, 4]), 3)
    def test_single(self): self.assertIsNone(second_largest([7]))
    def test_empty(self): self.assertIsNone(second_largest([]))
    def test_all_equal(self): self.assertIsNone(second_largest([2, 2]))
    def test_negative(self): self.assertEqual(second_largest([-1, -5, -3]), -3)
''')
