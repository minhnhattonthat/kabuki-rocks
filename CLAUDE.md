# Kabuki Rocks (SNES, Atlus 1994) English translation

Skill: translate-retro-game (H:/translation/kabuki-rocks/.claude/skills/translate-retro-game/SKILL.md, `$SKILL` below). Read it before ROM, text or QA work.

## Commands (run from repo root)
- Build:    TBD (phase 2)  -> build/kabuki_en.sfc
- Check:    `python -X utf8 tools/check.py`  (pytest tests/; the pre-commit hook runs this)
- Smoke:    `python -X utf8 $SKILL/scripts/emu.py build/kabuki_en.sfc --out work/qa/smoke --route tools/routes/boot.txt --smoke --sheet`
- Release:  TBD (`$SKILL/scripts/bps.py`; never publish without the user)

## Paths
- Original ROM: `rom/Kabuki Rocks (Japan).sfc` (gitignored). LoROM, 1.5 MB (12 Mbit), header $7FC0 "KABUKI ROCKS", 8 KB SRAM.
  SHA1 391d2144290f287fb5fbc872c14a6102d98fc7f5, MD5 daae6c39f7d168954e2b568c47b3bdd1, CRC32 ad324f9d.
- Emulator: `tools/mesen2/Mesen.exe`; assembler `tools/asar/asar.exe` (both gitignored). Savestates: `work/states/`.
- Text: `script/` (TBD). Tables: `tbl/`. Glossary + rulings: `glossary.md`. RE notes: `docs/re/`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts read and analyse, never `.replace()` and write back.
- Honorifics / name order / credits / romanization: TBD (ask user).

## Status
- Done: Step 0 (tools, hooks, check). Original boots in Mesen (title ~f1080).
- Next: phase 1 recon (encoding, pointers, compression, graphics text).
