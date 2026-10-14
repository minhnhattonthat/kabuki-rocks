"""Fixed-size menu/battle label arrays (glyph words read N at a time by code; translated in place).

script/labels.json entries: {"id": "04825A", "cells": 3, "count": 6, "jp": [...], "en": [...], "lines": [1|2...]}
The array at id holds `count` labels of `cells` glyph words each (contiguous). English for a label that fits in
`cells` characters is written with the normal font; longer labels are baked with the tiny font (tools/font.py
render_label: two letters per cell, '/' splits two lines) into new glyph codes at build time.

    python -X utf8 tools/labels.py show       # Japanese of every array in script/labels.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import text  # noqa: E402
from script_ops import off  # noqa: E402

LABELS = ROOT / "script" / "labels.json"


def words(rom, cpu_addr, n):
    o = off(cpu_addr)
    return [rom[o + 2 * i] | rom[o + 2 * i + 1] << 8 for i in range(n)]


def jp_of(rom, ws):
    return "".join(" " if w == 0x02FF else text.glyph(rom, w) if w < 0x300 else f"[{w:04X}]" for w in ws)


def load():
    return json.loads(LABELS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    rom = text.ROM.read_bytes()
    for e in load():
        ws = words(rom, int(e["id"], 16), e["cells"] * e["count"])
        parts = [jp_of(rom, ws[i * e["cells"]:(i + 1) * e["cells"]]) for i in range(e["count"])]
        print(e["id"], e["cells"], " | ".join(parts), "->", e.get("en"))
