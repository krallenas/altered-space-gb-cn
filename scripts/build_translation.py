from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from small_text_builder import build_small_text_rom
from large_text_font import load_glyphs, text_width


WORKSPACE = Path(__file__).resolve().parents[1]
OUTPUT_ROM = WORKSPACE / "Altered Space - A 3-D Alien Adventure (USA).zh.gb"
LAYOUT_CSV = WORKSPACE / "text" / "large_text_layout.csv"

EXPECTED_SMALL_TEXT_BASE_SHA256 = "9C4023E8957BEABC42F5668D0826B2E99F3103A185E31A51C0D3207CC45FDF78"

BANK8_FILE_OFFSET = 0x20000
FONT_PAGE_BASE = 0x4200
FULL_STUB_ADDR = 0x00DC

PAGE_IDS = {
    "ending": 0,
    "access": 1,
    "no_items": 2,
    "desc_humphrey": 3,
    "desc_zaks": 4,
    "desc_droid1": 5,
    "desc_droid9": 6,
    "desc_garffs": 7,
    "stage": 8,
    "initials": 9,
}
PAGE_STORAGE = {"item_status": "no_items"}

SCRIPT_IDS = {
    "stage": 0x10,
    "access": 0x11,
    "desc_humphrey": 0x12,
    "desc_zaks": 0x13,
    "desc_droid1": 0x14,
    "desc_droid9": 0x15,
    "desc_garffs": 0x16,
    "ending": 0x17,
}
SCRIPT_REGIONS = {
    "stage": (0x00B2FC, 0x00B3A0),
    "access": (0x00B5D5, 0x00B634),
    "desc_humphrey": (0x00BD76, 0x00BD98),
    "desc_zaks": (0x00BD98, 0x00BDB3),
    "desc_droid1": (0x00BDB3, 0x00BDD8),
    "desc_droid9": (0x00BDD8, 0x00BDFB),
    "desc_garffs": (0x00BDFB, 0x00BE18),
    "ending": (0x00ADA4, 0x00AEBC),
}
SCRIPT_ADDRS = {
    "stage": 0x6000,
    "access": 0x6200,
    "desc_humphrey": 0x6300,
    "desc_zaks": 0x6380,
    "desc_droid1": 0x6400,
    "desc_droid9": 0x6480,
    "desc_garffs": 0x6500,
    "ending": 0x6800,
}
NO_ITEMS_REGION = (0x0179B6, 0x0179E3)
DESC_PAGES = {
    "desc_humphrey",
    "desc_zaks",
    "desc_droid1",
    "desc_droid9",
    "desc_garffs",
}
BANK_SCRIPT_REGIONS = {
    "stage": (0x6000, 0x6200),
    "access": (0x6200, 0x6300),
    "desc_humphrey": (0x6300, 0x6380),
    "desc_zaks": (0x6380, 0x6400),
    "desc_droid1": (0x6400, 0x6480),
    "desc_droid9": (0x6480, 0x6500),
    "desc_garffs": (0x6500, 0x6600),
    "ending": (0x6800, 0x6900),
    "initials": (0x6B00, 0x6C00),
}

OXYGEN_SELECTOR = 0x19
ITEM_SELECTOR = 0x1A
ALL_ITEMS_SELECTOR = 0x1B
INITIALS_SELECTOR = 0x1C
STATUS_BAR_DATA_ADDR = 0x6FA0
ALL_ITEMS_ROUTINE_ADDR = 0x7040
OXYGEN_SCRIPT_ADDR = 0x7100
ITEM_ROUTINE_BASE = 0x7200
ITEM_ROUTINE_END = 0x7800
INITIALS_SCRIPT_ADDR = 0x6B00

EXTENDED_LOADER_ADDRS = {
    "ending": 0x4180,
    "item_status": 0x41A0,
    "stage": 0x41C0,
    "initials": 0x41E0,
}
HIGH_DATA_ADDRS = {
    "stage": 0x5A00,
    "access": 0x5600,
    "ending": 0x5D00,
    "initials": 0x6A00,
    "item_status": 0x7800,
}
HIGH_RANGES = {
    "stage": list(range(0xA7, 0x100)),
    "access": list(range(0x46, 0x80)),
    "ending": list(range(0xA8, 0x100)),
    "initials": list(range(0x40, 0x80)),
    "item_status": list(range(0x80, 0x100)),
}

ACCESS_GRAPHICS_RANGE = range(0x30, 0x46)
ACCESS_PRESERVED_CODES = {0x00, *range(0x02, 0x0A), 0x1E, 0x1F, 0x23, 0x29}
ITEM_GRAPHICS_CODES = {0x28, 0x29, *range(0x30, 0x80)}
ENDING_GRAPHICS_CODES = set(range(0x30, 0xA8))
INITIALS_GRAPHICS_CODES = set(range(0x30, 0x40))

ENDING_GAP_EXTRAS = {
    "story_2": (1, 1, 1, 1, 2, 2, 1, 1, 1, 1),
    "story_3": (2, 2, 1, 1, 1, 1, 1, 1, 1, 1),
}

STAGE_SCROLL_ALIGNMENT_OFFSET = 0x00B2C2
ITEM_RENDERER_REGION = (0x017A56, 0x017A81)
OXYGEN_INLINE_REGION = (0x017ABB, 0x017AC1)
STATUS_WINDOW_Y_OFFSET = 0x017AC9
STATUS_DYNAMIC_REGION = (0x017AD4, 0x017AF2)
ITEM_GRAPHICS_SOURCE_REGIONS = (
    (0x0176C0, 0x0176E0),
    (0x017B11, 0x017B16),
)
ENDING_GRAPHICS_LOAD_REGION = (0x00AC1C, 0x00AC28)
ENDING_PRELOAD_GRAPHICS_LOAD_REGION = (0x00B27C, 0x00B288)
CREDITS_GRAPHICS_LOAD_REGION = (0x002C35, 0x002C4C)
INITIALS_PROMPT_REGION = (0x00043B, 0x00045A)

ITEM_PAIRS = (
    ("particle", "disruptor"),
    ("computer", "interface"),
    ("stun_gun", "stun_gun_hint"),
    ("key",),
    ("circuit", "jammer"),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def bank8_offset(address: int) -> int:
    if not 0x4000 <= address < 0x8000:
        raise ValueError(f"bank 8 address out of range: 0x{address:04X}")
    return BANK8_FILE_OFFSET + address - 0x4000


def u16(value: int) -> list[int]:
    return [value & 0xFF, value >> 8]


def encode_tile_run(script: bytearray, tile_ids: list[int], current_base: int) -> int:
    for tile_id in tile_ids:
        base = 0x00 if tile_id < 0x80 else 0x80
        if base != current_base:
            script.extend([0x86, base])
            current_base = base
        code = tile_id - base
        if not 0 <= code < 0x80:
            raise ValueError(f"tile 0x{tile_id:02X} cannot be encoded")
        script.append(code)
    return current_base


def fix_header_checksum(rom: bytearray) -> int:
    checksum = 0
    for value in rom[0x0134:0x014D]:
        checksum = (checksum - value - 1) & 0xFF
    rom[0x014D] = checksum
    return checksum


def fix_global_checksum(rom: bytearray) -> int:
    rom[0x014E] = 0
    rom[0x014F] = 0
    checksum = sum(rom) & 0xFFFF
    rom[0x014E] = checksum >> 8
    rom[0x014F] = checksum & 0xFF
    return checksum


def storage_page(page: str) -> str:
    return PAGE_STORAGE.get(page, page)


def load_layout() -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    with LAYOUT_CSV.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            grouped.setdefault(row["page"], []).append(row)
    return grouped


def ordered_characters(layout: dict[str, list[dict[str, str]]]) -> list[str]:
    characters: list[str] = []
    for rows in layout.values():
        for row in rows:
            for char in row["text"]:
                if char.isspace() or char in characters:
                    continue
                characters.append(char)
    return characters


def page_limit(page: str) -> int:
    return 0x25 if storage_page(page) in DESC_PAGES else 0x30


def page_source_offset(page: str) -> int:
    stored = storage_page(page)
    address = FONT_PAGE_BASE + PAGE_IDS[stored] * 0x200
    return bank8_offset(address)


def preserved_codes(page: str) -> set[int]:
    if page == "access":
        return ACCESS_PRESERVED_CODES
    if page == "initials":
        return set(range(0x30))
    return {0x00}


def low_ranges(page: str) -> list[int]:
    preserved = preserved_codes(page)
    result = [code for code in range(1, page_limit(page)) if code not in preserved]
    if page == "item_status":
        result = [code for code in result if code not in {0x28, 0x29}]
    return result


def clear_unused_low_tiles(rom: bytearray, page: str) -> None:
    source = page_source_offset(page)
    keep = preserved_codes(page)
    for code in range(page_limit(page)):
        if code in keep:
            continue
        start = source + code * 8
        rom[start : start + 8] = bytes(8)


def fixed_tiles(phase2: bytes, page: str) -> dict[bytes, int]:
    source = page_source_offset(page)
    result = {bytes(8): 0}
    for code in sorted(preserved_codes(page)):
        tile = phase2[source + code * 8 : source + (code + 1) * 8]
        result.setdefault(tile, code)
    return result


def render_line_patterns(
    row: dict[str, str],
    glyphs: dict[str, tuple[int, ...]],
    advances: dict[str, int],
) -> dict[str, object]:
    text = row["text"]
    natural_width = text_width(text, advances)
    width = 144 if row["page"] == "ending" else natural_width
    if width < natural_width:
        raise ValueError(f"target width is too small for {row['page']}/{row['entry']}")
    center_left = int(row["center_left"], 0)
    center_width = int(row["center_width"], 0)
    pixel_x = center_left + (center_width - width) // 2 + int(row["x_adjust"], 0)
    pixel_y = int(row["y_pixel"], 0)
    first_x = pixel_x // 8
    last_x = (pixel_x + width - 1) // 8
    first_y = pixel_y // 8
    last_y = (pixel_y + 11) // 8
    canvas = [[False] * 160 for _ in range(256)]
    extra_width = width - natural_width
    gap_count = len(text) - 1
    cursor = pixel_x
    for index, char in enumerate(text):
        if not char.isspace():
            bitmap = glyphs[char]
            for glyph_y, value in enumerate(bitmap):
                for glyph_x in range(12):
                    if value & (1 << (11 - glyph_x)):
                        canvas[pixel_y + glyph_y][cursor + glyph_x] = True
        cursor += advances[char]
        if index < gap_count:
            custom_extras = ENDING_GAP_EXTRAS.get(row["entry"])
            if custom_extras is not None:
                if len(custom_extras) != gap_count or sum(custom_extras) != extra_width:
                    raise ValueError(f"invalid ending spacing for {row['entry']}")
                cursor += custom_extras[index]
            else:
                before = index * extra_width // gap_count
                after = (index + 1) * extra_width // gap_count
                cursor += after - before

    patterns: list[list[bytes]] = []
    for tile_y in range(first_y, last_y + 1):
        tile_row = []
        for tile_x in range(first_x, last_x + 1):
            values = []
            for row_y in range(8):
                value = 0
                for col_x in range(8):
                    if canvas[tile_y * 8 + row_y][tile_x * 8 + col_x]:
                        value |= 1 << (7 - col_x)
                values.append(value)
            tile_row.append(bytes(values))
        patterns.append(tile_row)
    return {
        "entry": row["entry"],
        "text": text,
        "pixel_x": pixel_x,
        "pixel_y": pixel_y,
        "width": width,
        "first_x": first_x,
        "first_y": first_y,
        "patterns": patterns,
    }


def allocate_page(
    phase2: bytes,
    page: str,
    lines: list[dict[str, object]],
) -> tuple[dict[int, bytes], list[dict[str, object]]]:
    bytes_to_id = fixed_tiles(phase2, page)
    available = low_ranges(page) + HIGH_RANGES.get(page, [])
    tile_bytes: dict[int, bytes] = {}
    encoded_lines = []
    for line in lines:
        encoded_rows: list[list[int]] = []
        for pattern_row in line["patterns"]:
            encoded_row = []
            for pattern in pattern_row:
                if pattern not in bytes_to_id:
                    if not available:
                        raise ValueError(f"{page}: packed 12px lines exceed tile capacity")
                    tile_id = available.pop(0)
                    bytes_to_id[pattern] = tile_id
                    tile_bytes[tile_id] = pattern
                encoded_row.append(bytes_to_id[pattern])
            encoded_rows.append(encoded_row)
        encoded_lines.append({**line, "tile_ids": encoded_rows})
    return tile_bytes, encoded_lines


def write_low_tiles(rom: bytearray, page: str, tiles: dict[int, bytes]) -> None:
    source = page_source_offset(page)
    for tile_id, tile in tiles.items():
        if tile_id >= page_limit(page):
            continue
        start = source + tile_id * 8
        rom[start : start + 8] = tile


def write_tile_data_block(
    rom: bytearray,
    page: str,
    tiles: dict[int, bytes],
    tile_ids: list[int],
) -> tuple[int, int, int]:
    if not tile_ids:
        raise ValueError(f"{page}: expected tile data")
    first = tile_ids[0]
    if tile_ids != list(range(first, tile_ids[-1] + 1)):
        raise ValueError(f"{page}: temporary tile allocation must be contiguous")
    data = b"".join(tiles[tile_id] for tile_id in tile_ids)
    source = HIGH_DATA_ADDRS[page]
    start = bank8_offset(source)
    rom[start : start + len(data)] = data
    return source, first, len(tile_ids)


def write_high_tiles(
    rom: bytearray, page: str, tiles: dict[int, bytes]
) -> tuple[int, int, int]:
    high_ids = sorted(tile_id for tile_id in tiles if tile_id >= page_limit(page))
    return write_tile_data_block(rom, page, tiles, high_ids)


def copy_sequence(source: int, destination: int, byte_count: int) -> bytes:
    return bytes(
        [
            0x21,
            *u16(source),
            0x11,
            *u16(destination),
            0x01,
            *u16(byte_count),
            0xCD,
            0x09,
            0x2C,
        ]
    )


def copy_raw_sequence(source: int, destination: int, byte_count: int) -> bytes:
    return bytes(
        [
            0x21,
            *u16(source),
            0x11,
            *u16(destination),
            0x01,
            *u16(byte_count),
            0xCD,
            0x4E,
            0x07,
        ]
    )


def patch_extended_loader(
    rom: bytearray,
    page: str,
    high_source: int,
    first_tile: int,
    tile_count: int,
) -> None:
    if tile_count <= 0:
        raise ValueError(f"{page}: expected high tile data")
    stored = storage_page(page)
    low_source = FONT_PAGE_BASE + PAGE_IDS[stored] * 0x200
    low_bytes = page_limit(page) * 16
    routine = bytearray(copy_sequence(low_source, 0x8000, low_bytes))
    routine.extend(
        copy_sequence(
            high_source,
            0x8000 + first_tile * 16,
            tile_count * 16,
        )
    )
    routine.extend([0x11, 0x00, 0x83, 0x01, 0x00, 0x00, 0xC9])
    address = EXTENDED_LOADER_ADDRS[page]
    if len(routine) > 0x20:
        raise ValueError(f"extended loader too large for {page}")
    start = bank8_offset(address)
    rom[start : start + 0x20] = routine + bytes([0xFF] * (0x20 - len(routine)))

    slot_address = 0x4040 + PAGE_IDS[stored] * 0x0D
    slot = bank8_offset(slot_address)
    rom[slot : slot + 0x0D] = bytes([0xC3, *u16(address)]) + bytes([0xFF] * 10)


def make_packed_script(
    lines: list[dict[str, object]],
    map_selector: int = 0,
    final_position: tuple[int, int] | None = None,
) -> bytes:
    script = bytearray([0xD7, 0x82, map_selector, 0x86, 0x00])
    current_base = 0
    for line in lines:
        first_x = int(line["first_x"])
        first_y = int(line["first_y"])
        for row_index, tile_ids in enumerate(line["tile_ids"]):
            script.extend([0x81, first_x, first_y + row_index])
            current_base = encode_tile_run(script, tile_ids, current_base)
    if final_position is not None:
        script.extend([0x81, final_position[0], final_position[1]])
    if current_base != 0:
        script.extend([0x86, 0x00])
    script.extend([0x80, 0xC9])
    return bytes(script)


def make_tile_stream(tile_ids: list[int]) -> bytes:
    stream = bytearray([0x86, 0x00])
    current_base = encode_tile_run(stream, tile_ids, 0)
    if current_base != 0:
        stream.extend([0x86, 0x00])
    stream.append(0x80)
    return bytes(stream)


def item_routine_addresses() -> tuple[int, ...]:
    addresses = []
    cursor = ITEM_ROUTINE_BASE + 29
    for entries in ITEM_PAIRS:
        addresses.append(cursor)
        cursor += len(entries) * 2 * 24 + 1
    return tuple(addresses)


def build_item_routine_blob(lines: list[dict[str, object]]) -> bytes:
    by_entry = {str(line["entry"]): line for line in lines}
    item_rows: list[list[tuple[int, int, list[int]]]] = []
    item_streams: list[list[bytes]] = []
    for entries in ITEM_PAIRS:
        rows: list[tuple[int, int, list[int]]] = []
        streams: list[bytes] = []
        base_offsets = (0, 2) if len(entries) == 2 else (1,)
        for entry, base_offset in zip(entries, base_offsets):
            line = by_entry[entry]
            for row_index, tile_ids in enumerate(line["tile_ids"]):
                rows.append((int(line["first_x"]), base_offset + row_index, tile_ids))
                streams.append(make_tile_stream(tile_ids))
        item_rows.append(rows)
        item_streams.append(streams)

    routine_addresses = item_routine_addresses()
    cursor = ITEM_ROUTINE_BASE + 29
    for rows, address in zip(item_rows, routine_addresses):
        if cursor != address:
            raise ValueError("item routine address calculation mismatch")
        cursor += len(rows) * 24 + 1
    stream_addresses: list[list[int]] = []
    for streams in item_streams:
        addresses = []
        for stream in streams:
            addresses.append(cursor)
            cursor += len(stream)
        stream_addresses.append(addresses)
    if cursor > ITEM_ROUTINE_END:
        raise ValueError("item 12px routines exceed reserved bank-8 region")

    blob = bytearray([0xF0, 0xF0, 0x3D])
    for item_index, address in enumerate(routine_addresses):
        blob.extend([0xFE, item_index, 0xCA, *u16(address)])
    blob.append(0xC9)
    for rows, addresses in zip(item_rows, stream_addresses):
        routine = bytearray()
        for (tile_x, y_offset, _), stream_address in zip(rows, addresses):
            routine.extend([0x3E, tile_x, 0xEA, 0x0C, 0xC0])
            routine.extend([0xF0, 0xEF, 0xC6, y_offset, 0xEA, 0x0D, 0xC0])
            routine.extend([0x11, 0x0B, 0xC0, 0xCD, 0x59, 0x01])
            routine.extend([0x11, *u16(stream_address), 0xCD, 0x59, 0x01])
        routine.append(0xC9)
        blob.extend(routine)
    for streams in item_streams:
        for stream in streams:
            blob.extend(stream)
    if ITEM_ROUTINE_BASE + len(blob) != cursor:
        raise ValueError("item routine address calculation mismatch")
    return bytes(blob)


def patch_dispatch(rom: bytearray) -> None:
    entries = [(page_id, 0x4040 + page_id * 0x0D) for page_id in range(10)]
    entries.extend((SCRIPT_IDS[page], SCRIPT_ADDRS[page]) for page in SCRIPT_IDS)
    entries.extend(
        [
            (OXYGEN_SELECTOR, OXYGEN_SCRIPT_ADDR),
            (ITEM_SELECTOR, ITEM_ROUTINE_BASE),
            (ALL_ITEMS_SELECTOR, ALL_ITEMS_ROUTINE_ADDR),
            (INITIALS_SELECTOR, INITIALS_SCRIPT_ADDR),
        ]
    )
    dispatch = bytearray([0x79])
    for selector, target in entries:
        dispatch.extend([0xFE, selector, 0xCA, *u16(target)])
    dispatch.append(0xC9)
    if len(dispatch) > 0x80:
        raise ValueError("translation dispatch does not fit")
    start = bank8_offset(0x4100)
    rom[start : start + 0x80] = dispatch + bytes([0xFF] * (0x80 - len(dispatch)))
    entry = bank8_offset(0x4000)
    rom[entry : entry + 0x40] = bytes([0xC3, 0x00, 0x41]) + bytes([0xFF] * 0x3D)


def write_bank_script(rom: bytearray, page: str, script: bytes) -> None:
    start_address, end_address = BANK_SCRIPT_REGIONS[page]
    if len(script) > end_address - start_address:
        raise ValueError(f"bank script does not fit for {page}: {len(script)} bytes")
    start = bank8_offset(start_address)
    rom[start : start + end_address - start_address] = script + bytes(
        [0xFF] * (end_address - start_address - len(script))
    )


def patch_wrapper(rom: bytearray, page: str) -> None:
    start, end = SCRIPT_REGIONS[page]
    if rom[start] != 0xD7:
        raise ValueError(f"unexpected small-text script start for {page}")
    wrapper = bytes(
        [0x3E, SCRIPT_IDS[page], 0xCD, FULL_STUB_ADDR & 0xFF, FULL_STUB_ADDR >> 8, 0xC9]
    )
    if len(wrapper) > end - start:
        raise ValueError(f"wrapper does not fit for {page}")
    rom[start:end] = wrapper + bytes(end - start - len(wrapper))


def patch_no_items_script(rom: bytearray, script: bytes) -> None:
    start, end = NO_ITEMS_REGION
    if rom[start] != 0xD7:
        raise ValueError("unexpected small-text no-items script")
    if len(script) > end - start:
        raise ValueError(f"no-items script does not fit: {len(script)} > {end - start}")
    rom[start:end] = script + bytes(end - start - len(script))


def patch_initials_prompt(rom: bytearray) -> None:
    start, end = INITIALS_PROMPT_REGION
    if rom[start : start + 2] != bytes([0x28, 0x11]):
        raise ValueError("unexpected small-text initials prompt wrapper")
    wrapper = bytes(
        [
            0x28,
            0x06,
            0x3E,
            INITIALS_SELECTOR,
            0xCD,
            FULL_STUB_ADDR & 0xFF,
            FULL_STUB_ADDR >> 8,
            0xC9,
            0xC9,
        ]
    )
    rom[start:end] = wrapper + bytes(end - start - len(wrapper))


def patch_item_renderer(rom: bytearray) -> None:
    start, end = ITEM_RENDERER_REGION
    if rom[start : start + 3] != bytes([0xF0, 0xF0, 0x3D]):
        raise ValueError("unexpected small-text item-name renderer")
    wrapper = bytes(
        [
            0x3E,
            ITEM_SELECTOR,
            0xCD,
            FULL_STUB_ADDR & 0xFF,
            FULL_STUB_ADDR >> 8,
            0xC9,
        ]
    )
    rom[start:end] = wrapper + bytes(end - start - len(wrapper))


def make_all_items_routine() -> bytes:
    return bytes([0x21, 0xB9, 0xC1, 0x06, 0x05, 0x3E, 0x01, 0xCD, 0xBE, 0x02, 0xC9])


def patch_status_panel(rom: bytearray) -> None:
    start, end = OXYGEN_INLINE_REGION
    expected = bytes([0xD7, 0x2A, 0x2B, 0x00, 0x83, 0x80])
    if rom[start:end] != expected:
        raise ValueError("unexpected small-text oxygen label script")
    rom[start:end] = bytes(
        [0x3E, OXYGEN_SELECTOR, 0xCD, FULL_STUB_ADDR & 0xFF, FULL_STUB_ADDR >> 8, 0x00]
    )
    if rom[STATUS_WINDOW_Y_OFFSET] != 0x7A:
        raise ValueError("unexpected small-text status window position")
    rom[STATUS_WINDOW_Y_OFFSET] = 0x72


def status_bar_tile_data(phase2: bytes) -> bytes:
    data = bytearray()
    for tile_id in range(0x77, 0x7F):
        start = 0x017B11 + (tile_id - 0x30) * 16
        original = phase2[start : start + 16]
        rows = [original[index : index + 2] for index in range(0, 16, 2)]
        if any(rows[index] != bytes(2) for index in (0, 1, 5, 6)):
            raise ValueError(f"unexpected oxygen bar padding in tile 0x{tile_id:02X}")
        data.extend(b"".join([bytes(2), bytes(2), bytes(2), *rows[:5]]))
    return bytes(data)


def patch_stage_scroll_alignment(rom: bytearray) -> None:
    if rom[STAGE_SCROLL_ALIGNMENT_OFFSET] != 0x04:
        raise ValueError("unexpected small-text stage scroll alignment")
    rom[STAGE_SCROLL_ALIGNMENT_OFFSET] = 0x08


def allocation_tile_bytes(
    phase2: bytes,
    page: str,
    tile_id: int,
    page_tiles: dict[str, dict[int, bytes]],
) -> bytes:
    tile = page_tiles[page].get(tile_id)
    if tile is not None:
        return tile
    source = page_source_offset(page) + tile_id * 8
    return phase2[source : source + 8]


def main() -> None:
    phase2 = build_small_text_rom()
    if sha256(phase2) != EXPECTED_SMALL_TEXT_BASE_SHA256:
        raise ValueError("small-text base hash does not match the validated build")
    if len(phase2) != 0x40000:
        raise ValueError("unexpected small-text base size")

    layout = load_layout()
    glyphs, advances, metrics = load_glyphs(ordered_characters(layout))
    cjk_metrics = [row for row in metrics if not str(row["char"]).isascii()]
    if any(
        row["packed_advance_pixels"] != 12
        or not 1 <= row["ink_width"] <= 11
        or not 1 <= row["ink_height"] <= 11
        for row in cjk_metrics
    ):
        raise ValueError("unexpected zpix 12px CJK metrics")

    rom = bytearray(phase2)
    page_tiles: dict[str, dict[int, bytes]] = {}
    page_lines: dict[str, list[dict[str, object]]] = {}
    for page, rows in layout.items():
        rendered = [render_line_patterns(row, glyphs, advances) for row in rows]
        page_tiles[page], page_lines[page] = allocate_page(phase2, page, rendered)
        clear_unused_low_tiles(rom, page)
        write_low_tiles(rom, page, page_tiles[page])

    high_meta = {
        page: write_high_tiles(rom, page, page_tiles[page])
        for page in ("stage", "access", "ending", "initials", "item_status")
    }
    scripts = {
        page: make_packed_script(page_lines[page])
        for page in ("stage", "access", *sorted(DESC_PAGES), "ending")
    }
    access_source, access_first, access_count = high_meta["access"]
    scripts["access"] = copy_sequence(
        access_source,
        0x8000 + access_first * 16,
        access_count * 16,
    ) + scripts["access"]
    initials_loader = 0x4040 + PAGE_IDS["initials"] * 0x0D
    initials_script = bytes([0xCD, *u16(initials_loader)]) + make_packed_script(
        page_lines["initials"]
    )
    item_lines = page_lines["item_status"]
    message_line = [line for line in item_lines if line["entry"] == "message"]
    oxygen_line = [line for line in item_lines if line["entry"] == "air"]
    inventory_lines = [
        line
        for line in item_lines
        if line["entry"] not in {"message", "air"}
    ]
    no_items_script = make_packed_script(message_line)
    oxygen_body = make_packed_script(
        oxygen_line,
        map_selector=1,
        final_position=(0, 3),
    )
    bar_data = status_bar_tile_data(phase2)
    bar_data_start = bank8_offset(STATUS_BAR_DATA_ADDR)
    rom[bar_data_start : bar_data_start + len(bar_data)] = bar_data
    oxygen_script = copy_raw_sequence(
        STATUS_BAR_DATA_ADDR,
        0x8000 + 0x77 * 16,
        len(bar_data),
    ) + oxygen_body
    item_blob = build_item_routine_blob(inventory_lines)

    patch_dispatch(rom)
    for page in ("ending", "initials", "item_status", "stage"):
        patch_extended_loader(rom, page, *high_meta[page])
    for page in SCRIPT_IDS:
        write_bank_script(rom, page, scripts[page])
        patch_wrapper(rom, page)
    write_bank_script(rom, "initials", initials_script)
    patch_initials_prompt(rom)
    patch_no_items_script(rom, no_items_script)

    oxygen_start = bank8_offset(OXYGEN_SCRIPT_ADDR)
    rom[oxygen_start : oxygen_start + 0x100] = oxygen_script + bytes(
        [0xFF] * (0x100 - len(oxygen_script))
    )
    item_start = bank8_offset(ITEM_ROUTINE_BASE)
    rom[item_start : bank8_offset(ITEM_ROUTINE_END)] = item_blob + bytes(
        [0xFF] * (ITEM_ROUTINE_END - ITEM_ROUTINE_BASE - len(item_blob))
    )
    all_items_routine = make_all_items_routine()
    all_items_start = bank8_offset(ALL_ITEMS_ROUTINE_ADDR)
    rom[all_items_start : all_items_start + 0x20] = all_items_routine + bytes(
        [0xFF] * (0x20 - len(all_items_routine))
    )

    patch_item_renderer(rom)
    patch_status_panel(rom)
    patch_stage_scroll_alignment(rom)

    header = fix_header_checksum(rom)
    global_sum = fix_global_checksum(rom)
    OUTPUT_ROM.write_bytes(rom)

    print(f"output={OUTPUT_ROM}")
    print(f"size=0x{len(rom):X}")
    for page in sorted(page_tiles):
        threshold = page_limit(page)
        low = sum(tile_id < threshold for tile_id in page_tiles[page])
        high = len(page_tiles[page]) - low
        print(
            f"{page}: unique_tiles={len(page_tiles[page])} low={low} high={high}"
        )
    for page in ("stage", "access", "ending", "initials", "item_status"):
        source, first, count = high_meta[page]
        print(
            f"{page}: high_source=0x{source:04X} "
            f"tiles=0x{first:02X}-0x{first + count - 1:02X}"
        )
    for page in sorted(scripts):
        print(f"{page}: script_bytes={len(scripts[page])}")
    print(f"oxygen_script_bytes={len(oxygen_script)}")
    print(f"item_routine_bytes={len(item_blob)}")
    print(f"header_checksum=0x{header:02X}")
    print(f"global_checksum=0x{global_sum:04X}")


if __name__ == "__main__":
    main()
