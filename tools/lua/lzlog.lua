-- Log every call of the decompressor 00:8E1E: "Z <frame> src=<24-bit> dst=<24-bit> size=<n> ret=<caller>".
-- (Caller sets source $1C-$1E, destination $1F-$21, size $22 with DP = $0400.)
--   emu.py ROM ... --script tools/lua/lzlog.lua [--var FROM=1800]
local mem, from = emu.memType.snesMemory, FROM or 0
local function rd(a) return emu.read(a, mem) end
L.on_exec(0x008E1E, 0x008E1E, function()
  if L.frame < from then return end
  local sp = emu.getState()["cpu.sp"]
  local ret = rd(sp + 1) | rd(sp + 2) << 8 | rd(sp + 3) << 16
  L.log(string.format("Z %d src=%06X dst=%06X size=%04X ret=%06X", L.frame,
    rd(0x41E) << 16 | rd(0x41D) << 8 | rd(0x41C), rd(0x421) << 16 | rd(0x420) << 8 | rd(0x41F),
    rd(0x423) << 8 | rd(0x422), ret))
end)
