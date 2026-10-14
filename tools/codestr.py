"""Catalog Japanese strings stored as 16-bit LE glyph words in code/data banks (battle, menus, shops, system).

Two shapes seen: fixed-length arrays padded with 0x02FF (battle messages, e.g. 02:E12C, printed with a count in X)
and lists ending in a word with bit 15 set (dictionary style). Words < 0x300 are glyphs (tbl/jp.tbl).

    python -X utf8 tools/codestr.py [--min 3] [--banks 00-07,0C-0F,...]   # print candidates
    python -X utf8 tools/codestr.py --refs 02E12C                          # 16-bit references in the same bank
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import text  # noqa: E402
from script_ops import off  # noqa: E402

SKIP_BANKS = {0x08, 0x09, 0x0A, 0x0B, 0x10, 0x1F, 0x2D, 0x2F}  # event scripts, font, dictionary
KANA = re.compile(r"[぀-ヿ一-鿿]")


def cpu(o):
    return ((o // 0x8000) << 16) | 0x8000 | (o % 0x8000)


def glyph_ok(w):
    return w == 0x02FF or (w < 0x300 and w.to_bytes(2, "big") in text.JP.dec)


def plausible(s):
    """Graphics/tables decode as text too: keep strings that look like Japanese prose or names."""
    t = s.replace(" ", "")
    if len(t) < 3 or t.count("あ") > len(t) * 0.25 or len(set(t)) < max(2, len(t) // 3):
        return False
    kana = sum(1 for c in t if "ぁ" <= c <= "ー")
    kanji = sum(1 for c in t if "一" <= c <= "鿿")
    return kanji <= len(t) * 0.5 and kana >= len(t) * 0.6


def scan(rom, minjp=3, banks=None):
    out = []
    for bank in range(len(rom) // 0x8000):
        if bank in SKIP_BANKS or (banks and bank not in banks):
            continue
        base = bank * 0x8000
        for par in (0, 1):
            i = base + par
            while i < base + 0x8000 - 1:
                j, chars, term = i, [], None
                while j < base + 0x8000 - 1:
                    w = rom[j] | rom[j + 1] << 8
                    if glyph_ok(w & 0x7FFF):
                        chars.append(w & 0x7FFF)
                        j += 2
                        if w & 0x8000:
                            term = "bit15"
                            break
                    else:
                        break
                s = "".join(" " if c == 0x02FF else text.JP.dec[c.to_bytes(2, "big")] for c in chars)
                if len(KANA.findall(s)) >= minjp and plausible(s):
                    out.append((i, j - i, term or ("pad" if s.endswith(" ") else "?"), s))
                    i = j
                else:
                    i += 2
    out.sort()
    return out


def decode_at(rom, bank, addr, maxw=48):
    """Bit-15-terminated glyph string at bank:addr -> (list of codes, text) or None."""
    o = off(bank << 16 | addr)
    ws = []
    for k in range(maxw):
        if (addr + 2 * k) > 0xFFFE:
            return None
        w = rom[o + 2 * k] | rom[o + 2 * k + 1] << 8
        if not glyph_ok(w & 0x7FFF):
            return None
        ws.append(w & 0x7FFF)
        if w & 0x8000:
            s = "".join(" " if c == 0x02FF else text.JP.dec[c.to_bytes(2, "big")] for c in ws)
            return ws, s
    return None


def referenced(rom, banks):
    """{(bank, addr): [(site, kind)]} for bit-15 strings reached by LDX/LDY/LDA #imm or by pointer tables."""
    found = {}
    for bank in banks:
        b = rom[bank * 0x8000:(bank + 1) * 0x8000]
        for i in range(len(b) - 2):
            v = b[i + 1] | b[i + 2] << 8
            if v < 0x8000:
                continue
            kind = {0xA2: "ldx", 0xA0: "ldy", 0xA9: "lda"}.get(b[i])
            r = decode_at(rom, bank, v)
            if not r or not plausible(r[1]) or len(KANA.findall(r[1])) < 2:
                continue
            if kind:
                found.setdefault((bank, v), []).append((cpu(bank * 0x8000 + i), kind))
        # pointer tables: >= 2 consecutive words that each point at a plausible string
        def ptr_ok(j):
            v = b[j] | b[j + 1] << 8
            r = decode_at(rom, bank, v) if v >= 0x8000 else None
            return v if r and plausible(r[1]) else None
        ok = [ptr_ok(j) for j in range(len(b) - 1)]
        for i in range(len(b) - 3):
            if ok[i] is None or ok[i + 2] is None or (i >= 2 and ok[i - 2] is not None):
                continue
            j = i
            while j < len(b) - 1 and ok[j] is not None:
                found.setdefault((bank, ok[j]), []).append((cpu(bank * 0x8000 + j), "table"))
                j += 2
    return found


CODE_JSON = Path(__file__).resolve().parent.parent / "script" / "code.json"
EXCLUDE = {"1EFCF8", "2AFDFF"}  # data that happens to decode (checked by eye)


def catalog(rom):
    """Referenced bit-15 strings, minus false hits that start inside another string."""
    banks = [b for b in range(len(rom) // 0x8000) if b not in SKIP_BANKS]
    found = referenced(rom, banks)
    for k in EXCLUDE:
        found.pop((int(k[:2], 16), int(k[2:], 16)), None)
    for i in range(11):  # party name table 1E:B3CA (kanji names fail the kana heuristic)
        site = 0x1EB3CA + 2 * i
        v = int.from_bytes(rom[off(site):off(site) + 2], "little")
        found.setdefault((0x1E, v), [(site, "table")])
    spans = {k: decode_at(rom, *k) for k in found}
    out = []
    for (bank, addr), rs in sorted(found.items()):
        inside = any(b == bank and a < addr < a + 2 * len(spans[(b, a)][0]) for (b, a) in spans)
        if inside:
            continue
        ws, s = spans[(bank, addr)]
        out.append({"id": f"{bank:02X}{addr:04X}", "len": len(ws), "jp": s, "en": "",
                    "refs": [[f"{site:06X}", k] for site, k in rs], "notes": ""})
    return out


def dump(rom, force=False):
    import json
    if CODE_JSON.exists() and not force:
        sys.exit(f"{CODE_JSON} exists; --force overwrites English")
    entries = catalog(rom)
    with open(CODE_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{CODE_JSON.name}: {len(entries)} strings")


def refs(rom, o):
    """16-bit LE references to file offset o inside its own bank (immediates and data words)."""
    a = cpu(o) & 0xFFFF
    bank = o // 0x8000
    b = rom[bank * 0x8000:(bank + 1) * 0x8000]
    return [(cpu(bank * 0x8000 + m.start()), b[m.start() - 1] if m.start() else None)
            for m in re.finditer(re.escape(a.to_bytes(2, "little")), b)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=3)
    ap.add_argument("--banks")
    ap.add_argument("--refs")
    ap.add_argument("--byref", action="store_true", help="reference-driven catalog (exact string starts)")
    ap.add_argument("--dump", action="store_true", help="write script/code.json (refuses to overwrite without --force)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    rom = text.ROM.read_bytes()
    if a.dump:
        dump(rom, a.force)
        sys.exit()
    if a.byref:
        banks = [b for b in range(len(rom) // 0x8000) if b not in SKIP_BANKS]
        for (bank, addr), rs in sorted(referenced(rom, banks).items()):
            ws, s = decode_at(rom, bank, addr)
            kinds = " ".join(f"{site:06X}:{k}" for site, k in rs[:4])
            print(f"{bank:02X}{addr:04X} {len(ws):3d} [{kinds}] {s}")
        sys.exit()
    if a.refs:
        o = off(int(a.refs, 16))
        for r, prev in refs(rom, o):
            print(f"{r:06X} prev={prev:02X}" if prev is not None else f"{r:06X}")
        sys.exit()
    banks = None
    if a.banks:
        banks = set()
        for part in a.banks.split(","):
            lo, _, hi = part.partition("-")
            banks.update(range(int(lo, 16), int(hi or lo, 16) + 1))
    for o, n, term, s in scan(rom, a.min, banks):
        if term == "?":
            continue  # unterminated runs are mostly graphics/data
        rs = refs(rom, o)
        tag = " ".join(f"{r:06X}:{p:02X}" for r, p in rs[:4] if p is not None)
        print(f"{cpu(o):06X} {n // 2:3d} {term:5s} [{tag}] {s}")
