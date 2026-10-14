# Translator brief - Kabuki Rocks (SNES, 1994)

You translate part of the Japanese script of Kabuki Rocks (comic kabuki RPG) into English for a fan patch. Work only on the batch in your dispatch. Do all translation yourself; do not dispatch subagents.

## Read first
1. `docs/style-reference.md` - voice, approved pairs, mechanics.
2. `glossary.md` - binding names and terms (rulings at the top). Use names exactly.

## Input: `work/tl/<batch>.tsv`
`id<TAB>Japanese`. ` / ` marks a line break inside the box (ignore it; the build re-wraps). Dictionary words (names, items, shouts) are already spliced into the text as plain Japanese. Runs are in story order within a bank: use neighbours for context. Several runs can be pieces of one scene; keep names/pronouns consistent across them.

## Output: `work/tl/<batch>.out.tsv`, written with your file-write tool (never a shell heredoc)
`id<TAB>English`, every input id exactly once, same order. Plain ASCII only: straight quotes, `...`, `--`; no tabs inside the English, no `{n}`, no Japanese. Keep every control token (`{wait}` `{clr}` `{delay:XX}` `{p9a}` `{ba}` `{b8:..}` `{choice:..}` `{jump:..}` `{name93}` `{name94}`) as in the style reference.

## Validate
Run `python -X utf8 tools/batches.py check <batch>` from the repo root and fix every reported id until it prints OK. (The check wraps text exactly as the build does; you do not need to count characters. Aim for brevity: boxes hold 3 lines of 28 characters, and very long speeches mean many pages.)

## Style
- Faithful: keep information and order of ideas; adapt idiom not meaning. Don't add or skip content. Jokes and wordplay keep their punch (no translator notes).
- Full names and terms, never abbreviate. Honorifics kept hyphenated (Tensai-sama). Names per glossary.
- No suffix glued onto a variable. Do not put a/an right before {name93}/{name94}.
- Speaker prefix `Name:` as in the style reference.
- Do not edit glossary.md, tools/ or any other file.

## Report (reply with only this)
Files written and entry count; then lines: `NEW TERM: jp -> en`, `UNSURE: id - note`, `LONG: id - note`.
