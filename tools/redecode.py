"""Re-decode every `jp` field in script/*.json from the ROM with the current tbl/jp.tbl, keeping the English.
Run after fixing a wrong glyph in tbl/jp.tbl.   python -X utf8 tools/redecode.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import text  # noqa: E402
from script_ops import off  # noqa: E402

rom = text.ROM.read_bytes()
changed = 0
for p in sorted(text.SCRIPT.glob("bank_*.json")):
    entries = json.loads(p.read_text(encoding="utf-8"))
    for e in entries:
        o = off(int(e["id"], 16))
        jp = text.decode(rom, rom[o:o + e["size"]])
        if jp != e["jp"]:
            e["jp"], changed = jp, changed + 1
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
        f.write("\n")
print(f"{changed} jp fields updated")
