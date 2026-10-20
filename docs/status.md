# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 8 (QA in the emulator), release prep started. Last local patch: release/KabukiRocks_EN_v0.3.zip (bps + README.txt, patched CRC32 46df1a3b, smoke ok; not published).
- **Done:**
  - Dialogue: all 1194 non-empty event-script runs translated (`script/bank_XX.json`); credits/profile cards hand-laid (bank 2D). 16 runs are empty.
  - Dictionary: 1283/1331 words (`script/dict.json`, banks $30/$31).
  - Menus: every surveyed menu screen in English (field, item, status, config, song lists, shop, battle) via `labels.json` (baked tiny-font cells) and runtime tiny text (`asm/tiny.asm`); code strings (`code.json`, bank $3B), incl. the bank $05 boot/attract prologue and the Continue screen.
  - System messages: all 34 RAM-script copier call sites (`sysmsg.json` whole templates incl. the table-driven walking-style popup 00:9C64; `sysfrag.json` fragments after a name/item/amount).
  - Graphics: title menu, curtains, battle placard, 18 chapter cards (`cards.json`), 7 town shop signs (`assets/signs.txt`).
  - Playtests 2026-10-19/20 logged and fixed in `docs/bugs.md`.
- **Next (release gate, skill phase 9):**
  - Debug tool (`tools/debug/`, phase 2) does not exist yet: scenes are reached from user savestates and `build.py --debug`.
  - Visual-QA gate (`qa_gate.py`) has no manifest yet.
  - `jp_left.py build/kabuki_en_cs.sfc --orig rom/... --tbl tbl/jp.tbl` reports 6311 unchanged runs: mostly the original copies of relocated text (e.g. the sysfrag fragments at 00:96F9-) and false hits in code; needs `--range`/`--known` before it means anything.
  - Not surveyed: ending, game over, save screens; graphics text beyond the intro and towns.
  - Still open from earlier notes: party name table 1E:B3CA, `{name93}` rename prompt (0888FA), battle-message fragment spacing, menu cursor sites 0x12E/0x12F.
- **Open bugs** (`docs/bugs.md`):
  - Shop Sell help line garbage / wrong descriptions (steps 0013-0021): likely a QA inventory poke; re-check on a real save.
  - Button Settings "Abutton" / "Bbutton": imm label 04AEE2 has 3 cells, no room for a space.
  - Song Weapon greyed songs with no hint; Forte "Compose a song weapon" does nothing (step 0039; battle savestate starts on Jiraiya's turn): both probably original behaviour, unchecked against JP.
  - Battle item list: weapon icon overlaps the count ("100-Kan Hammer").
- **Waiting on the user:** romanization with macrons dropped (glossary, pending OK); readings of コウセン / セイガ (boss titles); whether to publish (see docs/decisions.md).
