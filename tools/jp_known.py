"""Known-run list for the leftover-Japanese scan: every original the build relocates (event-script runs, code
strings, dictionary words) and the labels kept in Japanese on purpose. One even file offset per line.

    python -X utf8 tools/jp_known.py > work/jp_known.txt
    python -X utf8 $SKILL/scripts/jp_left.py build/kabuki_en.sfc --orig "rom/Kabuki Rocks (Japan).sfc" \
        --tbl tbl/jp.tbl --le16 --known work/jp_known.txt
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "script"


def off(cpu):
    return (cpu >> 16) * 0x8000 + (cpu & 0x7FFF)


def spans():
    """(file offset, bytes, note) of each known run."""
    for p in sorted(S.glob("bank_*.json")):
        for e in json.loads(p.read_text(encoding="utf-8")):
            if e["en"]:
                yield off(int(e["id"], 16)), e["size"], f"relocated {p.stem} {e['id']}"
    for e in json.loads((S / "code.json").read_text(encoding="utf-8")):
        if e["en"]:
            yield off(int(e["id"], 16)), 2 * e["len"], f"relocated code string {e['id']}"
    for e in json.loads((S / "dict.json").read_text(encoding="utf-8")):
        if e["en"]:
            yield off(0x2F0000 | int(e["ptr"], 16)), 2 * e["len"], f"relocated dictionary word {e['id']}"
    for e in json.loads((S / "labels.json").read_text(encoding="utf-8")):
        if not e["en"] and "cells" in e:
            yield off(int(e["id"], 16)), 2 * e["cells"] * e["count"], f"kept Japanese label {e['id']}"


if __name__ == "__main__":
    for o, n, note in spans():
        for k in range(o - o % 2, o + n, 2):
            print(f"{k:06X} {note}")
