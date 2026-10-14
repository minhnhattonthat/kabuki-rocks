-- Screenshot each map an event-script warp (op C8) lands on: w_<map><b><x><y>.png, DELAY frames after the warp op.
--   emu.py ROM ... --script tools/lua/warpshot.lua [--var DELAY=120]
local mem = emu.memType.snesMemory
local delay = DELAY or 120
local pending = {}
local function rd(a) return emu.read(a, mem) end
L.on_exec(0x03805B, 0x03805B, function()
  local base = rd(0x0827) | rd(0x0828) << 8
  local off = rd(0x082A) | rd(0x082B) << 8
  local p = rd(0x0829) << 16 | ((base + off) & 0xFFFF)
  if rd(p) == 0xC8 then
    local name = string.format("w_%02X%02X%02X%02X", rd(p + 1), rd(p + 2), rd(p + 3), rd(p + 4))
    pending[#pending + 1] = { L.frame + delay, name }
  end
end)
L.on_frame(function(f)
  for i = #pending, 1, -1 do
    if pending[i][1] == f then
      L.shot(pending[i][2] .. ".png")
      table.remove(pending, i)
    end
  end
end)
