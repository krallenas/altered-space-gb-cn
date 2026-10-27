<div align="center">

**中文 | [English](README_EN.md)**

</div>

# Altered Space GB Chinese Translation (汉化版)

An unofficial Chinese fan translation of the Game Boy game *Altered Space: A 3-D Alien Adventure* (1991, published by Sony Imagesoft).

This project provides a complete build toolchain: starting from the original English ROM, a Python pipeline generates the Chinese ROM directly — fully reproducible and verifiable. The translation was AI-assisted and manually reviewed.

## Features

- **Dual-font scheme**: 12px pixel line-bitmap large text (Zpix) + 7px bitmap small text (DinkieBitmap); Chinese glyphs can span multiple 8×8 tiles
- **Fully scripted build**: one command turns the original ROM into the Chinese version, no manual patching
- **Strictly verifiable**: SHA256 baselines for both input and output ROMs, with a built-in verifier for translation sync, tile ranges and checksums
- **Complete translation table**: ~40 reviewed entries covering UI, items, characters, stages and the ending

## Usage

### 1. Prepare the original ROM

This repository **does not contain any game ROM**. Prepare the US retail ROM yourself and name it:

```
Altered Space - A 3-D Alien Adventure (USA).gb
```

Place it in the repository root. Its SHA256 should be:

```
4F6450321EE163D5FD8A942816B10AF1CE41BBCAD62185A550C97B16CAC125A1
```

### 2. Build

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python scripts/sync_translation_review.py
python scripts/build_translation.py
python scripts/verify_translation.py
```

On success, the Chinese ROM is generated in the root directory:

```
Altered Space - A 3-D Alien Adventure (USA).zh.gb
```

SHA256 of the current official output:

```
A1C223C9DF82D1AC7CC17AE7BA2002EB720D8586970CD5EA5B788B9B677743BB
```

Load the resulting `.zh.gb` into any Game Boy emulator to play.

## Repository Layout

| Path | Description |
|---|---|
| `scripts/translation_base.py` | Original ROM structure, text pages and base patch definitions |
| `scripts/build_translation.py` | Builds the official Chinese ROM from the original ROM |
| `scripts/verify_translation.py` | Verifies input, output, translation sync, tile ranges and checksums |
| `scripts/small_text_builder.py` | Builds the 7px base translation layer in memory |
| `scripts/large_text_font.py` | Reads native 12px glyphs from zpix and packs full-line pixels |
| `scripts/build_small_font_data.py` | Rebuilds small-font glyph data when adding new 7px characters |
| `scripts/render_native_pixel_glyph.py` | Helper for inspecting a single native pixel glyph |
| `scripts/sync_translation_review.py` | Rebuilds the Markdown review table from the review CSV |
| `text/source_text.csv` | Offsets, lengths, English source text and script groups |
| `text/translation_review.csv` | The single source of truth for the Chinese translations |
| `text/large_text_layout.csv` | Pixel positions and tweaks for 12px full-line bitmap text |
| `text/small_text_layout.csv` | 7px base layout required before building the 12px overlay |
| `font_data/small_font_glyphs.csv` | 7px Chinese glyph data read directly by the build |
| `fonts/` | 7px / 12px font sources |
| `TRANSLATION_REVIEW.md` | Full English–Chinese review table (auto-generated) |

## Technical Notes

- 12px text is packed as full-line pixel bitmaps and may span 8×8 tiles; no reusable large-glyph table is built
- The access-denied page graphics occupy tiles `0x30–0x45`; text starts at dedicated tile `0x46`
- Ending graphics occupy `0x30–0xA7`; ending text uses `0xA8–0xFF`
- Item graphics `0x28–0x7F` must be preserved; `$C00B–$C00E` belong to the text-stream state
- Credits, copyright lines and `GAME OVER` remain in the original English
- The Chinese ROM is expanded to 256KB (extended font resources live in bank 0x08)

To edit translations, modify `text/translation_review.csv` and the relevant layout CSVs, then rebuild as described above.

## Font Credits

- [Zpix pixel font](https://github.com/SolidZORO/zpix-pixel-font): source of the 12px large text (free for personal, non-commercial use)
- [DinkieBitmap 7px Demo](https://atipo.co.uk): source of the 7px small text (demo version)

## Disclaimer

This project is for technical research and learning purposes only and is not affiliated with the original copyright holders. The repository does not include or distribute any game ROM; please provide a legally obtained original ROM and support the official release.

## License

Build scripts and documentation are released under the [MIT License](LICENSE). All game-related content (ROM, graphics, original text) remains the property of its respective copyright holders and is NOT covered by this license.
