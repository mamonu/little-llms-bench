#!/usr/bin/env python3
"""Print what a model actually said on a task.

    python show_run.py py19_tokenizer            # latest run containing it
    python show_run.py py19_tokenizer --reasoning-only
    python show_run.py --list                    # runs on disk
"""
import argparse, glob, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("task_id", nargs="?")
ap.add_argument("--run", help="specific run directory")
ap.add_argument("--reasoning-only", action="store_true")
ap.add_argument("--list", action="store_true")
a = ap.parse_args()

runs = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs", "*")))
if a.list or not a.task_id:
    for r in runs:
        try:
            d = json.load(open(os.path.join(r, "results.json"), encoding="utf-8"))
            print(f"{os.path.basename(r):<55} {d['summary']['passed']}/{d['summary']['total']}")
        except Exception:
            pass
    sys.exit(0)

search = [a.run] if a.run else list(reversed(runs))
for r in search:
    f = os.path.join(r, "results.json")
    if not os.path.exists(f):
        continue
    for rec in json.load(open(f, encoding="utf-8"))["records"]:
        if rec["id"] != a.task_id:
            continue
        print(f"# {rec['id']}  [{os.path.basename(r)}]")
        print(f"# {'PASS' if rec['passed'] else 'FAIL'}  {rec.get('detail','')}")
        print(f"# {rec.get('latency')}s  {rec.get('completion_tokens')} tokens  "
              f"finish={rec.get('finish_reason')}\n")
        reasoning = rec.get("reasoning")
        if reasoning:
            print("=" * 70 + "\nREASONING\n" + "=" * 70)
            print(reasoning)
        elif rec.get("reasoning_chars"):
            print(f"[{rec['reasoning_chars']} chars of reasoning were not saved - "
                  f"this run predates reasoning capture]")
        if not a.reasoning_only:
            print("\n" + "=" * 70 + "\nANSWER\n" + "=" * 70)
            print(rec.get("extracted") or rec.get("raw") or "(empty)")
        sys.exit(0)
print(f"no record of {a.task_id}", file=sys.stderr)
sys.exit(1)
