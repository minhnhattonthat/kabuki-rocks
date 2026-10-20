# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 9 (release gate run 2026-10-20). Last local patch: release/KabukiRocks_EN_v0.4.zip (bps + README.txt, patched CRC32 021320eb, gate 75/75, smoke ok; not published).
- **Done:**
  - Dialogue: all 1194 non-empty event-script runs translated (`script/bank_XX.json`); credits/profile cards hand-laid (bank 2D). 16 runs are empty.
  - Dictionary: 1283/1331 words (`script/dict.json`, banks $30/$31).
  - Menus: every surveyed menu screen in English (field, item, status, config, song lists, shop, battle) via `labels.json` (baked tiny-font cells) and runtime tiny text (`asm/tiny.asm`); code strings (`code.json`, bank $3B), incl. the bank $05 boot/attract prologue and the Continue screen.
  - System messages: all 34 RAM-script copier call sites (`sysmsg.json` whole templates incl. the table-driven walking-style popup 00:9C64; `sysfrag.json` fragments after a name/item/amount).
  - Graphics: title menu, curtains, battle placard, 18 chapter cards (`cards.json`), 7 town shop signs (`assets/signs.txt`).
  - Playtests 2026-10-19/20 logged and fixed in `docs/bugs.md`.
  - Release gate (2026-10-20): debug tour `tools/debug/tour.py` reaches 30 scenes from cold boot (cards 1-17, battle, game over, credits, ending, save jizo, chest exchange, composer, jizo map, travel, bank-$0F modes); 75 sheets in `work/qa/manifest.tsv`, reviewer verdicts in `work/qa/verdicts/`; `tools/release.py` now runs `qa_gate.py check` and asserts the debug bank is empty.
  - Leftover-Japanese scan: `tools/jp_known.py > work/jp_known.txt`, then `jp_left.py build/kabuki_en.sfc --orig rom/... --tbl tbl/jp.tbl --le16 --known work/jp_known.txt`: ~730 runs left, the sentence-like ones checked by hand (dead copies or handled by the dictionary / FIXED); the rest are data that happens to decode.
  - Gate result: `qa_gate.py check` 75/75 ok (recheck_2.tsv: travel/jizo place names, jizo-map plaques, composer button bar, exchange names in the tiny font).
- **Next:**
  - Standby Cargo menu and sound-test help (code.json 1ED4D6-1ED55A, 04CC89) translated but not seen in the emulator.
  - Still open from earlier notes: party name table 1E:B3CA, `{name93}` rename prompt (0888FA), battle-message fragment spacing, menu cursor sites 0x12E/0x12F.
- **Open bugs** (`docs/bugs.md`):
  - Shop Sell help line garbage / wrong descriptions (steps 0013-0021): likely a QA inventory poke; re-check on a real save.
  - Button Settings "Abutton" / "Bbutton": imm label 04AEE2 has 3 cells, no room for a space.
  - Song Weapon greyed songs with no hint; Forte "Compose a song weapon" does nothing (step 0039; battle savestate starts on Jiraiya's turn): both probably original behaviour, unchecked against JP.
  - Battle item list: weapon icon overlaps the count ("100-Kan Hammer").
- **Waiting on the user:** romanization with macrons dropped (glossary, pending OK); readings of コウセン / セイガ (boss titles); whether to publish (see docs/decisions.md).
