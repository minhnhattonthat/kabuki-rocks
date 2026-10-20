"""Shoot the fragment system messages of script/sysfrag.json the way the game assembles them.

Like tools/qa_sysmsg.py: a QA debug build warps to a room, tools/lua/callstub.lua runs a stub on the main thread
that writes the text op, the leader's name (00:90FA) or an amount, then each fragment through the call site's own
`LDY #frag ; JSL helper` (read back from the build), an item or song word between fragments, and runs the script.

    python -X utf8 tools/qa_sysfrag.py            # -> work/qa/sysfrag/<first site>.png
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from qa_sysmsg import SKILL, BOOT, HOOK  # noqa: E402

OUT = ROOT / "work" / "qa" / "sysfrag"
ROM = ROOT / "build" / "qa_sysfrag.sfc"
ITEM, SONG, DIGITS = 0x0380, 0x0410, (0x00B5, 0x00B0, 0x00B0)  # Bamboo-maru, a song word, "500"
# (prefix, [fragment sites], word stored after the first fragment); prefix "name" = leader name, "amount" = DIGITS
MESSAGES = [("name", ["0091D0"], None), ("name", ["009217"], None), ("amount", ["009328"], None),
            ("name", ["00955D", "009583"], ITEM), ("name", ["0095E8", "00960E"], ITEM),
            ("name", ["00963E"], None), ("name", ["00969B", "0096C1"], ITEM), ("name", ["00993B"], None),
            ("name", ["2BF357"], "slot")]
SLOT_SITE = 0x2BF382  # STA $7F40xx,x of the song word, X just past the copy


def off(a):
    return (a >> 16) * 0x8000 + (a & 0x7FFF)


def stub(rom, prefix, sites, word):
    code = bytearray.fromhex("08c23048da5a8b")  # PHP ; REP #$30 ; PHA ; PHX ; PHY ; PHB
    code += bytes.fromhex("a989008f00407f a20100".replace(" ", ""))  # LDA #$0089 ; STA $7F4000 ; LDX #1
    if prefix == "name":
        code += bytes.fromhex("22fa9000")  # JSL $0090FA (leader name at X)
    else:
        for d in DIGITS:
            code += bytes([0xA9]) + d.to_bytes(2, "big") + bytes.fromhex("9f00407fe8e8")  # LDA ; STA ,x ; INX x2
    for i, s in enumerate(sites):
        o = off(int(s, 16))
        code += rom[o - 3:o + 4]  # LDY #frag ; JSL helper
        if i == 0 and word == "slot":
            so = off(SLOT_SITE)
            code += bytes([0xA9]) + SONG.to_bytes(2, "big") + rom[so:so + 4]  # LDA #song ; STA $7F40xx,x
        elif i == 0 and word:
            code += bytes([0xA9]) + word.to_bytes(2, "big") + bytes.fromhex("9f00407fe8e8")
    code += bytes.fromhex("a9ffff22008003")  # LDA #$FFFF ; JSL $038000 (run it)
    code += bytes.fromhex("ab7afa6828") + bytes([0x5C, HOOK & 0xFF, HOOK >> 8 & 0xFF, HOOK >> 16])
    return code.hex()


def shoot(rom, m):
    out = OUT / m[1][0]
    subprocess.run([sys.executable, "-X", "utf8", str(SKILL / "emu.py"), str(ROM), "--out", str(out), "--route-str",
                    BOOT, "--frames", "2350", "--script", str(ROOT / "tools" / "lua" / "callstub.lua"),
                    "--var", "AT=2150", "--var", f"HOOK={HOOK:#x}", "--var", f'STUB="{stub(rom, *m)}"'],
                   check=True, capture_output=True)
    (out / "final.png").replace(OUT / f"{m[1][0]}.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "build.py"), "--out", str(ROM), "--debug",
                    "C8 00 0A 0A 0B BC 09 FF"] + sys.argv[1:], check=True, capture_output=True)
    rom = ROM.read_bytes()
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda m: shoot(rom, m), MESSAGES))
    subprocess.run([sys.executable, "-X", "utf8", str(SKILL / "sheet.py"), *sorted(map(str, OUT.glob("*.png"))),
                    "--cols", "3", "--div", "1", "--crop", "0,0,256,80", "--out", str(OUT.parent / "sysfrag_sheet.png")],
                   check=True)


if __name__ == "__main__":
    main()
