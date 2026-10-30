# Kabuki Rocks English translation

Unofficial English fan translation of **Kabuki Rocks** (歌舞伎ロックス; Super Famicom, Atlus / RED, 1994): the source
text and tools that build the patch.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| Dialogue / story | Translated |
| Menus (field, item, status, config, song lists, shop, battle) and system messages | Translated (money sign kept as 両, read "ryo") |
| Boot/attract prologue, title menu, Continue and save screens | Translated |
| Graphics text: curtains, battle placards, 18 chapter cards, town shop signs | Translated |
| Song composer, chest exchange, travel menu and jizo-map place names | Translated |
| Standby Cargo menu, sound-test help | Not checked in play (translated, not yet seen on screen) |
| Credits | Translated |

Known issues: Button Settings labels read "Abutton" / "Bbutton" (no room for a space); in the battle item list the
weapon icon can overlap the item count. Playtest log: `docs/bugs.md`.

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English (dialogue `bank_XX.json`, dictionary, menus, system messages, chapter cards). Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `build.py`, `asm/`, `assets/`, `tbl/` | The build: text insertion, engine patches, English fonts and graphics. |
| `tools/` | Python tools: extract, lint, QA, release. |
| `tests/` | pytest suite (ROM-dependent tests skip when the ROM is absent). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md`, `docs/bugs.md` | Rulings with their reasons; current progress; playtest bug log. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |

## Build your own patched ROM

Needs Python 3.12+, pytest (for the checks), [Asar](https://github.com/RPGHacker/asar) 1.91 at `tools/asar/asar.exe`,
and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/kabuki-rocks
cd kabuki-rocks
# copy your dump to: rom/Kabuki Rocks (Japan).sfc
#   (1572864 bytes, no header, SHA-1 391d2144290f287fb5fbc872c14a6102d98fc7f5; the build refuses any other dump, see rom.sha1)
python -X utf8 build.py                                 # -> build/kabuki_en.sfc (2 MB)
python -X utf8 tools/check.py                           # tests + text lint
```

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is Atlus's and is included only so the
translation can be checked against it. Kabuki Rocks is (c) Atlus / RED; this project is not affiliated with them.
Do not share patched ROMs.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
