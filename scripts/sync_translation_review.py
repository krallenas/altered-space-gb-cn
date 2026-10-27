from __future__ import annotations

import csv
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
REVIEW_CSV = WORKSPACE / "text" / "translation_review.csv"
REVIEW_MARKDOWN = WORKSPACE / "TRANSLATION_REVIEW.md"


def load_rows(path: Path = REVIEW_CSV) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# 最新中英译文对照表",
        "",
        "本文件由 `text/translation_review.csv` 自动生成，禁止手工修改。",
    ]
    current_category = None
    for row in rows:
        category = row["category"]
        if category != current_category:
            lines.extend(
                [
                    "",
                    f"## {category}",
                    "",
                    "| 英文 | 当前中文 | 字体 | 状态 | 说明 |",
                    "|---|---|---|---|---|",
                ]
            )
            current_category = category
        values = [
            row["english"],
            row["current_chinese"],
            row["font"],
            row["status"],
            row["notes"],
        ]
        lines.append("| " + " | ".join(escape_cell(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    content = render_markdown(load_rows())
    with REVIEW_MARKDOWN.open("w", encoding="utf-8", newline="\n") as output:
        output.write(content)
    print(f"updated={REVIEW_MARKDOWN}")


if __name__ == "__main__":
    main()
