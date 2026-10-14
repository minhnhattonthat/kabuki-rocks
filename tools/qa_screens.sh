#!/bin/sh
# Capture the UI screens of a build into one contact sheet (debug starts: docs/re/debug.md).
#   sh tools/qa_screens.sh [ROM_ARGS]   -> work/qa/screens/sheet.png (+ one PNG per screen)
# ROM_ARGS go to build.py (default: the English build; pass --reloc-jp for the Japanese original).
set -e
cd "$(dirname "$0")/.."
SKILL=.claude/skills/translate-retro-game/scripts
OUT=work/qa/screens
BOOT="1100 -;6 start;200 -;6 start;200 -"
GIVE="A4 30 75 B5 1B B5 2B B5 3C A2 44 A2 43 A2 42 A2 45"
mkdir -p $OUT work/states
rm -f $OUT/*.png
shot() {  # name rom state route frames
  python -X utf8 $SKILL/emu.py "$2" --out work/qa/_s --state-in "$3" --route-str "$4" --frames "$5" \
    --script tools/lua/glyphlog.lua --script tools/lua/battleglyph.lua >/dev/null
  cp work/qa/_s/final.png "$OUT/$1.png"
  cp work/qa/_s/log.txt "$OUT/$1.log"
}
python -X utf8 build.py "$@" --out build/qa_field.sfc --debug "$GIVE C8 00 0A 0A 0B BC 09 FF" >/dev/null
python -X utf8 $SKILL/emu.py build/qa_field.sfc --out work/qa/_s --route-str "$BOOT;500 -" --frames 2400 \
  --state-out work/states/qa_field.mss >/dev/null
shot 01_menu build/qa_field.sfc work/states/qa_field.mss "20 -;6 x;60 -" 120
n=2
for d in 0 1 2 3 4 5; do
  r="20 -;6 x;40 -"
  i=0; while [ $i -lt $d ]; do r="$r;6 down;12 -"; i=$((i+1)); done
  shot "0${n}_sub$d" build/qa_field.sfc work/qa/../states/qa_field.mss "$r;6 a;60 -;6 a;60 -" 400
  n=$((n+1))
done
python -X utf8 build.py "$@" --out build/qa_shop.sfc --debug "$GIVE C8 00 0A 0A 0B BC 09 D1 01 FF" >/dev/null
python -X utf8 $SKILL/emu.py build/qa_shop.sfc --out work/qa/_s --route-str "$BOOT;500 -" --frames 2350 \
  --state-out work/states/qa_shop.mss >/dev/null
shot 10_shop build/qa_shop.sfc work/states/qa_shop.mss "30 -" 60
shot 11_shopbuy build/qa_shop.sfc work/states/qa_shop.mss "30 -;6 a;60 -" 120
shot 12_shopbuy2 build/qa_shop.sfc work/states/qa_shop.mss "30 -;6 a;60 -;6 a;60 -" 200
shot 13_shophelp build/qa_shop.sfc work/states/qa_shop.mss "30 -;6 down;10 -;6 down;10 -;6 down;10 -;6 a;60 -" 200
python -X utf8 build.py "$@" --out build/qa_battle.sfc \
  --debug "$GIVE C8 00 0A 0A 0B BC 09 D2 40 00 1C 80 3F FF" >/dev/null
python -X utf8 $SKILL/emu.py build/qa_battle.sfc --out work/qa/_s --route-str "$BOOT;650 -" --frames 2400 \
  --state-out work/states/qa_battle.mss >/dev/null
shot 20_battle build/qa_battle.sfc work/states/qa_battle.mss "30 -" 60
shot 21_battlecmd build/qa_battle.sfc work/states/qa_battle.mss "120 -;6 a;40 -" 200
python -X utf8 $SKILL/sheet.py "$OUT/*.png" --cols 4 --div 1 --out $OUT/sheet.png
python -X utf8 tools/jpscreen.py $OUT/*.log > $OUT/japanese.txt || true
echo "japanese left: $OUT/japanese.txt ($(grep -c '^  ' $OUT/japanese.txt) callers)"
