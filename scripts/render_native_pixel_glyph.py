from __future__ import annotations

import argparse
import struct
from pathlib import Path


def read_tables(data: bytes) -> dict[str, tuple[int, int]]:
    count = struct.unpack_from(">H", data, 4)[0]
    tables = {}
    for index in range(count):
        pos = 12 + index * 16
        tag = data[pos : pos + 4].decode("latin1")
        _, offset, length = struct.unpack_from(">III", data, pos + 4)
        tables[tag] = (offset, length)
    return tables


def cmap_glyph_id(data: bytes, tables: dict[str, tuple[int, int]], codepoint: int) -> int:
    cmap, _ = tables["cmap"]
    count = struct.unpack_from(">H", data, cmap + 2)[0]
    subtables = []
    for index in range(count):
        platform, encoding, relative = struct.unpack_from(">HHI", data, cmap + 4 + index * 8)
        offset = cmap + relative
        fmt = struct.unpack_from(">H", data, offset)[0]
        subtables.append((fmt, platform, encoding, offset))

    for fmt, _, _, offset in sorted(subtables, key=lambda item: (item[0] != 12, item[0] != 4)):
        if fmt == 12:
            groups = struct.unpack_from(">I", data, offset + 12)[0]
            for index in range(groups):
                start, end, glyph = struct.unpack_from(">III", data, offset + 16 + index * 12)
                if start <= codepoint <= end:
                    return glyph + codepoint - start
        elif fmt == 4 and codepoint <= 0xFFFF:
            segments = struct.unpack_from(">H", data, offset + 6)[0] // 2
            end_pos = offset + 14
            start_pos = end_pos + segments * 2 + 2
            delta_pos = start_pos + segments * 2
            range_pos = delta_pos + segments * 2
            for index in range(segments):
                end = struct.unpack_from(">H", data, end_pos + index * 2)[0]
                start = struct.unpack_from(">H", data, start_pos + index * 2)[0]
                if not start <= codepoint <= end:
                    continue
                delta = struct.unpack_from(">h", data, delta_pos + index * 2)[0]
                range_offset = struct.unpack_from(">H", data, range_pos + index * 2)[0]
                if range_offset == 0:
                    return (codepoint + delta) & 0xFFFF
                glyph_pos = range_pos + index * 2 + range_offset + (codepoint - start) * 2
                glyph = struct.unpack_from(">H", data, glyph_pos)[0]
                return 0 if glyph == 0 else (glyph + delta) & 0xFFFF
    raise ValueError(f"character U+{codepoint:04X} is not in the font")


def glyph_contours(
    data: bytes, tables: dict[str, tuple[int, int]], glyph_id: int
) -> list[list[tuple[int, int]]]:
    head, _ = tables["head"]
    loca, _ = tables["loca"]
    glyf, _ = tables["glyf"]
    location_format = struct.unpack_from(">h", data, head + 50)[0]
    if location_format == 0:
        start = struct.unpack_from(">H", data, loca + glyph_id * 2)[0] * 2
    else:
        start = struct.unpack_from(">I", data, loca + glyph_id * 4)[0]
    pos = glyf + start
    contour_count = struct.unpack_from(">h", data, pos)[0]
    if contour_count < 0:
        raise ValueError("composite glyphs are not supported by this preview tool")

    end_points = list(struct.unpack_from(">" + "H" * contour_count, data, pos + 10))
    point_count = end_points[-1] + 1 if end_points else 0
    cursor = pos + 10 + contour_count * 2
    instruction_length = struct.unpack_from(">H", data, cursor)[0]
    cursor += 2 + instruction_length

    flags = []
    while len(flags) < point_count:
        flag = data[cursor]
        cursor += 1
        flags.append(flag)
        if flag & 0x08:
            repeat = data[cursor]
            cursor += 1
            flags.extend([flag] * repeat)
    if any(not flag & 0x01 for flag in flags):
        raise ValueError("off-curve points are not supported by this pixel-font preview tool")

    xs = []
    value = 0
    for flag in flags:
        if flag & 0x02:
            delta = data[cursor]
            cursor += 1
            value += delta if flag & 0x10 else -delta
        elif not flag & 0x10:
            value += struct.unpack_from(">h", data, cursor)[0]
            cursor += 2
        xs.append(value)

    ys = []
    value = 0
    for flag in flags:
        if flag & 0x04:
            delta = data[cursor]
            cursor += 1
            value += delta if flag & 0x20 else -delta
        elif not flag & 0x20:
            value += struct.unpack_from(">h", data, cursor)[0]
            cursor += 2
        ys.append(value)

    points = list(zip(xs, ys))
    contours = []
    first = 0
    for end in end_points:
        contours.append(points[first : end + 1])
        first = end + 1
    return contours


def winding_number(x: float, y: float, polygon: list[tuple[int, int]]) -> int:
    winding = 0
    for index, (x1, y1) in enumerate(polygon):
        x2, y2 = polygon[(index + 1) % len(polygon)]
        cross = (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)
        if y1 <= y < y2 and cross > 0:
            winding += 1
        elif y2 <= y < y1 and cross < 0:
            winding -= 1
    return winding


def rasterize(contours: list[list[tuple[int, int]]], units_per_em: int, top: int) -> bytes:
    step = units_per_em / 8
    rows = []
    for row in range(8):
        value = 0
        y = top - (row + 0.5) * step
        for col in range(8):
            x = (col + 0.5) * step
            if sum(winding_number(x, y, contour) for contour in contours) != 0:
                value |= 1 << (7 - col)
        rows.append(value)
    return bytes(rows)


def write_preview(path: Path, glyph: bytes, scale: int = 64) -> None:
    width = height = 8 * scale
    stride = (width * 3 + 3) & ~3
    pixels = bytearray()
    for y in range(height - 1, -1, -1):
        cell_y = y // scale
        for x in range(width):
            cell_x = x // scale
            filled = bool(glyph[cell_y] & (1 << (7 - cell_x)))
            grid = x % scale == 0 or y % scale == 0
            if grid:
                color = (180, 180, 180)
            elif filled:
                color = (0, 0, 0)
            else:
                color = (255, 255, 255)
            pixels.extend(color)
        pixels.extend(b"\x00" * (stride - width * 3))

    header_size = 14 + 40
    file_size = header_size + len(pixels)
    header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, header_size)
    dib = struct.pack("<IIIHHIIIIII", 40, width, height, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + dib + pixels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("font", type=Path)
    parser.add_argument("character")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    if len(args.character) != 1:
        raise SystemExit("character must contain exactly one Unicode character")
    data = args.font.read_bytes()
    tables = read_tables(data)
    head, _ = tables["head"]
    os2, _ = tables["OS/2"]
    units_per_em = struct.unpack_from(">H", data, head + 18)[0]
    typo_ascent = struct.unpack_from(">h", data, os2 + 68)[0]
    glyph_id = cmap_glyph_id(data, tables, ord(args.character))
    contours = glyph_contours(data, tables, glyph_id)
    glyph = rasterize(contours, units_per_em, typo_ascent)
    write_preview(args.output, glyph)

    print(f"font={args.font.resolve()}")
    print(f"character={args.character} U+{ord(args.character):04X}")
    print(f"glyph_id={glyph_id}")
    print(f"units_per_em={units_per_em} native_ppem=8 body_pixels=7")
    print(f"bytes={glyph.hex(' ').upper()}")
    for value in glyph:
        print("".join("#" if value & (1 << (7 - col)) else "." for col in range(8)))
    print(f"preview={args.output.resolve()}")


if __name__ == "__main__":
    main()
