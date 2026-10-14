# Kabuki Rocks (SNES, Atlus/RED 1994) English translation

Skill: translate-retro-game (H:/translation/kabuki-rocks/.claude/skills/translate-retro-game/SKILL.md, `$SKILL` below). Read it before ROM, text or QA work.

## Commands (run from repo root)
- Build:    `python -X utf8 build.py` -> build/kabuki_en.sfc (2 MB). `--marker` = "(id)" markers; `--qa ID=TEXT` overrides one run; `--reloc-jp` = mechanism test
- Check:    `python -X utf8 tools/check.py` (pytest tests/ + tools/lint.py; the pre-commit hook runs this)
- Smoke:    `python -X utf8 $SKILL/scripts/emu.py build/kabuki_en.sfc --out work/qa/smoke --route tools/routes/boot.txt --smoke --sheet`
- Intro tour: `--route-str "1100 -;6 start;200 -;6 start;200 -;6 a;200 -" --mash 200 --mash-key a --frames 9000 --shot-every 50` (mash slower than ~150 frames or pages are shot mid-transition)
- Text: `tools/text.py dump` (refuses to overwrite), `tools/batches.py split|check|merge bNNN`, `tools/wrap.py "text"`, `tools/dictwords.py dump`
- Release:  TBD (`$SKILL/scripts/bps.py`; never publish without the user)

## Paths
- ROM: `rom/Kabuki Rocks (Japan).sfc` (LoROM 1.5 MB; SHA1 391d2144290f287fb5fbc872c14a6102d98fc7f5, CRC32 ad324f9d). Emulator `tools/mesen2/Mesen.exe`, asar `tools/asar/` (gitignored). States: `work/states/` (theater_free.mss = free play after intro, field_menu.mss).
- Text: `script/bank_XX.json` (event-script runs: id = CPU addr, jp tokens, en), `script/dict.json` (bank $2F dictionary, not inserted yet). Tables `tbl/jp.tbl`, `tbl/en.tbl` (generated from the font). Font bitmaps `assets/font_en.txt`.
- RE notes: `docs/re/text.md` (script VM, text grammar, names, width gate), `docs/re/font.md` (codec, font, dictionary), `docs/re/graphics.md` (survey). Glossary + rulings: `glossary.md`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts read and analyse, never `.replace()` and write back.
- Honorifics kept, hyphenated; JP name order. Romanization: official English, else Hepburn (macrons dropped, pending user OK). Credits: English. No abbreviations (engine work first). Plans pre-approved. Details: glossary.md.
- English is unwrapped in JSON; build/lint wrap to 3 lines x 28 cells and add pages ({wait}{clr}). Speaker style `Name: text`. {name93}=Rock {name94}=Makki are substituted as text by the build (a name code at a line start triggers the JP hanging indent).
- No earlier English patch found (web search 2026-10-15).

## Status (2026-10-15)
- Done: phases 0-4 for dialogue (identity build, extract + roundtrip, jump-out relocation, English font, width gate, marker build). Pilot: prologue 14 runs in bank_08 (088015-088638), boots clean.
- Next: user approves pilot style -> docs/style-reference.md + translator brief -> 34 batches (`work/tl/bNNN.tsv`). Then dictionary insertion (names/items/menus; bank $2F, menus need wider windows or small font), RAM-script system messages (00:90C2), menu cursor sites still using 0x12E/0x12F (docs/re/font.md), window-1 / choice widths, graphics survey past the intro (needs saves).
- Known: untranslated JP shows wrong glyphs for 12 sacrificed kanji and old punctuation 0x127-0x12F in builds with the English font.
