from __future__ import annotations

import argparse
import csv
import struct
from pathlib import Path

from render_native_pixel_glyph import (
    cmap_glyph_id,
    glyph_contours,
    rasterize,
    read_tables,
)


def is_cjk(char: str) -> bool:
    codepoint = ord(char)
    return 0x3400 <= codepoint <= 0x9FFF or 0xF900 <= codepoint <= 0xFAFF


def load_characters(path: Path) -> list[str]:
    characters = []
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            for char in row["text"]:
                if is_cjk(char) and char not in characters:
                    characters.append(char)
    return characters


def write_grid_preview(path: Path, glyphs: list[tuple[str, bytes]]) -> None:
    scale = 8
    padding = 4
    cell = 8 * scale + padding * 2
    columns = 10
    rows = (len(glyphs) + columns - 1) // columns
    width = columns * cell + 1
    height = rows * cell + 1
    stride = (width * 3 + 3) & ~3
    canvas = [[(255, 255, 255) for _ in range(width)] for _ in range(height)]

    for index, (_, glyph) in enumerate(glyphs):
        cell_x = (index % columns) * cell
        cell_y = (index // columns) * cell
        for x in range(cell_x, cell_x + cell + 1):
            if x < width:
                canvas[cell_y][x] = (190, 190, 190)
                if cell_y + cell < height:
                    canvas[cell_y + cell][x] = (190, 190, 190)
        for y in range(cell_y, cell_y + cell + 1):
            if y < height:
                canvas[y][cell_x] = (190, 190, 190)
                if cell_x + cell < width:
                    canvas[y][cell_x + cell] = (190, 190, 190)
        for row in range(8):
            for col in range(8):
                if not glyph[row] & (1 << (7 - col)):
                    continue
                start_x = cell_x + padding + col * scale
                start_y = cell_y + padding + row * scale
                for y in range(start_y, start_y + scale):
                    for x in range(start_x, start_x + scale):
                        canvas[y][x] = (0, 0, 0)

    pixels = bytearray()
    for row in reversed(canvas):
        for red, green, blue in row:
            pixels.extend((blue, green, red))
        pixels.extend(b"\x00" * (stride - width * 3))
    header_size = 14 + 40
    header = struct.pack("<2sIHHI", b"BM", header_size + len(pixels), 0, 0, header_size)
    dib = struct.pack("<IIIHHIIIIII", 40, width, height, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + dib + pixels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("font", type=Path)
    parser.add_argument("layout_csv", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()

    font_data = args.font.read_bytes()
    tables = read_tables(font_data)
    head, _ = tables["head"]
    os2, _ = tables["OS/2"]
    units_per_em = struct.unpack_from(">H", font_data, head + 18)[0]
    typo_ascent = struct.unpack_from(">h", font_data, os2 + 68)[0]
    characters = load_characters(args.layout_csv)

    glyphs = []
    for char in characters:
        glyph_id = cmap_glyph_id(font_data, tables, ord(char))
        if glyph_id == 0:
            raise ValueError(f"missing glyph U+{ord(char):04X}")
        contours = glyph_contours(font_data, tables, glyph_id)
        glyphs.append((char, rasterize(contours, units_per_em, typo_ascent)))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    binary_path = args.out_dir / "small_font_glyphs.bin"
    csv_path = args.out_dir / "small_font_glyphs.csv"
    preview_path = args.out_dir / "small_font_glyphs.bmp"
    binary_path.write_bytes(b"".join(glyph for _, glyph in glyphs))
    with csv_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["index", "char", "unicode", "bytes_hex"])
        writer.writeheader()
        for index, (char, glyph) in enumerate(glyphs):
            writer.writerow(
                {
                    "index": index,
                    "char": char,
                    "unicode": f"U+{ord(char):04X}",
                    "bytes_hex": glyph.hex(" ").upper(),
                }
            )
    write_grid_preview(preview_path, glyphs)

    print(f"font={args.font.resolve()}")
    print(f"layout={args.layout_csv.resolve()}")
    print(f"glyphs={len(glyphs)}")
    print(f"missing=0")
    print(f"bin={binary_path.resolve()}")
    print(f"csv={csv_path.resolve()}")
    print(f"preview={preview_path.resolve()}")


if __name__ == "__main__":
    main()
