# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-10-15 | Honorifics and name order | keep (-san), drop; JP or Western order | Kept, hyphenated (Goemon-sama); JP order. Edo-period setting, names are kabuki roles. |
| D2 | 2026-10-15 | Romanization source for names | official art, earlier patch, Hepburn | Official English (title screen, box, manual, in-game) first, else Hepburn with macrons dropped (macrons pending user OK). No earlier English patch exists (web search 2026-10-15). |
| D3 | 2026-10-15 | Credits | stay Japanese, translate | English. |
| D4 | 2026-10-15 | Abbreviations | engine work first (default), abbreviate | None: wider boxes, tiny font, relocation before shortening; abbreviate only as a flagged last resort. |
| D5 | 2026-10-15 | Graphics text left in Japanese | none (default), list | None: title, menus, banners, chapter cards in scope. 両 kept as the currency sign (reads "ryo" in text). |
| D6 | 2026-10-15 | Specs and plans | need approval, pre-approved | Pre-approved: work through the phases, report at the end. |
| D7 | 2026-10-15 | Jokes and wordplay | literal, keep the punch | Keep the punch over literal meaning; no suffix glued onto a variable ("1th"), rephrase instead. |
| D8 | 2026-10-20 | Open glossary terms from the playtest | user decides each, Claude recommends | User: "decide based on your recommendation". 十八番 -> Forte (fits 6 tiny letters, "Specialty" doesn't); 体力/声力 -> HP/VP; おひねり kept as ohineri (an NPC explains it); 装備 tab -> Gear; Kantaro, Satakeya!!, Planet Rendako, Hanakawado added. |
| D9 | 2026-10-20 | Release | publish, local only | Local patches only (release/, gitignored) until the user says to publish. Replaced by D10. |
| D10 | 2026-10-20 | Publish | stay local, publish | User: "publish to github minhnhattonthat". Public repo minhnhattonthat/kabuki-rocks, release v1.0 (bps + zip), like the sibling projects. |
