#!/usr/bin/env python3
"""lolllmbench - a small Python + Bash benchmark for local LLMs.

Talks to any OpenAI-compatible /v1/chat/completions endpoint, grades Python
tasks by actually executing the model's code against hidden unit tests, and
grades Bash tasks by normalised string match.

Usage
-----
    python run_bench.py --model my-model
    python run_bench.py --model my-model --only python --limit 5
    python run_bench.py --config config.json --model my-model
    python run_bench.py --list

Only the standard library is used.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import datetime as dt
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tasks.python_tasks import TASKS as PY_TASKS  # noqa: E402
from tasks.bash_tasks import TASKS as SH_TASKS, ANSWER_INSTRUCTIONS  # noqa: E402

HIDDEN_MARKER = "# ---- HIDDEN TESTS ----"

PY_SYSTEM = (
    "You are a precise Python programmer. Reply with exactly one Python code "
    "block and nothing else - no prose, no explanation, no example usage, no "
    "tests. The code must be complete and runnable on Python 3 using only the "
    "standard library, and must define exactly what the task asks for."
)

SH_SYSTEM = (
    "You are a precise UNIX shell expert. " + ANSWER_INSTRUCTIONS
)


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------
DEFAULTS = {
        "base_url": "http://localhost:8000/v1",
        "api_key": "not-needed",
        "model": "local-model",
        "temperature": 0.0,
        "max_tokens": 1024,
        "request_timeout": 300,
        "exec_timeout": 15,
        "concurrency": 1,
        "stream": False,
        "extra_body": {},
}


def load_config(path: Path | None) -> dict:
    cfg = {**DEFAULTS, "api_key": os.environ.get("OPENAI_API_KEY") or "not-needed"}
    if path is not None:
        supplied = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(supplied, dict):
            raise ValueError("config must be a JSON object")
        unknown = supplied.keys() - DEFAULTS.keys()
        if unknown:
            raise ValueError("unknown config keys: " + ", ".join(sorted(unknown)))
        cfg.update(supplied)
    return cfg


def validate_config(cfg: dict) -> None:
    for key in ("base_url", "api_key", "model"):
        if not isinstance(cfg[key], str) or not cfg[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    url = urllib.parse.urlsplit(cfg["base_url"])
    if url.scheme not in ("http", "https") or not url.hostname or url.query or url.fragment:
        raise ValueError("base_url must be an HTTP(S) API base URL without query or fragment")
    if url.username or url.password:
        raise ValueError("use api_key for authentication, not credentials in base_url")
    for key in ("max_tokens", "concurrency"):
        if type(cfg[key]) is not int or cfg[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    for key in ("temperature", "request_timeout", "exec_timeout"):
        value = cfg[key]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
        if value < 0 or (key != "temperature" and value == 0):
            raise ValueError(f"{key} must be {'non-negative' if key == 'temperature' else 'positive'}")
    if type(cfg["stream"]) is not bool:
        raise ValueError("stream must be true or false")
    if not isinstance(cfg["extra_body"], dict):
        raise ValueError("extra_body must be a JSON object")
    reserved = cfg["extra_body"].keys() & {"model", "messages", "temperature", "max_tokens", "stream"}
    if reserved:
        raise ValueError("extra_body cannot override core request fields: " + ", ".join(sorted(reserved)))


# --------------------------------------------------------------------------
# endpoint
# --------------------------------------------------------------------------
def _chat_stream(cfg: dict, system: str, user: str) -> tuple[str, dict]:
    """Same as chat(), but prints tokens to the terminal as they arrive."""
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
        "stream": True,
    }
    payload.update(cfg.get("extra_body") or {})
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + str(cfg.get("api_key", "not-needed")),
        },
        method="POST",
    )
    t0 = time.time()
    text_parts: list[str] = []
    reason_parts: list[str] = []
    finish = None
    usage: dict = {}
    mode = None
    try:
        with urllib.request.urlopen(req, timeout=cfg["request_timeout"]) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                if chunk.get("usage"):
                    usage = chunk["usage"]
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                ch = choices[0]
                finish = ch.get("finish_reason") or finish
                delta = ch.get("delta") or {}
                r = delta.get("reasoning_content") or delta.get("reasoning")
                c = delta.get("content")
                if r:
                    if mode != "r":
                        sys.stdout.write("\n------ thinking ------\n")
                        mode = "r"
                    reason_parts.append(r)
                    sys.stdout.write(r)
                    sys.stdout.flush()
                if c:
                    if mode != "c":
                        sys.stdout.write("\n------ answer ------\n")
                        mode = "c"
                    text_parts.append(c)
                    sys.stdout.write(c)
                    sys.stdout.flush()
    except Exception as exc:  # noqa: BLE001
        return "".join(text_parts), {
            "error": f"{type(exc).__name__}: {exc}",
            "latency": round(time.time() - t0, 2),
        }

    sys.stdout.write("\n")
    sys.stdout.flush()
    text = "".join(text_parts)
    reasoning = "".join(reason_parts)
    meta = {
        "latency": round(time.time() - t0, 2),
        "completion_tokens": usage.get("completion_tokens"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "finish_reason": finish,
        "reasoning_chars": len(reasoning),
        "reasoning": reasoning,
    }
    if not text.strip() and (reasoning or finish == "length"):
        meta["truncated_thinking"] = True
    return text, meta


def chat(cfg: dict, system: str, user: str) -> tuple[str, dict]:
    """POST to /chat/completions. Returns (text, meta)."""
    if cfg.get("stream"):
        return _chat_stream(cfg, system, user)
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
        "stream": False,
    }
    # server-specific knobs, e.g. {"chat_template_kwargs": {"enable_thinking": false}}
    payload.update(cfg.get("extra_body") or {})
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + str(cfg.get("api_key", "not-needed")),
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=cfg["request_timeout"]) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return "", {"error": f"HTTP {exc.code}: {exc.read()[:400]!r}", "latency": time.time() - t0}
    except Exception as exc:  # noqa: BLE001
        return "", {"error": f"{type(exc).__name__}: {exc}", "latency": time.time() - t0}

    try:
        msg = body["choices"][0]["message"]
        text = msg.get("content") or ""
    except Exception:  # noqa: BLE001
        return "", {"error": "unexpected response shape", "raw": body, "latency": time.time() - t0}

    # reasoning models put chain-of-thought in a sibling field, not in content
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    usage = body.get("usage") or {}
    meta = {
        "latency": round(time.time() - t0, 2),
        "completion_tokens": usage.get("completion_tokens"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "finish_reason": body["choices"][0].get("finish_reason"),
        "reasoning_chars": len(reasoning),
        "reasoning": reasoning,
    }
    if not text.strip() and (reasoning or meta["finish_reason"] == "length"):
        meta["truncated_thinking"] = True
    return text, meta


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------
FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\r?\n(.*?)```", re.DOTALL)
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_thinking(text: str) -> str:
    text = THINK_RE.sub("", text)
    # unterminated <think> block: keep only what follows the last </think>
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text


def extract_python(text: str) -> str:
    """Pull the model's code out of its reply."""
    text = strip_thinking(text)
    blocks = FENCE_RE.findall(text)
    if blocks:
        py = [b for lang, b in blocks if lang.lower() in ("python", "py", "python3")]
        chosen = py if py else [b for _, b in blocks]
        # concatenate all code blocks: some models split imports from the body
        return "\n\n".join(b.rstrip() for b in chosen)
    return text.strip()


def extract_answer(text: str, lines: int = 1) -> str:
    """Pull a short literal answer out of a reply."""
    text = strip_thinking(text)
    blocks = FENCE_RE.findall(text)
    if blocks:
        text = blocks[-1][1]
    kept = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not kept:
        return ""
    return "\n".join(kept[-lines:])


def normalise(s: str) -> str:
    out = []
    for ln in s.splitlines():
        ln = ln.strip().strip("`").strip()
        ln = re.sub(r"\s+", " ", ln)
        ln = ln.strip("'\"")
        out.append(ln.lower())
    return "\n".join(x for x in out if x)


# --------------------------------------------------------------------------
# grading
# --------------------------------------------------------------------------
def grade_python(task: dict, code: str, exec_timeout: int) -> dict:
    if not code.strip():
        return {"passed": False, "detail": "empty completion"}
    program = code + "\n\n" + HIDDEN_MARKER + "\n" + task["tests"] + "\nprint('__OK__')\n"
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "candidate.py"
        f.write_text(program, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("PYTHONPATH", None)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(f)],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return {"passed": False, "detail": f"timeout after {exec_timeout}s"}
    ok = proc.returncode == 0 and "__OK__" in (proc.stdout or "")
    detail = ""
    if not ok:
        err = (proc.stderr or "").strip().splitlines()
        detail = err[-1] if err else f"exit {proc.returncode}"
    return {"passed": ok, "detail": detail, "returncode": proc.returncode}


def grade_bash(task: dict, reply: str) -> dict:
    want = task["answer"]
    nlines = len(want.splitlines()) if task.get("multiline") else 1
    got = extract_answer(reply, lines=nlines)
    candidates = [normalise(c) for c in [want] + list(task.get("accept", []))]

    # what the model actually offered, in a few readings
    forms = [normalise(got)]
    if not task.get("multiline"):
        # a single-line answer written one item per line still counts:
        # "1\n2\n3\n4\n5" is the right knowledge, wrong rendering
        for k in range(2, 8):
            block = extract_answer(reply, lines=k)
            forms.append(normalise(block.replace("\n", " ")))

    ok = any(f in candidates for f in forms)
    return {"passed": ok, "detail": "" if ok else f"got {got!r}, want {want!r}", "answer": got}


# --------------------------------------------------------------------------
# running
# --------------------------------------------------------------------------
def build_prompt(task: dict, kind: str) -> str:
    if kind == "python":
        return task["prompt"] + "\n\nReturn only the code."
    return task["prompt"] + "\n\n" + ANSWER_INSTRUCTIONS


def run_one(cfg: dict, task: dict, kind: str) -> dict:
    system = PY_SYSTEM if kind == "python" else SH_SYSTEM
    reply, meta = chat(cfg, system, build_prompt(task, kind))
    rec = {
        "id": task["id"],
        "kind": kind,
        "category": task["category"],
        "difficulty": task["difficulty"],
        "raw": reply,
        **meta,
    }
    if meta.get("error"):
        rec.update({"passed": False, "detail": meta["error"]})
        return rec
    if meta.get("truncated_thinking"):
        rec.update({
            "passed": False,
            "detail": (f"no answer: model emitted {meta.get('completion_tokens')} tokens of "
                       f"reasoning ({meta['reasoning_chars']} chars) and hit the token cap "
                       f"before writing content - raise --max-tokens or disable thinking"),
        })
        return rec
    if kind == "python":
        code = extract_python(reply)
        rec["extracted"] = code
        rec.update(grade_python(task, code, cfg["exec_timeout"]))
    else:
        rec.update(grade_bash(task, reply))
    return rec


def select_tasks(only: str, limit: int | None, ids: list[str] | None):
    picked = []
    if only in ("all", "python"):
        picked += [(t, "python") for t in PY_TASKS]
    if only in ("all", "bash"):
        picked += [(t, "bash") for t in SH_TASKS]
    if ids:
        wanted = set(ids)
        picked = [p for p in picked if p[0]["id"] in wanted]
    if limit:
        picked = picked[:limit]
    return picked


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------
def summarise(records: list[dict]) -> dict:
    def rate(rows):
        return round(100.0 * sum(r["passed"] for r in rows) / len(rows), 1) if rows else 0.0

    by = lambda key: {  # noqa: E731
        v: {"n": len([r for r in records if r[key] == v]),
            "pass": sum(r["passed"] for r in records if r[key] == v),
            "pct": rate([r for r in records if r[key] == v])}
        for v in sorted({r[key] for r in records})
    }
    return {
        "total": len(records),
        "passed": sum(r["passed"] for r in records),
        "score_pct": rate(records),
        "by_kind": by("kind"),
        "by_difficulty": by("difficulty"),
        "by_category": by("category"),
        "errors": [r["id"] for r in records if r.get("error")],
    }


def write_report(outdir: Path, cfg: dict, records: list[dict], summary: dict) -> Path:
    lines = []
    a = lines.append
    a(f"# lolllmbench report - `{cfg['model']}`\n")
    a(f"- endpoint: `{cfg['base_url']}`")
    a(f"- run: {dt.datetime.now().isoformat(timespec='seconds')}")
    a(f"- temperature: {cfg['temperature']}\n")
    a(f"## Score: **{summary['passed']}/{summary['total']}  ({summary['score_pct']}%)**\n")

    def table(title, block):
        a(f"### By {title}\n")
        a("| " + title + " | passed | total | % |")
        a("|---|---:|---:|---:|")
        for k, v in block.items():
            a(f"| {k} | {v['pass']} | {v['n']} | {v['pct']} |")
        a("")

    table("kind", summary["by_kind"])
    table("difficulty", summary["by_difficulty"])
    table("category", summary["by_category"])

    a("## Per task\n")
    a("| id | kind | diff | result | latency | note |")
    a("|---|---|---|---|---:|---|")
    for r in records:
        note = (r.get("detail") or "").replace("|", "\\|")[:110]
        a(f"| {r['id']} | {r['kind']} | {r['difficulty']} | "
          f"{'PASS' if r['passed'] else 'FAIL'} | {r.get('latency','')} | {note} |")
    a("")

    fails = [r for r in records if not r["passed"]]
    if fails:
        a("## Failures in detail\n")
        for r in fails:
            a(f"### {r['id']} ({r['difficulty']})\n")
            a(f"*{r.get('detail','')}*\n")
            a("```\n" + (r.get("extracted") or r.get("raw") or "")[:2000] + "\n```\n")

    path = outdir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
def parse_options(argv=None):
    ap = argparse.ArgumentParser(
        description="Benchmark Python + Bash through a local, LAN, or cloud OpenAI-compatible API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
        epilog="""Precedence: built-in defaults < OPENAI_API_KEY < config file < explicit flags.
No config file is loaded unless -config/--config is supplied.
extra_body replaces the file's object; core request fields cannot be overridden there.
The server must provide Chat Completions; this does not start a model server.

Examples:
  python run_bench.py --config
  python run_bench.py -config my-config.json --max-tokens 8192
  python run_bench.py --base-url http://localhost:8000/v1 --model local-model
  python run_bench.py --base-url http://192.168.1.10:8000/v1 --model local-model
  python run_bench.py --base-url https://api.example.com/v1 --model cloud-model
""")
    ap.add_argument("-config", "--config", nargs="?", const=str(ROOT / "config.json"),
                    metavar="PATH", help="load JSON file; omitted PATH means config.json beside this script")
    descriptions = {
        "base_url": "API base URL including any /v1 prefix; /chat/completions is appended",
        "api_key": "Bearer API key; defaults to OPENAI_API_KEY or not-needed",
        "model": "model ID accepted by your server",
        "temperature": "non-negative sampling temperature",
        "max_tokens": "positive completion token cap (including reasoning on some servers)",
        "request_timeout": "positive HTTP socket timeout in seconds",
        "exec_timeout": "positive timeout in seconds for each Python grading subprocess",
        "concurrency": "positive number of simultaneous requests",
        "extra_body": 'JSON object of provider options, e.g. {"seed":42}; replaces file value',
    }
    for key, description in descriptions.items():
        converter = (int if key in ("max_tokens", "concurrency") else
                     float if key in ("temperature", "request_timeout", "exec_timeout") else
                     json.loads if key == "extra_body" else str)
        default_note = "" if key == "api_key" else f" (built-in: {json.dumps(DEFAULTS[key])})"
        ap.add_argument("--" + key.replace("_", "-"), type=converter, help=description + default_note)
    ap.add_argument("--only", choices=["all", "python", "bash"], default="all",
                    help="task language to select (default: all)")
    ap.add_argument("--limit", type=int, help="run the first N selected tasks; positive integer (default: all)")
    ap.add_argument("--id", action="append", help="run only these task ids (repeatable)")
    stream = ap.add_mutually_exclusive_group()
    stream.add_argument("--stream", action="store_true", default=None,
                        help="print tokens and reasoning live; forces concurrency 1 (default: off)")
    stream.add_argument("--no-stream", dest="stream", action="store_false",
                        help="disable streaming, including when enabled in the config file")
    ap.add_argument("--outdir", default=str(ROOT / "runs"),
                    help="parent directory for timestamped results (default: runs beside this script)")
    ap.add_argument("--list", action="store_true", help="list tasks and exit")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(Path(args.config) if args.config else None)
        for key in DEFAULTS:
            val = getattr(args, key, None)
            if val is not None:
                cfg[key] = val
        validate_config(cfg)
        if args.limit is not None and args.limit <= 0:
            raise ValueError("limit must be a positive integer")
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    if cfg["stream"]:
        cfg["concurrency"] = 1
    return args, cfg


def main() -> int:
    args, cfg = parse_options()

    tasks = select_tasks(args.only, args.limit, args.id)

    if args.list:
        for t, kind in tasks:
            print(f"{t['id']:<26} {kind:<7} {t['difficulty']:<7} {t['category']}")
        print(f"\n{len(tasks)} tasks")
        return 0

    if not tasks:
        print("no tasks selected", file=sys.stderr)
        return 2

    print(f"model={cfg['model']}  endpoint={cfg['base_url']}  tasks={len(tasks)}")
    records: list[dict] = []
    workers = max(1, int(cfg.get("concurrency", 1)))

    def work(pair):
        t, kind = pair
        return run_one(cfg, t, kind)

    if workers == 1:
        for i, pair in enumerate(tasks, 1):
            rec = work(pair)
            records.append(rec)
            print(f"[{i:>2}/{len(tasks)}] {rec['id']:<26} "
                  f"{'PASS' if rec['passed'] else 'FAIL'}  {rec.get('detail','')[:70]}")
    else:
        with futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for rec in pool.map(work, tasks):
                records.append(rec)
                print(f"{rec['id']:<26} {'PASS' if rec['passed'] else 'FAIL'}  "
                      f"{rec.get('detail','')[:70]}")

    order = {t["id"]: i for i, (t, _) in enumerate(tasks)}
    records.sort(key=lambda r: order[r["id"]])
    summary = summarise(records)

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_model = re.sub(r"[^A-Za-z0-9._-]+", "_", str(cfg["model"]))
    outdir = Path(args.outdir) / f"{stamp}_{safe_model}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "results.json").write_text(
        json.dumps({"config": {k: v for k, v in cfg.items() if k != "api_key"},
                    "summary": summary, "records": records}, indent=2),
        encoding="utf-8",
    )
    report = write_report(outdir, cfg, records, summary)

    print("\n" + "=" * 60)
    print(f"SCORE {summary['passed']}/{summary['total']}  ({summary['score_pct']}%)")
    for k, v in summary["by_difficulty"].items():
        print(f"  {k:<7} {v['pass']}/{v['n']}  ({v['pct']}%)")
    print(f"\nreport:  {report}")
    print(f"results: {outdir / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
