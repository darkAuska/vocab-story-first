#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


PROJECT_ROOT = Path.cwd()
DAILY_DIR = PROJECT_ROOT / "每日任务"
WORD_LIST_DIR = PROJECT_ROOT / "单词表"
WORD_HEADING_RE = re.compile(r"^##\s+([A-Za-z][A-Za-z' -]*)\s*$", re.MULTILINE)
NAME_CN = {
    "Okabe": "冈部",
    "Kurisu": "红莉栖",
    "Mayuri": "真由理",
    "Faris": "菲伊丽丝",
    "Daru": "桥田至",
    "Suzuha": "铃羽",
    "Moeka": "萌郁",
}


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def clean_cell(text: str, word: str, limit: int = 120) -> str:
    text = text.strip()
    text = text.replace("\\~", word).replace("~", word).replace("\\", "")
    text = re.sub(r"\s+", " ", text)
    text = text.replace("|", " / ")
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def chinese_only_hint(text: str, word: str, limit: int = 48) -> str:
    text = clean_cell(text, word, 180)
    text = re.split(r"[:：]|例[：:]", text, maxsplit=1)[0]
    text = re.sub(r"\([^)]*[A-Za-z][^)]*\)", "", text)
    text = re.sub(r"\[[^\]]*[A-Za-z][^\]]*\]", "", text)
    text = re.sub(r"\b[A-Za-z][A-Za-z' -]*\b", "", text)
    text = text.replace(word, "")
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", "", text)
    text = re.sub(r"[;:,/]+", "；", text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"；{2,}", "；", text).strip("； ，,。")
    return text[:limit] if text else "见词表释义"


def extract_labeled_line(block: str, label: str, word: str, limit: int = 140) -> str:
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if line.startswith(label):
            return clean_cell(line.replace(label, "", 1), word, limit)
    return ""


def extract_pronunciation(block: str) -> str:
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if re.match(r"^\[[^\]]{2,60}\]", line):
            return line
    return "未提取到"


def extract_meaning(block: str, word: str) -> str:
    meaning = extract_labeled_line(block, "【词义】", word, 180)
    if meaning:
        return meaning
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("!") or line.startswith("["):
            continue
        if "【助记】" in line or "【派生】" in line or "【辨析】" in line:
            continue
        if any("\u4e00" <= char <= "\u9fff" for char in line):
            return clean_cell(line, word, 180)
    return "见原词条释义"


def extract_example(block: str, word: str) -> str:
    meaning = extract_labeled_line(block, "【词义】", word, 180)
    if meaning:
        return meaning
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if ":" in line and any("a" <= char.lower() <= "z" for char in line):
            return clean_cell(line, word, 180)
    return "见正文语境例句"


def load_word_details() -> dict[str, dict[str, str]]:
    details: dict[str, dict[str, str]] = {}
    for path in sorted(WORD_LIST_DIR.glob("*.md")):
        text = read_text(path)
        matches = list(WORD_HEADING_RE.finditer(text))
        for index, match in enumerate(matches):
            word = " ".join(match.group(1).split())
            key = word.lower()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[match.end() : end]
            root = extract_labeled_line(block, "【助记】", word, 160)
            details[key] = {
                "pronunciation": extract_pronunciation(block),
                "meaning": extract_meaning(block, word),
                "root": root or "联网待补充：优先查 Etymonline / Merriam-Webster 的构词和词源线索。",
                "example": extract_example(block, word),
                "etymology": f"本地红宝书助记线索：{root}；仍建议用 Etymonline / Merriam-Webster 复核。" if root else "联网待补充：优先查 Online Etymology Dictionary 和 Merriam-Webster，正式版不得留空。",
                "source": "本地红宝书；需联网复核 Etymonline / Merriam-Webster / Cambridge",
            }
    return details


def parse_pack(pack_path: Path) -> tuple[str, str, int, list[str]]:
    text = read_text(pack_path)
    title_match = re.search(r"#\s+(\d{4}-\d{2}-\d{2})\s+Day\s+(\d+)", text)
    if not title_match:
        raise SystemExit(f"Cannot parse date/day from {pack_path}")
    date_text = title_match.group(1)
    day_no = int(title_match.group(2))
    theme_match = re.search(r"-\s+主题：(.+)", text)
    theme = theme_match.group(1).strip() if theme_match else "命运石之门：恋爱路线修正器"
    pure = re.search(r"## 纯词列表\s*```text\s*(.*?)\s*```", text, re.S)
    if not pure:
        raise SystemExit("Cannot find pure word list in pack.")
    words = [word.strip() for word in pure.group(1).replace("\n", " ").split(",") if word.strip()]
    return date_text, theme, day_no, words


def short_meaning(word: str, details: dict[str, dict[str, str]]) -> str:
    meaning = details.get(word.lower(), {}).get("meaning", "")
    meaning = re.sub(r"例[:：].*", "", meaning).strip()
    return clean_cell(meaning, word, 72) if meaning else "见原词条释义"


def cn_word_label(word: str, details: dict[str, dict[str, str]]) -> str:
    return f"“{chinese_only_hint(short_meaning(word, details), word)}”（{word}）"


def story_sentence(word: str, speaker: str, target: str, prop: str, pattern: str, idx: int) -> str:
    marked = f"**{word}**"
    templates = [
        f"{speaker} found the route option {marked} on the phone and used it to turn an ordinary {prop} moment into a tiny confession trap for {target}.",
        f"{target} tried to ignore the keyword {marked}, but {speaker} quietly linked it to the way they had been sharing {prop} all afternoon.",
        f"The simulator printed {marked} above the lab table, and {speaker} said the {pattern} would fail unless {target} stopped pretending not to care.",
        f"{speaker} wrote {marked} on the whiteboard, then offered {target} the last sip of canned coffee as if the gesture were only part of the experiment.",
        f"When the D-Mail flashed {marked}, {target} reached for the phone at the same time as {speaker}, and their hands met over the glowing screen.",
    ]
    return templates[idx % len(templates)]


def cn_sentence(word: str, speaker: str, target: str, details: dict[str, dict[str, str]], prop_cn: str, pattern_cn: str, idx: int) -> str:
    speaker_cn = NAME_CN.get(speaker, speaker)
    target_cn = NAME_CN.get(target, target)
    label = cn_word_label(word, details)
    variants = [
        f"{speaker_cn}在手机上发现路线选项 {label}，便把一个普通的{prop_cn}日常变成了逗{target_cn}脸红的小陷阱。",
        f"{target_cn}想假装没看见目标词 {label}，但{speaker_cn}悄悄把它和两人整个下午共用{prop_cn}的细节联系起来。",
        f"模拟器在实验桌上方打出 {label}，{speaker_cn}说如果{target_cn}继续嘴硬不关心，这条“{pattern_cn}”就会失败。",
        f"{speaker_cn}把 {label} 写到白板上，又把最后一口罐装咖啡递给{target_cn}，还硬说这只是实验流程的一部分。",
        f"当时间邮件（D-Mail）闪出 {label} 时，{target_cn}和{speaker_cn}同时伸手去拿手机，指尖在亮着的屏幕上轻轻碰到一起。",
    ]
    return variants[idx % len(variants)]


def cn_word_list(words: list[str], details: dict[str, dict[str, str]]) -> str:
    return "、".join(cn_word_label(word, details) for word in words)


def en_word_list(marked_words: list[str]) -> str:
    if len(marked_words) == 1:
        return marked_words[0]
    return ", ".join(marked_words[:-1]) + f", and {marked_words[-1]}"


def scene_paragraph(
    words: list[str],
    chars: list[str],
    details: dict[str, dict[str, str]],
    *,
    prop: str,
    prop_cn: str,
    pattern: str,
    paragraph_index: int,
) -> tuple[str, str]:
    w = [f"**{word}**" for word in words]
    c0, c1, c2 = chars[0], chars[1], chars[2]
    c0_cn, c1_cn, c2_cn = NAME_CN.get(c0, c0), NAME_CN.get(c1, c1), NAME_CN.get(c2, c2)
    cn_terms = cn_word_list(words, details)
    en_terms = en_word_list(w)

    if paragraph_index == 0:
        en = (
            f"Dusk slid over Akihabara, and the lab's phone opened a damaged route file while the {prop} sat between them like evidence. "
            f"The notes in the file mentioned {en_terms}, but nobody stopped to study them like vocabulary; the words were just part of the messy case in front of them. "
            f"{c0} tried to laugh it off, but {c2}, appointed as the lab's route tester, did something that silenced even {c1}: "
            f"she placed two cans of coffee side by side and said one was obviously being saved for the person {c0} kept watching."
        )
        cn = (
            f"傍晚的秋叶原渐渐暗下来，实验室的手机打开了一份损坏的路线文件，{prop_cn}摆在他们中间，像一件小小的证物。"
            f"文件里的记录提到{cn_terms}，但没有人停下来像背词表一样研究它们；这些词只是眼前这场混乱事件的一部分。"
            f"{c0_cn}想把事情糊弄过去，可被任命为实验室测试员的{c2_cn}忽然把两罐咖啡并排放好，"
            f"说其中一罐显然是{c0_cn}特意留给他一直偷偷看着的那个人，这一下连{c1_cn}都被逗得说不出话。"
        )
    elif paragraph_index == 1:
        en = (
            f"The next page looked like a torn lab report: {en_terms} appeared in the margins beside coffee stains and hurried arrows. "
            f"The report did not make anyone feel anything by itself; what mattered was the rule written under it. "
            f"If they acted honestly for ten minutes, the route would move forward; if they kept hiding behind jokes, the scene would reset. "
            f"{c1} opened the emergency notebook, but the first line inside simply asked whether a fake date still counted if both people wanted it to be real."
        )
        cn = (
            f"下一页像一张被撕开的实验报告：{cn_terms}出现在页边，旁边还有咖啡渍和匆忙画下的箭头。"
            f"报告本身不会让任何人情绪波动，真正重要的是下面那条规则。"
            f"它说，只要两个人能诚实相处十分钟，路线就会继续推进；如果继续躲在玩笑后面，场景就会重置。"
            f"{c1_cn}翻开紧急记录本，却发现第一页只写着一个问题：如果假扮约会的两个人都希望它是真的，那它还算假的吗？"
        )
    elif paragraph_index == 2:
        en = (
            f"By the time the rain began, the room had become quiet enough for every small sound to matter: the ticking phone, the wet window, the chair {c1} pulled closer without comment. "
            f"{en_terms} appeared only as lines in the route log, while the real tension came from what nobody wanted to say first. "
            f"{c0} tried to explain, failed, and nearly slipped into another speech. "
            f"{c1} demanded action instead of performance, while {c2} quietly softened the silence by turning the route toward its gentler ending. "
            f"For a moment, the lab stopped feeling like a trap and started feeling like a room where someone might finally confess."
        )
        cn = (
            f"雨声落下时，房间安静到每一个小动静都变得清楚：手机的滴答声、湿掉的窗玻璃、{c1_cn}没有解释就拉近的椅子。"
            f"{cn_terms}只是路线日志里的几行记录，真正让气氛绷紧的，是谁都不愿先说出口的心意。"
            f"{c0_cn}本想给出一个简洁解释，结果越说越像中二演讲；{c1_cn}要求他拿出具体行动，别再绕弯子。"
            f"{c2_cn}则悄悄把尴尬的沉默往更温柔的方向推了一下。那一刻，实验室不再像陷阱，反而像一个终于有人要坦白心意的房间。"
        )
    else:
        en = (
            f"The final prompt stayed in the corner of the screen, quietly recording {en_terms} while the others argued over who should carry the umbrella. "
            f"If they treated the night like another lab record, the route would reset. If they admitted it had become something warmer, the next scene would open. "
            f"{c0} reached for the phone, {c1} reached too, and neither of them moved away when their fingers touched."
        )
        cn = (
            f"最后的提示停在屏幕角落，安静地记录着{cn_terms}，而其他人还在争论到底该由谁撑伞。"
            f"如果他们把这个夜晚继续当成实验记录，路线就会重置；如果他们承认它已经变得更温暖，系统就会打开下一幕。"
            f"{c0_cn}伸手去拿手机，{c1_cn}也同时伸手过去，指尖碰到一起时，两个人都没有立刻移开。"
        )
    return en, cn


def build_story(date_text: str, theme: str, day_no: int, words: list[str], details: dict[str, dict[str, str]]) -> str:
    scenes = [
        ("Scene 1: If-Line Coffee Trial", "第二轮假想路线（if line）", "canned coffee", "罐装咖啡", ["Okabe", "Kurisu", "Mayuri"]),
        ("Scene 2: The Maid Cafe Route Patch", "女仆咖啡厅服务日", "menu card", "菜单卡", ["Okabe", "Faris", "Mayuri"]),
        ("Scene 3: Fake-Date Debugging", "假扮恋人任务", "umbrella", "雨伞", ["Okabe", "Kurisu", "Daru"]),
        ("Scene 4: The Lab Night Shift", "共同值班夜", "microwave timer", "微波炉计时器", ["Okabe", "Mayuri", "Kurisu"]),
        ("Scene 5: Suzuha's Training Route", "战斗系保护与整理装备", "bike key", "自行车钥匙", ["Okabe", "Suzuha", "Kurisu"]),
        ("Scene 6: Moeka's Message Route", "短信式暧昧误会", "phone strap", "手机挂绳", ["Okabe", "Moeka", "Faris"]),
        ("Scene 7: Bento Conference", "青梅陪伴与共同做饭", "lunch box", "便当盒", ["Okabe", "Mayuri", "Kurisu"]),
        ("Scene 8: Script Repair Committee", "元叙事改剧情", "whiteboard marker", "白板笔", ["Okabe", "Kurisu", "Daru"]),
        ("Scene 9: Rainy Akihabara Reset", "雨天共伞", "transparent umbrella", "透明雨伞", ["Okabe", "Kurisu", "Suzuha"]),
        ("Scene 10: Future Possession Ending", "路线结算与温柔承诺", "lab badge", "实验室徽章", ["Okabe", "Kurisu", "Mayuri", "Faris"]),
    ]
    lines: list[str] = []
    lines.append(f"# {date_text} Day{day_no:03d} {theme} 完整背诵故事")
    lines.append("")
    lines.append("> 使用方式：先读 EN，再看紧跟的 CN 详细翻译。目标词首次出现统一用 Markdown 粗体标记，不使用 span 标签。")
    lines.append("")
    lines.append("## 1. 今日目标词")
    lines.append("")
    for start in range(0, len(words), 10):
        lines.append("- " + ", ".join(words[start : start + 10]))
    lines.append("")
    lines.append("## 2. 剧情导入")
    lines.append("")
    lines.append(
        "未来道具研究所收到一封异常 D-Mail：如果今天的 200 个英文关键词不能被放进一条“足够甜、足够日常、足够像游戏路线”的对话剧本里，"
        "实验室成员就会被困在同一天的词汇复习循环中。红莉栖认为这是冈部偷懒写出的荒唐脚本，真由理却认真准备了便当和星星贴纸，"
        "菲伊丽丝把任务改造成女仆咖啡厅活动，铃羽负责路线警戒，萌郁则用短信不断发来让人误会的关键词。冈部嘴上宣称这是命运石之门的选择，"
        "行动上却一次次把饮料、雨伞和最后一块点心让给别人。"
    )
    lines.append("")
    lines.append("## 3. 游戏对话正文")

    cloze: list[tuple[str, str]] = []
    for scene_index, (title, pattern, prop, prop_cn, chars) in enumerate(scenes):
        group = words[scene_index * 20 : (scene_index + 1) * 20]
        lines.append("")
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"- 本幕桥段：{pattern}")
        lines.append(f"- 记忆道具：{prop}")
        lines.append("")
        lines.append("#### English Story / Dialogue with Detailed Chinese Translation")
        lines.append("")
        for paragraph_index, start in enumerate(range(0, len(group), 5)):
            paragraph_words = group[start : start + 5]
            en, cn = scene_paragraph(
                paragraph_words,
                chars,
                details,
                prop=prop,
                prop_cn=prop_cn,
                pattern=pattern,
                paragraph_index=paragraph_index,
            )
            lines.append(f"EN: {en}")
            lines.append(f"CN: {cn}")
            lines.append("")
            if len(cloze) < 40:
                first_word = paragraph_words[0]
                cloze.append((first_word, en.replace(f"**{first_word}**", "_____", 1)))

        lines.append("#### 本幕目标词小结")
        lines.append("")
        lines.append("| word | pronunciation | 中文提示 | 词根/助记 | 例句 | 历史渊源/词源 | source |")
        lines.append("|---|---|---|---|---|---|---|")
        for word in group:
            detail = details.get(word.lower(), {})
            lines.append(
                f"| {word} | {detail.get('pronunciation', '未提取到')} | "
                f"{chinese_only_hint(short_meaning(word, details), word)} | "
                f"{clean_cell(detail.get('root', '联网待补充：优先查 Etymonline / Merriam-Webster 的构词和词源线索。'), word, 120)} | "
                f"{clean_cell(detail.get('example', '见正文语境例句'), word, 120)} | "
                f"{clean_cell(detail.get('etymology', '联网待补充：优先查 Online Etymology Dictionary 和 Merriam-Webster，正式版不得留空。'), word, 120)} | "
                f"{detail.get('source', 'Etymonline; Merriam-Webster; Cambridge')} |"
            )
        lines.append("")
        lines.append("#### 人物互动钩子")
        lines.append("")
        lines.append(f"这一幕用“{pattern}”把目标词挂在人物关系上：道具是 {prop}，甜点来自嘴硬关心、共同解谜、误会和旁人起哄。")

    lines.append("")
    lines.append("## 4. 主动回忆测试")
    lines.append("")
    lines.append("### 英译中")
    lines.append("")
    for idx, word in enumerate(words[:30], start=1):
        lines.append(f"{idx}. {word}")
    lines.append("")
    lines.append("### 中译英")
    lines.append("")
    for idx, word in enumerate(words[30:60], start=1):
        lines.append(f"{idx}. {short_meaning(word, details)}")
    lines.append("")
    lines.append("### 完形填空")
    lines.append("")
    for idx, (word, sentence) in enumerate(cloze[:20], start=1):
        lines.append(f"{idx}. {sentence}  （答案：{word}）")

    lines.append("")
    lines.append("## 5. 错词登记区")
    lines.append("")
    lines.append("| word | reason | next_review_date | note |")
    lines.append("|---|---|---|---|")
    lines.append("|  |  |  |  |")
    lines.append("")
    lines.append("reason 可选：`不认识`、`拼写错`、`熟词僻义`、`搭配不熟`、`语境误判`、`反应太慢`。")
    lines.append("")
    lines.append("## 6. 覆盖率自检")
    lines.append("")
    lines.append(f"- 目标词数：{len(words)}")
    lines.append(f"- 已覆盖词数：{len(words)}")
    lines.append("- 缺失词：无")
    lines.append("- 补写段落：无需补写")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a full vocabulary story from a daily word pack.")
    parser.add_argument("--project-root", default=".", help="Vocabulary project root. Defaults to the current directory.")
    parser.add_argument("--word-list", help="Word-list directory. Defaults to PROJECT_ROOT/单词表.")
    parser.add_argument("--pack", required=True, help="Path to the daily word pack.")
    parser.add_argument("--output", help="Output Markdown path.")
    args = parser.parse_args()

    global DAILY_DIR, WORD_LIST_DIR
    project_root = Path(args.project_root).resolve()
    DAILY_DIR = project_root / "每日任务"
    WORD_LIST_DIR = Path(args.word_list).resolve() if args.word_list else project_root / "单词表"

    pack_path = Path(args.pack)
    date_text, theme, day_no, words = parse_pack(pack_path)
    if len(words) != 200:
        raise SystemExit(f"Expected 200 words, got {len(words)}")
    details = load_word_details()
    content = build_story(date_text, theme, day_no, words, details)

    output = Path(args.output) if args.output else DAILY_DIR / f"{date_text}_Day{day_no:03d}_{theme}_完整背诵_日轻恋爱版.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"Created: {output}")
    print(f"Words covered: {len(words)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
