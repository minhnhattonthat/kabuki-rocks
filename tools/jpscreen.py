"""Japanese glyphs a build still draws, from glyph logs (tools/lua/glyphlog.lua "G ..." lines, battleglyph.lua "B ...").

    python -X utf8 tools/jpscreen.py work/qa/screens/*.log     # per log: caller, codes, decoded Japanese

English font codes (0x101-0x164), space, icons (0x1F0-0x1FA), digits and the baked label codes of the last build
(build/baked_codes.json) count as done; everything else is reported.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import text  # noqa: E402


def done_codes():
    ok = set(range(0x101, 0x165)) | {0x02FF} | set(range(0x1F0, 0x1FB))
    p = ROOT / "build" / "baked_codes.json"
    if p.exists():
        ok |= set(json.loads(p.read_text(encoding="utf-8")))
    return ok


def report(path, rom, ok):
    by = collections.OrderedDict()
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        p = line.split()
        if not p or p[0] not in ("G", "B") or len(p) < 4:
            continue
        code = int(p[2], 16)
        caller = p[-1] if p[0] == "G" else p[3]
        by.setdefault(caller, []).append(code)
    out = []
    for caller, codes in by.items():
        jp = [c for c in codes if c not in ok and c < 0x300]
        if jp:
            s = "".join(text.glyph(rom, c) for c in codes if c < 0x300)
            out.append(f"  {caller} {len(jp)}/{len(codes)} {s[:60]}")
    return out


if __name__ == "__main__":
    rom = text.ROM.read_bytes()
    ok = done_codes()
    for path in sys.argv[1:]:
        lines = report(path, rom, ok)
        if lines:
            print(Path(path).name)
            print("\n".join(lines))
