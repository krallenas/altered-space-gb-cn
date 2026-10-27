from __future__ import annotations

import csv
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
ORIGINAL_ROM = WORKSPACE / "Altered Space - A 3-D Alien Adventure (USA).gb"
TEXT_CSV = WORKSPACE / "text" / "source_text.csv"

FONT_BANK = 0x08
EXPANDED_ROM_SIZE = 0x40000
FONT_BANK_FILE_OFFSET = FONT_BANK * 0x4000
FONT_PAGE_BASE = 0x4200
PAGE_STRIDE = 0x200
ORIGINAL_FONT_OFFSET = 0x0007E4
ORIGINAL_FONT_BYTES = 0x180
FULL_STUB_ADDR = 0x00DC

PAGES = {
    "ending": {"id": 0, "groups": {"script_00ADA4"}, "font_sequence_offsets": [0x00AC7F]},
    "access": {"id": 1, "groups": {"script_00B5D5"}, "font_sequence_offsets": [0x00B5B0]},
    "no_items": {"id": 2, "groups": {"script_0179B6", "item_names"}, "font_sequence_offsets": [0x017AF2]},
    "desc_humphrey": {"id": 3, "groups": {"script_00BD76"}, "desc_index": 0},
    "desc_zaks": {"id": 4, "groups": {"script_00BD98"}, "desc_index": 1},
    "desc_droid1": {"id": 5, "groups": {"script_00BDB3"}, "desc_index": 2},
    "desc_droid9": {"id": 6, "groups": {"script_00BDD8"}, "desc_index": 3},
    "desc_garffs": {"id": 7, "groups": {"script_00BDFB"}, "desc_index": 4},
    "stage": {"id": 8, "groups": {"script_00B2FC"}},
    "initials": {
        "id": 9,
        "groups": {"script_00043E"},
        "source_slots": [0x26, 0x27, 0x2A],
    },
}

ACCESS_HIDDEN_LINES = [
    {
        "offset": 0x00B568,
        "byte_len": 19,
        "source": "PLANS FOR STAGE    ",
        "translation": "访问资料库",
    }
]

NO_ITEMS_HIDDEN_LINES = [
    {
        "offset": 0x017ABC,
        "byte_len": 3,
        "source": "AIR",
        "translation": "气",
    }
]

INITIALS_PATCH_START = 0x00043B
INITIALS_PATCH_END = 0x00045A

STAGE_CALL_OFFSET = 0x00B2B2
STAGE_SCRIPT_START = 0x00B2FC
STAGE_SCRIPT_END = 0x00B3C7
STAGE_WRAPPER_OFFSET = 0x00B3A0
STAGE_WRAPPER_ADDR = 0x73A0

ASCII_CODES = {" ": 0x00}
for index, char in enumerate("0123456789", start=0x01):
    ASCII_CODES[char] = index
for index, char in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=0x0B):
    ASCII_CODES[char] = index
ASCII_CODES.update(
    {
        ".": 0x25,
        ",": 0x26,
        "'": 0x27,
        ":": 0x28,
        "-": 0x29,
        "&": 0x2A,
        "?": 0x2B,
        "!": 0x2C,
    }
)


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


class BuilderFacade:
    ASCII_CODES = ASCII_CODES
    fix_header_checksum = staticmethod(fix_header_checksum)
    fix_global_checksum = staticmethod(fix_global_checksum)


BUILDER = BuilderFacade()


def load_builder() -> BuilderFacade:
    return BUILDER


def load_rows() -> list[dict[str, str]]:
    with TEXT_CSV.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def u16(value: int) -> list[int]:
    return [value & 0xFF, value >> 8]


def page_copy_routine(source: int, byte_count: int = 0x0300) -> bytes:
    return bytes(
        [
            0x21,
            *u16(source),
            0x11,
            0x00,
            0x80,
            0x01,
            byte_count & 0xFF,
            byte_count >> 8,
            0xCD,
            0x09,
            0x2C,
            0xC9,
        ]
    )


def build_bank8_code() -> bytes:
    code = bytearray([0xFF] * (FONT_PAGE_BASE - 0x4000))
    routine_base = 0x0040
    dispatch = bytearray([0x79])
    for name in PAGES:
        page_id = int(PAGES[name]["id"])
        routine_addr = 0x4000 + routine_base + page_id * 0x000D
        dispatch.extend([0xFE, page_id, 0xCA, *u16(routine_addr)])
    dispatch.extend([0xC3, *u16(0x4000 + routine_base)])
    code[: len(dispatch)] = dispatch
    for name in PAGES:
        source = FONT_PAGE_BASE + int(PAGES[name]["id"]) * PAGE_STRIDE
        byte_count = 0x0250 if name.startswith("desc_") else 0x0300
        routine = page_copy_routine(source, byte_count)
        start = routine_base + int(PAGES[name]["id"]) * 0x000D
        code[start : start + len(routine)] = routine
    return bytes(code)


def build_full_stub() -> bytes:
    return bytes(
        [
            0x4F,
            0xFA,
            0xC7,
            0xC0,
            0xF5,
            0x3E,
            FONT_BANK,
            0xCD,
            0x6B,
            0x2B,
            0xCD,
            0x00,
            0x40,
            0xF1,
            0xC3,
            0x6B,
            0x2B,
        ]
    )


def build_desc_stub() -> bytes:
    return bytes(
        [
            0xCD,
            0x15,
            0x2C,
            0xF0,
            0xEF,
            0xC6,
            0x03,
            0xCD,
            FULL_STUB_ADDR & 0xFF,
            FULL_STUB_ADDR >> 8,
            0xC9,
        ]
    )


def patch_code(rom: bytearray) -> int:
    stub = build_full_stub()
    if any(rom[FULL_STUB_ADDR : FULL_STUB_ADDR + len(stub)]):
        raise ValueError("low stub area is not empty")
    rom[FULL_STUB_ADDR : FULL_STUB_ADDR + len(stub)] = stub

    desc_stub_addr = FULL_STUB_ADDR + len(stub)
    desc_stub = build_desc_stub()
    if any(rom[desc_stub_addr : desc_stub_addr + len(desc_stub)]):
        raise ValueError("desc stub area is not empty")
    rom[desc_stub_addr : desc_stub_addr + len(desc_stub)] = desc_stub

    original = bytes([0x21, 0xE4, 0x07, 0x11, 0x00, 0x80, 0x01, 0x00, 0x03, 0xCD, 0x09, 0x2C])
    count = 0
    for config in PAGES.values():
        if "font_sequence_offsets" not in config:
            continue
        page_id = int(config["id"])
        replacement = bytes(
            [0x3E, page_id, 0xCD, FULL_STUB_ADDR & 0xFF, FULL_STUB_ADDR >> 8]
        ) + bytes(7)
        for offset in config["font_sequence_offsets"]:
            if rom[offset : offset + len(original)] != original:
                raise ValueError(f"unexpected font sequence at 0x{offset:06X}")
            rom[offset : offset + len(original)] = replacement
            count += 1

    desc_original_call = bytes([0xCD, 0x15, 0x2C])
    desc_patched_call = bytes([0xCD, desc_stub_addr & 0xFF, desc_stub_addr >> 8])
    desc_call_offset = 0x00BCF9
    if rom[desc_call_offset : desc_call_offset + 3] != desc_original_call:
        raise ValueError(f"unexpected desc call at 0x{desc_call_offset:06X}")
    rom[desc_call_offset : desc_call_offset + 3] = desc_patched_call
    return count + 1
