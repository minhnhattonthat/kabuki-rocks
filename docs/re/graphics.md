# Graphics-text survey (phase 1, partial)

Reached so far: boot logos, title, intro play + theatre (free play from `work/states/theater_free.mss`), field menu (`work/states/field_menu.mss`, X button).

| Screen | Element | Kind | Status |
|---|---|---|---|
| Boot | ATLUS / RED logos | sprite/BG art, Latin | keep |
| Title | "KABUKI ROCKS!" logo | BG art, already English | keep |
| Field menu | name, 1両役者 rank, 体力/声力 labels, 次の役者まで, commands 歌武器 道具 十八番 装備 状態 設定, けいかいする, money 両 | **font text** (BG3 glyph codes, incl. runtime 0x2xx kanji: 状態 0x272/0x273, 設定 0x271/0x1B0) | text work: command column is 3-4 cells wide -> needs a wider window or small font |

Not yet reached: shops, inns, item/equip/status sub-screens, battle (commands, messages, enemy names), save/load, name entry (if any), ending/credits. Need a save or long route; ask the user for SRAM saves.
