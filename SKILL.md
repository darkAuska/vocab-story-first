---
name: vocab-story-first
description: Create gamified English vocabulary memorization Markdown files from local word lists. Use when the user wants daily non-repeating vocabulary packs, story-first word recovery from a natural English story, ordered red-book extraction, bilingual EN/CN story scenes, target-word bolding, Chinese translations, pronunciation/root/etymology/example summaries with original source URLs, or review tests for Chinese English learners.
---

# Vocab Story First

Use this skill to build or operate a local English vocabulary memorization project that turns word lists into story-based Markdown study files.

## Project Layout

Expect or create this project layout:

```text
PROJECT_ROOT/
├── 单词表/
├── 每日任务/
├── 状态/
└── 模板/
```

Initialize a new project with:

```powershell
python "<skill>/scripts/init_vocab_project.py" --project-root "<PROJECT_ROOT>"
```

Put `.md`, `.txt`, `.csv`, or `.pdf` word lists in `单词表/`. If `.md` files exist, scripts prefer `.md` and sort files containing `上`, `中`, `下` in that order.

## Workflow Choice

Use `ordered` mode when the user prioritizes stable red-book progress:

```powershell
python "<skill>/scripts/pick_words.py" `
  --project-root "<PROJECT_ROOT>" `
  --count 200 `
  --theme "<theme>"
```

Use `story-first` mode when the user prioritizes a natural story:

1. Write or locate an English story draft.
2. Scan it for unused words from the local word list:

```powershell
python "<skill>/scripts/story_first_pick.py" `
  --project-root "<PROJECT_ROOT>" `
  --story-draft "<PROJECT_ROOT>/每日任务/Day003_story_draft.md" `
  --count 200 `
  --theme "<theme>"
```

If story-first finds fewer than the requested count, expand the story with more natural scenes and rerun. Do not fill the gap with a word list unless the user explicitly switches back to ordered mode.

## Story Generation Rules

Before writing the final story, read only the reference files needed for the task:

- `references/story-first-mode.md`: story-first process and failure behavior.
- `references/natural-scene-rules.md`: avoid list/log/keyword-driven prose.
- `references/bilingual-format-rules.md`: English paragraph followed by detailed Chinese translation.
- `references/romance-interaction-rules.md`: sweet daily romantic interaction, when the user wants that tone.
- `references/online-etymology-rules.md`: word-summary table, Chinese root/etymology notes, and original source URLs.
- `references/review-loop.md`: active recall and wrong-word review.

For Chinese learners, write `CN:` lines mostly in Chinese. Put English target words in parentheses after the Chinese meaning, e.g. `冲淡（dilute）`, not `dilute（冲淡）`.

For target words, use Markdown bold on the first occurrence: `**word**`. Do not use HTML spans.

## Online Enrichment

After a full story Markdown exists, enrich the word-summary rows:

```powershell
python "<skill>/scripts/enrich_word_summaries_online.py" `
  --project-root "<PROJECT_ROOT>" `
  --pack "<PROJECT_ROOT>/每日任务/YYYY-MM-DD_Day003_theme_抽词包.md" `
  --markdown "<PROJECT_ROOT>/每日任务/YYYY-MM-DD_Day003_theme_完整背诵.md" `
  --workers 4
```

The enrichment script uses Etymonline and Cambridge pages where available. It must not copy entire dictionary pages. It should produce detailed Chinese study notes, short necessary excerpts only, and keep each original word-entry URL in `source / 资料依据`.

## Validation Checklist

Before finishing a task, verify:

- Target word count matches the pack, usually 200.
- No target word was used in previous history unless the user requested a reset.
- Every target word appears in the final story and is bolded on first occurrence.
- Summary tables include pronunciation, Chinese hint, root/mnemonic, example, etymology/history, and `source / 资料依据`.
- Source cells contain original URLs, not only source names or homepages.
- No placeholders remain: `未抓取到`, `需人工复核`, `SSLError`, `联网抓取失败`.
- `状态/vocab_state.json` is updated only by pack-generation scripts, not by rewriting an old day.
