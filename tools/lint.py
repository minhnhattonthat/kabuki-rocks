"""Lint English script text. Exit 1 on any error; prints errors and one summary line.

    python -X utf8 tools/lint.py [--verbose]

Box (measured 2026-10-15, docs/re/font.md): 28 cells of 8 px per line, 3 lines per page. A line that ends in
{wait} loses its last cell to the blinking arrow. Overlong lines do not clip: they overwrite other lines.
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import text  # noqa: E402
import wrap  # noqa: E402

WIDTH, LINES = 28, 3
NAME_LEN = wrap.NAME_LEN
KEEP = {"jump", "choice", "b8", "ba", "name93", "name94"}  # must match the Japanese multiset
PAGE = {"clr", "p9a"}
JP_CHARS = re.compile(r"[぀-ヿ一-鿿「」『』。、！？]")


def cells(tok):
    m = text.TOKEN.fullmatch(tok)
    word, wcode, name, arg, hexw, ch = m.groups()
    if wcode:
        return len(word)
    if name:
        return NAME_LEN.get(name, 0)
    return 1


def ctrl(s):
    """Multiset of the control codes that must survive translation, with their arguments."""
    return Counter(f"{n}:{a}" for n, a in re.findall(r"\{(\w+)(?::([0-9A-F]+))?\}", s) if n in KEEP)


def check(e):
    errs = []
    en = wrap.wrap(e["en"])  # the build inserts the same line and page breaks
    if JP_CHARS.search(en):
        errs.append("Japanese left in en")
    if ctrl(en) != ctrl(e["jp"]):
        errs.append(f"control codes differ: jp {sorted(ctrl(e['jp']).elements())} en {sorted(ctrl(en).elements())}")
    try:
        text.encode(en, text.EN.enc)
    except (ValueError, KeyError) as x:
        errs.append(f"not encodable: {x}")
        return errs
    line, nlines, toks = 0, 1, [m.group(0) for m in text.TOKEN.finditer(en)]
    for i, tok in enumerate(toks):
        name = re.fullmatch(r"\{(\w+)(?::[0-9A-F]+)?\}", tok)
        name = name[1] if name else None
        if name == "n":
            line, nlines = 0, nlines + 1
            if nlines > LINES:
                errs.append(f"more than {LINES} lines on a page")
        elif name in PAGE:
            line, nlines = 0, 1
        elif name == "wait":
            if line > WIDTH - 1:
                errs.append(f"line before {{wait}} is {line} cells (max {WIDTH - 1}, arrow)")
        else:
            line += cells(tok)
            if line == WIDTH + 1:
                errs.append(f"line over {WIDTH} cells: ...{''.join(toks[max(0, i - 12):i + 1])}")
    return errs


ITEM_CELLS = 10  # item-name slot in the field lists (04:DF35 price at +$14), drawn by asm/tiny.asm


def tiny_cells(s, tiny):
    """Cells asm/tiny.asm uses for s: two tiny letters per cell; a [code] token or a letter missing from the
    tiny font takes a full cell and restarts the pairing."""
    n = run = 0
    for tok in re.findall(r"\[[0-9A-F]{4}\]|.", s):
        if len(tok) == 1 and tok in tiny:
            run += 1
        else:
            n, run = n + (run + 1) // 2 + 1, 0
    return n + (run + 1) // 2


def item_errors():
    """Item names (dictionary 0x300-0x34F, and every icon-prefixed equipment name) must fit ITEM_CELLS."""
    import json
    import font
    tiny = font.load_tiny()
    out = []
    for e in json.loads((text.ROOT / "script" / "dict.json").read_text(encoding="utf-8")):
        c = int(e["id"], 16)
        if e["en"] and (0x300 <= c < 0x350 or (c < 0x400 and e["en"].startswith("[01F"))):
            if tiny_cells(e["en"], tiny) > ITEM_CELLS:
                out.append(f"dict {e['id']}: item name {e['en']!r} over {ITEM_CELLS} tiny cells")
    return out


def main():
    entries = text.load()
    done = [e for e in entries if e["en"]]
    n = 0
    for e in done:
        for err in check(e):
            n += 1
            print(f"{e['id']}: {err}")
    for err in item_errors():
        n += 1
        print(err)
    print(f"lint: {len(done)}/{len(entries)} runs translated, {n} errors")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
