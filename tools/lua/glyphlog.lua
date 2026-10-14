-- Log every glyph code handed to 00:BA9D (glyph -> tile words) with the caller's return address.
-- Lines: "G <frame> <code> <caller 24-bit>". Use with a short window; decode with tbl/jp.tbl + tools/text.py.
--   emu.py ROM ... --script tools/lua/glyphlog.lua [--var FROM=30 --var TO=150]
local mem = emu.memType.snesMemory
local from, to = FROM or 0, TO or math.huge
L.on_exec(0x00BA9D, 0x00BA9D, function()
  if L.frame < from or L.frame > to then return end
  local s = emu.getState()
  local sp = s["cpu.sp"]
  local ret = emu.read(sp + 1, mem) | emu.read(sp + 2, mem) << 8 | emu.read(sp + 3, mem) << 16
  L.log(string.format("G %d %04X %06X", L.frame, s["cpu.a"] & 0xFFFF, ret))
end)
