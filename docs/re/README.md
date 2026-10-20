# Reverse-engineering notes

One file per subsystem (text engine, pointers, compression, font, graphics). Mark every finding with how far it is
proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely (byte pattern, another game, an earlier patch's notes). Promote it to verified
  before code depends on it.

Addresses are for the dump in `rom.sha1` unless a note says otherwise.

| File | Covers | State |
|---|---|---|
| `text.md` | event-script VM, text grammar, names, jump-out relocation, width gate | verified (roundtrip tests, marker build) |
| `font.md` | font codec, glyph table, dictionary, tiny text, menu cursors | verified; runtime glyphs 0x227-0x231 inferred, 0x229 guessed 尺 |
| `graphics.md` | graphics-text survey: title, curtains, placard, chapter cards, shop signs | verified for the intro and towns; ending, game over and save screens not surveyed |
| `debug.md` | QA debug builds (`build.py --debug`, bank $3F) | verified |
