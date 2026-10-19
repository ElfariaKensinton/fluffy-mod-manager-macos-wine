#!/usr/bin/env python3
"""Apply the Fluffy 3.084 trainer memory-region scan crash guard fix."""

import argparse
import os
import stat
import sys
import tempfile
from pathlib import Path

ORIGINAL = bytes.fromhex("80 7c 24 79 10 75 1a e8 ba 20 14 00 c3")
PATCHED = bytes.fromhex("80 7c 24 6b 10 73 1a e8 ba 20 14 00 c3")
BACKUP_SUFFIX = ".pre-trainer-region-size-guard.bak"


def inspect(data: bytes) -> str:
    original_count = data.count(ORIGINAL)
    patched_count = data.count(PATCHED)
    if original_count == 1 and patched_count == 0:
        return "needs-patch"
    if original_count == 0 and patched_count == 1:
        return "already-patched"
    raise ValueError(
        "Unsupported Modmanager.exe build: expected the unique Fluffy 3.084 "
        "trainer scan signature. No executable changes were made."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("exe", type=Path)
    parser.add_argument("--check", action="store_true", help="validate patch compatibility without writing")
    args = parser.parse_args()

    path = args.exe.resolve()
    if not path.is_file():
        print(f"Modmanager.exe not found: {path}", file=sys.stderr)
        return 1
    data = path.read_bytes()
    try:
        state = inspect(data)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    if state == "already-patched":
        print("Trainer scan guard is already patched.")
        return 0
    if args.check:
        print("Fluffy trainer scan signature found; patch can be applied.")
        return 0

    backup = path.with_name(path.name + BACKUP_SUFFIX)
    if backup.exists():
        backup_data = backup.read_bytes()
        try:
            backup_state = inspect(backup_data)
        except ValueError:
            backup_state = "invalid"
        if backup_state != "needs-patch":
            print(f"Refusing to replace incompatible backup: {backup}", file=sys.stderr)
            return 1
        if backup_data != data:
            print(f"Refusing to overwrite existing non-matching backup: {backup}", file=sys.stderr)
            return 1
    else:
        backup.write_bytes(data)
        os.chmod(backup, stat.S_IMODE(path.stat().st_mode))

    patched = data.replace(ORIGINAL, PATCHED, 1)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(patched)
        os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise

    print(f"Patched trainer memory-region guard; original saved as {backup.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
