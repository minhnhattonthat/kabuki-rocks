-- Log the CPU's program counter and the return addresses on the stack every EVERY frames: where is the game stuck?
-- Lines: "PC <frame> <pc> stack: <6 bytes from SP+1>".
--   emu.py ROM ... --script tools/lua/pcsample.lua [--var EVERY=60]
local every = EVERY or 60
local mem = emu.memType.snesMemory
L.on_frame(function(f)
  if f % every ~= 0 then return end
  local s = emu.getState()
  local t = {}
  for i = 1, 6 do t[#t + 1] = string.format("%02X", emu.read(s["cpu.sp"] + i, mem)) end
  L.log(string.format("PC %d %02X%04X stack: %s", f, s["cpu.k"], s["cpu.pc"], table.concat(t, " ")))
end)
