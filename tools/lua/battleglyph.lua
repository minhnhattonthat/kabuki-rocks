-- Log glyph codes handed to the battle text routine 02:F08F with the caller's return address
-- ("B <frame> <code> <ret>"), to find where battle text fragments come from.
--   emu.py ROM ... --script tools/lua/battleglyph.lua [--var FROM=1900 --var TO=3600]
local mem = emu.memType.snesMemory
local from, to = FROM or 0, TO or math.huge
L.on_exec(0x02F08F, 0x02F08F, function()
  if L.frame < from or L.frame > to then return end
  local s = emu.getState()
  local sp = s["cpu.sp"]
  local ret = emu.read(sp + 1, mem) | emu.read(sp + 2, mem) << 8 | emu.read(sp + 3, mem) << 16
  L.log(string.format("B %d %04X %06X X=%04X Y=%04X DB=%02X", L.frame, s["cpu.a"] & 0xFFFF, ret, s["cpu.x"], s["cpu.y"], s["cpu.dbr"]))
end)
