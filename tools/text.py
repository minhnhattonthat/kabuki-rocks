"""Script text: extract inline text runs to script/*.json and encode them back.

    python -X utf8 tools/text.py dump [--force]   # write script/bank_XX.json (refuses to overwrite without --force)
    python -X utf8 tools/text.py stats

Run tokens (jp field): glyphs from tbl/jp.tbl; dictionary words as {ウメばあちゃん#0A9D}; controls as {n} {wait}
{clr} {delay:78} {name93} {name94} {p9a} {b8:0102} {ba}; pointers as {jump:08A0F0} / {choice:08A0F0} (CPU address).
Unknown glyph codes as [XXXX].
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / ".claude/skills/translate-retro-game/scripts"))
import dictwords  # noqa: E402
import script_ops  # noqa: E402
from tbl import Table  # noqa: E402

ROM = ROOT / "rom" / "Kabuki Rocks (Japan).sfc"
SCRIPT = ROOT / "script"
JP = Table.load(ROOT / "tbl" / "jp.tbl")
EN = Table.load(ROOT / "tbl" / "en.tbl")
CTRL = {code[0]: (name, argc) for code, (name, argc) in JP.ctrl.items()}
CTRL_ENC = {name: (code, argc) for code, (name, argc) in CTRL.items()}
PTR_CTRL = {"jump", "choice"}


def glyph(rom, w):
    if w >= 0x300:
        s = "".join(JP.dec.get(c.to_bytes(2, "big"), f"[{c:04X}]") for c in dictwords.word(rom, w))
        return f"{{{s}#{w:04X}}}"
    return JP.dec.get(w.to_bytes(2, "big"), f"[{w:04X}]")


def decode(rom, raw):
    out, i = [], 0
    while i < len(raw):
        b = raw[i]
        if b < 0x80:
            out.append(glyph(rom, b << 8 | raw[i + 1])); i += 2
            continue
        name, argc = CTRL[b]
        args = raw[i + 1:i + 1 + argc]
        if name in PTR_CTRL:
            out.append(f"{{{name}:{args[2]:02X}{args[1]:02X}{args[0]:02X}}}")
        elif argc:
            out.append(f"{{{name}:{args.hex().upper()}}}")
        else:
            out.append(f"{{{name}}}")
        i += 1 + argc
    return "".join(out)


TOKEN = re.compile(r"\{([^{}#:]*)#([0-9A-F]{4})\}|\{(\w+)(?::([0-9A-F]+))?\}|\[([0-9A-F]{4})\]|(.)", re.S)


def encode(s, enc=None):
    """Tokens -> bytes. enc: glyph table (Table.enc keyed by char), default JP."""
    enc = enc or JP.enc
    out = bytearray()
    for m in TOKEN.finditer(s):
        word, wcode, name, arg, hexw, ch = m.groups()
        if wcode:
            out += bytes.fromhex(wcode)
        elif name:
            code, argc = CTRL_ENC[name]
            a = bytes.fromhex(arg or "")
            if name in PTR_CTRL:
                a = a[::-1]
            if len(a) != argc:
                raise ValueError(f"{{{name}}} needs {argc} arg bytes: {s!r}")
            out += bytes([code]) + a
        elif hexw:
            out += bytes.fromhex(hexw)
        else:
            if ch not in enc:
                raise ValueError(f"no code for {ch!r} in {s!r}")
            out += enc[ch]
    return bytes(out)


def runs(rom):
    """Every distinct text run reachable from the script table: {cpu addr: Item}."""
    out = {}
    for e in script_ops.table(rom):
        try:
            items = script_ops.parse(rom, e)
        except ValueError:
            continue  # ids 263-270: garbage entries (docs/re/text.md)
        for it in items:
            if it.op is None:
                out[it.addr] = it
    return dict(sorted(out.items()))


def dump(force=False):
    rom = ROM.read_bytes()
    banks = {}
    for a, it in runs(rom).items():
        banks.setdefault(a >> 16, []).append({
            "id": f"{a:06X}", "size": it.size, "jp": decode(rom, it.args), "en": "", "notes": ""})
    SCRIPT.mkdir(exist_ok=True)
    for bank, entries in banks.items():
        p = SCRIPT / f"bank_{bank:02X}.json"
        if p.exists() and not force:
            print(f"skip {p.name} (exists; --force overwrites English)")
            continue
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            json.dump(entries, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"{p.name}: {len(entries)} runs")


def load():
    out = []
    for p in sorted(SCRIPT.glob("bank_*.json")):
        out += json.loads(p.read_text(encoding="utf-8"))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dump":
        dump("--force" in sys.argv)
    elif cmd == "stats":
        e = load()
        print(f"{len(e)} runs, {sum(1 for x in e if x['en'])} translated")
    else:
        print(__doc__)
