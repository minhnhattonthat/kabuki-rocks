-- Log a WRAM range as hex at frame AT: "P <addr> <bytes>" (16 per line).
--   emu.py ROM ... --script tools/lua/peek.lua --var ADDR=0x7E5E85 --var LEN=96 --var AT=2300
local addr, len, at = assert(ADDR, "set --var ADDR=0x..."), LEN or 16, assert(AT, "set --var AT=<frame>")
L.on_frame(function(f)
  if f ~= at then return end
  for a = addr, addr + len - 1, 16 do
    local t = {}
    for i = a, math.min(a + 15, addr + len - 1) do t[#t + 1] = string.format("%02X", emu.read(i, emu.memType.snesMemory)) end
    L.log(string.format("P %06X %s", a, table.concat(t, " ")))
  end
end)
