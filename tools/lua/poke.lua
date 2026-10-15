-- Write bytes into memory at frame AT (e.g. fill the inventory 7E:5E85 for QA; FF = empty slot).
--   emu.py ROM ... --script tools/lua/poke.lua --var ADDR=0x7E5E85 --var 'BYTES="00 01 0C"' --var AT=2300
local addr, at = assert(ADDR, "set --var ADDR=0x..."), assert(AT, "set --var AT=<frame>")
L.on_frame(function(f)
  if f ~= at then return end
  local i = 0
  for h in string.gmatch(assert(BYTES, "set --var BYTES"), "%x%x") do
    emu.write(addr + i, tonumber(h, 16), emu.memType.snesMemory)
    i = i + 1
  end
  L.log(string.format("poked %d bytes at %06X", i, addr))
end)
