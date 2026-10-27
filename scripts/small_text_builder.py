from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import translation_base


WORKSPACE = Path(__file__).resolve().parents[1]
LAYOUT_CSV = WORKSPACE / "text" / "small_text_layout.csv"
GLYPH_CSV = (
    WORKSPACE
    / "font_data"
    / "small_font_glyphs.csv"
)

EXPECTED_ORIGINAL_SHA256 = "4F6450321EE163D5FD8A942816B10AF1CE41BBCAD62185A550C97B16CAC125A1"
EXPECTED_ORIGINAL_SIZE = 0x20000

SCRIPT_REGIONS = {
    "ending": (0x00ADA4, 0x00AEBC),
    "access": (0x00B5D5, 0x00B634),
    "no_items": (0x0179B6, 0x0179E3),
    "desc_humphrey": (0x00BD76, 0x00BD98),
    "desc_zaks": (0x00BD98, 0x00BDB3),
    "desc_droid1": (0x00BDB3, 0x00BDD8),
    "desc_droid9": (0x00BDD8, 0x00BDFB),
    "desc_garffs": (0x00BDFB, 0x00BE18),
}

DESCRIPTION_PAGE = {
    "humphrey_name": "desc_humphrey",
    "humphrey_description": "desc_humphrey",
    "zaks_name": "desc_zaks",
    "zaks_description": "desc_zaks",
    "droid_1_name": "desc_droid1",
    "droid_1_description": "desc_droid1",
    "droid_9_name": "desc_droid9",
    "droid_9_description": "desc_droid9",
    "garffs_name": "desc_garffs",
    "garffs_description": "desc_garffs",
}

ITEM_ENTRY = {
    "PARTICLE": "particle",
    "DISRUPTOR": "disruptor",
    "COMPUTER": "computer",
    "INTERFACE": "interface",
    "STUN GUN": "stun_gun",
    "KEY": "key",
    "CIRCUIT": "circuit",
    "JAMMER": "jammer",
}

EXPLICIT_SLOTS = {
    "initials": [0x26, 0x27, 0x2A, 0x2C],
}

EXTRA_SLOTS = {
    "no_items": [0x27, 0x28, 0x29, 0x2A, 0x2B],
    "stage": [0x26, 0x27],
}

ACCESS_WINDOW_POSITION_OFFSET = 0x00B5A3

PAGE_GLYPH_TRANSFORMS = {
    "desc_droid9": {
        "9": "left_1",
    },
}


def load_base():
    return translation_base


def load_layout() -> list[dict[str, str]]:
    with LAYOUT_CSV.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def load_glyphs() -> dict[str, bytes]:
    glyphs = {}
    with GLYPH_CSV.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            glyphs[row["char"]] = bytes.fromhex(row["bytes_hex"])
    return glyphs


def parse_int(value: str) -> int:
    return int(value, 0)


def layout_page(row: dict[str, str]) -> str:
    screen = row["screen"]
    if screen in {"initials", "ending", "access", "stage"}:
        return screen
    if screen in {"no_items", "item"}:
        return "no_items"
    if screen == "description":
        return DESCRIPTION_PAGE[row["entry"]]
    raise ValueError(f"unknown layout screen {screen!r}")


def encode_text(builder, text: str, mapping: dict[str, int]) -> bytes:
    output = bytearray()
    index = 0
    while index < len(text):
        if text.startswith("(C)", index):
            output.append(0x2D)
            index += 3
            continue
        if text.startswith("(R)", index):
            output.append(0x2E)
            index += 3
            continue
        char = text[index]
        if char not in mapping:
            raise ValueError(f"unmapped character {char!r} in {text!r}")
        output.append(mapping[char])
        index += 1
    return bytes(output)


def text_codes(builder, text: str) -> set[int]:
    return set(encode_text(builder, text, builder.ASCII_CODES))


def build_page_maps(base, source_rows, layout_rows):
    page_texts = {name: [] for name in base.PAGES}
    for row in layout_rows:
        page_texts[layout_page(row)].append(row["text"])

    hidden_sources = {
        "access": [item["source"] for item in base.ACCESS_HIDDEN_LINES],
        "no_items": [item["source"] for item in base.NO_ITEMS_HIDDEN_LINES],
    }
    maps = {}
    debug = []
    for name, config in base.PAGES.items():
        source_codes = set()
        for row in source_rows:
            if row["group"] in config["groups"]:
                source_codes.update(text_codes(base.load_builder(), row["source"]))
        for text in hidden_sources.get(name, []):
            source_codes.update(text_codes(base.load_builder(), text))

        final_ascii = set()
        chinese = []
        for text in page_texts[name]:
            for char in text:
                if char in base.load_builder().ASCII_CODES:
                    final_ascii.add(base.load_builder().ASCII_CODES[char])
                elif ord(char) > 127 and char not in chinese:
                    chinese.append(char)
                elif ord(char) <= 127:
                    raise ValueError(f"unsupported ASCII {char!r} in {name}: {text!r}")

        if name in EXPLICIT_SLOTS:
            available = list(EXPLICIT_SLOTS[name])
        else:
            available = sorted(source_codes - final_ascii - {0x00})
            for code in EXTRA_SLOTS.get(name, []):
                if code not in available:
                    available.append(code)

        if len(chinese) > len(available):
            raise ValueError(f"{name}: needs {len(chinese)} slots, has {len(available)}")
        collisions = final_ascii.intersection(available[: len(chinese)])
        if collisions:
            raise ValueError(f"{name}: assigned slots collide with final ASCII: {collisions}")

        mapping = dict(base.load_builder().ASCII_CODES)
        for char, code in zip(chinese, available):
            mapping[char] = code
            debug.append({"page": name, "char": char, "code": f"0x{code:02X}"})
        maps[name] = mapping
    return maps, debug


def build_font_pages(base, original: bytes, page_maps, glyphs) -> bytes:
    original_page = bytearray(
        original[base.ORIGINAL_FONT_OFFSET : base.ORIGINAL_FONT_OFFSET + base.ORIGINAL_FONT_BYTES]
    )
    page_count = max(int(config["id"]) for config in base.PAGES.values()) + 1
    bank_data = bytearray([0xFF] * (base.FONT_PAGE_BASE - 0x4000 + base.PAGE_STRIDE * page_count))
    for name, config in base.PAGES.items():
        page = bytearray(original_page)
        for char, code in page_maps[name].items():
            if ord(char) <= 127:
                continue
            if char not in glyphs:
                raise ValueError(f"missing native 7px glyph {char!r}")
            page[code * 8 : code * 8 + 8] = glyphs[char]

        for char, transform in PAGE_GLYPH_TRANSFORMS.get(name, {}).items():
            code = page_maps[name][char]
            glyph = bytes(page[code * 8 : code * 8 + 8])
            if transform == "right_1":
                if any(row & 0x01 for row in glyph):
                    raise ValueError(f"cannot shift {char!r} right without clipping")
                glyph = bytes(row >> 1 for row in glyph)
            elif transform == "left_1":
                if any(row & 0x80 for row in glyph):
                    raise ValueError(f"cannot shift {char!r} left without clipping")
                glyph = bytes((row << 1) & 0xFF for row in glyph)
            elif transform == "up_1":
                glyph = glyph[1:] + bytes([0x00])
            else:
                raise ValueError(f"unknown glyph transform {transform!r}")
            page[code * 8 : code * 8 + 8] = glyph

        start = base.FONT_PAGE_BASE - 0x4000 + int(config["id"]) * base.PAGE_STRIDE
        bank_data[start : start + len(page)] = page
    return bytes(bank_data)


def make_d7_script(base, lines, mapping) -> bytes:
    script = bytearray([0xD7, 0x82, 0x00, 0x86, 0x00])
    for row in lines:
        script.extend([0x81, parse_int(row["x"]), parse_int(row["y"])])
        script.extend(encode_text(base.load_builder(), row["text"], mapping))
    script.extend([0x80, 0xC9])
    return bytes(script)


def patch_script_region(rom: bytearray, start: int, end: int, script: bytes) -> None:
    if rom[start] != 0xD7 or rom[end - 2 : end] != bytes([0x80, 0xC9]):
        raise ValueError(f"unexpected D7 script region 0x{start:06X}..0x{end - 1:06X}")
    if len(script) > end - start:
        raise ValueError(f"script at 0x{start:06X} does not fit: {len(script)} > {end - start}")
    rom[start:end] = script + bytes(end - start - len(script))


def patch_regular_scripts(base, rom, layout_rows, page_maps) -> int:
    grouped = {name: [] for name in SCRIPT_REGIONS}
    for row in layout_rows:
        page = layout_page(row)
        if page in grouped and row["x"] and row["y"]:
            grouped[page].append(row)
    count = 0
    for page, (start, end) in SCRIPT_REGIONS.items():
        script = make_d7_script(base, grouped[page], page_maps[page])
        patch_script_region(rom, start, end, script)
        count += 1
    return count


def patch_stage(base, rom: bytearray, layout_rows, mapping) -> int:
    if rom[base.STAGE_CALL_OFFSET : base.STAGE_CALL_OFFSET + 3] != bytes([0xCD, 0xFC, 0x72]):
        raise ValueError("unexpected original stage call")
    lines = [row for row in layout_rows if row["screen"] == "stage"]
    script = make_d7_script(base, lines, mapping)
    if base.STAGE_SCRIPT_START + len(script) > base.STAGE_WRAPPER_OFFSET:
        raise ValueError("small-text stage script overlaps wrapper")
    page_id = int(base.PAGES["stage"]["id"])
    wrapper = bytes(
        [0x3E, page_id, 0xCD, base.FULL_STUB_ADDR & 0xFF, base.FULL_STUB_ADDR >> 8, 0xC3, 0xFC, 0x72]
    )
    rom[base.STAGE_SCRIPT_START : base.STAGE_SCRIPT_END] = bytes(
        base.STAGE_SCRIPT_END - base.STAGE_SCRIPT_START
    )
    rom[base.STAGE_SCRIPT_START : base.STAGE_SCRIPT_START + len(script)] = script
    rom[base.STAGE_WRAPPER_OFFSET : base.STAGE_WRAPPER_OFFSET + len(wrapper)] = wrapper
    rom[base.STAGE_CALL_OFFSET : base.STAGE_CALL_OFFSET + 3] = bytes(
        [0xCD, base.STAGE_WRAPPER_ADDR & 0xFF, base.STAGE_WRAPPER_ADDR >> 8]
    )
    return len(lines)


def patch_initials(base, rom: bytearray, row, mapping) -> int:
    original = bytes([0x20, 0x01, 0xC9, 0xD7, 0x82, 0x00, 0x81, 0x00, 0x00])
    original += encode_text(base.load_builder(), "ENTER YOUR INITIALS:", base.load_builder().ASCII_CODES)
    original += bytes([0x80, 0xC9])
    start = base.INITIALS_PATCH_START
    end = base.INITIALS_PATCH_END
    if rom[start:end] != original:
        raise ValueError("unexpected original initials prompt")

    encoded = encode_text(base.load_builder(), row["text"], mapping)
    script = bytearray(
        [
            0x28,
            0x00,
            0x3E,
            int(base.PAGES["initials"]["id"]),
            0xCD,
            base.FULL_STUB_ADDR & 0xFF,
            base.FULL_STUB_ADDR >> 8,
            0xD7,
            0x82,
            0x00,
            0x81,
            parse_int(row["x"]),
            parse_int(row["y"]),
            *encoded,
            0x80,
            0xC9,
        ]
    )
    script[1] = len(script) - 3
    if len(script) > len(original):
        raise ValueError("small-text initials script does not fit")
    rom[start:end] = script + bytes(len(original) - len(script))
    return 1


def centered_text(row: dict[str, str]) -> str:
    text = row["text"]
    width = int(row["width"])
    if len(text) > width:
        raise ValueError(f"fixed text does not fit {row['screen']}/{row['entry']}")
    return " " * ((width - len(text)) // 2) + text


def patch_fixed_text(base, rom: bytearray, source_rows, layout_rows, page_maps) -> int:
    by_key = {(row["screen"], row["entry"]): row for row in layout_rows}
    count = 0

    hidden = base.ACCESS_HIDDEN_LINES[0]
    access_row = by_key[("access", "hidden_label")]
    text = centered_text(access_row)
    encoded = encode_text(base.load_builder(), text, page_maps["access"])
    rom[hidden["offset"] : hidden["offset"] + hidden["byte_len"]] = encoded + bytes(
        hidden["byte_len"] - len(encoded)
    )
    count += 1

    for source_row in source_rows:
        if source_row["group"] != "item_names":
            continue
        entry = ITEM_ENTRY[source_row["source"].strip()]
        row = by_key[("item", entry)]
        text = centered_text(row)
        encoded = encode_text(base.load_builder(), text, page_maps["no_items"])
        offset = int(source_row["offset"], 16)
        byte_len = int(source_row["byte_len"])
        rom[offset : offset + byte_len] = encoded + bytes(byte_len - len(encoded))
        count += 1

    air = base.NO_ITEMS_HIDDEN_LINES[0]
    air_row = by_key[("item", "air")]
    text = centered_text(air_row)
    encoded = encode_text(base.load_builder(), text, page_maps["no_items"])
    rom[air["offset"] : air["offset"] + air["byte_len"]] = encoded + bytes(
        air["byte_len"] - len(encoded)
    )
    count += 1
    return count


def patch_access_window_position(rom: bytearray) -> int:
    expected = bytes([0x3E, 0x08, 0xE0, 0x4B, 0x3E, 0x82, 0xE0, 0x4A])
    start = ACCESS_WINDOW_POSITION_OFFSET
    if rom[start : start + len(expected)] != expected:
        raise ValueError("unexpected access window position setup")
    rom[start + 5] = 0x81
    return 1


def build_small_text_rom() -> bytes:
    base = load_base()
    builder = base.load_builder()
    original = base.ORIGINAL_ROM.read_bytes()
    if len(original) != EXPECTED_ORIGINAL_SIZE:
        raise ValueError("unexpected original ROM size")
    if hashlib.sha256(original).hexdigest().upper() != EXPECTED_ORIGINAL_SHA256:
        raise ValueError("original ROM hash does not match the validated USA ROM")
    source_rows = base.load_rows()
    layout_rows = load_layout()
    glyphs = load_glyphs()
    page_maps, _ = build_page_maps(base, source_rows, layout_rows)
    font_pages = build_font_pages(base, original, page_maps, glyphs)
    bank8_code = base.build_bank8_code()

    rom = bytearray(original)
    rom.extend([0xFF] * (base.EXPANDED_ROM_SIZE - len(rom)))
    rom[base.FONT_BANK_FILE_OFFSET : base.FONT_BANK_FILE_OFFSET + len(bank8_code)] = bank8_code
    data_start = base.FONT_PAGE_BASE - 0x4000
    rom[
        base.FONT_BANK_FILE_OFFSET + data_start : base.FONT_BANK_FILE_OFFSET + len(font_pages)
    ] = font_pages[data_start:]

    code_patches = base.patch_code(rom)
    script_patches = patch_regular_scripts(base, rom, layout_rows, page_maps)
    stage_lines = patch_stage(base, rom, layout_rows, page_maps["stage"])
    initials_row = next(row for row in layout_rows if row["screen"] == "initials")
    initials_patches = patch_initials(base, rom, initials_row, page_maps["initials"])
    fixed_patches = patch_fixed_text(base, rom, source_rows, layout_rows, page_maps)
    access_window_patches = patch_access_window_position(rom)

    rom[0x0148] = 0x03
    builder.fix_header_checksum(rom)
    builder.fix_global_checksum(rom)
    return bytes(rom)
