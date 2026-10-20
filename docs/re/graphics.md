# Graphics-text survey

Reached: boot logos, title, intro, field menus (all sub-screens), shops, battle, the 131 maps of the warp tour
(work/qa/maps3: no Japanese signage seen at full-screen scale). Not reached: ending, game over, save screens beyond
the Save Jizo dialogue.

| Screen | Element | Source | Status |
|---|---|---|---|
| Boot | ATLUS / RED logos | art, Latin | keep |
| Title | KABUKI ROCKS! logo, (c) ATLUS/RED | BG1 art, Latin | keep |
| Title | menu 初公演 / 再公演 | BG1 16x16 kanji, tiles in compressed block 18:D26D (tile 0 = BG1 tile 0); map = byte stream at 19:8xxx (`85 n1..n6` per row) | NEW GAME / CONTINUE (build.py patch_title; 再公演 row moved to unused tiles $10C-$113) |
| Title | curtain text れっど / あとらす (vertical) | BG3 2bpp, raw tiles in bank $18 (file 0xC00A0...) | RED / ATLUS (patch_title) |
| Battle | empty party slot placard 出演者求む | OBJ 16x16 x 9, compressed 24:AE58 (6x6 tiles, rows interleaved 0,3,1,4,2,5) | ACTORS / WANTED (patch_placard) |
| Battle | knocked-out member placard 休演中 | same format, compressed 24:AC33 (loader 02:A59E -> 7E:9800) | OFF / STAGE (patch_placard) |
| Composer | button bar CLEAR もとす えんそう とうろく おわる | OBJ sheet 1A:AAB64 (LZ, $B40, loaded by 0F:C851), buttons = 32x16 at tiles $20/$24/$28/$2C (+$10 bottom); also the help line's highlighted button (sprite) | BACK PLAY SAVE DONE (build.py patch_composer) |
| Jizo map | region plaque イズモ ... オエド | OBJ metasprites 2E:E255 (7 x 25 bytes: 80 04 01 00 00 + 5x2 tile/attr), tiles in sheet 1A:B613 (LZ, $1A80, loaded by 0F:A299) | English region names, dialogue font (build.py patch_plaques) |
| Menus | 8x8 overlay kanji (体力 声力 次の役者まで 攻守早 個 空き 回) | overlay tile blocks 1F:AB82.. (build.py MENU_TILES, per window style) | English / icons / blank |
| Story | chapter cards 一番 旅立ち .. 十八番 メイン・テーマ (18) | BG 4bpp tiles, compressed 1D:8000 (0x2C60); per-chapter maps via 10:C06A (2 words/row), heights 1E:E1FE, frame 1E:E228; other tiles in the block are the curtain | "ACT n" + title turned 90 deg (build.py patch_cards, script/cards.json) |
| Towns | shop signs 武 防 道 宿 楽 靴 茶 (16x16) | map tile block 151 = 1B:D99D (table 01:A0E2, loader 00:8A3A), the only block holding them | sword / shield / bag / INN / note / boot / teacup (build.py patch_signs, assets/signs.txt) |
| Menus | money and rank unit 両 | glyph 0xE8, overlay 0x3C3 | kept as the currency sign |

Tools: `--script tools/lua/lzlog.lua` logs every decompression (source, destination, size); probes/snes_dmalog.lua
the DMA into VRAM; `vramfind.py` for raw tiles.
