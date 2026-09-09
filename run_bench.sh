#!/bin/sh
# PYTHON may name a Python 3 executable; arguments are forwarded unchanged.
case "$0" in
    */*) SCRIPT_DIR=${0%/*} ;;
    *) SCRIPT_DIR=. ;;
esac
SCRIPT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR" && pwd) || exit 1
exec "${PYTHON:-python3}" "$SCRIPT_DIR/run_bench.py" --config "$SCRIPT_DIR/config.json" "$@"
