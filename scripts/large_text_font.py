from __future__ import annotations

import struct
from pathlib import Path

from render_native_pixel_glyph import (
    cmap_glyph_id,
    glyph_contours,
    read_tables,
    winding_number,
)


WORKSPACE = Path(__file__).resolve().parents[1]
FONT_PATH = WORKSPACE / "fonts" / "zpix.ttf"

UNITS_PER_EM = 1200
ASCENT = 1000
DESCENT = -200
GRID_UNITS = 100
GLYPH_SIZE = 12


def validate_contours(char: str, contours: list[list[tuple[int, int]]]) -> None:
    points = [point for contour in contours for point in contour]
    if not points:
        raise ValueError(f"empty glyph U+{ord(char):04X}")
    if any(x % GRID_UNITS or y % GRID_UNITS for x, y in points):
        raise ValueError(f"off-grid zpix outline U+{ord(char):04X}")
    min_x = min(x for x, _ in points)
    max_x = max(x for x, _ in points)
    min_y = min(y for _, y in points)
    max_y = max(y for _, y in points)
    if min_x < 0 or max_x > UNITS_PER_EM:
        raise ValueError(f"horizontal clipping risk U+{ord(char):04X}: {min_x}..{max_x}")
    if min_y < DESCENT or max_y > ASCENT:
        raise ValueError(f"vertical clipping risk U+{ord(char):04X}: {min_y}..{max_y}")


def rasterize(contours: list[list[tuple[int, int]]]) -> tuple[int, ...]:
    rows = []
    for row in range(GLYPH_SIZE):
        value = 0
        y = ASCENT - (row + 0.5) * GRID_UNITS
        for col in range(GLYPH_SIZE):
            x = (col + 0.5) * GRID_UNITS
            if sum(winding_number(x, y, contour) for contour in contours) != 0:
                value |= 1 << (GLYPH_SIZE - 1 - col)
        rows.append(value)
    return tuple(rows)


def bitmap_bounds(bitmap: tuple[int, ...]) -> tuple[int, int, int, int]:
    pixels = [
        (col, row)
        for row, value in enumerate(bitmap)
        for col in range(GLYPH_SIZE)
        if value & (1 << (GLYPH_SIZE - 1 - col))
    ]
    return (
        min(col for col, _ in pixels),
        max(col for col, _ in pixels),
        min(row for _, row in pixels),
        max(row for _, row in pixels),
    )


def load_glyphs(
    characters: list[str],
) -> tuple[dict[str, tuple[int, ...]], dict[str, int], list[dict[str, object]]]:
    font_data = FONT_PATH.read_bytes()
    tables = read_tables(font_data)
    head, _ = tables["head"]
    hhea, _ = tables["hhea"]
    hmtx, _ = tables["hmtx"]
    units_per_em = struct.unpack_from(">H", font_data, head + 18)[0]
    ascent, descent = struct.unpack_from(">hh", font_data, hhea + 4)
    horizontal_metrics = struct.unpack_from(">H", font_data, hhea + 34)[0]
    if (units_per_em, ascent, descent) != (UNITS_PER_EM, ASCENT, DESCENT):
        raise ValueError(
            f"unexpected zpix metrics: upm={units_per_em} ascent={ascent} descent={descent}"
        )

    glyphs: dict[str, tuple[int, ...]] = {}
    advances: dict[str, int] = {}
    metric_rows: list[dict[str, object]] = []
    for index, char in enumerate(characters):
        glyph_id = cmap_glyph_id(font_data, tables, ord(char))
        if glyph_id == 0:
            raise ValueError(f"missing glyph U+{ord(char):04X}")
        contours = glyph_contours(font_data, tables, glyph_id)
        validate_contours(char, contours)
        bitmap = rasterize(contours)
        min_x, max_x, min_y, max_y = bitmap_bounds(bitmap)
        metric_id = min(glyph_id, horizontal_metrics - 1)
        advance_units = struct.unpack_from(">H", font_data, hmtx + metric_id * 4)[0]
        if advance_units % GRID_UNITS:
            raise ValueError(f"off-grid advance U+{ord(char):04X}: {advance_units}")
        font_advance = advance_units // GRID_UNITS
        advance = font_advance if char.isascii() else GLYPH_SIZE
        glyphs[char] = bitmap
        advances[char] = advance
        metric_rows.append(
            {
                "index": index,
                "char": char,
                "unicode": f"U+{ord(char):04X}",
                "font_advance_pixels": font_advance,
                "packed_advance_pixels": advance,
                "ink_width": max_x - min_x + 1,
                "ink_height": max_y - min_y + 1,
                "min_x": min_x,
                "max_x": max_x,
                "min_y": min_y,
                "max_y": max_y,
                "rows_hex": " ".join(f"{value:03X}" for value in bitmap),
            }
        )

    space_id = cmap_glyph_id(font_data, tables, ord(" "))
    metric_id = min(space_id, horizontal_metrics - 1)
    space_units = struct.unpack_from(">H", font_data, hmtx + metric_id * 4)[0]
    advances[" "] = space_units // GRID_UNITS
    return glyphs, advances, metric_rows


def text_width(text: str, advances: dict[str, int]) -> int:
    return sum(advances[char] for char in text)
