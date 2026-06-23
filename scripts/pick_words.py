#!/usr/bin/env python3
"""Pick non-repeating daily vocabulary words and create a Markdown task pack."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import re
import sys
from pathlib import Path


WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
MD_WORD_HEADING_RE = re.compile(r"^##\s+([A-Za-z][A-Za-z' -]*)\s*$", re.MULTILINE)
SOURCE_ORDER = ("上", "中", "下")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def read_pdf_text(path: Path, cache_dir: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SystemExit(
            "PDF input requires the Python package 'pypdf'. "
            "Install it or convert the PDF to a txt/csv word list first."
        ) from exc

    stat = path.stat()
    safe_stem = re.sub(r'[\\/:*?"<>|\s]+', "_", path.stem).strip("_")
    cache_path = cache_dir / f"{safe_stem}_{stat.st_size}_{stat.st_mtime_ns}.txt"
    if cache_path.exists():
        return read_text(cache_path)

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        chunks.append(f"\n\n--- PDF PAGE {page_no} ---\n\n{text}")

    output = "\n".join(chunks)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(output, encoding="utf-8")
    return output


def read_source_text(path: Path, cache_dir: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return read_pdf_text(path, cache_dir)
    return read_text(path)


def discover_source_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise SystemExit(f"Word list path is neither a file nor a directory: {path}")

    files = [item for item in path.iterdir() if item.is_file() and item.suffix.lower() in {".md", ".txt", ".csv", ".pdf"}]
    if not files:
        raise SystemExit(f"No supported word list files found in: {path}")

    md_files = [item for item in files if item.suffix.lower() == ".md"]
    if md_files:
        files = md_files

    def sort_key(item: Path) -> tuple[int, str]:
        name = item.name
        for index, marker in enumerate(SOURCE_ORDER):
            if marker in name:
                return (index, name)
        return (len(SOURCE_ORDER), name)

    return sorted(files, key=sort_key)


def extract_meaning(block: str) -> str:
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("【词义】"):
            return line.replace("【词义】", "", 1).strip()

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("!") or line.startswith("<") or line.startswith("["):
            continue
        if "【助记】" in line or "【派生】" in line or "【辨析】" in line:
            continue
        if any("\u4e00" <= char <= "\u9fff" for char in line):
            return line
    return ""


def extract_markdown_heading_entries(text: str, source_name: str) -> list[dict[str, str]]:
    matches = list(MD_WORD_HEADING_RE.finditer(text))
    if not matches:
        return []

    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    line_starts = [0]
    for match in re.finditer(r"\n", text):
        line_starts.append(match.end())

    def line_number(offset: int) -> int:
        lo, hi = 0, len(line_starts)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid
        return lo + 1

    for index, match in enumerate(matches):
        word = " ".join(match.group(1).split())
        key = word.lower()
        if key in seen:
            continue
        seen.add(key)

        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        meaning = extract_meaning(block)
        source = f"{word}：{meaning}" if meaning else word
        entries.append(
            {
                "word": word,
                "key": key,
                "line": str(line_number(match.start())),
                "source": source,
                "source_file": source_name,
                "meaning": meaning,
            }
        )
    return entries


def extract_entries(text: str, source_name: str = "") -> list[dict[str, str]]:
    md_entries = extract_markdown_heading_entries(text, source_name)
    if md_entries:
        return md_entries

    entries: list[dict[str, str]] = []
    seen: set[str] = set()

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = WORD_RE.search(line)
        if not match:
            continue

        display = match.group(0).strip()
        key = display.lower()
        if key in seen:
            continue

        seen.add(key)
        entries.append(
            {
                "word": display,
                "key": key,
                "line": str(line_no),
                "source": line,
                "source_file": source_name,
                "meaning": "",
            }
        )

    return entries


def read_all_entries(paths: list[Path], cache_dir: Path) -> tuple[list[dict[str, str]], str]:
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    hash_parts: list[str] = []

    for path in paths:
        text = read_source_text(path, cache_dir)
        hash_parts.append(str(path))
        hash_parts.append(text)
        for entry in extract_entries(text, path.name):
            if entry["key"] in seen:
                continue
            seen.add(entry["key"])
            entries.append(entry)

    return entries, "\n".join(hash_parts)


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"lists": {}}
    return json.loads(read_text(path))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def markdown_word_table(entries: list[dict[str, str]]) -> str:
    lines = ["| # | word | source file | source line | source text |", "|---:|---|---|---:|---|"]
    for idx, entry in enumerate(entries, start=1):
        source = entry["source"].replace("|", "\\|")
        source_file = entry.get("source_file", "").replace("|", "\\|")
        lines.append(f"| {idx} | {entry['word']} | {source_file} | {entry['line']} | {source} |")
    return "\n".join(lines)


def build_task_pack(
    *,
    date_text: str,
    day_no: int,
    theme: str,
    source_label: str,
    selected: list[dict[str, str]],
    remaining_after: int,
) -> str:
    words_inline = ", ".join(entry["word"] for entry in selected)
    table = markdown_word_table(selected)
    target_words_block = "\n".join(
        f"- {entry['word']}：{entry.get('meaning') or entry['source']}" for entry in selected
    )

    return f"""# {date_text} Day {day_no:03d} 抽词包

## 元信息

- 日期：{date_text}
- 主题：{theme}
- 单词表：`{source_label}`
- 今日目标词数：{len(selected)}
- 本次抽取后剩余未用词数：{remaining_after}

## 今日 200 词

{table}

## 可直接复制给 AI 的生成提示词

你是一个“游戏化背单词场景编剧 + 考研英语助教”。请根据下面的主题、人物设定和目标词，生成一份完整 Markdown 背诵文件。

### 今日主题

{theme}

### 人物设定与故事背景

优先读取 `模板/当前人物设定与故事背景.md`、`模板/命运石之门生成约束.md`、`模板/中英呈现规则.md`、`模板/人物互动日常规则.md`、`模板/甜甜恋爱互动规则.md`、`模板/起点日轻恋爱桥段规则.md`、`模板/联网词根词源要求.md` 和 `模板/场景自然融入规则.md`。如果当天另有新设定，再把新设定粘贴到这里覆盖默认设定。

### 今日目标词

{target_words_block}

### 强制规则

1. 必须使用全部目标词，不能遗漏。
2. 每个目标词第一次出现时必须用 Markdown 粗体 `**word**` 标记。
3. 目标词要自然嵌入游戏对话场景，可以加入非目标词，但不要让非目标词喧宾夺主。
4. 每 15-25 个目标词分成一幕。
5. 每幕结束后列出本幕目标词和中文提示。
6. 生成主动回忆测验：英译中 30 题、中译英 30 题、完形填空 20 题。
7. 最后做覆盖率自检，输出目标词数、已覆盖词数、缺失词。若有缺失，补写一段覆盖缺失词。
8. 使用原作设定和人物关系，但每天写原创支线任务，不要大段复刻原作剧情或连续照搬原作台词。
9. 正文英文先行，中文延迟出现；不要全篇一句英文一句中文直译。
10. 目标词第一次出现的关键句可以用 `EN / CN / Word` 三行格式解释，目标词第二次及以后出现时只保留英文正文。
11. 每幕必须有足够人物互动和日常细节，至少安排 2-3 个角色互相说话或行动；不要写成实验报告或单词例句合集。
12. 每幕至少安排一个甜甜的恋爱互动钩子：嘴硬关心、吃醋误会、被旁人起哄、共同解谜、互相照顾或告白未遂均可。
13. 恋爱互动必须清甜、暧昧、轻喜剧，不写露骨内容，不让人物脱离原本性格。
14. 每幕后的目标词小结必须包含：单词、发音、中文提示、词根/助记、例句、历史渊源/词源。
15. 如果本地词表没有明确词根、助记或历史词源，不能写“本地没有”就结束；必须联网查询高置信来源后补全。词源优先 Online Etymology Dictionary 和 Merriam-Webster，发音优先 Cambridge Dictionary 和 Merriam-Webster，并在小结表中保留来源名或链接。
16. `CN:` 行必须以中文为主，英文只能放在括号里；人物名、道具、桥段名要中文化。目标词写成“中文释义（English word）”，不要写成“English word（中文释义）”。
16. 输出文件内容即可，不要解释写作过程。

### 输出文件名建议

`每日任务/{date_text}_Day{day_no:03d}_{theme}_完整背诵.md`

## 纯词列表

```text
{words_inline}
```
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Vocabulary project root. Defaults to the current directory.")
    parser.add_argument("--word-list", help="Path to the source word list file or directory. Defaults to PROJECT_ROOT/单词表.")
    parser.add_argument("--state", help="Path to vocab_state.json. Defaults to PROJECT_ROOT/状态/vocab_state.json.")
    parser.add_argument("--output-dir", help="Output directory. Defaults to PROJECT_ROOT/每日任务.")
    parser.add_argument("--count", type=int, default=200, help="How many unused words to pick.")
    parser.add_argument("--theme", default="游戏对话场景", help="Daily story theme.")
    parser.add_argument("--selection", choices=("ordered", "random"), default="ordered", help="Pick words in source order or randomly.")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed.")
    parser.add_argument("--date", default=None, help="Date string, default is today.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without updating state.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    word_list = Path(args.word_list).resolve() if args.word_list else project_root / "单词表"
    source_paths = discover_source_paths(word_list)
    state_path = Path(args.state).resolve() if args.state else project_root / "状态" / "vocab_state.json"
    output_dir = Path(args.output_dir).resolve() if args.output_dir else project_root / "每日任务"

    entries, state_text = read_all_entries(source_paths, project_root / "状态" / "cache")
    if not entries:
        raise SystemExit("No English words were found in the source word list.")

    list_hash = hashlib.sha256(state_text.encode("utf-8", errors="replace")).hexdigest()[:16]
    state = load_state(state_path)
    state.setdefault("lists", {})
    list_state = state["lists"].setdefault(
        list_hash,
        {
            "source_path": str(word_list),
            "created_at": dt.datetime.now().isoformat(timespec="seconds"),
            "used_words": [],
            "history": [],
        },
    )

    used = set(list_state.get("used_words", []))
    unused = [entry for entry in entries if entry["key"] not in used]
    if len(unused) < args.count:
        raise SystemExit(
            f"Not enough unused words: requested {args.count}, available {len(unused)}. "
            "Use a larger list or reset state deliberately."
        )

    if args.selection == "random":
        rng = random.Random(args.seed)
        selected = rng.sample(unused, args.count)
        selected.sort(key=lambda item: item["word"].lower())
    else:
        selected = unused[: args.count]
    date_text = args.date or dt.date.today().isoformat()
    day_no = len(list_state.get("history", [])) + 1
    remaining_after = len(unused) - len(selected)
    md = build_task_pack(
        date_text=date_text,
        day_no=day_no,
        theme=args.theme,
        source_label=", ".join(str(path) for path in source_paths),
        selected=selected,
        remaining_after=remaining_after,
    )

    safe_theme = re.sub(r'[\\/:*?"<>|\s]+', "_", args.theme).strip("_") or "theme"
    output_path = output_dir / f"{date_text}_Day{day_no:03d}_{safe_theme}_抽词包.md"

    if args.dry_run:
        print(md)
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")

    selected_keys = [entry["key"] for entry in selected]
    list_state["used_words"] = sorted(used.union(selected_keys))
    list_state["source_path"] = str(word_list)
    list_state["last_used_at"] = dt.datetime.now().isoformat(timespec="seconds")
    list_state.setdefault("history", []).append(
        {
            "date": date_text,
            "day_no": day_no,
            "theme": args.theme,
            "selection": args.selection,
            "count": len(selected),
            "output_path": str(output_path),
            "words": selected_keys,
        }
    )
    save_state(state_path, state)

    print(f"Created: {output_path}")
    print(f"Selected words: {len(selected)}")
    print(f"Remaining unused words: {remaining_after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
