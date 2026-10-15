-- Log executed instructions in a CPU range (default bank $3E): "T <frame> <pc> A X Y P DB SP", first LIMIT lines.
--   emu.py ROM ... --script tools/lua/trace.lua [--var LO=0x3E8000 --var HI=0x3EFFFF --var LIMIT=3000]
local lo, hi, limit, n = LO or 0x3E8000, HI or 0x3EFFFF, LIMIT or 3000, 0
L.on_exec(lo, hi, function()
  if n >= limit then return end
  n = n + 1
  local s = emu.getState()
  L.log(string.format("T %d %06X A=%04X X=%04X Y=%04X P=%02X DB=%02X SP=%04X", L.frame, s["cpu.k"] << 16 | s["cpu.pc"],
    s["cpu.a"], s["cpu.x"], s["cpu.y"], s["cpu.ps"], s["cpu.dbr"], s["cpu.sp"]))
end)
