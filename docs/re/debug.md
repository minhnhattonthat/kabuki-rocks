# QA debug builds (never in a release)

`python -X utf8 build.py --out build/dbg_X.sfc --debug "HEX"`: script id 0 (runs right after "new game" on the title screen) is
redirected to the given event-script bytes at 3F:8000 (bank $3F is reserved for this). Boot route to reach it:
`--route-str "1100 -;6 start;200 -;6 start;200 -"` (script starts ~f1806).

Useful ops (tools/script_ops.py):
- `A4 lo hi` add money (A4 30 75 = 30000). `B5 xx` party join (seen: 1B 2B 3C 40 5B 6B 7B 8B AB 10 20 50). `A2 xx` item-related but does NOT fill the inventory (seen 11 19 3A 42-46 AB); `A0 xx PTR` jumps if item xx is owned. To own items, poke the inventory (7E:5E85, FF = empty) with tools/lua/poke.lua.
- `80 42` sets event flag $42 (enables the Song Weapon menu). Song weapons per member: 7E:51EB + member*$AB, 4 tabs
  x 24 ids. tools/qa_screens.sh pokes inventory, counts and songs.
- System messages (RAM scripts) can't be reached by a script jump; `python -X utf8 tools/qa_sysmsg.py` runs each
  through the game's own copy/run path with tools/lua/callstub.lua (main-thread stub in 7F:E100).
- `@` in the hex = the 3-byte address of the byte after it (a jump target that just continues), e.g. `D2 40 00 @ FF`.
- `C8 map b x y` warp, then `BC 09` (fade in). `8F n` wait n frames. `FF` end (player gets control).
- `D2 lo hi PTR24` battle (seen ids 4000 497C 887B 937C 107D 507D ... ); PTR = where to continue (e.g. the FF after it).

Recipes:
- Battle: `A4 30 75 B5 1B B5 2B C8 00 0A 0A 0B BC 09 D2 40 00 14 80 3F BC 09 FF` (battle starts ~f1920; mash A). The `BC 09` after the battle fades the field back in; without it the screen stays black after the rewards until the field menu redraws it (same in JP).
- Map tour: tools/lua/warpshot.lua + every warp from the scripts (work/maptour.hex) -> work/qa/maps3/w_<warp>.png. Warps `FF xx xx xx` are world maps (random battles); `xx xx 0C 05` are small rooms.
- Field menu: any map + X.

Scene tour (release gate): `python -X utf8 tools/debug/tour.py [name-prefix..] [--jp]` builds one debug ROM per row of
`tools/debug/scenes.tsv` (name, frames, mash, shot interval, start hex, route, sav, extra emu.py args) and writes
contact sheets to `work/qa/tour/<name>/` (`--jp`: the relocated-JP reference build, `work/qa/tour_jp/`). Rows cover
the intro, Continue, chapter cards 1-17, battle + rewards, game over (`D2 .. 99`: the loss path soft-resets),
credits, ending, save jizo, chest exchange (`E1 F2`), jizo map (`E1 F4`), composer, travel menu (callstub) and
the bank-$0F `D3 01-03` modes. Then `qa_gate.py init work/qa/manifest.tsv work/qa/tour` for the reviewers.
