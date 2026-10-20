#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/Fluffy-Mod-Manager" >&2
  exit 2
fi
FLUFFY_DIR="$(cd "$1" 2>/dev/null && pwd)" || { echo "Fluffy folder not found: $1" >&2; exit 1; }
[[ -f "$FLUFFY_DIR/Modmanager.exe" ]] || { echo "Modmanager.exe not found in: $FLUFFY_DIR" >&2; exit 1; }
python3 "$ROOT/patch_trainer_guard.py" --check "$FLUFFY_DIR/Modmanager.exe"

MESA_FILES=(opengl32.dll libgallium_wgl.dll libspirv_to_dxil.dll dxil.dll)
NEED_MESA=0
for dll in "${MESA_FILES[@]}"; do
  [[ -f "$FLUFFY_DIR/$dll" ]] || NEED_MESA=1
done

if [[ "$NEED_MESA" -eq 0 ]]; then
  echo "All Mesa runtime files already exist in the target folder; skipping download."
else
  # Pinned official pal1000/mesa-dist-win MinGW x64 release and its GitHub asset digest.
  MESA_URL="https://github.com/pal1000/mesa-dist-win/releases/download/26.2.4/mesa3d-26.2.4-release-mingw.7z"
  MESA_SHA256="36a30a04d8cab6e2bea2d3c747c326d15024d9711dd80f45ef97ac6f2c3c5086"
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/fluffy-mesa.XXXXXX")"
  trap 'rm -rf -- "$TMP"' EXIT
  ARCHIVE="$TMP/mesa.7z"
  echo "Downloading Mesa 26.2.4 x64 runtime from the official release…"
  curl --fail --location --retry 3 --retry-all-errors --connect-timeout 20 "$MESA_URL" --output "$ARCHIVE"
  ACTUAL_SHA256="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
  [[ "$ACTUAL_SHA256" == "$MESA_SHA256" ]] || { echo "Mesa download checksum mismatch; refusing to install it." >&2; exit 1; }

  mkdir "$TMP/unpacked"
  if ! /usr/bin/tar -xf "$ARCHIVE" -C "$TMP/unpacked" 2>/dev/null; then
    if command -v 7zz >/dev/null 2>&1; then
      7zz x -y "-o$TMP/unpacked" "$ARCHIVE" >/dev/null
    elif command -v 7z >/dev/null 2>&1; then
      7z x -y "-o$TMP/unpacked" "$ARCHIVE" >/dev/null
    else
      echo "macOS could not extract the Mesa archive. Install 7-Zip (brew install sevenzip) and rerun." >&2
      exit 1
    fi
  fi
  MESA_DIR="$TMP/unpacked/x64"
  for dll in "${MESA_FILES[@]}"; do
    [[ -f "$MESA_DIR/$dll" ]] || { echo "Official Mesa archive is missing x64/$dll." >&2; exit 1; }
  done

  for dll in "${MESA_FILES[@]}"; do
    if [[ -f "$FLUFFY_DIR/$dll" && ! -e "$FLUFFY_DIR/$dll.bak" ]]; then
      cp -p "$FLUFFY_DIR/$dll" "$FLUFFY_DIR/$dll.bak"
    fi
    cp -p "$MESA_DIR/$dll" "$FLUFFY_DIR/$dll"
  done
fi
[[ -f "$ROOT/bin/FluffyModManager-Mesa.exe" ]] || { echo "Bundled launcher binary missing: $ROOT/bin/FluffyModManager-Mesa.exe" >&2; exit 1; }
cp -p "$ROOT/bin/FluffyModManager-Mesa.exe" "$FLUFFY_DIR/FluffyModManager-Mesa.exe"
python3 "$ROOT/patch_trainer_guard.py" "$FLUFFY_DIR/Modmanager.exe"
echo "Verified Mesa runtime files, installed the bounded trainer scanner, and created: $FLUFFY_DIR/FluffyModManager-Mesa.exe"
echo "Run this EXE through the same Wine/NotProton prefix as the game."
