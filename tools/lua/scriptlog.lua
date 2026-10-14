-- Log every event-script opcode dispatch (03:805B) and text-printer entry (03:9201).
-- Lines: "S <frame> <cpu addr> <op>" and "T <frame> <cpu addr>". Script pointer = $0827-$0829 + $082A.
--   emu.py ROM ... --script tools/lua/scriptlog.lua
local mem = emu.memType.snesMemory
local function rd(a) return emu.read(a, mem) end
local function cur()
  local base = rd(0x0827) | rd(0x0828) << 8
  local off = rd(0x082A) | rd(0x082B) << 8
  return rd(0x0829) << 16 | ((base + off) & 0xFFFF)
end
L.on_exec(0x03805B, 0x03805B, function()
  local p = cur()
  L.log(string.format("S %d %06X %02X", L.frame, p, rd(p)))
end)
L.on_exec(0x039201, 0x039201, function()
  L.log(string.format("T %d %06X", L.frame, cur()))
end)
