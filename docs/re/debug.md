# QA debug builds (never in a release)

`python -X utf8 build.py --out build/dbg_X.sfc --debug "HEX"`: script id 0 (runs right after "new game" on the title screen) is
redirected to the given event-script bytes at 3F:8000 (bank $3F is reserved for this). Boot route to reach it:
`--route-str "1100 -;6 start;200 -;6 start;200 -"` (script starts ~f1806).

Useful ops (tools/script_ops.py):
- `A4 lo hi` add money (A4 30 75 = 30000). `B5 xx` party join (seen: 1B 2B 3C 40 5B 6B 7B 8B AB 10 20 50). `A2 xx` give item (seen 11 19 3A 42-46 AB).
- `C8 map b x y` warp, then `BC 09` (fade in). `8F n` wait n frames. `FF` end (player gets control).
- `D2 lo hi PTR24` battle (seen ids 4000 497C 887B 937C 107D 507D ... ); PTR = where to continue (e.g. the FF after it).

Recipes:
- Battle: `A4 30 75 B5 1B B5 2B C8 00 0A 0A 0B BC 09 D2 40 00 14 80 3F FF` (battle starts ~f1920; mash A).
- Map tour: tools/lua/warpshot.lua + every warp from the scripts (work/maptour.hex) -> work/qa/maps3/w_<warp>.png. Warps `FF xx xx xx` are world maps (random battles); `xx xx 0C 05` are small rooms.
- Field menu: any map + X.
