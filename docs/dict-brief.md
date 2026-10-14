# Dictionary translator brief - Kabuki Rocks (SNES, 1994)

You translate part of the game's word dictionary (item names, item descriptions, song/weapon names, monster names, battle messages, place names, stock phrases) into English for a fan patch. Work only on the batch in your dispatch. Do all translation yourself; do not dispatch subagents.

## Read first
1. `docs/style-reference.md` (tone) and `glossary.md` (binding names and terms; many items, places and characters already have English there; earlier dialogue translations used them, so these words must match).
2. Optionally grep `work/tl/b0*.out.tsv` for how a term was already rendered in dialogue (e.g. item pickup lines "Got the 'X'!!"): item names must match.

## Input: `work/tl/<batch>.tsv`
`id<TAB>glyph count<TAB>Japanese`. Ids are dictionary codes; groups by id range:
- 0300-03FF items (names; `[01F0]`..`[01FA]` are item-category icon glyphs placed before the name: keep them verbatim at the start), plus some shop phrases and place names.
- 0400-04FF song titles (song weapons). 0500-05FF monster names.
- 0600-06FF item/skill descriptions shown in the menu; 0700-07FF short effect lines.
- 0800-08FF battle messages. They are glued after or between a character/monster NAME that the game inserts at the start or middle, e.g. `は 戦闘不能になった` = "<name> was knocked out". Write the fragment so it reads correctly with a name in front (and begins with a space-free word if the Japanese has no leading space): "was knocked out". Keep any leading/trailing space the Japanese has only if it separates words.
- 0900-09FF names (characters, bosses, places) - use the glossary spellings exactly. Names with a trailing 「 are speaker labels: write `Name:`.
- 0A00-0AFF stock phrases and sentence fragments used inside dialogue; translate each as a natural fragment (they were mostly already covered when the dialogue was translated).
Unknown glyph tokens like `[0227]` are run-time kanji already decoded where known; if one remains, infer it from context and translate the whole word. Only the icon tokens `[01F0]`..`[01FA]` are kept.

## Output: `work/tl/<batch>.out.tsv`, written with your file-write tool (never a shell heredoc)
`id<TAB>English`, every input id exactly once, same order. Plain ASCII only. No `{` characters, no backslashes, no tabs inside the English. Full names and terms, never abbreviate. Item names in Title Case, descriptions in sentence case without a final period unless the Japanese has one.

## Length
Menus are narrow and the engine will be adapted to fit, but short is better. Item/song/monster names: aim for 20 characters or fewer (never abbreviate; pick the shorter natural wording). Descriptions and effect lines: aim for 28 or fewer; the game wraps nothing here. If you cannot stay within these without losing meaning, still write the full text and report `LONG: id - length`.

## Validate
Run `python -X utf8 tools/dictbatch.py check <batch>` from the repo root and fix every reported id until it prints OK.

## Report (reply with only this)
Files written and entry count; then lines: `NEW TERM: jp -> en`, `UNSURE: id - note`, `LONG: id - length`. Do not edit glossary.md, tools/ or any other file.
