"""Kabuki Rocks graphics codec (decompressor 00:8E1E).

Commands (c = control byte):
  FF n      zero fill n+0x20            E0-FE     zero fill (c&1F)+1
  C0-DF b   fill (c&1F)+2 copies of b    A0-BF ..  (c&1F)+1 bytes, each written as 00,b
  80-9F ..  (c&1F)+1 literal bytes       00-7F lo  copy (c>>2)+2 bytes from out[pos-0x400+((c&3)<<8|lo)]
Stops when the next two bytes are 7F FF, or the output reached the caller's size limit.
LZ source may lie before the output start (pos-0x400 < 0): the game reads whatever is in WRAM there,
so the compressor never emits such references.

    python -X utf8 tools/lz.py d ROM OFFSET SIZE OUT    # decompress
"""
import sys


def decompress(data, off, limit=0x10000):
    out = bytearray()
    i = off
    while True:
        c = data[i]
        if c == 0xFF:
            out += bytes(data[i + 1] + 0x20); i += 2
        elif c >= 0xE0:
            out += bytes((c & 0x1F) + 1); i += 1
        elif c >= 0xC0:
            out += bytes([data[i + 1]]) * ((c & 0x1F) + 2); i += 2
        elif c >= 0xA0:
            n = (c & 0x1F) + 1
            for b in data[i + 1:i + 1 + n]:
                out += bytes([0, b])
            i += 1 + n
        elif c >= 0x80:
            n = (c & 0x1F) + 1
            out += data[i + 1:i + 1 + n]; i += 1 + n
        else:
            n = (c >> 2) + 2
            src = len(out) - 0x400 + ((c & 3) << 8 | data[i + 1])
            if src < 0:
                raise ValueError(f"LZ ref before output start at {i:#x}")
            for k in range(n):
                out.append(out[src + k])
            i += 2
        if data[i:i + 2] == b"\x7f\xff":
            return bytes(out), i + 2 - off
        if len(out) >= limit:
            return bytes(out), i - off


def compress(raw):
    """Greedy encoder; always ends with 7F FF."""
    out = bytearray()
    lit = bytearray()

    def flush():
        while lit:
            chunk = lit[:32]; del lit[:32]
            out.append(0x80 | (len(chunk) - 1)); out.extend(chunk)

    pos = 0
    n = len(raw)
    while pos < n:
        best = (0, None)  # (gain-length, encoder)
        # zero run
        z = 0
        while pos + z < n and raw[pos + z] == 0 and z < 0x11F:
            z += 1
        if z >= 2:
            best = (z, "z")
        # byte run
        b = raw[pos]; r = 0
        while pos + r < n and raw[pos + r] == b and r < 33:
            r += 1
        if r >= 3 and r > best[0]:
            best = (r, "r")
        # LZ
        lo = max(0, pos - 0x400)
        bl, bs = 0, 0
        for s in range(lo, pos):
            k = 0
            while k < 33 and pos + k < n and raw[s + k] == raw[pos + k]:
                k += 1
            if k > bl:
                bl, bs = k, s
                if k == 33:
                    break
        if bl >= 3 and bl > best[0]:
            best = (bl, "lz")
        kind = best[1]
        if kind is None:
            lit.append(raw[pos]); pos += 1
            continue
        flush()
        if kind == "z":
            if z >= 32:  # E0|31 would be FF, the long form
                out += bytes([0xFF, z - 0x20])
            else:
                out.append(0xE0 | (z - 1))
            pos += z
        elif kind == "r":
            out += bytes([0xC0 | (r - 2), b]); pos += r
        else:
            d = bs - (pos - 0x400)
            out += bytes([((bl - 2) << 2) | (d >> 8), d & 0xFF]); pos += bl
    flush()
    out += b"\x7f\xff"
    return bytes(out)


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "d":
        rom = open(sys.argv[2], "rb").read()
        raw, used = decompress(rom, int(sys.argv[3], 16), int(sys.argv[4], 16))
        open(sys.argv[5], "wb").write(raw)
        print(f"{len(raw):#x} bytes from {used:#x} compressed")
    else:
        print(__doc__)
