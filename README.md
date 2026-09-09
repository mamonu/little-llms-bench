# litlle llm bench

A small, self-contained benchmark for grading local LLMs on **Python** and **Bash**.
Python 3.10+ and the standard library only — no pip install. Works with a model
server on this machine, on your home network, or a cloud service offering an
OpenAI-compatible **Chat Completions** endpoint.

**Start with `--stream`** to see tokens and reasoning as the server emits them.
This is especially useful when debugging reasoning models: you can see their
progress before the final answer arrives. Streaming uses one request at a time;
reasoning is visible when the server includes it in the response.

- **20 Python tasks**, graded by *actually executing* the model's code against hidden
  unit tests in an isolated subprocess. Pass = exit code 0.
- **10 Bash tasks**, graded by normalised string match (no shell execution, so this
  runs fine on Windows).
- Tiered `easy` / `medium` / `hard`, tagged by category.

## Quick start

```sh
git clone https://github.com/mamonu/little-llms-bench.git
cd little-llms-bench
python run_bench.py --list
python run_bench.py --help
```

Use `python3` on macOS, or `py -3` on Windows if that is how Python is installed.

### Configure once

Copy `config.example.json` to `config.json`, then edit the endpoint and model ID.
Your personal `config.json` is ignored by Git.

```sh
python run_bench.py --config --stream
python run_bench.py -config other-config.json --max-tokens 16384
```

`-config` and `--config` are aliases. Without a path they read `config.json`
beside the Python script; explicit relative paths resolve from your current
directory. A missing or invalid file reports a usage error.

Launchers always read the adjacent `config.json` and forward extra flags:

```bat
rem Windows (Command Prompt; in PowerShell use .\run_bench.bat)
run_bench.bat --stream
run_bench.bat --only bash --limit 3
```

```sh
# macOS / Linux
./run_bench.sh --stream
./run_bench.sh --only python --limit 3
```

Both launchers work from other directories. A later `--config PATH` selects a
different file. Set `PYTHON` to an interpreter executable path if needed (no
embedded arguments). The Windows launcher tries `py -3`, then `python`; the
shell launcher defaults to `python3`. They preserve the runner's exit status.

### Configure per run

Without `--config`, no file is loaded. Every config key has a matching flag:
replace underscores with hyphens, such as `request_timeout` → `--request-timeout`.
Precedence is **built-in defaults < `OPENAI_API_KEY` < config file < explicit flags**.

```sh
# Server on this machine
python run_bench.py --base-url http://localhost:8000/v1 --model your-model --max-tokens 8192

# Server on your home network (use its actual IP and port)
python run_bench.py --base-url http://192.168.1.10:8000/v1 --model your-model

# Cloud: set OPENAI_API_KEY in your environment, then use the provider's URL/model
python run_bench.py --base-url https://api.example.com/v1 --model provider-model
```

The URLs above are examples. Supply the API **base** URL, including `/v1` or
another prefix if required; the runner appends `/chat/completions`. It uses HTTP
or HTTPS and sends `Authorization: Bearer <api_key>`. It does not load model
weights or start a server. LAN servers must listen on a reachable network
interface. Cloud services must support the Chat Completions request/response
format and Bearer authentication; Responses-only or custom-auth APIs need an adapter.

For cloud config files, remove `api_key` from the copied example to use
`OPENAI_API_KEY`, or replace `not-needed` with your key. A file's `api_key`
overrides the environment. `--api-key` overrides both.

Try `--only bash --limit 1` for a small endpoint smoke test.

### Useful flags

| flag | effect |
|---|---|
| `-h` / `--help` | complete help, defaults, precedence, and examples |
| `--stream` / `--no-stream` | debug with live tokens and reasoning; enabled streaming forces concurrency `1` |
| `-config [PATH]` / `--config [PATH]` | explicitly load JSON settings |
| `--base-url URL` | API base URL; default `http://localhost:8000/v1` |
| `--api-key KEY` | Bearer token; default environment key or `not-needed` |
| `--model ID` | server model ID; default `local-model` |
| `--only python` / `--only bash` | run one half |
| `--limit N` | first N tasks |
| `--id py17_retry_decorator` | run specific tasks (repeatable) |
| `--temperature 0.2` | non-negative sampling temperature; default `0.0` |
| `--max-tokens 8192` | positive token cap; built-in default `1024`, example config `8192` |
| `--request-timeout 300` | positive HTTP socket timeout in seconds; default `300` |
| `--exec-timeout 15` | positive Python grading timeout in seconds; default `15` |
| `--concurrency 4` | positive parallel request count; default `1` |
| `--extra-body JSON` | provider-specific JSON object; default `{}` |
| `--outdir PATH` | output parent directory; default `runs` beside the script |
| `--list` | print the task table and exit |

`--extra-body` replaces the config file's entire `extra_body` object. It cannot
contain `model`, `messages`, `temperature`, `max_tokens`, or `stream`; use the
dedicated settings for those options. For example, in macOS/Linux:

```sh
python3 run_bench.py --config --extra-body '{"chat_template_kwargs":{"enable_thinking":false}}'
```

For Windows, putting nested provider options in the JSON config avoids shell
quoting differences. Providers may restrict temperatures, token limits, or extra
fields; choose settings supported by your server.

## Output

Each run writes `runs/<timestamp>_<model>/`:

- `report.md` — score, breakdowns by kind / difficulty / category, per-task table,
  and an excerpt of each failure (up to 2,000 characters).
- `results.json` — everything machine-readable, including each raw completion.

Comparing models is just running it twice with different `--model` and diffing the
two `report.md` files.

## How Python grading works

The model is told to reply with exactly one Python code block. The harness:

1. strips `<think>…</think>` blocks (reasoning models),
2. pulls out the fenced code block(s) — concatenating them if the model split
   imports from the body — falling back to the whole reply if there are no fences,
3. writes `<model code>` + hidden tests to a temp file,
4. runs it with `python -I` (isolated mode, no user site-packages or `PYTHONPATH`) in a
   temp cwd with a timeout (`exec_timeout`, default 15s).

Tests use plain `assert`s and check behaviour the prompt actually specifies:
edge cases, error types, non-mutation of inputs, and — for `py18` — a 200k-element
timing check that fails a naive `max()`-per-window solution. `py19` blocks
`eval`/`exec`/`compile` by inspecting the submitted source.

## How Bash grading works

Bash questions are output-prediction ("what does this print?") with a single
canonical answer. The harness takes the last non-empty line (or last N lines for
multi-line answers), strips fences/quotes/backticks, collapses whitespace, and
lowercases before comparing. Tasks may list extra `accept` variants.

## Adding tasks

Edit `tasks/python_tasks.py` or `tasks/bash_tasks.py` — each task is a dict, and
the docstring at the top of each file documents the fields. Every Python task
carries a `reference` solution. Then run:

```
python verify_tasks.py
```

which asserts that (a) every reference solution passes its own tests, (b) every
task *rejects* an empty solution (so no test is vacuously true), and (c) every
Bash answer key round-trips through the grader and rejects a wrong answer.
Current state: 20 + 10 tasks, 0 problems.

Run CLI and transport regression tests without contacting a model:

```sh
python -m unittest discover -s tests -v
```

Git ignores `runs/`, `logs/`, local config, Python caches, common weight files,
and model/artifact directories. Keep custom private config files outside the
repository or add their paths to `.gitignore` before committing.

## Caveats

- The harness executes model-generated Python on this machine. A temp directory,
  isolated Python mode, and a timeout are not a security sandbox. Use a disposable
  VM/container with restricted access for untrusted generated code.
- A model scoring 0 on everything is usually a prompt-format problem (no code
  fences) rather than incompetence — check `report.md`'s failure section, it
  includes the raw reply.
