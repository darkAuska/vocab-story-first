#!/usr/bin/env python3
"""Create a daily word pack by scanning a story draft first.

This keeps the old ordered picker intact. The story-first workflow is:

1. Write a natural English story draft.
2. Scan the draft for words that exist in the red-book word list.
3. Remove words already used in previous days.
4. Keep the first N matches in story order, mark first appearances, and
   create a daily pack.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PICK_PATH = SCRIPT_DIR / "pick_words.py"

spec = importlib.util.spec_from_file_location("pick_words", PICK_PATH)
pick = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pick)

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "before",
    "after",
    "again",
    "also",
    "any",
    "away",
    "back",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "me",
    "my",
    "nor",
    "not",
    "of",
    "on",
    "or",
    "our",
    "ours",
    "she",
    "so",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "they",
    "this",
    "to",
    "too",
    "us",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "why",
    "who",
    "whom",
    "whose",
    "will",
    "with",
    "would",
    "you",
    "your",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

IRREGULAR_LEMMAS = {
    "ate": "eat",
    "began": "begin",
    "begun": "begin",
    "brought": "bring",
    "caught": "catch",
    "chose": "choose",
    "chosen": "choose",
    "felt": "feel",
    "found": "find",
    "gave": "give",
    "given": "give",
    "gone": "go",
    "grew": "grow",
    "heard": "hear",
    "held": "hold",
    "kept": "keep",
    "knew": "know",
    "laid": "lay",
    "led": "lead",
    "left": "leave",
    "lost": "lose",
    "made": "make",
    "met": "meet",
    "paid": "pay",
    "ran": "run",
    "read": "read",
    "rose": "rise",
    "said": "say",
    "sent": "send",
    "shook": "shake",
    "shown": "show",
    "spoke": "speak",
    "spoken": "speak",
    "stood": "stand",
    "taught": "teach",
    "thought": "think",
    "told": "tell",
    "took": "take",
    "wore": "wear",
    "worn": "wear",
    "wrote": "write",
}


def read_json(path: Path) -> dict:
    if not path.exists():
        return {"lists": {}}
    return json.loads(pick.read_text(path))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_entries(word_list: Path, cache_dir: Path) -> tuple[list[dict[str, str]], str, list[Path]]:
    paths = pick.discover_source_paths(word_list)
    entries, state_text = pick.read_all_entries(paths, cache_dir)
    return entries, state_text, paths


def state_for_list(state: dict, list_hash: str, word_list: Path) -> dict:
    state.setdefault("lists", {})
    return state["lists"].setdefault(
        list_hash,
        {
            "source_path": str(word_list),
            "created_at": dt.datetime.now().isoformat(timespec="seconds"),
            "used_words": [],
            "history": [],
        },
    )


def scannable_text(markdown: str) -> str:
    """Prefer EN lines when present; otherwise scan prose and skip CN/table/code."""
    en_lines: list[str] = []
    in_code = False
    prose_lines: list[str] = []

    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("EN:"):
            en_lines.append(line[3:].strip())
            continue
        if line.startswith(("CN:", "|", "#", ">", "- 日期：", "- 主题：")):
            continue
        if any("\u4e00" <= char <= "\u9fff" for char in line):
            continue
        prose_lines.append(raw)

    return "\n".join(en_lines or prose_lines)


def lemma_candidates(token: str) -> list[str]:
    raw = token.lower().strip("'")
    if raw.endswith("'s"):
        raw = raw[:-2]
    candidates = [raw]
    if raw in IRREGULAR_LEMMAS:
        candidates.append(IRREGULAR_LEMMAS[raw])
    if len(raw) > 4 and raw.endswith("ies"):
        candidates.append(raw[:-3] + "y")
    if len(raw) > 4 and raw.endswith("ied"):
        candidates.append(raw[:-3] + "y")
    if len(raw) > 5 and raw.endswith("ing"):
        stem = raw[:-3]
        candidates.append(stem)
        if len(stem) > 2 and stem[-1] == stem[-2]:
            candidates.append(stem[:-1])
        candidates.append(stem + "e")
    if len(raw) > 4 and raw.endswith("ed"):
        stem = raw[:-2]
        candidates.append(stem)
        if len(stem) > 2 and stem[-1] == stem[-2]:
            candidates.append(stem[:-1])
        candidates.append(stem + "e")
    if len(raw) > 3 and raw.endswith("es"):
        candidates.append(raw[:-2])
    if len(raw) > 3 and raw.endswith("s"):
        candidates.append(raw[:-1])
    deduped: list[str] = []
    for item in candidates:
        if item and item not in deduped:
            deduped.append(item)
    return deduped


def scan_story(
    draft_text: str,
    entries: list[dict[str, str]],
    used_words: set[str],
    count: int,
) -> tuple[list[dict[str, str]], dict[str, str], int]:
    entry_by_key = {
        entry["key"]: entry
        for entry in entries
        if " " not in entry["key"] and len(entry["key"]) > 2 and entry["key"] not in STOP_WORDS
    }
    selected: list[dict[str, str]] = []
    selected_keys: set[str] = set()
    first_surface: dict[str, str] = {}
    total_redbook_hits = 0

    for match in TOKEN_RE.finditer(scannable_text(draft_text)):
        surface = match.group(0)
        chosen_key = ""
        for candidate in lemma_candidates(surface):
            if candidate in entry_by_key:
                chosen_key = candidate
                break
        if not chosen_key:
            continue
        total_redbook_hits += 1
        if chosen_key in used_words or chosen_key in selected_keys:
            continue
        selected_keys.add(chosen_key)
        first_surface[chosen_key] = surface
        selected.append(entry_by_key[chosen_key])
        if len(selected) >= count:
            break

    return selected, first_surface, total_redbook_hits


def mark_first_appearances(markdown: str, selected_keys: set[str]) -> str:
    marked: set[str] = set()
    in_code = False

    def mark_line(line: str) -> str:
        if line.strip().startswith("CN:"):
            return line

        def repl(match: re.Match) -> str:
            surface = match.group(0)
            for candidate in lemma_candidates(surface):
                if candidate in selected_keys and candidate not in marked:
                    marked.add(candidate)
                    return f"**{surface}**"
            return surface

        return TOKEN_RE.sub(repl, line)

    output: list[str] = []
    for raw in markdown.splitlines():
        if raw.strip().startswith("```"):
            in_code = not in_code
            output.append(raw)
            continue
        output.append(raw if in_code else mark_line(raw))
    return "\n".join(output) + ("\n" if markdown.endswith("\n") else "")


def story_first_pack(
    *,
    date_text: str,
    day_no: int,
    theme: str,
    source_label: str,
    selected: list[dict[str, str]],
    remaining_after: int,
    marked_story: str,
    total_redbook_hits: int,
) -> str:
    base_pack = pick.build_task_pack(
        date_text=date_text,
        day_no=day_no,
        theme=theme,
        source_label=source_label,
        selected=selected,
        remaining_after=remaining_after,
    )
    words_inline = ", ".join(entry["word"] for entry in selected)
    return f"""{base_pack}

## story-first 扫描结果

- 模式：先写故事，再从故事中回收红宝书未用词
- 故事中红宝书命中次数：{total_redbook_hits}
- 本次保留的新词数：{len(selected)}
- 去重规则：同一词头只保留首次命中；已在历史中使用过的词跳过
- 词形规则：支持常见复数、过去式、过去分词、现在分词和少量不规则词回到词头

## story-first 已标记故事草稿

{marked_story.rstrip()}

## story-first 纯词列表

```text
{words_inline}
```
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Vocabulary project root. Defaults to the current directory.")
    parser.add_argument("--word-list", help="Path to the red-book word list directory. Defaults to PROJECT_ROOT/单词表.")
    parser.add_argument("--state", help="Path to vocab_state.json. Defaults to PROJECT_ROOT/状态/vocab_state.json.")
    parser.add_argument("--output-dir", help="Output directory. Defaults to PROJECT_ROOT/每日任务.")
    parser.add_argument("--story-draft", required=True, help="Markdown or text file containing the story draft.")
    parser.add_argument("--count", type=int, default=200, help="How many unused red-book words to keep.")
    parser.add_argument("--theme", default="命运石之门：story-first自然故事", help="Daily story theme.")
    parser.add_argument("--date", default=None, help="Date string, default is today.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without updating state.")
    parser.add_argument("--allow-short", action="store_true", help="Write a pack even when fewer than count words are found.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    word_list = Path(args.word_list).resolve() if args.word_list else project_root / "单词表"
    draft_path = Path(args.story_draft).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else project_root / "每日任务"
    state_path = Path(args.state).resolve() if args.state else project_root / "状态" / "vocab_state.json"

    entries, state_text, source_paths = source_entries(word_list, project_root / "状态" / "cache")
    if not entries:
        raise SystemExit("No English words were found in the source word list.")

    list_hash = hashlib.sha256(state_text.encode("utf-8", errors="replace")).hexdigest()[:16]
    state = read_json(state_path)
    list_state = state_for_list(state, list_hash, word_list)
    used = set(list_state.get("used_words", []))

    draft_text = pick.read_text(draft_path)
    selected, first_surface, total_redbook_hits = scan_story(draft_text, entries, used, args.count)
    if len(selected) < args.count and not args.allow_short:
        raise SystemExit(
            f"Story-first found only {len(selected)} unused red-book words, requested {args.count}. "
            "Expand the story draft and run again, or pass --allow-short for a diagnostic pack."
        )

    date_text = args.date or dt.date.today().isoformat()
    day_no = len(list_state.get("history", [])) + 1
    selected_keys = [entry["key"] for entry in selected]
    remaining_after = len([entry for entry in entries if entry["key"] not in used]) - len(selected)
    marked_story = mark_first_appearances(draft_text, set(selected_keys))
    md = story_first_pack(
        date_text=date_text,
        day_no=day_no,
        theme=args.theme,
        source_label=", ".join(str(path) for path in source_paths),
        selected=selected,
        remaining_after=remaining_after,
        marked_story=marked_story,
        total_redbook_hits=total_redbook_hits,
    )

    safe_theme = re.sub(r'[\\/:*?"<>|\s]+', "_", args.theme).strip("_") or "story_first"
    output_path = output_dir / f"{date_text}_Day{day_no:03d}_{safe_theme}_story-first抽词包.md"

    if args.dry_run:
        print(md)
        print(f"Selected words: {len(selected)}")
        print("First surfaces:", ", ".join(f"{key}={first_surface.get(key, key)}" for key in selected_keys[:30]))
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")

    list_state["used_words"] = sorted(used.union(selected_keys))
    list_state["source_path"] = str(word_list)
    list_state["last_used_at"] = dt.datetime.now().isoformat(timespec="seconds")
    list_state.setdefault("history", []).append(
        {
            "date": date_text,
            "day_no": day_no,
            "theme": args.theme,
            "selection": "story-first",
            "count": len(selected),
            "output_path": str(output_path),
            "story_draft": str(draft_path),
            "total_redbook_hits": total_redbook_hits,
            "words": selected_keys,
        }
    )
    write_json(state_path, state)

    print(f"Created: {output_path}")
    print(f"Selected words: {len(selected)}")
    print(f"Remaining unused words: {remaining_after}")
    print(f"Story red-book hits: {total_redbook_hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
