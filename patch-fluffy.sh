#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 /path/to/Fluffy-Mod-Manager [path/to/Mesa-runtime-x64]" >&2
  exit 2
fi
FLUFFY_DIR="$(cd "$1" 2>/dev/null && pwd)" || { echo "Fluffy folder not found: $1" >&2; exit 1; }
[[ -f "$FLUFFY_DIR/Modmanager.exe" ]] || { echo "Modmanager.exe not found in: $FLUFFY_DIR" >&2; exit 1; }
if [[ $# -eq 2 ]]; then
  MESA_DIR="$(cd "$2" 2>/dev/null && pwd)" || { echo "Mesa folder not found: $2" >&2; exit 1; }
  for required in opengl32.dll libgallium_wgl.dll; do
    [[ -f "$MESA_DIR/$required" ]] || { echo "Mesa runtime is missing $required: $MESA_DIR" >&2; exit 1; }
  done
  for dll in opengl32.dll libgallium_wgl.dll dxil.dll spirv_to_dxil.dll; do
    if [[ -f "$MESA_DIR/$dll" ]]; then
      if [[ -f "$FLUFFY_DIR/$dll" ]]; then cp -p "$FLUFFY_DIR/$dll" "$FLUFFY_DIR/$dll.bak"; fi
      cp -p "$MESA_DIR/$dll" "$FLUFFY_DIR/$dll"
    fi
  done
fi
for required in opengl32.dll libgallium_wgl.dll; do
  [[ -f "$FLUFFY_DIR/$required" ]] || { echo "Missing $required beside Modmanager.exe. Supply the Mesa runtime folder as argument 2." >&2; exit 1; }
done
[[ -f "$ROOT/bin/FluffyModManager-Mesa.exe" ]] || { echo "Bundled launcher binary missing: $ROOT/bin/FluffyModManager-Mesa.exe" >&2; exit 1; }
cp -p "$ROOT/bin/FluffyModManager-Mesa.exe" "$FLUFFY_DIR/FluffyModManager-Mesa.exe"
echo "Created: $FLUFFY_DIR/FluffyModManager-Mesa.exe"
echo "Run this EXE through the same Wine/NotProton prefix as the game."
