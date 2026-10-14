# Style reference (approved pilot, 2026-10-15)

Kabuki Rocks: a comic kabuki-themed RPG. The hero Rock and Makki fight to bring back "song plays" (musical kabuki) banned by the tyrant shogun Tensai. Tone: light, jokey, full of kabuki and Edo parody, regional dialects (Kansai, Kyushu, etc.), catchphrases and puns. Keep the punch over literal meaning.

## Voice
- Speaker prefix is part of the text: `Name: line`. The JP form `役者A「` becomes `Actor A:`; `客「` = `Audience:`. Keep the prefix whenever the JP has one.
- Nobles / the shogun (Actor A, Tensai) speak stiffly and royally ("We", "Ourselves"). Commoners and Rock are casual. Dialect speakers get a matching English flavor, lightly (a Kansai merchant: "Y'know", "ain't"; ござる samurai: archaic but readable).
- Kabuki shouts from the audience keep the shop-name call: `Otowaya!`, `Satakeya!`.
- Sound/laugh interjections stay short: `Fngyaaah!!`.
- Punctuation: 「」 dropped after the speaker prefix; ・・・ / ‥‥ -> `...`; ！？ -> `!?`. ASCII only. The font has no `~`-style tilde in dialogue use; avoid it.

## Approved pairs
JP: 役者A「それから モンスターも ころしてはいかん！
EN: Actor A: And furthermore, no one may kill monsters either!

JP: 役者C「世界のへいわを ゆるがす にっくきやつ！ 将軍といえども ゆるしちゃ おけねえ！
EN: Actor C: Vile wretch who shakes the peace of the world! Shogun or no shogun, I cannot let this stand!

JP: {name93}「おい {name94}！ 歌しばいが そろそろ はじまるぜェ
EN: {name93}: Hey, {name94}! The song play's about to start!

## Mechanics
- Write each run's English as plain sentences. Do not write line breaks or `{n}`; the build wraps to 3 lines of 28 characters and adds pages.
- Keep these tokens exactly, in the same order and places relative to sentences: `{wait}` `{clr}` `{delay:XX}` `{p9a}` `{ba}` `{b8:XXXX}` `{choice:XXXXXX}` `{jump:XXXXXX}` `{name93}` `{name94}`.
- A `{choice:...}` marks a yes/no prompt: the text before it is the question, the two answers (e.g. はい/いいえ) follow in the next run; keep the token where it falls.
