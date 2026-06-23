#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REFERENCES = SKILL_DIR / "references"

REFERENCE_TO_TEMPLATE = {
    "story-first-mode.md": "story-first模式.md",
    "natural-scene-rules.md": "场景自然融入规则.md",
    "bilingual-format-rules.md": "中英呈现规则.md",
    "romance-interaction-rules.md": "甜甜恋爱互动规则.md",
    "online-etymology-rules.md": "联网词根词源要求.md",
    "review-loop.md": "背诵闭环.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a vocabulary-story project directory.")
    parser.add_argument("--project-root", required=True, help="Target project root.")
    parser.add_argument("--overwrite-templates", action="store_true", help="Overwrite existing template files.")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    for name in ("单词表", "每日任务", "状态", "模板"):
        (root / name).mkdir(parents=True, exist_ok=True)

    for source_name, target_name in REFERENCE_TO_TEMPLATE.items():
        source = REFERENCES / source_name
        target = root / "模板" / target_name
        if target.exists() and not args.overwrite_templates:
            continue
        shutil.copyfile(source, target)

    readme = root / "模板" / "人物设定与故事背景模板.md"
    if not readme.exists() or args.overwrite_templates:
        readme.write_text(
            "# 人物设定与故事背景\n\n"
            "在这里写角色、关系、世界观、故事风格和禁忌。story-first 模式会优先保持正常故事感，再回收词表词汇。\n",
            encoding="utf-8",
        )

    print(f"Initialized vocabulary project: {root}")
    print(f"Put word-list .md/.txt/.csv/.pdf files into: {root / '单词表'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
