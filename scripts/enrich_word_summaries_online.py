#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from bs4 import BeautifulSoup


SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_PATH = Path.cwd() / "状态" / "online_word_cache.json"
GEN_PATH = SCRIPT_DIR / "generate_full_story.py"

spec = importlib.util.spec_from_file_location("gen", GEN_PATH)
gen = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gen)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_md(text: str, limit: int = 220) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("|", " / ")
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def zh_etymology_text(text: str, *, hint: str = "", limit: int = 360) -> str:
    """Summarize Etymonline snippets in Chinese rather than mechanically translating them."""
    raw = clean_md(text, 1200).replace("据 Etymonline：", "")

    def date_zh(s: str) -> str:
        patterns = [
            (r"early\s+(\d+)(?:st|nd|rd|th)c\.", r"\1 世纪早期"),
            (r"late\s+(\d+)(?:st|nd|rd|th)c\.", r"\1 世纪晚期"),
            (r"mid-?(\d+)(?:st|nd|rd|th)c\.", r"\1 世纪中期"),
            (r"(\d+)(?:st|nd|rd|th)c\.", r"\1 世纪"),
            (r"c\.\s*(\d{3,4})", r"约 \1 年"),
            (r"(\d{4})s", r"\1 年代"),
        ]
        for pattern, repl in patterns:
            m = re.search(pattern, s)
            if m:
                return re.sub(pattern, repl, m.group(0))
        return ""

    lang_map = [
        ("Old French", "古法语"),
        ("Middle French", "中古法语"),
        ("French", "法语"),
        ("Middle Dutch", "中古荷兰语"),
        ("Middle Low German", "中古低地德语"),
        ("Old Norse", "古诺尔斯语"),
        ("Medieval Latin", "中世纪拉丁语"),
        ("Late Latin", "晚期拉丁语"),
        ("Latin", "拉丁语"),
        ("Greek", "希腊语"),
        ("Old English", "古英语"),
        ("Middle English", "中古英语"),
        ("Proto-Germanic", "原始日耳曼语"),
        ("PIE root", "原始印欧语词根"),
    ]
    sources: list[str] = []
    for en, zh in lang_map:
        for match in re.finditer(rf"from {re.escape(en)}\s+([^,.;]+)", raw):
            form = match.group(1).strip()
            form = re.sub(r"\s+", " ", form)
            form = re.split(r'\s+"|\s+\(|\s+or directly|\s+and directly|\s+and/or', form, maxsplit=1)[0].strip()
            form = form.replace(" and ", " 和 ")
            form = form.strip(" )(")
            if form and len(form) < 80:
                item = f"源自{zh} {form}"
                if item not in sources:
                    sources.append(item)

    if "merger of two obsolete verbs" in raw:
        m = re.search(r"merger of two obsolete verbs,?\s*([^.;]+)", raw)
        if m:
            forms = m.group(1).strip().replace(" and ", " 和 ")
            sources.append(f"由两个已废弃动词合并而来：{forms}")
    if "echoic origin" in raw:
        sources.append("很可能属于拟声来源")
    if "unknown origin" in raw:
        sources.append("词源不明，需按权威词典保守记忆")
    if "past participle" in raw:
        sources.append("含过去分词构词线索")
    if "diminutive" in raw:
        sources.append("含指小词构词线索")
    if "agent noun" in raw:
        sources.append("含施事名词构词线索")
    if "noun of action" in raw:
        sources.append("含动作名词构词线索")

    date = date_zh(raw)
    parts = []
    if date:
        parts.append(f"{date}已有相关用法")
    if sources:
        parts.append("；".join(sources[:3]))
    if not parts:
        parts.append("可追溯到 Etymonline 记录的早期英语或欧洲语源线索")
    if hint and hint != "见词表释义":
        parts.append(f"记忆时联系中文义“{hint}”")
    return clean_md("据 Etymonline：" + "；".join(parts) + "。", limit)


def fetch(url: str, timeout: int = 8) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_etymonline(word: str) -> dict[str, str]:
    url = f"https://www.etymonline.com/word/{word}"
    try:
        text = fetch(url)
    except Exception as exc:
        return {"url": url, "etymology": f"未抓取到 Etymonline：{type(exc).__name__}", "root": "需人工复核"}

    soup = BeautifulSoup(text, "html.parser")
    plain = soup.get_text("\n")
    marker = f"Origin and history of  {word}"
    start = plain.lower().find(marker.lower())
    if start == -1:
        start = plain.lower().find(f"\n{word}\n")
    section = plain[start : start + 2500] if start >= 0 else plain[:2500]
    stop_match = re.search(r"\nEntries linking to|\nalso from|\nAdvertisement|\nMore to explore", section)
    if stop_match:
        section = section[: stop_match.start()]
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    lines = [line for line in lines if line not in {"Search", "Log in", "Columns", "Forum", "Apps", "Premium"}]

    ety = " ".join(lines[:12])
    ety = re.sub(r"Origin and history of\s+", "", ety, flags=re.I)
    ety = re.sub(rf"^{re.escape(word)}\s+{re.escape(word)}\s*", f"{word} ", ety, flags=re.I)
    ety = clean_md(ety, 360)

    root = ety
    from_match = re.search(r"(from [^.。;]+(?:[.;]|$))", ety, flags=re.I)
    if from_match:
        root = from_match.group(1)
    root = clean_md(f"据 Etymonline：{root}", 220)
    etymology = clean_md(f"据 Etymonline：{ety}", 360)
    return {"url": url, "etymology": etymology, "root": root}


def extract_cambridge(word: str) -> dict[str, str]:
    url = f"https://dictionary.cambridge.org/dictionary/english/{word}"
    try:
        text = fetch(url)
    except Exception as exc:
        return {"url": url, "pronunciation": "", "definition": "", "example": f"未抓取到 Cambridge：{type(exc).__name__}"}

    soup = BeautifulSoup(text, "html.parser")
    ipas = []
    for node in soup.select("span.ipa"):
        ipa = node.get_text(strip=True)
        if ipa and ipa not in ipas:
            ipas.append(ipa)
    defs = [node.get_text(" ", strip=True) for node in soup.select(".def")]
    examples = [node.get_text(" ", strip=True) for node in soup.select(".examp")]

    pronunciation = " / ".join(f"/{ipa}/" for ipa in ipas[:2])
    definition = clean_md(defs[0], 160) if defs else ""
    example = clean_md(examples[0], 180) if examples else definition
    return {"url": url, "pronunciation": pronunciation, "definition": definition, "example": example}


def enrich_word(word: str, cache: dict) -> dict:
    key = word.lower()
    cached = cache.get(key)
    if is_valid_cached(cached):
        return cached

    cambridge = extract_cambridge(word)
    etymonline = extract_etymonline(word)

    entry = {
        "version": 2,
        "word": word,
        "pronunciation": cambridge.get("pronunciation") or "需复核",
        "definition": cambridge.get("definition") or "",
        "example": cambridge.get("example") or "见正文语境例句",
        "root": etymonline.get("root") or "需人工复核",
        "etymology": etymonline.get("etymology") or "需人工复核",
        "source": f"Etymonline: {etymonline.get('url')}; Cambridge: {cambridge.get('url')}",
    }
    cache[key] = entry
    return entry


def is_valid_cached(entry: dict | None) -> bool:
    if not entry or entry.get("version") != 2:
        return False
    joined = " ".join(str(entry.get(field, "")) for field in ("pronunciation", "example", "root", "etymology"))
    if any(marker in joined for marker in ("未抓取到", "联网抓取失败", "需人工复核", "SSLError")):
        return False
    return bool(entry.get("etymology") and entry.get("source"))


def markdown_row(word: str, details: dict[str, dict[str, str]], online: dict) -> str:
    local = details.get(word.lower(), {})
    pronunciation = online.get("pronunciation") or local.get("pronunciation", "需复核")
    hint = gen.chinese_only_hint(gen.short_meaning(word, details), word)
    root_raw = online.get("root") or local.get("root", "需复核")
    example = online.get("example") or local.get("example", "见正文语境例句")
    definition = online.get("definition") or ""
    etymology_raw = online.get("etymology") or local.get("etymology", "需复核")
    root = zh_etymology_text(root_raw, hint=hint, limit=220)
    etymology = zh_etymology_text(etymology_raw, hint=hint, limit=360)
    source = (
        f"Etymonline 摘要：{etymology}；"
        f"Cambridge 摘要：发音 {pronunciation}；释义 {definition or hint}；例句 {example}；"
        f"链接：{online.get('source', '')}"
    )
    return (
        f"| {word} | {clean_md(pronunciation, 80)} | {clean_md(hint, 80)} | "
        f"{clean_md(root, 220)} | {clean_md(example, 180)} | "
        f"{clean_md(etymology, 360)} | {clean_md(source, 1400)} |"
    )


def enrich_all(words: list[str], cache: dict, workers: int) -> dict[str, dict]:
    enriched: dict[str, dict] = {}
    pending = [word for word in words if not is_valid_cached(cache.get(word.lower()))]
    for word in words:
        if is_valid_cached(cache.get(word.lower())):
            enriched[word.lower()] = cache[word.lower()]

    if pending:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {executor.submit(enrich_word, word, cache): word for word in pending}
            completed = 0
            for future in as_completed(future_map):
                word = future_map[future]
                try:
                    entry = future.result()
                except Exception as exc:
                    entry = {
                        "version": 2,
                        "word": word,
                        "pronunciation": "需复核",
                        "definition": "",
                        "example": f"联网抓取失败：{type(exc).__name__}",
                        "root": "需人工复核",
                        "etymology": "需人工复核",
                        "source": f"Etymonline: https://www.etymonline.com/word/{word}; Cambridge: https://dictionary.cambridge.org/dictionary/english/{word}",
                    }
                    cache[word.lower()] = entry
                enriched[word.lower()] = entry
                completed += 1
                if completed % 10 == 0 or completed == len(pending):
                    write_json(CACHE_PATH, cache)
                    print(f"Fetched {completed}/{len(pending)} new words", flush=True)
    write_json(CACHE_PATH, cache)
    return enriched


def update_markdown(path: Path, words: list[str], details: dict[str, dict[str, str]], cache: dict, workers: int) -> None:
    content = path.read_text(encoding="utf-8")
    enriched = enrich_all(words, cache, workers)

    def repl(match: re.Match) -> str:
        word = match.group(1)
        if word.lower() not in enriched:
            return match.group(0)
        return markdown_row(word, details, enriched[word.lower()])

    updated = re.sub(r"^\|\s*([A-Za-z][A-Za-z'-]*)\s*\|.*$", repl, content, flags=re.M)
    path.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich word summary tables with online dictionary/etymology data.")
    parser.add_argument("--project-root", default=".", help="Vocabulary project root. Defaults to the current directory.")
    parser.add_argument("--word-list", help="Word-list directory. Defaults to PROJECT_ROOT/单词表.")
    parser.add_argument("--cache", help="Online cache JSON path. Defaults to PROJECT_ROOT/状态/online_word_cache.json.")
    parser.add_argument("--pack", required=True)
    parser.add_argument("--markdown", required=True)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    global CACHE_PATH
    project_root = Path(args.project_root).resolve()
    gen.WORD_LIST_DIR = Path(args.word_list).resolve() if args.word_list else project_root / "单词表"
    CACHE_PATH = Path(args.cache).resolve() if args.cache else project_root / "状态" / "online_word_cache.json"

    _, _, _, words = gen.parse_pack(Path(args.pack))
    details = gen.load_word_details()
    cache = read_json(CACHE_PATH)
    update_markdown(Path(args.markdown), words, details, cache, max(1, args.workers))
    print(f"Updated: {args.markdown}")
    print(f"Words enriched: {len(words)}")
    print(f"Cache: {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
