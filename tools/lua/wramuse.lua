-- Which WRAM is never written after boot? Marks 64-byte blocks of $7E2000-$7FFFFF written from frame FROM on;
-- at frame TO logs the untouched runs of at least 512 bytes ("free LO-HI SIZE"). Pass --frames > TO.
--   emu.py ROM ... --script tools/lua/wramuse.lua --var FROM=1000 --var TO=8000
local from, to = FROM or 1000, assert(TO, "set --var TO=<frame>")
local hit = {}
L.on_write(0x7E2000, 0x7FFFFF, function(addr)
  if L.frame >= from then hit[(addr & 0x1FFFF) >> 6] = true end
end)
L.on_frame(function(f)
  if f ~= to then return end
  local start
  for b = 0x2000 >> 6, (0x20000 >> 6) do
    if b < (0x20000 >> 6) and not hit[b] then
      start = start or b
    elseif start then
      if (b - start) * 64 >= 512 then
        L.log(string.format("free %06X-%06X %d", 0x7E0000 + start * 64, 0x7E0000 + b * 64 - 1, (b - start) * 64))
      end
      start = nil
    end
  end
end)
