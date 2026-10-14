"""Kabuki Rocks event-script VM (bank $03, dispatch 03:805B, handler table 03:810F).

Script op = 1 byte >= 0x80 (handler index op & 0x7F; 0x7F/0xFF = end), then its args.
OPS[op] = (name, n, ptr, kind):
  n     fixed arg bytes read first
  ptr   True: a 24-bit LE CPU pointer (lo hi bank) follows the n bytes
  kind  'op'   falls through
        'cond' if the condition holds -> jump to ptr, else skip it (all via 03:82B2 / 03:95E8)
        'jmp'  unconditional jump (ends the path)
        'end'  ends the path (0x7F/0xFF end, 0x99 soft reset)
        'text' inline text run follows (printer 03:9201/03:920B), then the next op
        'bad'  handler is `BRA *` (hangs): never valid in a script
Names are guesses from the handlers; 'x' = unknown purpose.

Text run (03:9201), read until a byte it does not handle (that byte is the next script op):
  hh ll (hh < 0x80)  character, big-endian (>= 0x300: dictionary word)
  86 lo hi bk        jump, text continues (in text mode) at bk:hilo
  9D lo hi bk        yes/no: answer 1 continues after it, answer 2 jumps (text mode) to the pointer
  92 nn              delay
  B8 aa bb           portrait/sound (03:89CE)
  8F 90 91 93 94 9A BA  one byte (newline, clear, wait-key, name, name, reset column, sfx)
  anything else >= 0x80 ends the run

    python -X utf8 tools/script_ops.py [ROM]    # parse every entry of the pointer table 03:978E
"""
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

T = True
OPS = {
    0x80: ("flag_set", 1, 0, "op"),        # 7E:6175 bit n
    0x81: ("flag_clr", 1, 0, "op"),
    0x82: ("if_flag_jmp", 1, T, "cond"),   # jump if 7E:6175 bit n set
    0x83: ("flag2_set", 1, 0, "op"),       # 7E:622B bit n
    0x84: ("flag2_clr", 1, 0, "op"),
    0x85: ("if_flag2_jmp", 1, T, "cond"),
    0x86: ("jmp", 0, T, "jmp"),
    0x87: ("text_w1", 0, 0, "text"),       # window 1 ($34-$39)
    0x88: ("text_w1", 0, 0, "text"),
    0x89: ("text_w1", 0, 0, "text"),
    0x8A: ("close_w1", 0, 0, "op"),
    0x8B: ("text_w1_clear", 0, 0, "text"),
    0x8C: ("text_w2", 0, 0, "text"),       # window 2 ($3C-$41), the usual dialogue op
    0x8D: ("close_w2", 0, 0, "op"),
    0x8E: ("text_w2_clear", 0, 0, "text"),
    0x8F: ("wait", 1, 0, "op"),            # 8F-92 share 03:83E0: wait n frames
    0x90: ("wait", 1, 0, "op"),
    0x91: ("wait", 1, 0, "op"),
    0x92: ("wait", 1, 0, "op"),
    0x93: ("x_bacd", 1, 0, "op"),          # JSL 03:BACD
    0x94: ("x_bacd", 1, 0, "op"),
    0x95: ("x_bacd", 1, 0, "op"),
    0x96: ("x_bc76", 1, 0, "op"),
    0x97: ("x_bc76", 1, 0, "op"),
    0x98: ("set_5e73", 1, 0, "op"),
    0x99: ("reset", 0, 0, "end"),          # resets stack, JML 00:9A35
    0x9A: ("wait_actors", 0, 0, "op"),
    0x9B: ("wait_actors", 0, 0, "op"),
    0x9C: ("hang", 0, 0, "bad"),
    0x9D: ("sound", 1, 0, "op"),           # JSL 10:8087
    0x9E: ("sound", 1, 0, "op"),
    0x9F: ("sound_restore", 0, 0, "op"),
    0xA0: ("if_item_jmp", 1, T, "cond"),   # 04:EEB3, jump if carry clear
    0xA1: ("if_x_e880_jmp", 1, T, "cond"),
    0xA2: ("item_x", 1, 0, "op"),
    0xA3: ("if_money_lt_jmp", 2, T, "cond"),
    0xA4: ("money_add", 2, 0, "op"),
    0xA5: ("pay_or_jmp", 2, T, "cond"),    # jump if money < n, else subtract
    0xA6: ("if_x_b35c_jmp", 1, T, "cond"),
    0xA7: ("if_stat_eq_jmp", 1, T, "cond"),
    0xA8: ("if_stat_eq_jmp", 1, T, "cond"),
    0xA9: ("if_stat_lt_jmp", 3, T, "cond"),
    0xAA: ("x_b30a", 2, 0, "op"),
    0xAB: ("x_b28d", 3, 0, "op"),
    0xAC: ("x_b28d", 3, 0, "op"),
    0xAD: ("x_b384", 1, 0, "op"),
    0xAE: ("x_b384", 1, 0, "op"),
    0xAF: ("x_b2d1", 3, 0, "op"),
    0xB0: ("x_b2d1", 3, 0, "op"),
    0xB1: ("if_x_c5e1_jmp", 2, T, "cond"),
    0xB2: ("x_c610", 2, 0, "op"),
    0xB3: ("if_not_member_jmp", 1, T, "cond"),
    0xB4: ("if_party_full_jmp", 0, T, "cond"),
    0xB5: ("party_join", 1, 0, "op"),
    0xB6: ("party_leave", 1, 0, "op"),
    0xB7: ("if_rand_gt_jmp", 1, T, "cond"),
    0xB8: ("portrait", 2, 0, "op"),        # 03:89CE
    0xB9: ("hang", 0, 0, "bad"),
    0xBA: ("sfx_1d", 0, 0, "op"),
    0xBB: ("hang", 0, 0, "bad"),
    0xBC: ("sys", 1, 0, "op"),             # sub-op: 0-9 via table 03:8B6D, 80-FE sfx off, FF
    0xBD: ("x_8aad", 2, 0, "op"),
    0xBE: ("x_b752", 1, 0, "op"),
    0xBF: ("actor_spawn", 3, 0, "op"),
    0xC0: ("actor_move", 3, 0, "op"),
    0xC1: ("camera", 1, 0, "op"),
    0xC2: ("camera", 1, 0, "op"),
    0xC3: ("actor_pos", 3, 0, "op"),
    0xC4: ("x_b154", 3, 0, "op"),
    0xC5: ("actor_remove", 1, 0, "op"),
    0xC6: ("obj_remove", 1, 0, "op"),
    0xC7: ("actor_prio", 1, 0, "op"),
    0xC8: ("warp", 4, 0, "op"),            # map, ?, x, y -> JSL 01:8000
    0xC9: ("x_bacd_wait", 1, 0, "op"),
    0xCA: ("actor_anim", 1, 0, "op"),      # CA-CE: anim (op - CA)
    0xCB: ("actor_anim", 1, 0, "op"),
    0xCC: ("actor_anim", 1, 0, "op"),
    0xCD: ("actor_anim", 1, 0, "op"),
    0xCE: ("actor_anim", 1, 0, "op"),
    0xCF: ("x_bdf6", 1, 0, "op"),
    0xD0: ("x_be99", 1, 0, "op"),
    0xD1: ("x_ccc1", 1, 0, "op"),
    0xD2: ("battle", 2, T, "cond"),        # jump if $1635 bit 15 clear after the fight
    0xD3: ("mode", 1, 0, "op"),
    0xD4: ("hang", 0, 0, "bad"),
    0xD5: ("x_eed3_jmp", 1, T, "cond"),
    0xD6: ("hang", 0, 0, "bad"),
    0xD7: ("x_b623", 4, 0, "op"),
    0xD8: ("x_b623", 4, 0, "op"),
    0xD9: ("x_b733", 4, 0, "op"),
    0xDA: ("set_5a", 1, 0, "op"),
    0xDB: ("x_dec5", 1, 0, "op"),
    0xDC: ("x_dec5", 1, 0, "op"),
    0xDD: ("scroll", 3, 0, "op"),
    0xDE: ("scroll", 3, 0, "op"),
    0xDF: ("if_5e74_jmp", 2, T, "cond"),
    0xE0: ("x_c96e", 0, 0, "op"),
    0xE1: ("x_e1", 1, 0, "op"),
    0xE2: ("x_d747", 0, 0, "op"),
    0xE3: ("x_078000", 0, 0, "op"),
    0xFF: ("end", 0, 0, "end"),
}
OPS[0x7F] = OPS[0xFF]
TEXT_LEN = {0x8F: 1, 0x90: 1, 0x91: 1, 0x92: 2, 0x93: 1, 0x94: 1, 0x9A: 1, 0xB8: 3, 0xBA: 1}
TABLE, TABLE_END = 0x03978E, 0x039F7A  # 676 entries; code (03:9F7A PHP) follows


class Item(NamedTuple):
    addr: int       # CPU address
    op: int | None  # None = text run
    size: int
    args: bytes     # fixed args (op) or raw bytes (text run)
    targets: tuple  # pointer targets


def off(a):
    return ((a & 0x7F0000) >> 1) | (a & 0x7FFF)


def ptr(rom, a):
    o = off(a)
    return rom[o] | rom[o + 1] << 8 | rom[o + 2] << 16


def rd(rom, a):
    if not a & 0x8000 or off(a) >= len(rom):
        raise ValueError(f"{a:06X}: outside ROM")
    return rom[off(a)]


def text_run(rom, a):
    """Text run at a -> (Item, next op addr or None if it ended with a jump)."""
    start, tg, end = a, [], None
    while end is None:
        b = rd(rom, a)
        if b < 0x80:
            rd(rom, a + 1)
            a += 2
        elif b in (0x86, 0x9D):
            tg.append(ptr(rom, a + 1))
            rd(rom, a + 3)
            a += 4
            if b == 0x86:
                break
        elif b in TEXT_LEN:
            a += TEXT_LEN[b]
        else:
            end = a
    o = off(start)
    return Item(start, None, a - start, rom[o:o + a - start], tuple(tg)), end


def decode(rom, a):
    """Op at a -> (Item, fall-through addr or None)."""
    op = rd(rom, a)
    if op not in OPS or OPS[op][3] == "bad":
        raise ValueError(f"{a:06X}: invalid op {op:02X}")
    name, n, has_ptr, kind = OPS[op]
    o = off(a) + 1
    tg = (ptr(rom, a + 1 + n),) if has_ptr else ()
    size = 1 + n + 3 * bool(has_ptr)
    rd(rom, a + size - 1)
    nxt = None if kind in ("jmp", "end") else a + size
    return Item(a, op, size, rom[o:o + n], tg), nxt


def successors(rom, a):
    """Op addresses the VM can dispatch right after the op at a (follows text jumps)."""
    it, nxt = decode(rom, a)
    out = list(it.targets)
    if OPS[it.op][3] == "text":
        todo, seen, out = [nxt], set(), []
        while todo:
            t = todo.pop()
            if t in seen:
                continue
            seen.add(t)
            run, end = text_run(rom, t)
            todo += run.targets
            if end is not None:
                out.append(end)
    elif nxt is not None:
        out.append(nxt)
    return out


def parse(rom, cpu_addr):
    """Recursive descent from a script entry. Returns Items sorted by address; raises ValueError."""
    items, todo = {}, [(cpu_addr, False)]
    while todo:
        a, text = todo.pop()
        if (a, text) in items:
            continue
        if text:
            it, nxt = text_run(rom, a)
            todo += [(t, True) for t in it.targets]
            if nxt is not None:
                todo.append((nxt, False))
        else:
            it, nxt = decode(rom, a)
            todo += [(t, False) for t in it.targets]
            if nxt is not None:
                todo.append((nxt, OPS[it.op][3] == "text"))
        items[(a, text)] = it
    return sorted(items.values(), key=lambda i: (i.addr, i.op is not None))


def table(rom):
    return [ptr(rom, a) for a in range(TABLE, TABLE_END, 3)]


def main(path):
    rom = Path(path).read_bytes()
    entries = table(rom)
    ok, fails, runs, cover, ops = 0, [], {}, defaultdict(set), defaultdict(int)
    for i, e in enumerate(entries):
        try:
            items = parse(rom, e)
        except ValueError as x:
            fails.append((i, e, str(x)))
            continue
        ok += 1
        for it in items:
            if it.op is None:
                runs[it.addr] = it
                cover[it.addr >> 16].update(range(it.addr, it.addr + it.size))
            else:
                ops[it.op] += 1
    print(f"entries: {len(entries)}  parsed: {ok}  failed: {len(fails)}")
    for i, e, x in fails:
        print(f"  id {i:3d} @ {e:06X}: {x}")
    print(f"text runs: {len(runs)}  bytes: {sum(len(c) for c in cover.values())}")
    for bank in sorted(cover):
        print(f"  bank {bank:02X}: {sum(1 for r in runs if r >> 16 == bank)} runs, {len(cover[bank])} bytes")
    print("unused ops:", " ".join(f"{o:02X}" for o in sorted(OPS) if o not in ops and OPS[o][3] != "bad"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "rom" / "Kabuki Rocks (Japan).sfc")
