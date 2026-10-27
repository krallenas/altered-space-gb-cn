from __future__ import annotations

import hashlib
from pathlib import Path

from build_translation import (
    ACCESS_PRESERVED_CODES,
    BANK8_FILE_OFFSET,
    CREDITS_GRAPHICS_LOAD_REGION,
    DESC_PAGES,
    ENDING_GRAPHICS_CODES,
    ENDING_GRAPHICS_LOAD_REGION,
    ENDING_PRELOAD_GRAPHICS_LOAD_REGION,
    EXTENDED_LOADER_ADDRS,
    HIGH_DATA_ADDRS,
    ITEM_GRAPHICS_CODES,
    ITEM_GRAPHICS_SOURCE_REGIONS,
    ITEM_RENDERER_REGION,
    ITEM_ROUTINE_BASE,
    ITEM_ROUTINE_END,
    ITEM_SELECTOR,
    INITIALS_GRAPHICS_CODES,
    INITIALS_PROMPT_REGION,
    INITIALS_SCRIPT_ADDR,
    INITIALS_SELECTOR,
    ALL_ITEMS_ROUTINE_ADDR,
    LAYOUT_CSV,
    NO_ITEMS_REGION,
    OXYGEN_INLINE_REGION,
    OXYGEN_SCRIPT_ADDR,
    OXYGEN_SELECTOR,
    OUTPUT_ROM,
    PAGE_IDS,
    SCRIPT_ADDRS,
    SCRIPT_IDS,
    STAGE_SCROLL_ALIGNMENT_OFFSET,
    STATUS_DYNAMIC_REGION,
    STATUS_BAR_DATA_ADDR,
    STATUS_WINDOW_Y_OFFSET,
    allocate_page,
    allocation_tile_bytes,
    bank8_offset,
    build_item_routine_blob,
    load_layout,
    make_packed_script,
    make_all_items_routine,
    ordered_characters,
    page_limit,
    page_source_offset,
    preserved_codes,
    render_line_patterns,
    status_bar_tile_data,
    storage_page,
)
from small_text_builder import build_small_text_rom
from small_text_builder import load_layout as load_small_layout
from large_text_font import load_glyphs
from sync_translation_review import load_rows as load_review_rows
from sync_translation_review import render_markdown


WORKSPACE = Path(__file__).resolve().parents[1]

EXPECTED_HASHES = {
    "README.md": "12E06392E7BE7F920013359F8E3666B3FBE38B6EB145135FF80E0D4E51CBAED6",
    "TRANSLATION_REVIEW.md": "FC4BF6FF648FDD795E2542589B31CDFBA48D114EB976DD604F241A39648E700B",
    "Altered Space - A 3-D Alien Adventure (USA).gb": "4F6450321EE163D5FD8A942816B10AF1CE41BBCAD62185A550C97B16CAC125A1",
    "Altered Space - A 3-D Alien Adventure (USA).zh.gb": "A1C223C9DF82D1AC7CC17AE7BA2002EB720D8586970CD5EA5B788B9B677743BB",
    "fonts/zpix.ttf": "ED39F02845E8C0B8CDBA275432250FB03E8528826F058BC151753BD62B44B744",
    "fonts/DinkieBitmap7pxDemo.ttf": "3EC3B2D3F08E7B5790E3896DE232BA8689D4AC4F8373F2DAAF01B14746045DCA",
    "font_data/small_font_glyphs.csv": "82DB1BC0AF979305304A5690D8E9012D828FA4FA7DF7AE2314E07FCFBC453C58",
    "text/source_text.csv": "9055AE5811C5F3C2C2C5F39FF1334FB5B1B88B64077E8729DB3256EE2706521D",
    "text/small_text_layout.csv": "D2B3740EE90457EB9D483D5B0C6279244B5C29B2BB23E2FB0EE5EF71C7EC6934",
    "text/large_text_layout.csv": "5966AD29E9092B2B66E09EBCA9DFB9C97758C17621F48513B89BD3397B28C3A9",
    "text/translation_review.csv": "9DEB1A74876476922DE0783E8A84F55C40E1D0E5177CDE7077B1BE33D2C7607B",
    "item.png": "9AE209BC653F7E674CD7C409C14BC7FEF3F638B2831CBEFE2745D28C4A3ED8D9",
    "key.png": "0B0DB98EF3AFD28D77BF1A27B04CA5FD154A8A6A1EFFD91859C2721A81B373DF",
}
EXPECTED_GLOBAL_CHECKSUM = 0xD060

REQUIRED_FILES = [
    "scripts/translation_base.py",
    "scripts/small_text_builder.py",
    "scripts/large_text_font.py",
    "scripts/build_translation.py",
    "scripts/build_small_font_data.py",
    "scripts/render_native_pixel_glyph.py",
    "scripts/sync_translation_review.py",
    "scripts/verify_translation.py",
    "README.md",
    "TRANSLATION_REVIEW.md",
]

REVIEW_LAYOUT_BINDINGS = {
    "initials": ("initials", "prompt"),
    "access_denied": ("access", "denied"),
    "access_explanation_1": ("access", "explanation_1"),
    "access_explanation_2": ("access", "explanation_2"),
    "no_items": ("item_status", "message"),
    "particle_disruptor": ("item_status", "particle"),
    "computer_interface": ("item_status", "computer"),
    "stun_gun": ("item_status", "stun_gun"),
    "key": ("item_status", "key"),
    "circuit_breaker": ("item_status", "circuit"),
    "air": ("item_status", "air"),
    "humphrey_name": ("desc_humphrey", "name"),
    "humphrey_description": ("desc_humphrey", "description"),
    "zaks_name": ("desc_zaks", "name"),
    "zaks_description": ("desc_zaks", "description"),
    "droid_1_name": ("desc_droid1", "name"),
    "droid_1_description": ("desc_droid1", "description"),
    "droid_9_name": ("desc_droid9", "name"),
    "droid_9_description": ("desc_droid9", "description"),
    "garffs_name": ("desc_garffs", "name"),
    "garffs_description": ("desc_garffs", "description"),
    "heading": ("stage", "heading"),
    **{f"stage_{number}": ("stage", f"stage_{number}") for number in range(1, 9)},
}

REVIEW_ITEM_HINT_BINDINGS = {
    "particle_disruptor": "disruptor",
    "computer_interface": "interface",
    "stun_gun": "stun_gun_hint",
    "circuit_breaker": "jammer",
}

ALLOWED_DIFF_RANGES = [
    (0x014D, 0x0150),
    (STAGE_SCROLL_ALIGNMENT_OFFSET, STAGE_SCROLL_ALIGNMENT_OFFSET + 1),
    INITIALS_PROMPT_REGION,
    (0x00ADA4, 0x00AEBC),
    (0x00B2FC, 0x00B3A0),
    (0x00B5D5, 0x00B634),
    (0x00BD76, 0x00BE18),
    (0x0179B6, 0x0179E3),
    ITEM_RENDERER_REGION,
    OXYGEN_INLINE_REGION,
    (STATUS_WINDOW_Y_OFFSET, STATUS_WINDOW_Y_OFFSET + 1),
    (0x020000, 0x024000),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def header_checksum(data: bytes) -> int:
    checksum = 0
    for value in data[0x0134:0x014D]:
        checksum = (checksum - value - 1) & 0xFF
    return checksum


def global_checksum(data: bytes) -> int:
    return (sum(data[:0x014E]) + sum(data[0x0150:])) & 0xFFFF


def in_allowed_range(offset: int) -> bool:
    return any(start <= offset < end for start, end in ALLOWED_DIFF_RANGES)


def decode_script(
    data: bytes,
    start: int,
    map_selector: int = 0,
) -> list[tuple[int, int, int]]:
    prefix = bytes([0xD7, 0x82, map_selector, 0x86, 0x00])
    if data[start : start + len(prefix)] != prefix:
        raise ValueError(f"unexpected packed script prefix at 0x{start:06X}")
    writes: list[tuple[int, int, int]] = []
    index = start + len(prefix)
    base = 0
    cursor_x: int | None = None
    cursor_y: int | None = None
    while index < len(data):
        value = data[index]
        index += 1
        if value < 0x80:
            if cursor_x is None or cursor_y is None:
                raise ValueError("tile code before packed script position")
            writes.append((cursor_x, cursor_y, base + value))
            cursor_x += 1
            continue
        if value == 0x81:
            cursor_x = data[index]
            cursor_y = data[index + 1]
            index += 2
            continue
        if value == 0x86:
            base = data[index]
            index += 1
            continue
        if value == 0x80:
            if data[index] != 0xC9:
                raise ValueError("packed script does not end with RET")
            return writes
        raise ValueError(f"unsupported packed script opcode 0x{value:02X}")
    raise ValueError("unterminated packed script")


def allocation_offset(page: str, tile_id: int) -> int:
    if tile_id < page_limit(page):
        return page_source_offset(page) + tile_id * 8
    first_ids = {
        "stage": 0xA7,
        "access": 0x46,
        "ending": 0xA8,
        "initials": 0x40,
        "item_status": 0x80,
    }
    if page not in first_ids:
        raise ValueError(f"unexpected high tile for {page}: 0x{tile_id:02X}")
    return bank8_offset(HIGH_DATA_ADDRS[page]) + (tile_id - first_ids[page]) * 8


def expected_layout_allocations(
    phase2: bytes,
) -> tuple[
    dict[str, dict[int, bytes]],
    dict[str, list[dict[str, object]]],
    list[dict[str, str]],
]:
    layout = load_layout()
    glyphs, advances, _ = load_glyphs(ordered_characters(layout))
    page_tiles: dict[str, dict[int, bytes]] = {}
    page_lines: dict[str, list[dict[str, object]]] = {}
    expected_rows: list[dict[str, str]] = []
    for page, rows in layout.items():
        rendered = [render_line_patterns(row, glyphs, advances) for row in rows]
        page_tiles[page], page_lines[page] = allocate_page(phase2, page, rendered)
        for line in page_lines[page]:
            for row_index, tile_ids in enumerate(line["tile_ids"]):
                for column_index, tile_id in enumerate(tile_ids):
                    tile = allocation_tile_bytes(phase2, page, tile_id, page_tiles)
                    expected_rows.append(
                        {
                            "page": page,
                            "entry": str(line["entry"]),
                            "text": str(line["text"]),
                            "tile_x": str(int(line["first_x"]) + column_index),
                            "tile_y": str(int(line["first_y"]) + row_index),
                            "tile_id": f"0x{tile_id:02X}",
                            "vram": f"0x{0x8000 + tile_id * 16:04X}",
                            "bytes_hex": tile.hex(" ").upper(),
                        }
                    )
    return page_tiles, page_lines, expected_rows


def script_start(data: bytes, page: str) -> int:
    address = INITIALS_SCRIPT_ADDR if page == "initials" else SCRIPT_ADDRS[page]
    start = bank8_offset(address)
    if page in {"access", "initials"}:
        found = data.find(bytes([0xD7, 0x82, 0x00]), start, start + 0x40)
        if found < 0:
            raise ValueError(f"{page} script is missing its packed text body")
        return found
    return start


def main() -> None:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (WORKSPACE / relative).is_file():
            errors.append(f"missing required file: {relative}")

    for relative, expected in EXPECTED_HASHES.items():
        path = WORKSPACE / relative
        if not path.is_file():
            errors.append(f"missing hashed file: {relative}")
            continue
        actual = sha256(path)
        if expected and actual != expected:
            errors.append(f"SHA256 mismatch: {relative}: {actual} != {expected}")
        else:
            print(f"SHA256 OK  {relative}  {actual}")

    review_rows: list[dict[str, str]] = []
    try:
        review_rows = load_review_rows()
        expected_markdown = render_markdown(review_rows)
        actual_markdown = (WORKSPACE / "TRANSLATION_REVIEW.md").read_text(
            encoding="utf-8"
        )
        if actual_markdown != expected_markdown:
            errors.append(
                "TRANSLATION_REVIEW.md is not synchronized with translation_review.csv"
            )
    except (KeyError, OSError, ValueError) as error:
        errors.append(f"cannot validate translation review files: {error}")

    if review_rows:
        review_by_entry = {row["entry"]: row for row in review_rows}
        if len(review_by_entry) != len(review_rows):
            errors.append("translation review contains duplicate entry identifiers")
        large_layout = load_layout()
        large_by_key = {
            (page, row["entry"]): row
            for page, rows in large_layout.items()
            for row in rows
        }
        for entry, key in REVIEW_LAYOUT_BINDINGS.items():
            if entry not in review_by_entry or key not in large_by_key:
                errors.append(f"missing review/layout binding: {entry}")
                continue
            if review_by_entry[entry]["current_chinese"] != large_by_key[key]["text"]:
                errors.append(f"review/layout text mismatch: {entry}")

        small_by_key = {
            (row["screen"], row["entry"]): row for row in load_small_layout()
        }
        stage_plans = review_by_entry.get("stage_plans")
        hidden_label = small_by_key.get(("access", "hidden_label"))
        if not stage_plans or not hidden_label:
            errors.append("missing 8px stage-plans review/layout entry")
        elif stage_plans["current_chinese"] != hidden_label["text"]:
            errors.append("review/layout text mismatch: stage_plans")

        for entry, layout_entry in REVIEW_ITEM_HINT_BINDINGS.items():
            review_row = review_by_entry.get(entry)
            layout_row = large_by_key.get(("item_status", layout_entry))
            marker = "第二行说明："
            if not review_row or not layout_row or marker not in review_row["notes"]:
                errors.append(f"missing structured item hint review: {entry}")
                continue
            if review_row["notes"].split(marker, 1)[1] != layout_row["text"]:
                errors.append(f"review/layout item hint mismatch: {entry}")

        ending = review_by_entry.get("ending_story")
        ending_text = "".join(
            large_by_key[("ending", f"story_{line}")]["text"] for line in range(1, 5)
        )
        if not ending or ending["current_chinese"] != ending_text:
            errors.append("review/layout text mismatch: ending_story")

        expected_translated = set(REVIEW_LAYOUT_BINDINGS) | {
            "stage_plans",
            "ending_story",
        }
        actual_translated = {
            row["entry"] for row in review_rows if row["status"] == "已翻译"
        }
        if actual_translated != expected_translated:
            errors.append("review translated-entry set does not match the active layouts")
        for row in review_rows:
            if row["status"] == "保留英文" and row["current_chinese"] != row["english"]:
                errors.append(f"retained-English review mismatch: {row['entry']}")

    readme_path = WORKSPACE / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        documented_files = (set(EXPECTED_HASHES) | set(REQUIRED_FILES)) - {"README.md"}
        for relative in sorted(documented_files):
            if f"`{relative}`" not in readme:
                errors.append(f"README does not document required file: {relative}")
        if EXPECTED_HASHES[OUTPUT_ROM.name] not in readme:
            errors.append("README translated ROM hash is out of date")

    if not OUTPUT_ROM.is_file():
        errors.append("translated ROM is missing")
        phase2 = b""
        phase3 = b""
    else:
        phase2 = build_small_text_rom()
        phase3 = OUTPUT_ROM.read_bytes()
        if len(phase3) != 0x40000:
            errors.append(f"unexpected translated ROM size: 0x{len(phase3):X}")
        actual_header = header_checksum(phase3)
        stored_global = (phase3[0x014E] << 8) | phase3[0x014F]
        actual_global = global_checksum(phase3)
        if actual_header != phase3[0x014D] or actual_header != 0x98:
            errors.append("translated ROM header checksum mismatch")
        if actual_global != stored_global or actual_global != EXPECTED_GLOBAL_CHECKSUM:
            errors.append("translated ROM global checksum mismatch")

        unexpected = [
            offset
            for offset, (before, after) in enumerate(zip(phase2, phase3))
            if before != after and not in_allowed_range(offset)
        ]
        if unexpected:
            errors.append(f"unexpected changes begin at 0x{unexpected[0]:06X}")

        if phase3[STAGE_SCROLL_ALIGNMENT_OFFSET] != 0x08:
            errors.append("stage list is not aligned to the 144px screen boundary")
        if phase2[STAGE_SCROLL_ALIGNMENT_OFFSET] != 0x04:
            errors.append("unexpected small-text stage scroll alignment")
        if phase3[0x015F:0x0162] != phase2[0x015F:0x0162]:
            errors.append("text router changed")
        if phase3[0x2CC4:0x2CEC] != phase2[0x2CC4:0x2CEC]:
            errors.append("opening-logo region changed")

        if phase3[0x00B550:0x00B564] != phase2[0x00B550:0x00B564]:
            errors.append("access border/pattern changed")
        if phase3[0x00B568:0x00B57B] != phase2[0x00B568:0x00B57B]:
            errors.append("8px access hidden label changed")
        if phase3[0x00B5A3:0x00B5AB] != phase2[0x00B5A3:0x00B5AB]:
            errors.append("access Window position changed")
        if phase3[0x00B95E:0x00BABE] != phase2[0x00B95E:0x00BABE]:
            errors.append("shared access graphics source changed")
        access_loader = slice(0x02004D, 0x02005A)
        if phase3[access_loader] != phase2[access_loader]:
            errors.append("access page unexpectedly replaces the shared page loader")

        if phase3[slice(*ENDING_GRAPHICS_LOAD_REGION)] != phase2[
            slice(*ENDING_GRAPHICS_LOAD_REGION)
        ]:
            errors.append("ending graphics loader changed")
        if phase3[0x0054B4:0x005804] != phase2[0x0054B4:0x005804]:
            errors.append("ending graphics source changed")
        ending_preload = bytes.fromhex("21 04 58 11 00 83 01 80 07 CD 4E 07")
        if phase3[slice(*ENDING_PRELOAD_GRAPHICS_LOAD_REGION)] != ending_preload:
            errors.append("ending preloaded graphics no longer occupy tiles 0x30-0xA7")
        if phase3[slice(*CREDITS_GRAPHICS_LOAD_REGION)] != phase2[
            slice(*CREDITS_GRAPHICS_LOAD_REGION)
        ]:
            errors.append("credits graphics loader changed")
        if phase3[0x004C22:0x005422] != phase2[0x004C22:0x005422]:
            errors.append("credits graphics source changed")
        if phase3[0x002C4C:0x002CC4] != phase2[0x002C4C:0x002CC4]:
            errors.append("credits tilemap source changed")
        if phase3[0x00B022:0x00B0A7] != phase2[0x00B022:0x00B0A7]:
            errors.append("credits/personnel script changed")

        expected_initials_wrapper = bytes(
            [0x28, 0x06, 0x3E, INITIALS_SELECTOR, 0xCD, 0xDC, 0x00, 0xC9, 0xC9]
        )
        initials_start, initials_end = INITIALS_PROMPT_REGION
        if phase3[initials_start : initials_start + len(expected_initials_wrapper)] != expected_initials_wrapper:
            errors.append("initials 12px prompt wrapper mismatch")
        if any(phase3[initials_start + len(expected_initials_wrapper) : initials_end]):
            errors.append("old initials prompt script was not fully cleared")
        if phase3[0x008811:0x008826] != phase2[0x008811:0x008826]:
            errors.append("initials common font/graphics loader changed")
        if phase3[0x008306:0x008316] != phase2[0x008306:0x008316]:
            errors.append("initials cursor sprite tile calculation changed")

        for start, end in ITEM_GRAPHICS_SOURCE_REGIONS:
            if phase3[start:end] != phase2[start:end]:
                errors.append(f"item/status graphics source changed at 0x{start:06X}")
        if phase3[0x017AF2:0x017B10] != phase2[0x017AF2:0x017B10]:
            errors.append("item/status graphics load sequence changed")
        if phase3[slice(*STATUS_DYNAMIC_REGION)] != phase2[slice(*STATUS_DYNAMIC_REGION)]:
            errors.append("oxygen bar/marker dynamic code changed")
        if phase3[STATUS_WINDOW_Y_OFFSET] != 0x72:
            errors.append("expanded status panel does not use WY=0x72")
        expected_oxygen_wrapper = bytes(
            [0x3E, OXYGEN_SELECTOR, 0xCD, 0xDC, 0x00, 0x00]
        )
        if phase3[slice(*OXYGEN_INLINE_REGION)] != expected_oxygen_wrapper:
            errors.append("oxygen 12px inline wrapper mismatch")
        expected_item_prefix = bytes(
            [0x3E, ITEM_SELECTOR, 0xCD, 0xDC, 0x00, 0xC9]
        )
        item_start, item_end = ITEM_RENDERER_REGION
        if phase3[item_start : item_start + len(expected_item_prefix)] != expected_item_prefix:
            errors.append("item 12px renderer wrapper mismatch")
        if any(phase3[item_start + len(expected_item_prefix) : item_end]):
            errors.append("old item-name renderer was not fully cleared")
        all_items_routine = make_all_items_routine()
        all_items_start = bank8_offset(ALL_ITEMS_ROUTINE_ADDR)
        if phase3[all_items_start : all_items_start + len(all_items_routine)] != all_items_routine:
            errors.append("all-items initialization routine mismatch")

        if phase3[0x017F81:0x018000] != phase2[0x017F81:0x018000]:
            errors.append("original oxygen bar graphics source changed")
        expected_bar_data = status_bar_tile_data(phase2)
        bar_data_start = bank8_offset(STATUS_BAR_DATA_ADDR)
        if phase3[bar_data_start : bar_data_start + len(expected_bar_data)] != expected_bar_data:
            errors.append("oxygen bar temporary tiles were not shifted down 3px")

        for page in ("ending", "initials", "item_status", "stage"):
            loader = bank8_offset(EXTENDED_LOADER_ADDRS[page])
            if phase3[loader + 24 : loader + 31] != bytes.fromhex(
                "11 00 83 01 00 00 C9"
            ):
                errors.append(f"{page} loader does not restore DE=0x8300 and BC=0")
        ending_loader = bank8_offset(EXTENDED_LOADER_ADDRS["ending"])
        expected_ending_loader = bytes.fromhex(
            "21 00 42 11 00 80 01 00 03 CD 09 2C "
            "21 00 5D 11 80 8A 01 80 05 CD 09 2C"
        )
        if phase3[ending_loader : ending_loader + 24] != expected_ending_loader:
            errors.append("ending high tiles are not loaded into VRAM 0x8A80-0x8FFF")
        initials_loader = bank8_offset(EXTENDED_LOADER_ADDRS["initials"])
        expected_initials_loader = bytes.fromhex(
            "21 00 54 11 00 80 01 00 03 CD 09 2C "
            "21 00 6A 11 00 84 01 E0 00 CD 09 2C"
        )
        if phase3[initials_loader : initials_loader + 24] != expected_initials_loader:
            errors.append("initials prompt tiles are not loaded into VRAM 0x8400-0x84DF")

    allocations: list[dict[str, str]] = []
    page_tiles: dict[str, dict[int, bytes]] = {}
    page_lines: dict[str, list[dict[str, object]]] = {}
    if phase2:
        try:
            page_tiles, page_lines, allocations = expected_layout_allocations(phase2)
        except (KeyError, ValueError) as error:
            errors.append(f"cannot regenerate 12px allocations: {error}")

    if phase3 and allocations:
        checked_storage_pages: set[str] = set()
        for page in (
            "stage",
            "access",
            "item_status",
            "ending",
            "initials",
            *sorted(DESC_PAGES),
        ):
            stored = storage_page(page)
            if stored in checked_storage_pages:
                continue
            checked_storage_pages.add(stored)
            source = page_source_offset(page)
            keep = preserved_codes(page)
            allocated = {
                int(row["tile_id"], 16)
                for row in allocations
                if row["page"] == page and int(row["tile_id"], 16) < page_limit(page)
            }
            for code in range(page_limit(page)):
                start = source + code * 8
                if code in keep:
                    if phase3[start : start + 8] != phase2[start : start + 8]:
                        errors.append(f"preserved {page} tile changed: 0x{code:02X}")
                elif code not in allocated and phase3[start : start + 8] != bytes(8):
                    errors.append(f"unused small tile was not cleared: {page}/0x{code:02X}")

        for row in allocations:
            page = row["page"]
            tile_id = int(row["tile_id"], 16)
            if page == "access" and tile_id == 0x44:
                errors.append("access text overwrites the border tile 0x44")
                break
            if page == "ending" and tile_id in ENDING_GRAPHICS_CODES:
                errors.append(f"ending text overwrites image tile 0x{tile_id:02X}")
                break
            if page == "initials" and tile_id in INITIALS_GRAPHICS_CODES:
                errors.append(f"initials text overwrites cursor tile 0x{tile_id:02X}")
                break
            if page == "item_status" and tile_id in ITEM_GRAPHICS_CODES:
                errors.append(f"item/status text overwrites image tile 0x{tile_id:02X}")
                break
            expected = bytes.fromhex(row["bytes_hex"])
            offset = allocation_offset(page, tile_id)
            if phase3[offset : offset + 8] != expected:
                errors.append(
                    f"ROM packed tile mismatch: {page}/{row['entry']}/0x{tile_id:02X}"
                )
                break

        expected_writes: dict[str, list[tuple[int, int, int]]] = {}
        for row in allocations:
            expected_writes.setdefault(row["page"], []).append(
                (int(row["tile_x"]), int(row["tile_y"]), int(row["tile_id"], 16))
            )
        for page in ("stage", "access", *sorted(DESC_PAGES), "ending", "initials"):
            try:
                actual = decode_script(phase3, script_start(phase3, page))
            except ValueError as error:
                errors.append(str(error))
                continue
            if actual != expected_writes[page]:
                errors.append(f"packed script writes do not match allocation: {page}")

        message_writes = [
            (int(row["tile_x"]), int(row["tile_y"]), int(row["tile_id"], 16))
            for row in allocations
            if row["page"] == "item_status" and row["entry"] == "message"
        ]
        oxygen_writes = [
            (int(row["tile_x"]), int(row["tile_y"]), int(row["tile_id"], 16))
            for row in allocations
            if row["page"] == "item_status" and row["entry"] == "air"
        ]
        try:
            if decode_script(phase3, NO_ITEMS_REGION[0]) != message_writes:
                errors.append("no-items script writes do not match allocation")
            oxygen_start = bank8_offset(OXYGEN_SCRIPT_ADDR)
            oxygen_body = phase3.find(
                bytes([0xD7, 0x82, 0x01]),
                oxygen_start,
                oxygen_start + 0x40,
            )
            if oxygen_body < 0:
                errors.append("oxygen routine is missing its packed text body")
            elif decode_script(phase3, oxygen_body, map_selector=1) != oxygen_writes:
                errors.append("oxygen script writes do not match allocation")
        except ValueError as error:
            errors.append(str(error))

        if page_lines:
            inventory_lines = [
                line
                for line in page_lines["item_status"]
                if line["entry"] not in {"message", "air"}
            ]
            expected_blob = build_item_routine_blob(inventory_lines)
            start = bank8_offset(ITEM_ROUTINE_BASE)
            if phase3[start : start + len(expected_blob)] != expected_blob:
                errors.append("item 12px draw routines do not match regenerated layouts")
            if any(
                value != 0xFF
                for value in phase3[
                    start + len(expected_blob) : bank8_offset(ITEM_ROUTINE_END)
                ]
            ):
                errors.append("unused item routine bank region is not cleared")

        access_ids = {
            int(row["tile_id"], 16) for row in allocations if row["page"] == "access"
        }
        access_high = sorted(tile_id for tile_id in access_ids if tile_id >= 0x30)
        if access_high != list(range(0x46, 0x6F)):
            errors.append("access denial tiles are not the safe 0x46-0x6E range")
        stage_ids = {
            int(row["tile_id"], 16) for row in allocations if row["page"] == "stage"
        }
        stage_high = sorted(tile_id for tile_id in stage_ids if tile_id >= 0x30)
        if stage_high != list(range(0xA7, 0xE3)):
            errors.append("stage high tiles are not the expected 0xA7-0xE2 range")
        ending_ids = {
            int(row["tile_id"], 16) for row in allocations if row["page"] == "ending"
        }
        ending_high = sorted(tile_id for tile_id in ending_ids if tile_id >= 0x30)
        if ending_high != list(range(0xA8, 0x100)):
            errors.append("ending high tiles are not the expected 0xA8-0xFF range")
        initials_ids = {
            int(row["tile_id"], 16)
            for row in allocations
            if row["page"] == "initials"
        }
        initials_high = sorted(tile_id for tile_id in initials_ids if tile_id >= 0x30)
        if initials_high != list(range(0x40, 0x4E)):
            errors.append("initials high tiles are not the safe 0x40-0x4D range")
        item_ids = {
            int(row["tile_id"], 16)
            for row in allocations
            if row["page"] == "item_status"
        }
        item_high = sorted(tile_id for tile_id in item_ids if tile_id >= 0x80)
        if item_high != list(range(0x80, 0xE0)):
            errors.append("item/status high tiles are not the expected 0x80-0xDF range")
    layout = load_layout() if LAYOUT_CSV.is_file() else {}
    for page, rows in layout.items():
        if page == "item_status":
            continue
        occupied: set[tuple[int, int]] = set()
        for row in rows:
            y = int(row["y_pixel"], 0)
            center_left = int(row["center_left"], 0)
            center_width = int(row["center_width"], 0)
            max_height = 256 if page in {"stage", "ending"} else 144
            if y < 0 or y + 12 > max_height:
                errors.append(f"layout vertical overflow: {page}/{row['entry']}")
            if center_left < 0 or center_left + center_width > 160:
                errors.append(f"layout horizontal area overflow: {page}/{row['entry']}")
            for tile_y in range(y // 8, (y + 11) // 8 + 1):
                key = (tile_y, center_left)
                if key in occupied:
                    errors.append(f"layout row overlap: {page}/{row['entry']}")
                occupied.add(key)

    if errors:
        print("\nTRANSLATION CHECK FAILED")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("\nTRANSLATION CHECK PASSED")


if __name__ == "__main__":
    main()
