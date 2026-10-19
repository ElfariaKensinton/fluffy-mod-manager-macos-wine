#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CC="${CC:-x86_64-w64-mingw32-gcc}"
command -v "$CC" >/dev/null 2>&1 || { echo "Install mingw-w64 first (macOS: brew install mingw-w64)." >&2; exit 1; }
mkdir -p "$ROOT/bin"
"$CC" -Os -s -municode -mwindows -static -o "$ROOT/bin/FluffyModManager-Mesa.exe" "$ROOT/src/launcher.c"
echo "Built $ROOT/bin/FluffyModManager-Mesa.exe"
OBJ="$(mktemp "${TMPDIR:-/tmp}/fluffy-trainer.XXXXXX")"
trap 'rm -f -- "$OBJ"' EXIT
"$CC" -c -o "$OBJ" "$ROOT/src/trainer_scan.S"
python3 "$ROOT/build_trainer.py" "$OBJ"
