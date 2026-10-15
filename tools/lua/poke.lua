-- Write bytes into memory at frame AT, for QA set-ups: POKES = "ADDR:HEX;ADDR:HEX..." (24-bit hex address, bytes).
--   inventory 7E:5E85 (item ids, FF = empty); Rock's song weapons 7E:51EB (song ids, FF = empty; next member +$AB)
--   emu.py ROM ... --script tools/lua/poke.lua --var 'POKES="7E5E85:00010C;7E51EB:000102"' --var AT=2300
local at = assert(AT, "set --var AT=<frame>")
L.on_frame(function(f)
  if f ~= at then return end
  for addr, hex in string.gmatch(assert(POKES, "set --var POKES"), "(%x+):(%x+)") do
    local a, i = tonumber(addr, 16), 0
    for h in string.gmatch(hex, "%x%x") do
      emu.write(a + i, tonumber(h, 16), emu.memType.snesMemory)
      i = i + 1
    end
    L.log(string.format("poked %d bytes at %06X", i, a))
  end
end)
