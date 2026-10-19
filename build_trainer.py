#!/usr/bin/env python3
"""Extract the readable trainer_scan.S assembly's code and COFF relocations."""
import hashlib
import json
import struct
import sys
from pathlib import Path

obj = Path(sys.argv[1]).read_bytes()
machine, count, _, symbols_at, symbols_count, optional, _ = struct.unpack_from('<HHIIIHH', obj)
assert machine == 0x8664
strings = symbols_at + symbols_count * 18
symbols = {}
i = 0
while i < symbols_count:
    at = symbols_at + i * 18
    raw, value, section, kind, storage, auxiliary = struct.unpack_from('<8sIhHBB', obj, at)
    if raw[:4] == bytes(4):
        start = strings + struct.unpack_from('<I', raw, 4)[0]
        name = obj[start:obj.index(b'\0', start)].decode()
    else:
        name = raw.rstrip(b'\0').decode()
    symbols[i] = (name, value)
    i += 1 + auxiliary
end = next(v for n, v in symbols.values() if n == 'trainer_scan_end')
for i in range(count):
    at = 20 + optional + 40 * i
    if obj[at:at + 8].rstrip(b'\0') != b'.text':
        continue
    size, raw_at, reloc_at = struct.unpack_from('<III', obj, at + 16)
    reloc_count = struct.unpack_from('<H', obj, at + 32)[0]
    code = obj[raw_at:raw_at + end]
    relocations = []
    for j in range(reloc_count):
        offset, symbol, kind = struct.unpack_from('<IIH', obj, reloc_at + j * 10)
        assert kind == 4, 'Only AMD64 REL32 relocations are supported'
        assert struct.unpack_from('<i', code, offset)[0] == 0
        relocations.append({'offset': offset, 'symbol': symbols[symbol][0]})
    root = Path(__file__).resolve().parent / 'bin'
    root.mkdir(exist_ok=True)
    (root / 'trainer_scan.bin').write_bytes(code)
    (root / 'trainer_scan.json').write_text(json.dumps({'size': len(code), 'sha256': hashlib.sha256(code).hexdigest(), 'relocations': relocations}, indent=2) + '\n')
    print(f'Built {len(code)}-byte trainer scanner from src/trainer_scan.S')
    break
