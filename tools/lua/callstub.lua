-- Run code on the main thread once: at the first exec of HOOK (a routine the main loop calls, entered with JSL) from
-- frame AT on, write STUB (hex machine code, assembled for 7F:E100) there and divert the CPU to it. The stub must
-- end with JML HOOK so the routine then runs normally. Used by tools/qa_sysmsg.py.
--   emu.py ROM ... --script tools/lua/callstub.lua --var AT=2200 --var HOOK=0x008608 --var 'STUB="08c230...5c088600"'
local at, hook, base = assert(AT, "set --var AT"), HOOK or 0x008608, 0x7FE100
local done = false
L.on_exec(hook, hook, function()
  if done or L.frame < at then return end
  done = true
  local i = 0
  for h in string.gmatch(assert(STUB, "set --var STUB"), "%x%x") do
    emu.write(base + i, tonumber(h, 16), emu.memType.snesMemory)
    i = i + 1
  end
  local s = emu.getState()
  s["cpu.k"] = base >> 16
  s["cpu.pc"] = base & 0xFFFF
  emu.setState(s)
  L.log(string.format("stub %d bytes run at frame %d", i, L.frame))
end)
