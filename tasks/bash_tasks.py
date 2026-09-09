"""Bash task bank for litlle llm bench.

These are graded WITHOUT executing anything (the benchmark host is Windows):
the model is asked for a short exact answer, and the harness compares its last
non-empty line to the answer key after normalisation.

Each task is a dict:
    id          unique short id
    category    topic tag
    difficulty  easy | medium | hard
    prompt      the question
    answer      the canonical answer (string)
    accept      extra strings that also count as correct (optional)
    multiline   True if the expected answer spans several lines; the harness
                then compares the last N non-empty lines instead of one
"""

ANSWER_INSTRUCTIONS = (
    "Answer with the exact output only. No explanation, no code fences, "
    "no quotes, no leading '$'. If the output is multiple lines, print each "
    "on its own line."
)

TASKS = [
    {
        "id": "sh01_wc_words",
        "category": "pipes",
        "difficulty": "easy",
        "prompt": "What is the exact output of this command?\n\n    echo \"a b c\" | wc -w",
        "answer": "3",
    },
    {
        "id": "sh02_arith",
        "category": "arithmetic",
        "difficulty": "easy",
        "prompt": "What is the exact output of this script?\n\n    x=5\n    echo $((x * 3 + 1))",
        "answer": "16",
    },
    {
        "id": "sh03_cut",
        "category": "text-tools",
        "difficulty": "easy",
        "prompt": "What is the exact output of this command?\n\n    echo \"hello world\" | cut -d' ' -f2",
        "answer": "world",
    },
    {
        "id": "sh04_brace",
        "category": "expansion",
        "difficulty": "easy",
        "prompt": "What is the exact output of this command?\n\n    echo {1..5}",
        "answer": "1 2 3 4 5",
    },
    {
        "id": "sh05_grep_count",
        "category": "text-tools",
        "difficulty": "easy",
        "prompt": (
            "What is the exact output of this command?\n\n"
            "    printf '%s\\n' apple banana cherry | grep -c a"
        ),
        "answer": "2",
    },
    {
        "id": "sh06_awk_sum",
        "category": "awk",
        "difficulty": "medium",
        "prompt": (
            "What is the exact output of this command?\n\n"
            "    seq 1 5 | awk '{s += $1} END {print s}'"
        ),
        "answer": "15",
    },
    {
        "id": "sh07_param_expansion",
        "category": "expansion",
        "difficulty": "medium",
        "prompt": (
            "What is the exact output of this script?\n\n"
            "    f=/tmp/logs/app.2024.log\n"
            "    echo \"${f##*/}\"\n"
            "    echo \"${f%.*}\"\n"
            "    echo \"${f%%.*}\""
        ),
        "answer": "app.2024.log\n/tmp/logs/app.2024\n/tmp/logs/app",
        "multiline": True,
    },
    {
        "id": "sh08_awk_nf",
        "category": "awk",
        "difficulty": "medium",
        "prompt": (
            "What is the exact output of this command?\n\n"
            "    echo \"one:two:three\" | awk -F: '{print $NF}'"
        ),
        "answer": "three",
    },
    {
        "id": "sh09_exit_status",
        "category": "exit-status",
        "difficulty": "medium",
        "prompt": (
            "What is the exact output of this script?\n\n"
            "    false\n"
            "    echo $?\n"
            "    true && echo yes || echo no\n"
            "    echo $?"
        ),
        "answer": "1\nyes\n0",
        "multiline": True,
    },
    {
        "id": "sh10_chmod_numeric",
        "category": "permissions",
        "difficulty": "hard",
        "prompt": (
            "`ls -l` shows a file with the mode string -rwxr-xr--. What is the "
            "equivalent three-digit octal mode you would pass to chmod?"
        ),
        "answer": "754",
        "accept": ["0754"],
    },
]
