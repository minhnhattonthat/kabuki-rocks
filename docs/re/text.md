# Text and event script

LoROM. CPU addr -> file: `((a & 0x7F0000) >> 1) | (a & 0x7FFF)`.

## Event script VM (bank $03)
- Entry 03:8000, A = script id -> `$0825`. Direct page = $0800 inside the VM, so `$27-$29` = `$0827-$0829` (24-bit base), `$2A` = `$082A` (16-bit offset).
- Script pointer table: 03:978E, 3 bytes per id (24-bit LE CPU address). ids 0..~400+. Targets in banks $08-$0B (file 0x40000-0x5FFFF), $10, $2D. id < 0 ($25 bit15): RAM script at 7F:4000.
- Dispatch loop 03:805B: `op = byte & 0x7F`; 0x7F = end; else `JMP (03:810F + op*2)`. Handler table covers ops 0x80-0xE3 (0x00-0x63 after mask); bytes < 0x80 alias the same handlers.
- Script-level ops 0x86 (jump) and 0x9D (branch) carry 24-bit absolute pointers (lo hi bank), so script data cannot be moved without fixing them.

## Text printer (03:9201)
Called by script op 0x8C (handler 03:834B, call at 03:8392) and from 03:82FD. Reads from the script stream at `[$27],$2A` until a byte it does not handle, then returns to the VM (that byte is the next script op).

| bytes | meaning |
|---|---|
| `hh ll` with hh < 0x80 | character, 16-bit **big-endian**. < 0x300: one glyph (00:BA9D -> 2 tilemap words). >= 0x300: dictionary word (00:BBEE -> list in bank $2F, last word has bit 15 set) |
| `86 lo hi bk` | jump: continue text at bk:hihi (sets $27-$29, $2A=0) |
| `9D lo hi bk` | yes/no choice: first answer continues after the 4 bytes, second jumps to the pointer |
| `8F` | newline |
| `90` | (03:958B) page/clear? |
| `91` | wait for button, blinking arrow (glyph 0x0201) |
| `92 nn` | delay nn |
| `93` | insert name from 7E:614D (string of words, last has bit 15) |
| `94` | insert name from 7E:6159 (speaker "マッキー" in the intro) |
| `9A` | (03:958B, resets column) |
| `B8 nn nn` | portrait/face? (03:89CE) |
| `BA` | sound? (JSL 00:B6F2 Y=1D) |
| other >= 0x80 | end of text |

## Encoding (glyph codes)
- Gojuon hiragana from 0x0000: あ00 い01 う02 え03 お04 か05.. さ0A し0B.. た0F ち10 つ11 て12 と13 な14 に15 ぬ16 ね17 の18 は19..ま1E..も22 や23 ゆ24 よ25 ら26..ろ2A わ2B を2C ん2D. で=0x3B (dakuten block). っ=0x47?. 「=0xDF. 。=0xA1. Kanji around 0x100-0x2FF (前=0x1AF). Space = 0x02FF.
- Table to be completed from the font (tbl/jp.tbl).

## Samples
- 08:8944 (file 0x40944): `8C 94 00DF 0000 0047 02FF 003B 0022 02FF 000E 0018 01AF 0015 02FF 0A9D 0015 8F 0004 ...` = マッキー「あっ でも その前に ウメばあちゃんに / おゆるしを もらわないとね。 (0x0A9D = dictionary "ウメばあちゃん"?)

## Runtime trace
`tools/lua/scriptlog.lua` logs each opcode dispatch (S frame addr op) and text-printer entry (T frame addr).

## Script opcodes
Full table, arg layouts and parser: `tools/script_ops.py` (`python -X utf8 tools/script_ops.py` walks the whole pointer table). Checked against runtime traces in `tests/test_script_ops.py`.
- Pointer table 03:978E ends at 03:9F7A (code follows): **676 ids**, 641 distinct targets. ids 263-270 all point at 0A:FF45, garbage just past the end of the last script in bank $0A (never valid).
- Args are read with `LDA [$27],y`; no handler reads args through another routine except 03:89CE (B8, 2 bytes) and 03:95E8 (24-bit pointer). No call/return ops, no computed script jumps.
- Correction to the note above: at script level **0x9D is a 1-byte sound op**; the 0x9D yes/no pointer exists only inside text runs.
- Conditional jumps all go through 03:82B2 (`JSR 95E8`: `$27-$29` = 24-bit arg, `$2A` = 0); when false they skip the 3 pointer bytes:
  82/85 (flag bit, 1 byte), A0 A1 A6 A7 A8 B3 B7 D5 (1 byte), A3 A5 B1 D2 DF (2 bytes), A9 (3 bytes), B4 (none), then the pointer.
- Unconditional/ends: 86 ptr (jump), FF/7F (end), 99 (soft reset: resets the stack, JML 00:9A35).
- Text ops (inline text run at the next byte): 87 88 89 (window 1), 8B (window 1, clear first), 8C (window 2, the dialogue op), 8E (window 2, clear first). 8A / 8D close window 1 / 2.
- Text run: 9D and 86 targets continue **in text mode**, so they point at text, not at ops. 9D: answer 1 continues after the 4 bytes, answer 2 jumps (for RAM scripts, id >= 0xFFFE, 9D is 1 byte with no pointer).
- Fixed lengths (args after the op byte): 0: 8A 8D 9A 9B 9F BA E0 E2 E3 · 1: 80 81 83 84 8F-92 93-95 96 97 98 9D 9E A2 AD AE B5 B6 BC BE C1 C2 C5 C6 C7 C9 CA-CE CF D0 D1 D3 DA DB DC E1 · 2: A4 AA B2 B8 BD · 3: AB AC AF B0 BF C0 C3 C4 DD DE · 4: C8 D7 D8 D9.
- 9C B9 BB D4 D6: handler is `BRA *` (hang), never used. Bytes < 0x80 at op level alias `op|0x80` in the VM but never occur in reachable script.
- BC nn: sub-op; 00-09 via table 03:8B6D, 80-FE stop sound, FF special. 8F-92 share one handler (wait nn frames); CA-CE pass `op-CA` as a parameter; AF/B0 pass `op-A4`; C9 = 93 plus extra waits.
- RAM scripts (id 0xFFFF, run from 7F:4000) carry system/NPC messages that are **not** in the pointer table: bank-00 code writes an op (e.g. `89` = window-1 text) at 7F:4000, appends the hero name (7E:614D) and a string copied by 00:90C2/00:90C7 (Y = source address, e.g. 00:99EA), then `LDA #$FFFF; JSL 03:8000`. ~29 call sites (`A9 FF FF 22 00 80 03`) in banks 00, 01, 1E, 2B. Seen in a trace: `89 <text> A1 91 8A FF`.
- Coverage: 668/676 ids parse; 1210 text runs, 124.6 KB (bank 08 28.7K, 09 28.6K, 0A 24.8K, 0B 28.5K, 10 4.3K, 2D 9.8K). About 1.3 KB of unreachable script sits between scripts (largest 0B:D024-0B:D369, 837 bytes; also 10:DF92, 0B:CB6C, 09:E875, 0A:F0BE, 09:F2FA, and 09:B386 = `D5 40` + a pointer to itself).

## Text inventory and insertion (2026-10-15)
- Script runs: `tools/text.py dump` -> `script/bank_XX.json` (1210 runs, 16 empty). Roundtrip + JSON-vs-ROM tests in tests/test_text.py.
- Dictionary: `tools/dictwords.py dump` -> `script/dict.json` (1331 words, bank $2F A74F-FDC0). Used inline by script text (codes >= 0x300) and by menus (00:E117/E133 -> 04:B764/B77B). 181 words hold 0x2xx glyphs that differ per screen (menu/battle VRAM): read them from that screen's dump.
- Still to extract: RAM-script strings (00:90C2 sources, above); other glyph users 04:B727/B766/BB9C, 05:BA7F-BAC1, 05:EF19, 0F:C76E, 02:F091, 07:8CC5 (menus/battle).
- No free space in the 1.5 MB ROM. Build expands to 2 MB; banks $30-$3F (file 0x180000+) are free.
- Insertion (build.py): English goes to the expansion area, the run start becomes `86 lo hi bk`, English ends with `86` back to the op after the run. Every non-empty run is >= 4 bytes and no runs overlap. `build.py --reloc-jp` (all Japanese relocated this way) plays the intro identically.

## Names
- {name93} = 7E:614D, {name94} = 7E:6159: 6-word slots (12 bytes). Written by immediate `LDX #/STX` pairs at 00:9FE8-00:A00F (ロック, マッキー); patch that code for English (needs a copy loop if the name is longer than the JP one).
- Party name table 1E:B3CA (11 pointers, LE words, last | 0x8000): ロック マッキー ベンケイ じらいや 法界坊 ジロキチ フジムスメ 夕風 辰五郎 お七 景清. Used by 1E code (menus?); slot sizes there not yet measured.

## Width gate (measured 2026-10-15, marker build, intro box 08:8079)
- Dialogue window 2 (op 8C): 3 lines x 28 cells (8 px), first cell at x=16. Cell 28 sits under the right border; the {wait} arrow takes the last cell of its line.
- Longer lines do not clip: the window buffer is column-major and wraps, so the overflow overwrites the first cells of other lines. tools/lint.py enforces 28/3/27-before-wait.
- Line starts are fine with plain text (no indentation needed). Extra pages ({wait}{clr}) are free since text is relocated.
- Not yet measured: window 1 (ops 87-89/8B), choices (9D), RAM-script system messages, menus.
