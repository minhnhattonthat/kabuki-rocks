# Kabuki Rocks (SNES, Atlus/RED 1994) English translation

Skill: translate-retro-game (Claude Code: plugin, enabled in .claude/settings.json; other agents: `<SKILL_DIR>/SKILL.md`; `$SKILL` = the directory holding its SKILL.md). Read it before ROM, text or QA work. Tools that call the skill's scripts take its `scripts/` directory from the `SKILL` environment variable.

## Commands (run from repo root)
- Build:    `python -X utf8 build.py` -> build/kabuki_en.sfc (2 MB; checks the dump against `rom.sha1` first). `--marker` = "(id)" markers; `--qa ID=TEXT` overrides one run; `--reloc-jp` = mechanism test; `--debug HEX` = QA build (docs/re/debug.md, never released)
- Check:    `python -X utf8 tools/check.py` (pytest tests/ + tools/lint.py; the pre-commit hook runs this)
- Smoke:    `python -X utf8 $SKILL/scripts/emu.py build/kabuki_en.sfc --out work/qa/smoke --route tools/routes/boot.txt --smoke --sheet`
- Intro tour: `--route-str "1100 -;6 start;200 -;6 start;200 -;6 a;200 -" --mash 200 --mash-key a --frames 9000 --shot-every 50` (mash slower than ~150 frames or pages are shot mid-transition)
- QA sheets: `sh tools/qa_screens.sh` (menus + Japanese report in work/qa/screens/), `tools/qa_sysmsg.py`, `tools/qa_sysfrag.py`
- Text: `tools/text.py dump` (refuses to overwrite), `tools/batches.py split|check|merge bNNN`, `tools/wrap.py "text"`, `tools/dictwords.py dump`
- Release:  `python -X utf8 tools/release.py --ver X.Y` -> release/KabukiRocks_EN_vX.Y.bps (check + build + SNES checksum + BPS verify; never publish without the user)

## Paths
- Original ROM: `rom/Kabuki Rocks (Japan).sfc` (LoROM 1.5 MB, gitignored; SHA-1 in `rom.sha1`, checked by `tools/check_rom.py`; CRC32 ad324f9d). Emulator `tools/mesen2/Mesen.exe`, asar 1.91 `tools/asar/asar.exe` (both gitignored). Savestates: `work/states/` (theater_free.mss = free play after intro, field_menu.mss); user states in `H:\emulator\mesen\SaveStates\`.
- Text: `script/bank_XX.json` (event-script runs: id = CPU addr, jp tokens, en), `script/dict.json` (dictionary, banks $30/$31), `labels.json` (menu labels), `code.json` (strings in code -> bank $3B), `sysmsg.json` / `sysfrag.json` (RAM-script system messages), `cards.json` (chapter cards). Tables `tbl/jp.tbl`, `tbl/en.tbl` (generated from the font). Fonts and graphics `assets/` (licences: `docs/fonts.md`).
- Glossary: `glossary.md`. RE notes index: `docs/re/README.md`. Playtest bug log: `docs/bugs.md`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- English is unwrapped in JSON; build/lint wrap to 3 lines x 28 cells and add pages ({wait}{clr}). Speaker style `Name: text`. {name93}=Rock {name94}=Makki are substituted as text by the build (a name code at a line start triggers the JP hanging indent).
- Gotchas:
  - Bank use: $30-$3A free space (`Space` allocator), $3B-$3C code strings + hooks, $3D extended glyph table, $3F QA debug only.
  - The tiny-font pool is capped at `$0E40//16` tiles (WRAM mirror); `still_drawn` decides which kana/kanji tiles can be reused, so a glyph kept as a raw `[XXXX]` code in English must stay counted or its tile gets baked over.
  - The RAM-script copier (00:90C2/90C7) has several callers per template; relocating a template means repointing every caller's slot store (`sysmsg.json` slots), and table-driven messages (00:9C64) don't show up in `tools/sysmsg.py sites`.
  - Chapter-card frame tiles (`CARD_FRAME`) are shared with the curtain background; don't reuse tiles outside the original card maps.
  - The Continue / save screens need a cold boot with a save (`--sav`), not a savestate, to show the real strings.

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
