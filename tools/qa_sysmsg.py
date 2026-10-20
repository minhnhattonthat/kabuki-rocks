"""Shoot every system message of script/sysmsg.json in the emulator, the way the game shows them.

A QA debug build warps to a room; tools/lua/callstub.lua then diverts the main thread once through a stub that does
what the callers do: copy the template with 00:90C7 (from the message's bank), store the {slot} words (an item, a
digit) like the callers' `STA $7F40xx`, run the copy with `LDA #$FFFF ; JSL $038000`.

    python -X utf8 tools/qa_sysmsg.py            # -> work/qa/sysmsg/<site>.png + sheet.png
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import sysmsg  # noqa: E402

SKILL = Path(os.environ.get("SKILL", "C:/Users/Nathan/.claude/plugins/cache/retro-translation/translate-retro-game/"
                                     "29344d005fa4/skills/translate-retro-game")) / "scripts"  # as tools/qa_screens.sh
OUT = ROOT / "work" / "qa" / "sysmsg"
ROM = ROOT / "build" / "qa_sysmsg.sfc"
BOOT = "1100 -;6 start;200 -;6 start;200 -;300 -"
SLOT_FILL = {21: b"\x03\x80", 1: b"\x00\xb1"}  # by slot width: an item word, a digit (big-endian glyph words)
HOOK = 0x008608  # frame wait, called with JSL from the main loop


def stub(e, rom):
    bank, y = int(e["site"], 16) >> 16, int(e["y"], 16)
    _, data = sysmsg.stream(rom, bank, y)
    code = bytearray.fromhex("08c23048da5a8b")  # PHP ; REP #$30 ; PHA ; PHX ; PHY ; PHB
    code += bytes([0xF4, bank, bank, 0xAB, 0xAB, 0xA0, y & 0xFF, y >> 8])  # PEA ; PLB ; PLB (DB = bank) ; LDY #y
    code += bytes.fromhex("22c79000")  # JSL $0090C7 (copy to 7F:4000)
    k = 0
    for _, width in e.get("slots", []):  # the 00 00 words after each segment jump
        k = data.index(b"\x00\x00", k)
        code += bytes([0xA9]) + SLOT_FILL[width] + bytes([0x8F, k, 0x40, 0x7F])  # LDA #word ; STA $7F40kk
        k += 2
    code += bytes.fromhex("a9ffff22008003")  # LDA #$FFFF ; JSL $038000 (run it)
    code += bytes.fromhex("ab7afa6828") + bytes([0x5C, HOOK & 0xFF, HOOK >> 8 & 0xFF, HOOK >> 16])
    return code.hex()


def shoot(e, rom):
    out = OUT / e["site"]
    subprocess.run([sys.executable, "-X", "utf8", str(SKILL / "emu.py"), str(ROM), "--out", str(out), "--route-str",
                    BOOT, "--frames", "2350", "--script", str(ROOT / "tools" / "lua" / "callstub.lua"),
                    "--var", "AT=2150", "--var", f"HOOK={HOOK:#x}", "--var", f'STUB="{stub(e, rom)}"'],
                   check=True, capture_output=True)
    (out / "final.png").replace(OUT / f"{e['site']}.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*.png"):
        p.unlink()
    subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "build.py"), "--out", str(ROM), "--debug",
                    "C8 00 0A 0A 0B BC 09 FF"] + sys.argv[1:], check=True, capture_output=True)
    rom = ROM.read_bytes()
    entries = [e for e in json.loads((ROOT / "script" / "sysmsg.json").read_text(encoding="utf-8")) if e["en"]]
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda e: shoot(e, rom), entries))
    subprocess.run([sys.executable, "-X", "utf8", str(SKILL / "sheet.py"), str(OUT / "*.png"), "--cols", "4",
                    "--out", str(OUT / "sheet.png")], check=True)


if __name__ == "__main__":
    main()
