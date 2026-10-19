#!/usr/bin/env python3
"""Replace a verified Fluffy trainer scanner with bounded, checked memory reads."""
import argparse
import hashlib
import json
import os
import stat
import struct
import sys
import tempfile
from pathlib import Path

BACKUP_SUFFIX = '.pre-trainer-region-size-guard.bak'
# These are relocation fields, not instructions. All other original bytes must
# match the independently verified scanner shared by stock 3.083 and 3.084.
ORIGINAL_SIZE = 451
ORIGINAL_RELOCATIONS = (53, 60, 99, 119, 156, 162, 180, 210, 221, 386)
ORIGINAL_SHA256 = '7103e150ecc9d11db618377ffd4cb06d266eb3eb2c619ed5ea0c8d51a9ef7d23'
ROOT = Path(__file__).resolve().parent


def u16(data, offset):
    return struct.unpack_from('<H', data, offset)[0]


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


class PE:
    def __init__(self, data):
        self.data = data
        if data[:2] != b'MZ':
            raise ValueError('Not a Windows executable.')
        at = u32(data, 60)
        if data[at:at + 4] != b'PE\0\0' or u16(data, at + 4) != 0x8664:
            raise ValueError('The trainer replacement requires Windows x64 Fluffy.')
        optional = at + 24
        if u16(data, optional) != 0x20b:
            raise ValueError('Expected a PE32+ executable.')
        self.base = struct.unpack_from('<Q', data, optional + 24)[0]
        self.sections = []
        for i in range(u16(data, at + 6)):
            s = optional + u16(data, at + 20) + i * 40
            virtual_size, rva, raw_size, raw = struct.unpack_from('<IIII', data, s + 8)
            self.sections.append((rva, max(virtual_size, raw_size), raw, raw_size, u32(data, s + 36)))
        directory = optional + 112
        imports_rva = u32(data, directory + 8)
        self.imports = {}
        descriptor = self.offset(imports_rva)
        while any(data[descriptor:descriptor + 20]):
            names = u32(data, descriptor) or u32(data, descriptor + 16)
            slots = u32(data, descriptor + 16)
            j = 0
            while True:
                entry = struct.unpack_from('<Q', data, self.offset(names + j * 8))[0]
                if not entry:
                    break
                if not entry >> 63:
                    start = self.offset(entry) + 2
                    name = data[start:data.index(b'\0', start)].decode('ascii')
                    self.imports[name] = slots + j * 8
                j += 1
            descriptor += 20
        exception_rva, exception_size = struct.unpack_from('<II', data, directory + 24)
        self.functions = []
        start = self.offset(exception_rva)
        for at in range(start, start + exception_size, 12):
            begin, end, unwind = struct.unpack_from('<III', data, at)
            self.functions.append((begin, end, unwind, at))

    def offset(self, rva, size=1):
        for start, length, raw, raw_size, flags in self.sections:
            if start <= rva and rva + size <= start + raw_size:
                offset = raw + rva - start
                if offset + size <= len(self.data):
                    return offset
        raise ValueError(f'RVA 0x{rva:x} is outside file-backed sections.')

    def writable(self, rva):
        return any(start <= rva and rva + 8 <= start + size and flags & 0x80000000
                   for start, size, _, _, flags in self.sections)


def normalized(code, relocations):
    result = bytearray(code)
    for offset in relocations:
        result[offset:offset + 4] = bytes(4)
    return hashlib.sha256(result).hexdigest()


def replacement():
    code = (ROOT / 'bin/trainer_scan.bin').read_bytes()
    metadata = json.loads((ROOT / 'bin/trainer_scan.json').read_text())
    if len(code) != metadata['size'] or hashlib.sha256(code).hexdigest() != metadata['sha256']:
        raise ValueError('Trainer replacement artifacts do not match. Rebuild using build.sh.')
    return code, metadata


def plan(data):
    pe = PE(data)
    code, metadata = replacement()
    offsets = [r['offset'] for r in metadata['relocations']]
    matches = []
    for begin, end, unwind, record in pe.functions:
        if end - begin not in (ORIGINAL_SIZE, len(code)):
            continue
        raw = pe.offset(begin, end - begin)
        body = data[raw:raw + end - begin]
        if len(body) == len(code) and normalized(body, offsets) == metadata['sha256']:
            matches.append(('already-patched', [], begin))
            continue
        if len(body) != ORIGINAL_SIZE or normalized(body, ORIGINAL_RELOCATIONS) != ORIGINAL_SHA256:
            continue
        def target(field):
            return begin + field + 4 + struct.unpack_from('<i', body, field)[0]
        expected = {119: 'VirtualQueryEx', 162: 'VirtualQueryEx', 221: 'ReadProcessMemory'}
        if any(target(field) != pe.imports.get(name) for field, name in expected.items()):
            raise ValueError('Scanner import validation failed; refusing to modify it.')
        handle, base = target(99), target(60)
        if target(156) != handle or target(210) != handle or not pe.writable(handle) or not pe.writable(base):
            raise ValueError('Scanner game context validation failed; refusing to modify it.')
        # Keep the original prologue and unwind record; only extend the covered
        # range into verified compiler alignment padding, never another function.
        if code[:31] != body[:31] or data[pe.offset(unwind):pe.offset(unwind) + 2] != b'\x01\x1f':
            raise ValueError('Unexpected scanner prologue or x64 unwind format.')
        extra = len(code) - ORIGINAL_SIZE
        if extra < 0 or data[raw + ORIGINAL_SIZE:raw + len(code)] != b'\xcc' * extra:
            raise ValueError('Not enough verified alignment padding for the safe scanner.')
        if any(begin < other < begin + len(code) for other, _, _, _ in pe.functions):
            raise ValueError('Replacement would overlap another function.')
        symbols = {'fluffy_gamehandle': handle, 'fluffy_gamebase': base}
        for name in ('VirtualAlloc', 'VirtualQueryEx', 'ReadProcessMemory', 'VirtualFree'):
            if name not in pe.imports:
                raise ValueError(f'Required API import {name} is absent.')
            symbols['__imp_' + name] = pe.imports[name]
        output = bytearray(code)
        for relocation in metadata['relocations']:
            field = relocation['offset']
            struct.pack_into('<i', output, field, symbols[relocation['symbol']] - begin - field - 4)
        matches.append(('needs-patch', [(raw, bytes(output)), (record + 4, struct.pack('<I', begin + len(code)))], begin))
    if len(matches) != 1:
        digest = hashlib.sha256(data).hexdigest()
        raise ValueError(f'Could not uniquely verify the trainer scanner ({len(matches)} matches; EXE SHA-256 {digest}). '
                         'This checks the scanner code and API imports, not the displayed Fluffy version. No executable changes were made.')
    return matches[0]


def inspect(data):
    return plan(data)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    parser.add_argument('--check', action='store_true', help='validate without writing')
    args = parser.parse_args()
    path = args.exe.resolve()
    try:
        data = path.read_bytes()
        state, edits, rva = plan(data)
        if state == 'already-patched':
            print(f'Bounded trainer scanner already installed at RVA 0x{rva:x}.')
            return 0
        if args.check:
            print(f'Verified trainer scanner at RVA 0x{rva:x}; bounded-read patch can be applied.')
            return 0
        backup = path.with_name(path.name + BACKUP_SUFFIX)
        if backup.exists():
            if backup.read_bytes() != data:
                raise ValueError(f'Existing backup differs from this original EXE: {backup}. Preserve it before patching another build.')
        else:
            with backup.open('xb') as f:
                f.write(data)
            os.chmod(backup, stat.S_IMODE(path.stat().st_mode))
        patched = bytearray(data)
        for offset, value in edits:
            patched[offset:offset + len(value)] = value
        if inspect(patched) != 'already-patched':
            raise ValueError('Replacement validation failed before writing.')
        fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(patched)
            os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        print(f'Installed bounded trainer scanner at RVA 0x{rva:x}; original saved as {backup.name}')
        return 0
    except (OSError, ValueError, struct.error, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
