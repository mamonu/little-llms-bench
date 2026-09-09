"""Python task bank for lolllmbench.

Each task is a dict:
    id          unique short id
    category    topic tag
    difficulty  easy | medium | hard
    prompt      what the model is asked to do
    entry       the symbol the tests import/use
    tests       hidden test code, appended after the model's code; must
                raise/assert on failure and exit 0 on success
    reference   a known-good solution, used by verify_tasks.py

Grading: model code + tests are concatenated into one file and run in a
subprocess with a timeout. Exit code 0 == pass.
"""

TASKS = [
    # ---------------------------------------------------------------- easy
    {
        "id": "py01_reverse_words",
        "category": "strings",
        "difficulty": "easy",
        "entry": "reverse_words",
        "prompt": (
            "Write a function `reverse_words(s)` that takes a string and returns a "
            "string with the order of the whitespace-separated words reversed. "
            "Collapse runs of whitespace to a single space and strip leading/trailing "
            "whitespace. Example: reverse_words('  hello   big world ') -> "
            "'world big hello'."
        ),
        "tests": """
assert reverse_words("hello world") == "world hello"
assert reverse_words("  hello   big world ") == "world big hello"
assert reverse_words("one") == "one"
assert reverse_words("") == ""
assert reverse_words("   ") == ""
assert reverse_words("a b c d") == "d c b a"
""",
        "reference": """
def reverse_words(s):
    return " ".join(reversed(s.split()))
""",
    },
    {
        "id": "py02_fizzbuzz",
        "category": "control-flow",
        "difficulty": "easy",
        "entry": "fizzbuzz",
        "prompt": (
            "Write a function `fizzbuzz(n)` that returns a list of length n. For each "
            "i from 1 to n inclusive the element is 'FizzBuzz' if i is divisible by "
            "15, 'Fizz' if divisible by 3, 'Buzz' if divisible by 5, otherwise the "
            "string form of i. fizzbuzz(0) returns []."
        ),
        "tests": """
assert fizzbuzz(0) == []
assert fizzbuzz(1) == ["1"]
assert fizzbuzz(5) == ["1", "2", "Fizz", "4", "Buzz"]
r = fizzbuzz(15)
assert len(r) == 15 and r[14] == "FizzBuzz" and r[8] == "Fizz" and r[9] == "Buzz"
assert all(isinstance(x, str) for x in r)
""",
        "reference": """
def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out
""",
    },
    {
        "id": "py03_is_palindrome",
        "category": "strings",
        "difficulty": "easy",
        "entry": "is_palindrome",
        "prompt": (
            "Write a function `is_palindrome(s)` returning True if the string is a "
            "palindrome when ignoring case and any character that is not "
            "alphanumeric, otherwise False. The empty string is a palindrome."
        ),
        "tests": """
assert is_palindrome("A man, a plan, a canal: Panama") is True
assert is_palindrome("race a car") is False
assert is_palindrome("") is True
assert is_palindrome(".,") is True
assert is_palindrome("0P") is False
assert is_palindrome("Was it a car or a cat I saw?") is True
""",
        "reference": """
def is_palindrome(s):
    t = [c.lower() for c in s if c.isalnum()]
    return t == t[::-1]
""",
    },
    {
        "id": "py04_chunk",
        "category": "lists",
        "difficulty": "easy",
        "entry": "chunk",
        "prompt": (
            "Write a function `chunk(items, size)` that splits a list into "
            "consecutive sublists of length `size`, with the final chunk possibly "
            "shorter. Raise ValueError if size < 1. chunk([], 3) -> []."
        ),
        "tests": """
assert chunk([1,2,3,4,5], 2) == [[1,2],[3,4],[5]]
assert chunk([1,2,3,4], 2) == [[1,2],[3,4]]
assert chunk([], 3) == []
assert chunk([1], 10) == [[1]]
try:
    chunk([1,2], 0)
    raise AssertionError("expected ValueError")
except ValueError:
    pass
""",
        "reference": """
def chunk(items, size):
    if size < 1:
        raise ValueError("size must be >= 1")
    return [items[i:i+size] for i in range(0, len(items), size)]
""",
    },
    {
        "id": "py05_word_count",
        "category": "dicts",
        "difficulty": "easy",
        "entry": "word_count",
        "prompt": (
            "Write a function `word_count(text)` returning a dict mapping each word "
            "to how many times it appears. Words are case-insensitive and consist of "
            "runs of letters, digits and apostrophes; every other character is a "
            "separator. Example: word_count(\"Hi, hi! Don't\") -> "
            "{'hi': 2, \"don't\": 1}."
        ),
        "tests": """
assert word_count("Hi, hi! Don't") == {"hi": 2, "don't": 1}
assert word_count("") == {}
assert word_count("a a a b") == {"a": 3, "b": 1}
assert word_count("One-two one") == {"one": 2, "two": 1}
assert word_count("x1 X1 x2") == {"x1": 2, "x2": 1}
""",
        "reference": """
import re

def word_count(text):
    counts = {}
    for w in re.findall(r"[A-Za-z0-9']+", text.lower()):
        counts[w] = counts.get(w, 0) + 1
    return counts
""",
    },
    {
        "id": "py06_two_sum",
        "category": "algorithms",
        "difficulty": "easy",
        "entry": "two_sum",
        "prompt": (
            "Write a function `two_sum(nums, target)` that returns a tuple of the two "
            "indices (i, j) with i < j such that nums[i] + nums[j] == target. Return "
            "None if there is no such pair. Assume at most one valid answer."
        ),
        "tests": """
assert two_sum([2,7,11,15], 9) == (0,1)
assert two_sum([3,2,4], 6) == (1,2)
assert two_sum([3,3], 6) == (0,1)
assert two_sum([1,2,3], 100) is None
assert two_sum([], 0) is None
assert two_sum([-1,-2,-3,-4], -7) == (2,3)
""",
        "reference": """
def two_sum(nums, target):
    seen = {}
    for j, v in enumerate(nums):
        if target - v in seen:
            return (seen[target - v], j)
        if v not in seen:
            seen[v] = j
    return None
""",
    },
    {
        "id": "py07_flatten",
        "category": "recursion",
        "difficulty": "easy",
        "entry": "flatten",
        "prompt": (
            "Write a function `flatten(nested)` that flattens an arbitrarily nested "
            "list of lists into a single flat list, preserving order. Only `list` "
            "counts as nesting: tuples and strings are treated as plain values."
        ),
        "tests": """
assert flatten([1, [2, [3, [4]]], 5]) == [1,2,3,4,5]
assert flatten([]) == []
assert flatten([[], [[]], []]) == []
assert flatten(["ab", [(1,2), ["c"]]]) == ["ab", (1,2), "c"]
assert flatten([1,2,3]) == [1,2,3]
""",
        "reference": """
def flatten(nested):
    out = []
    for item in nested:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out
""",
    },
    # -------------------------------------------------------------- medium
    {
        "id": "py08_roman_to_int",
        "category": "parsing",
        "difficulty": "medium",
        "entry": "roman_to_int",
        "prompt": (
            "Write a function `roman_to_int(s)` converting an uppercase Roman "
            "numeral string (I, V, X, L, C, D, M, including subtractive forms like "
            "IV, IX, XL, CM) to an integer."
        ),
        "tests": """
assert roman_to_int("I") == 1
assert roman_to_int("IV") == 4
assert roman_to_int("IX") == 9
assert roman_to_int("LVIII") == 58
assert roman_to_int("MCMXCIV") == 1994
assert roman_to_int("MMMCMXCIX") == 3999
""",
        "reference": """
def roman_to_int(s):
    vals = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        if i + 1 < len(s) and v < vals[s[i+1]]:
            total -= v
        else:
            total += v
    return total
""",
    },
    {
        "id": "py09_merge_intervals",
        "category": "algorithms",
        "difficulty": "medium",
        "entry": "merge_intervals",
        "prompt": (
            "Write a function `merge_intervals(intervals)` taking a list of [start, "
            "end] pairs and returning a new list of non-overlapping intervals sorted "
            "by start, merging any that overlap or touch (e.g. [1,3] and [3,5] merge "
            "to [1,5]). Return a list of lists. The input must not be mutated."
        ),
        "tests": """
assert merge_intervals([]) == []
assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]
assert merge_intervals([[1,4],[4,5]]) == [[1,5]]
assert merge_intervals([[5,6],[1,2]]) == [[1,2],[5,6]]
assert merge_intervals([[1,10],[2,3],[4,5]]) == [[1,10]]
src = [[3,4],[1,2]]
merge_intervals(src)
assert src == [[3,4],[1,2]], "input was mutated"
""",
        "reference": """
def merge_intervals(intervals):
    out = []
    for start, end in sorted(intervals, key=lambda p: p[0]):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out
""",
    },
    {
        "id": "py10_group_anagrams",
        "category": "dicts",
        "difficulty": "medium",
        "entry": "group_anagrams",
        "prompt": (
            "Write a function `group_anagrams(words)` that groups words that are "
            "anagrams of each other. Return a list of groups; each group is a list of "
            "words sorted alphabetically, and the groups themselves are sorted by "
            "their first element. Comparison is case-sensitive."
        ),
        "tests": """
assert group_anagrams([]) == []
assert group_anagrams(["eat","tea","tan","ate","nat","bat"]) == [["ate","eat","tea"],["bat"],["nat","tan"]]
assert group_anagrams(["a"]) == [["a"]]
assert group_anagrams(["ab","ba","abc"]) == [["ab","ba"],["abc"]]
""",
        "reference": """
def group_anagrams(words):
    buckets = {}
    for w in words:
        buckets.setdefault("".join(sorted(w)), []).append(w)
    return sorted((sorted(g) for g in buckets.values()), key=lambda g: g[0])
""",
    },
    {
        "id": "py11_balanced",
        "category": "stacks",
        "difficulty": "medium",
        "entry": "is_balanced",
        "prompt": (
            "Write a function `is_balanced(s)` returning True if every bracket in the "
            "string is correctly matched and nested. Brackets are (), [] and {}; any "
            "other character is ignored."
        ),
        "tests": """
assert is_balanced("") is True
assert is_balanced("()[]{}") is True
assert is_balanced("(]") is False
assert is_balanced("([{}])") is True
assert is_balanced("([)]") is False
assert is_balanced("a(b[c]{d})e") is True
assert is_balanced("(") is False
assert is_balanced(")(") is False
""",
        "reference": """
def is_balanced(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack
""",
    },
    {
        "id": "py12_rotate_matrix",
        "category": "matrices",
        "difficulty": "medium",
        "entry": "rotate",
        "prompt": (
            "Write a function `rotate(matrix)` that rotates an n x n matrix (a list "
            "of lists) 90 degrees clockwise IN PLACE and returns None."
        ),
        "tests": """
m = [[1,2],[3,4]]
assert rotate(m) is None
assert m == [[3,1],[4,2]]
m = [[1,2,3],[4,5,6],[7,8,9]]
rotate(m)
assert m == [[7,4,1],[8,5,2],[9,6,3]]
m = [[1]]
rotate(m)
assert m == [[1]]
m = []
rotate(m)
assert m == []
""",
        "reference": """
def rotate(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    for row in matrix:
        row.reverse()
    return None
""",
    },
    {
        "id": "py13_rle",
        "category": "strings",
        "difficulty": "medium",
        "entry": "rle_encode",
        "prompt": (
            "Implement run-length encoding with two functions. `rle_encode(s)` turns "
            "a string into a string where each run of a repeated character becomes "
            "the character followed by the run length, but ONLY when the run length "
            "is 2 or more (a single character is emitted bare). `rle_decode(s)` is "
            "the exact inverse. Assume the input to rle_encode contains no digits."
        ),
        "tests": """
assert rle_encode("") == ""
assert rle_encode("abc") == "abc"
assert rle_encode("aaabbc") == "a3b2c"
assert rle_encode("aabbaa") == "a2b2a2"
assert rle_decode("a3b2c") == "aaabbc"
assert rle_decode("") == ""
assert rle_decode("abc") == "abc"
for s in ["", "a", "aa", "abcccccccccccdd", "zzzzzzzzzzzzy"]:
    assert rle_decode(rle_encode(s)) == s, s
""",
        "reference": """
import re

def rle_encode(s):
    out = []
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        n = j - i
        out.append(s[i] if n == 1 else s[i] + str(n))
        i = j
    return "".join(out)

def rle_decode(s):
    out = []
    for ch, num in re.findall(r"(\\D)(\\d*)", s):
        out.append(ch * (int(num) if num else 1))
    return "".join(out)
""",
    },
    {
        "id": "py14_top_k",
        "category": "algorithms",
        "difficulty": "medium",
        "entry": "top_k_frequent",
        "prompt": (
            "Write a function `top_k_frequent(items, k)` returning the k most "
            "frequent elements as a list, ordered by descending count; ties are "
            "broken by first appearance in the input. If k exceeds the number of "
            "distinct elements, return all of them."
        ),
        "tests": """
assert top_k_frequent([1,1,1,2,2,3], 2) == [1,2]
assert top_k_frequent([1], 1) == [1]
assert top_k_frequent([], 3) == []
assert top_k_frequent(["b","a","a","b","c"], 3) == ["b","a","c"]
assert top_k_frequent([1,2,3], 10) == [1,2,3]
assert top_k_frequent([5,5,4,4,3], 1) == [5]
""",
        "reference": """
def top_k_frequent(items, k):
    counts = {}
    order = {}
    for i, v in enumerate(items):
        counts[v] = counts.get(v, 0) + 1
        order.setdefault(v, i)
    ranked = sorted(counts, key=lambda v: (-counts[v], order[v]))
    return ranked[:k]
""",
    },
    {
        "id": "py15_parse_config",
        "category": "parsing",
        "difficulty": "medium",
        "entry": "parse_config",
        "prompt": (
            "Write a function `parse_config(text)` that parses INI-like text into a "
            "dict of dicts. Lines '[name]' open a section. Lines 'key = value' add an "
            "entry to the current section, with key and value stripped of surrounding "
            "whitespace. Blank lines and lines whose first non-space character is '#' "
            "are ignored. Keys before any section header go into the section ''. Only "
            "the first '=' splits the line."
        ),
        "tests": """
t = '''
# comment
top = 1

[db]
host = localhost
port= 5432
  url =  a=b=c

[empty]
'''
assert parse_config(t) == {
    "": {"top": "1"},
    "db": {"host": "localhost", "port": "5432", "url": "a=b=c"},
    "empty": {},
}
assert parse_config("") == {}
assert parse_config("[a]") == {"a": {}}
assert parse_config("k=v") == {"": {"k": "v"}}
""",
        "reference": """
def parse_config(text):
    result = {}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            result.setdefault(section, {})
        elif "=" in line:
            k, v = line.split("=", 1)
            if section is None:
                section = ""
                result.setdefault("", {})
            result[section][k.strip()] = v.strip()
    return result
""",
    },
    {
        "id": "py16_minstack",
        "category": "classes",
        "difficulty": "medium",
        "entry": "MinStack",
        "prompt": (
            "Write a class `MinStack` supporting push(x), pop() (returns the removed "
            "value), top() and get_min(), all in O(1) time. pop() and top() and "
            "get_min() must raise IndexError when the stack is empty. len(stack) must "
            "return the number of items."
        ),
        "tests": """
s = MinStack()
assert len(s) == 0
for m in ("pop", "top", "get_min"):
    try:
        getattr(s, m)()
        raise AssertionError("expected IndexError from " + m)
    except IndexError:
        pass
s.push(3); s.push(1); s.push(2)
assert s.get_min() == 1
assert s.top() == 2
assert s.pop() == 2
assert s.get_min() == 1
assert s.pop() == 1
assert s.get_min() == 3
assert len(s) == 1
s.push(3); s.push(3)
assert s.get_min() == 3
s.pop()
assert s.get_min() == 3
""",
        "reference": """
class MinStack:
    def __init__(self):
        self._items = []
        self._mins = []

    def push(self, x):
        self._items.append(x)
        self._mins.append(x if not self._mins else min(x, self._mins[-1]))

    def pop(self):
        if not self._items:
            raise IndexError("pop from empty stack")
        self._mins.pop()
        return self._items.pop()

    def top(self):
        if not self._items:
            raise IndexError("empty stack")
        return self._items[-1]

    def get_min(self):
        if not self._mins:
            raise IndexError("empty stack")
        return self._mins[-1]

    def __len__(self):
        return len(self._items)
""",
    },
    # ---------------------------------------------------------------- hard
    {
        "id": "py17_retry_decorator",
        "category": "decorators",
        "difficulty": "hard",
        "entry": "retry",
        "prompt": (
            "Write a decorator factory `retry(attempts=3, exceptions=(Exception,))` "
            "that returns a decorator. The decorated function is called up to "
            "`attempts` times; if it raises one of `exceptions` it is retried, and if "
            "the last attempt also raises, that exception propagates. Exceptions not "
            "listed propagate immediately without retrying. The wrapper must preserve "
            "the wrapped function's __name__ and __doc__, and must pass through both "
            "positional and keyword arguments and the return value. Do not sleep."
        ),
        "tests": """
calls = []

@retry(attempts=3)
def flaky(a, b=0):
    "docstring here"
    calls.append(1)
    if len(calls) < 3:
        raise ValueError("boom")
    return a + b

assert flaky(1, b=2) == 3
assert len(calls) == 3
assert flaky.__name__ == "flaky"
assert flaky.__doc__ == "docstring here"

calls2 = []

@retry(attempts=2, exceptions=(KeyError,))
def wrong():
    calls2.append(1)
    raise ValueError("nope")

try:
    wrong()
    raise AssertionError("should have raised")
except ValueError:
    pass
assert len(calls2) == 1, calls2

calls3 = []

@retry(attempts=2)
def always():
    calls3.append(1)
    raise RuntimeError("x")

try:
    always()
    raise AssertionError("should have raised")
except RuntimeError:
    pass
assert len(calls3) == 2
""",
        "reference": """
import functools

def retry(attempts=3, exceptions=(Exception,)):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last = None
            for i in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last = exc
            raise last
        return wrapper
    return decorator
""",
    },
    {
        "id": "py18_sliding_window_max",
        "category": "algorithms",
        "difficulty": "hard",
        "entry": "sliding_window_max",
        "prompt": (
            "Write a function `sliding_window_max(nums, k)` returning a list of the "
            "maximum of every contiguous window of length k. It must run in O(n) "
            "time (use a monotonic deque, not max() per window). Return [] if nums is "
            "empty; raise ValueError if k < 1 or k > len(nums) when nums is non-empty."
        ),
        "tests": """
assert sliding_window_max([], 3) == []
assert sliding_window_max([1,3,-1,-3,5,3,6,7], 3) == [3,3,5,5,6,7]
assert sliding_window_max([1], 1) == [1]
assert sliding_window_max([9,8,7,6], 2) == [9,8,7]
assert sliding_window_max([1,2,3,4], 4) == [4]
try:
    sliding_window_max([1,2], 5)
    raise AssertionError("expected ValueError")
except ValueError:
    pass
try:
    sliding_window_max([1,2], 0)
    raise AssertionError("expected ValueError")
except ValueError:
    pass
import random, time
random.seed(0)
big = [random.randint(0, 10**6) for _ in range(200000)]
t0 = time.time()
got = sliding_window_max(big, 1000)
assert time.time() - t0 < 5.0, "too slow, likely not O(n)"
assert got[0] == max(big[:1000])
assert got[-1] == max(big[-1000:])
""",
        "reference": """
from collections import deque

def sliding_window_max(nums, k):
    if not nums:
        return []
    if k < 1 or k > len(nums):
        raise ValueError("bad window size")
    dq = deque()
    out = []
    for i, v in enumerate(nums):
        while dq and nums[dq[-1]] <= v:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()
        if i >= k - 1:
            out.append(nums[dq[0]])
    return out
""",
    },
    {
        "id": "py19_tokenizer",
        "category": "parsing",
        "difficulty": "hard",
        "entry": "evaluate",
        "prompt": (
            "Write a function `evaluate(expr)` that evaluates an arithmetic "
            "expression string containing non-negative integers, + - * /, parentheses "
            "and arbitrary whitespace. Division is floating point. Standard precedence "
            "and left associativity apply. Return an int when the result is a whole "
            "number, otherwise a float. Raise ValueError on malformed input. Do NOT "
            "use eval, exec, or compile."
        ),
        "tests": """
import sys
_src = open(sys.argv[0], encoding="utf-8").read()
_src = _src.split("# ---- HIDDEN TESTS ----")[0]
for _b in ("ev" + "al(", "ex" + "ec(", "com" + "pile("):
    assert _b not in _src, "banned builtin used: " + _b

assert evaluate("1+1") == 2
assert evaluate(" 2 * (3 + 4) ") == 14
assert evaluate("10/4") == 2.5
assert evaluate("10/5") == 2
assert evaluate("2*3-4/2") == 4
assert evaluate("((((5))))") == 5
assert evaluate("100 - 10 - 10") == 80
assert abs(evaluate("1/3") - 0.3333333333333333) < 1e-12
for bad in ["", "1+", "(1", "1)", "*2", "1 2", "1++2"]:
    try:
        evaluate(bad)
        raise AssertionError("expected ValueError for " + repr(bad))
    except ValueError:
        pass
""",
        "reference": """
import re

def evaluate(expr):
    tokens = re.findall(r"\\d+|[()+\\-*/]|\\S", expr)
    for t in tokens:
        if not (t.isdigit() or t in "()+-*/"):
            raise ValueError("bad token " + t)
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def eat(tok=None):
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("unexpected end")
        t = tokens[pos]
        if tok is not None and t != tok:
            raise ValueError("expected " + tok)
        pos += 1
        return t

    def atom():
        t = peek()
        if t is None:
            raise ValueError("unexpected end")
        if t == "(":
            eat("(")
            v = expression()
            eat(")")
            return v
        if t.isdigit():
            return int(eat())
        raise ValueError("unexpected " + t)

    def term():
        v = atom()
        while peek() in ("*", "/"):
            op = eat()
            r = atom()
            if op == "*":
                v = v * r
            else:
                if r == 0:
                    raise ValueError("division by zero")
                v = v / r
        return v

    def expression():
        v = term()
        while peek() in ("+", "-"):
            op = eat()
            r = term()
            v = v + r if op == "+" else v - r
        return v

    result = expression()
    if pos != len(tokens):
        raise ValueError("trailing input")
    if isinstance(result, float) and result.is_integer():
        return int(result)
    return result
""",
    },
    {
        "id": "py20_lru_cache",
        "category": "classes",
        "difficulty": "hard",
        "entry": "LRUCache",
        "prompt": (
            "Write a class `LRUCache(capacity)` with get(key) and put(key, value), "
            "both O(1) average. get returns the value or None if absent. Both get and "
            "put count as a use, so the least recently USED key is evicted when the "
            "cache exceeds capacity. Re-putting an existing key updates its value and "
            "refreshes its recency. capacity < 1 raises ValueError. len(cache) returns "
            "the number of stored items."
        ),
        "tests": """
try:
    LRUCache(0)
    raise AssertionError("expected ValueError")
except ValueError:
    pass

c = LRUCache(2)
c.put(1, "a"); c.put(2, "b")
assert c.get(1) == "a"
c.put(3, "c")            # evicts 2 (1 was just used)
assert c.get(2) is None
assert c.get(3) == "c"
assert len(c) == 2
c.put(3, "cc")
assert c.get(3) == "cc"
assert len(c) == 2
c.put(4, "d")            # evicts 1
assert c.get(1) is None
assert c.get(3) == "cc" and c.get(4) == "d"

c = LRUCache(1)
c.put("x", 1); c.put("y", 2)
assert c.get("x") is None and c.get("y") == 2
""",
        "reference": """
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key):
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def __len__(self):
        return len(self._data)
""",
    },
]
