"""Build the patched ROM.

    python -X utf8 build.py [--out build/kabuki_en.sfc] [--marker]

Text runs with an `en` field are encoded into the expansion area (banks $30-$3F, file 0x180000-0x1FFFFF) and the
original run start is overwritten with `86 lo hi bank` (text-mode jump). The English ends with a jump back to the
byte after the original run (the next script op), unless it already ends with a {jump}. Runs without English stay
untouched, so a build with no English is byte-identical to the original (tests/test_build.py).
--marker replaces every run with "[id]" marker text (phase 4 tour).
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import text  # noqa: E402
from script_ops import off  # noqa: E402

EXP_BANKS = range(0x30, 0x40)  # LoROM 30:8000-3F:FFFF = file 0x180000-0x1FFFFF
ROM_SIZE = 0x200000


class Space:
    """Bump allocator in the expansion banks; a block never crosses a bank (text is read via [$27],y)."""

    def __init__(self):
        self.bank, self.pos = EXP_BANKS[0], 0x8000

    def alloc(self, n):
        if n > 0x8000:
            raise ValueError(f"block of {n} bytes cannot fit a bank")
        if self.pos + n > 0x10000:
            self.bank, self.pos = self.bank + 1, 0x8000
            if self.bank not in EXP_BANKS:
                raise ValueError("expansion area full")
        a = self.bank << 16 | self.pos
        self.pos += n
        return a


def jump(a):
    return bytes([0x86, a & 0xFF, a >> 8 & 0xFF, a >> 16])


def build(out, marker=False, encode=None, reloc_jp=False):
    rom = bytearray(text.ROM.read_bytes())
    entries = text.load()
    todo = []
    for e in entries:
        if e["size"] == 0:
            continue
        s = f"[{e['id']}]" if marker else e["jp"] if reloc_jp else e["en"]
        if s:
            todo.append((e, s))
    if todo:
        rom += b"\xff" * (ROM_SIZE - len(rom))
        space = Space()
        for e, s in todo:
            a = int(e["id"], 16)
            body = (encode or text.encode)(s)
            if not re.search(r"\{jump:[0-9A-F]{6}\}$", s):
                body += jump(a + e["size"])
            dst = space.alloc(len(body))
            rom[off(dst):off(dst) + len(body)] = body
            rom[off(a):off(a) + 4] = jump(dst)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(rom)
    return rom, len(todo)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "build" / "kabuki_en.sfc"))
    ap.add_argument("--marker", action="store_true")
    ap.add_argument("--reloc-jp", action="store_true", help="relocate the Japanese runs unchanged (mechanism test)")
    a = ap.parse_args()
    rom, n = build(a.out, a.marker, reloc_jp=a.reloc_jp)
    print(f"{a.out}: {len(rom):#x} bytes, {n} runs relocated")
