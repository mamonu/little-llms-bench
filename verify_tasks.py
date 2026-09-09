#!/usr/bin/env python3
"""Sanity-check the task bank without touching any model.

- Runs every Python task's reference solution against its hidden tests
  (all must pass) and, as a negative control, a deliberately empty solution
  (all must fail).
- Checks every Bash answer key round-trips through the harness grader.

Run this after editing tasks/*.py.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tasks.python_tasks import TASKS as PY_TASKS  # noqa: E402
from tasks.bash_tasks import TASKS as SH_TASKS  # noqa: E402
from run_bench import grade_python, grade_bash  # noqa: E402

EXEC_TIMEOUT = 30


def main() -> int:
    bad = 0

    print("== python reference solutions ==")
    for t in PY_TASKS:
        r = grade_python(t, t["reference"], EXEC_TIMEOUT)
        status = "ok  " if r["passed"] else "FAIL"
        if not r["passed"]:
            bad += 1
        print(f"  {status} {t['id']:<26} {r['detail']}")

    print("\n== python negative control (empty solution must fail) ==")
    for t in PY_TASKS:
        r = grade_python(t, "pass\n", EXEC_TIMEOUT)
        if r["passed"]:
            bad += 1
            print(f"  FAIL {t['id']:<26} passed with an empty solution!")
    print("  (silent = every task correctly rejected an empty solution)")

    print("\n== bash answer keys ==")
    seen = set()
    for t in SH_TASKS:
        if t["id"] in seen:
            bad += 1
            print(f"  FAIL duplicate id {t['id']}")
        seen.add(t["id"])
        reply = "Some preamble the model might add.\n" + t["answer"]
        r = grade_bash(t, reply)
        status = "ok  " if r["passed"] else "FAIL"
        if not r["passed"]:
            bad += 1
        print(f"  {status} {t['id']:<26} {r['detail']}")
        wrong = grade_bash(t, "definitely not the answer")
        if wrong["passed"]:
            bad += 1
            print(f"  FAIL {t['id']:<26} accepted a wrong answer")

    py_ids = {t["id"] for t in PY_TASKS}
    if len(py_ids) != len(PY_TASKS):
        bad += 1
        print("\nFAIL duplicate python task ids")

    print(f"\n{len(PY_TASKS)} python + {len(SH_TASKS)} bash tasks; {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
