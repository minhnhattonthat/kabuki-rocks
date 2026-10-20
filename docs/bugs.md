# Bugs

Tick `- [x] (fixed in <build>)` once re-checked from the cited state.

## 2026-10-19 playtest - kabuki_en.sfc sha1 7f7b5251d5f0
Evidence: `work/playtest/2026-10-19/NNNN.png|.sheetK.png|.<state>`, presses in `log.tsv`.

- [x] (fixed in patch_prologue: bank $05 strings read from $3B, lines re-centred) step 0000-0001 - text - boot screen before title - untranslated Japanese, about half the glyphs missing (blank cells); only the title is Latin - "本日は 来…いただ… て / とにあ…どう い 。/ な たい た いた た。/ 『KABUKI ROCKS』を…演いた 。/ い ( っ と に い。"
- [x] (fixed in patch_prologue) step 0002-0003 - text - attract intro narration over the planet map and castle - untranslated Japanese with garbled or missing glyphs - "は はるかかなた …… / …は … を ていた。/ …地『OEDO』は… / 邪7なかい"
- [x] (fixed 2026-10-20: tools/wrap.py keeps 2 cells for the arrow) step 0014, 0015, 0017, 0040, 0043 - text - dialogue box, line 3 - a line filling all 28 cells runs into the page-advance arrow; last character touched or hidden - "Do you not think they‡", "Shogun or no shogun,‡", "nothing but awful‡", "house is west‡", "What's he doing in‡"
- [ ] step 0009-0010 - text - chapter title card - graphic still Japanese (graphics survey, likely known) - "一番 旅立ち"
- [ ] step 0031-0035 - text - town shop banners - graphic kanji (known: graphics survey) - "武", "防", "宿"
- [ ] step 0021 - text - field menu (known) - "Song Weapon" crushed into two tiny lines behind the cursor icon; money and rank still show the Japanese glyph - "Song / Weapon", "0両", "Next rank in 30円"
- [ ] step 0023 - text - field menu (known) - cursor sprite overlaps the selected label - "Item"
- [ ] step 0024 - text - Item screen (known) - "Battle" tab jammed against the frame and the tab arrow - "Battle◀ Remedy Other"
- [ ] step 0048 - wording - town NPC - "ohineri" not in the glossary and never explained; money shows as "ryo" (step 0041 "Rock got 300 ryo!"), reads like two currencies - "earn ohineri, and buy strong weapons, ya hear."
- [x] (fixed 2026-10-20: tools/wrap.py rebalances a one-short-line last page; 180 -> 6 widows) step 0008-0009, 0014, 0017, 0019, 0040, 0041 - wording - dialogue (known: wrapper widow pages) - one or two words alone on a new page - "awake?!", "ought to suffer more?", "things.", "of the playhouse.", "thing."
- [x] (fixed 2026-10-20: "ourselves") step 0013 - wording - play cutscene - capital mid-sentence across a page break reads like a typo (royal "Ourselves"?) - "We shall allow no one but / Ourselves to enjoy anything!!"
- [ ] step 0015, 0043 - wording - names missing from the glossary (confirm) - "Kantaro", "Satakeya!!", "Planet Rendako"

## 2026-10-20 playtest - kabuki_en.sfc sha1 7f7b5251d5f0
Evidence: `work/playtest/menu/NNNN.png|.sheetK.png|.<state>`, presses in `log.tsv`.

- [x] (not a bug: the active tab is the one right of ◀; both screens list the same Remedy items. Weapons in it come from the QA inventory poke) step 0036-0040 - text - field Item vs shop Sell (QA state; re-check on a normal save) - field Item "Remedy" tab empty ("Free 24") while shop Sell "Remedy" lists 10 items incl. weapons (Kotetsu Blade, 100-Kan Hammer) - "Free 24"
- [ ] (likely QA poke: descriptions come from per-category records (02:DF7D, $5E85 ids), the poke put one id list in every tab; re-check on a real save) step 0014, 0015 - text - shop Sell help line - garbage glyph rows instead of a description - Kotetsu Blade: two lines of junk glyphs; Candy: two junk glyphs
- [ ] (likely QA poke, as above) step 0013, 0020, 0021 - text - shop Sell help line - wrong or missing description - Phoenix Feather shows "Hannya Ring"; 100-Kan Hammer shows "..."; Quick Cucumber Roll blank
- [x] (fixed 2026-10-20: stat names via labels.json tinyslots 04A250; arrow tiles remapped, build.py COMPARE_ARROW) step 0050 - text - Equip stat-compare box - Japanese left, garbled arrow - "攻撃力 16N 18"
- [x] (fixed 2026-10-20: names via labels.json tinytable 049451, padded to 20 letters) step 0043-0045 - text - Forte name window - stale "g" from "Compose a song" stays at the right edge for other members - "Rouse          g", "Grand Brawl  g"
- [x] (fixed 2026-10-20, as above) step 0042, 0046 - text - Forte name window - "Compose a song" runs into the right frame, "g" clipped - "Compose a song"
- [ ] step 0009-0011, 0036-0040 - text - Sell and Item tab bars - "Equip-/ment" hyphen-split over two tiny lines; stray slash after Battle - "Equip- ment", "Battle/"
- [ ] step 0002, 0003, 0024, 0048 - text - shop menu, buy list, equip sub-menu - cursor sprite covers the first letter of the selected label (field-menu bug on more screens) - "Help", "Bamboo-maru", "Sell", "Equip"
- [x] (ruling 2026-10-20: Forte; glossary and 2 dialogue lines updated) step 0027 - wording - field/battle menu - 十八番 shown as "Forte", glossary says "Specialty" - "Forte"
- [x] (fixed 2026-10-20: title now "Trade") step 0048, 0054 - wording - equip sub-menu "Trade" opens a screen titled "Exchange" - "Trade" / "Exchange"
- [ ] step 0048 - text - equip sub-menu - options in different fonts (tiny "Equip", large "Trade")
- [ ] step 0031 - wording - Song Weapon, Remedy tab - status-inflicting song under Remedy; check label/description - "Silent... How Sultry" / "Inflicts Polyp"
- [ ] ("Cancel / Commands" fixed 2026-10-20; "Abutton" open: imm label 04AEE2 has 3 cells = 6 tiny letters, no room for a space) step 0066 - wording - Button Settings - no space before "button"; "Cancel and Commands" unclear - "Abutton", "Bbutton", "Cancel and Commands"
- [x] (fixed 2026-10-20: shared line now "That's the deal, then?") step 0023 - wording - Sell confirm reuses the buy line - "That's what ya want, huh?" / "Stop selling"
- [ ] step 0072 - wording - Song Weapon - songs greyed, A does nothing, no hint (no song weapon equipped; likely original behaviour) - "Cheer Up"

## 2026-10-20 playtest - kabuki_en.sfc sha1 7f7b5251d5f0
Evidence: `work/playtest/battle/NNNN.png|.sheetK.png|.<state>`, presses in `log.tsv`.

- [x] (fixed 2026-10-20: string 02:8E78 now in code.json, glyph 0x229=尺 confirmed; ryo line shortened to fit 28 cells) step 0042 - text - post-battle reward message after the ryo line - untranslated Japanese, garbled glyphs, stray "!" at right edge (尺 = guessed glyph 0x229, also "Next rank in 20尺") - "10尺 え  はwr  かったJ          !"
- [x] (fixed 2026-10-20: loop 02:DB8E drawn in the tiny font) step 0020-0026 - text - battle Song Weapon list - names drawn in the large font spill past the list window over the Run button; scrolling leaves stale tile fragments - "Good Day to Blaze Off", "Man Who Calls Storms", "Eyes of 10,000 Volts"
- [x] (fixed 2026-10-20: description 02:DCAC in the tiny font, 15 cells = 30 letters, all 39 fit) step 0020-0026 - text - song description bar - description runs into the Cost/Area labels and numbers - "Fire, power level 225", "Thunder, power leve15", "Death (one-hit kill12"
- [x] (fixed 2026-10-20, as above) step 0023 - text - song description bar - Explosion text spills outside the right edge - "Explosion, power le85 4…f"
- [x] (fixed 2026-10-20: message line build.py patch_msgclear; song descriptions/rows via tiny text; recheck item descriptions) step 0024-0026, 0033 - text - battle descriptions/messages not cleared before a shorter string; tail of previous one remains (also song list rows: "Wave of Loverage", "Punch-kun's SongRun") - "Inflicts Poisonvel 6", "Deals holy damageve35", "Benkei took damageks!"
- [x] (fixed 2026-10-20: no name is printed (JP starts with 「), 22 shouts now in quotes) step 0030, 0032, 0036 - text - Forte shout lines miss the speaker name before the colon - ": One more push!", ": Have at thee!", ": Whoa, careful!"
- [x] (fixed 2026-10-20: ": A spirited blow!!") step 0041 - text - critical-hit message lacks punctuation after the name - "Rock A spirited blow!!"
- [ ] step 0009 - text - battle Item list - blank-name item (count 1, greyed) between Candy and Nigiri Sushi, garbage description - "        1"
- [ ] step 0007 - text - battle Item list - weapon icon overlaps the count - "100-Kan Hammer"
- [ ] step 0011 - text - battle Item list - long name runs into the count column - "Pickled Ginger Chips1"
- [x] (not a bug: JP build identical; the debug script lacks a fade-in after the battle, see docs/re/debug.md) step 0043 - blocker - after victory the screen stays black 900+ frames until the field menu is opened and closed (maybe debug state; confirm on a normal encounter) - (black screen)
- [ ] step 0039 - wording - Rock's Forte "Compose a song weapon": A does nothing, no message - "Compose a song weapon"
- [x] (fixed 2026-10-20: "and pals tried to flee") step 0028 - wording - failed escape says they fled, then contradicts (first-pass shot overwritten) - "Rock and pals fled" / "But they were cut off!"
- [x] (ruling 2026-10-20: VP in all text; HUD H/S letters are the original's, kept) step 0000, 0010 - wording - voice stat has three names: HUD "S", descriptions "Voice", field menu "VP" - "S", "Voice", "VP"
- [ ] step 0007, 0011 - wording - odd status names in item descriptions; check intent - "Cures Polyp", "Cures Love Slave", "Cures Hunched Over"
- [ ] step 0028 - wording - song-cast message: "was sung!" crushed into the tiny font after the title - "♪Good Day to Blaze Off♪ was sung!"

## 2026-10-20 playtest - kabuki_en.sfc sha1 7f7b5251d5f0
Evidence: `work/playtest/story/NNNN.png|.sheetK.png|.<state>`, presses in `log.tsv`.

- [x] (not a bug: talking to Ume unlocks it, march starts by itself; English matches JP hint; work/play/gate 0006-0020) step 0070-0071 - blocker? - Hana Town south gate - in the Soldier's Uniform the soldiers still block the gate with no hint where to go next (Ume: "give my regards", Makki: "come get me"); check the trigger and that the English points the player to it - "Soldier: Still a while before we head out."
- [ ] step 0065 - wording - Jingoro scene after the uniform change - one page fell between shots, unread; re-check - "Jingoro: Well, that suits..."
- [x] (reworded 2026-10-20; both names are in the JP line) step 0021 - wording - Hana Town NPC - town named twice, clunky; "Hana Town" not in glossary - "Head north from this 'Hana Town' and there's a town called 'Nakidokoro Town'."
- [ ] step 0062 - wording - Jingoro scene - "Hanakawado" (Sukenobu's family name) not in glossary - "your father is my friend, Hanakawado Sukenobu. A former actor."
- [x] (fixed 2026-10-20) step 0064 - wording - Jingoro scene - "get out of this town" twice - "Wear this and you can get out of this town. For now, just get out of this town!!"
- [x] (fixed 2026-10-20) step 0039 - wording - Jizo Sushi woman - odd phrasing - "they say the shop won't start business for a while yet."
- [x] (wrapper fix 2026-10-20) step 0013, 0046, 0062, 0064 - wording - more widow pages (known class) - "paper.", "Witless Woods!", "former actor.", "hear a word of it."
- [x] (wrapper fix 2026-10-20) step 0062, 0064 - text - more line-3 runs into the page arrow (known class) - "I will set the world right!'", "just get out of this town!!"

## 2026-10-20 playtest - kabuki_en.sfc sha1 7f7b5251d5f0
Evidence: `work/playtest/gate/NNNN.png|.sheetK.png|.<state>`, presses in `log.tsv`.

- [x] (fixed 2026-10-20: stray quote removed; JP speaker is a blank indent, so no name per glossary) step 0018 - text - outside the south gate, disguised Makki - opening quote never closed, no speaker name - "\"Oh, come on. Forgotten your childhood friend's face already?"
- [x] (wrapper fix 2026-10-20) step 0007, 0008, 0011 - wording - Ume dialogue - more widow pages (known class) - "it yourself after all...", "on.", "path you believe in."
