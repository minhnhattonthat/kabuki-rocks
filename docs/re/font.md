# Font and graphics compression

## Compression (00:8E1E)
Codec: `tools/lz.py` (decompress + greedy compress, roundtrip-tested on the font blocks). Commands:
FF n zero×(n+0x20) · E0-FE zero×((c&1F)+1) · C0-DF b: b×((c&1F)+2) · A0-BF: (c&1F)+1 bytes written as 00,b · 80-9F literal (c&1F)+1 · 00-7F lo: LZ copy (c>>2)+2 bytes from out[pos-0x400+((c&3)<<8|lo)]. Ends at `7F FF` or the caller's size limit ($22).
Caller sets source $1C/$1E (24-bit), dest $1F/$21, size $22, DP=$0400.

## Dialogue font (BG3, 2bpp)
- Loaded by 00:B7F6: 1F:8000 (file 0xF8000) -> 7F:A000 -> VRAM word $6000 (BG3 tiles 0-511); 1F:987D (0xF987D) -> VRAM $7000 (tiles 512-1023). 0x2000 bytes each.
- Glyph = 8x16: top tile + bottom tile. 00:BAEF maps a code (< 0x300) to two tile numbers: page = 0 (<0xB0), 1 (<0x140), 2 (<0x1C0), 3; index = (code - word[00:BB5A+2p])*2 + word[00:BB62+2p] into the byte-pair table 00:BC48 (file 0x3C48); tile = page<<8 | byte; FF = blank (tile 0x3FF). Tilemap attr OR 0x2C00 (priority, palette 3). Space 0x02FF = blank.
- Halves are shared between glyphs (dakuten tops etc.). Fixed 8 px per character; no width table.
- In `$060C >= 5` (another screen mode) 00:BB6A maps with a different VRAM base (attr $20/$21 + $0858/$0859).
- Codes 0x1F0-0x1FA: item-category icons. Codes 0x200-0x2FE: tiles 0x300+ that are rewritten at run time (per-screen kanji / window art); the ROM font has them blank. Seen in dictionary words (0x213, 0x219, 0x21A, 0x270): dump VRAM on that screen to read them.
- `tools/font.py sheet OUT.png --from 0 --to 1FF [--vram DUMP]` renders labelled glyphs. Table: `tbl/jp.tbl`.
- Latin A-Z (0xBA-0xD3) and digits (0xB0-0xB9) exist, uppercase only.

## English font
- `assets/font_en.txt` (8x16 bitmaps) -> `font.patch_font(rom)`: ASCII c -> code 0x100+(c-0x20), extras … ♪ — é ★ ▶ at 0x15F-0x164; returns the char -> code map. Review: `tools/font.py en-sheet OUT.png [--text ...]`.
- Real table ranges: page 1 = codes 0xB0-0x138, page 2 = 0x140-0x1B8. Codes 0x139-0x13F (Y Z [ \ ] ^ _) read the entries of 0x140-0x146 (` a-f), so each such byte must be free in both pages; `font.SACRIFICE` lists the 12 low-use page-2 kanji given up for that.
- Identical halves share one tile (blank halves too). BG3 tiles 0x2E0-0x2FF are rewritten at run time (VRAM dump), never used.
- Engine draws 0x12E (▶) / 0x12F (◀) as cursors (e.g. 03:93EF `LDA #$012E; JSL $00BA9D`); those codes are now N / O.

## Dictionary (codes >= 0x300)
`tools/dictwords.py`: group g = (code>>8)-3, base word at 00:BC38+2g (g=6 and code>=0x980: base F30B, idx-0x80; 0x6xx-0x7xx share a 9-bit index), pointer = word at 2F:(base+2*idx), string = LE words in bank $2F, last word has bit 15 set. Holds names, items, places, battle messages, menu strings (~2000 codes, many unused/garbage).

## Text box
Dialogue box: 2 lines of 16 px, ~28 cells of 8 px (measure in the width gate).

## Tiny text in lists (asm/tiny.asm, build.py patch_tiny, needs tools/asar/asar.exe)
- Menu lines go to the WRAM tilemap buffer 7E:2780 (top row) / 27C0 (bottom), Y = row*$80 + col*2, one glyph at a
  time through 04:B71D (attribute $1C00) / 04:B725 (attribute in $0709, $0C00 = greyed) -> 00:BA9D.
- Item-name loops (`LDA $2F0000,x ; BMI ; JSR $B71D|$B725`) at 04:9FE9, BEA7, C3FB (song names, untested), DF22
  (shop list), E118 (shop message line) and 04:B65A (equip/exchange) become JSL tiny71d/tiny725: two 3x5 letters
  per cell in the cell's top tile (rows 2-7), bottom tile blank $3FF; icons and letters the tiny font lacks take a
  full cell.
- Cells use BG3 page-0 tiles: `font.patch_font` packs the kana tiles that something may still draw (still_drawn +
  sysmsg.codes) from tile 1 up and blanks the other kana; the rest of page 0 is the pool (114 tiles now; ~228 once
  the system messages are translated). Tile 0 is BG3's transparent fill: never touch it.
- Slots: next fit, skipping slots the tilemap buffer still shows (OWNER table). Pixels go to a WRAM mirror at
  7F:D000 (7F:D000-FABF is never written by the game: tools/lua/wramuse.lua); the NMI frame-ready branch (00:82A8)
  DMAs dirty slots (channel 7, <= $600 bytes per frame) to VRAM $6000+tile*8. The font loader (00:B7F6, reloads page
  0 on every menu open/close) re-dirties the whole pool when it loads to VRAM $6000.
- Battle mode ($060C >= 5) keeps the per-glyph drawing.
- Inventory: 7E:5E85, one item id per slot (FF = empty); script op A2 does not add to it, A0 tests it. QA fills it
  with tools/lua/poke.lua (tools/qa_screens.sh).
