# vocab-story-first

`vocab-story-first` is a Codex skill for building story-based English vocabulary memorization files from local word lists.

It supports two workflows:

- `ordered`: take the next unused words from the word list in source order.
- `story-first`: write a natural English story first, then recover unused target words from that story.

The output is designed for Chinese English learners: English story first, detailed Chinese translation after each paragraph, bold target words, word-summary tables, online etymology notes, original source URLs, and active-recall tests.

## Install

Clone this repository into your Codex skills directory:

```powershell
git clone https://github.com/darkAuska/vocab-story-first.git "$env:USERPROFILE\.codex\skills\vocab-story-first"
```

Restart Codex after installation.

To check whether Codex can see the skill, ask:

```text
Use $vocab-story-first to initialize a vocabulary project.
```

## Project Layout

Create or choose a project folder. The skill expects this layout:

```text
PROJECT_ROOT/
├── 单词表/
├── 每日任务/
├── 状态/
└── 模板/
```

Initialize it with:

```powershell
python "$env:USERPROFILE\.codex\skills\vocab-story-first\scripts\init_vocab_project.py" `
  --project-root "D:\vocab-study"
```

Put your word-list files into:

```text
D:\vocab-study\单词表
```

Supported formats: `.md`, `.txt`, `.csv`, `.pdf`.

If `.md` files exist, the scripts prefer `.md` files. Files containing `上`, `中`, `下` in their names are sorted in that order.

## Use In Codex

After installing the skill and preparing the project, you can use natural prompts:

```text
Use $vocab-story-first. My project root is D:\vocab-study. Generate Day001 with ordered mode, 200 words, theme "Steins;Gate romantic daily life".
```

Or:

```text
Use $vocab-story-first. My project root is D:\vocab-study. Generate Day001 with story-first mode. First write a natural English story draft, then recover 200 unused words from the local word list.
```

For story-first mode, Codex should expand the story if fewer than 200 unused words are found. It should not fill the gap with unrelated word-list entries unless you explicitly switch to ordered mode.

## Manual Commands

### Ordered Mode

Use this when you want stable progress through the word list:

```powershell
python "$env:USERPROFILE\.codex\skills\vocab-story-first\scripts\pick_words.py" `
  --project-root "D:\vocab-study" `
  --count 200 `
  --theme "Steins;Gate romantic daily life"
```

This creates a daily pack in:

```text
D:\vocab-study\每日任务
```

It also updates:

```text
D:\vocab-study\状态\vocab_state.json
```

### Story-First Mode

First create an English story draft, for example:

```text
D:\vocab-study\每日任务\Day001_story_draft.md
```

Then scan it:

```powershell
python "$env:USERPROFILE\.codex\skills\vocab-story-first\scripts\story_first_pick.py" `
  --project-root "D:\vocab-study" `
  --story-draft "D:\vocab-study\每日任务\Day001_story_draft.md" `
  --count 200 `
  --theme "Steins;Gate romantic daily life"
```

If the script reports fewer than 200 unused words, expand the story draft with more natural scenes and run it again.

### Online Enrichment

After a full Markdown story exists, enrich the word-summary table:

```powershell
python "$env:USERPROFILE\.codex\skills\vocab-story-first\scripts\enrich_word_summaries_online.py" `
  --project-root "D:\vocab-study" `
  --pack "D:\vocab-study\每日任务\YYYY-MM-DD_Day001_theme_抽词包.md" `
  --markdown "D:\vocab-study\每日任务\YYYY-MM-DD_Day001_theme_完整背诵.md" `
  --workers 4
```

The enrichment step keeps original source URLs from dictionary pages. It should summarize and translate learning-relevant content into Chinese, not copy full dictionary pages.

## Validation Checklist

Before treating a day as finished, check:

- The target word count is correct, usually 200.
- No target word repeats a previous day unless you deliberately reset the state.
- Every target word appears in the story.
- First occurrences are marked with Markdown bold, for example `**dilute**`.
- `CN:` lines are mainly Chinese, with English words in parentheses after Chinese meanings.
- Summary rows include pronunciation, Chinese hint, root/mnemonic, example, etymology/history, and source evidence.
- Source evidence includes original URLs, not only source names.
- No placeholders remain: `未抓取到`, `需人工复核`, `SSLError`, `联网抓取失败`.

## Sharing With Others

Anyone can install the skill with:

```powershell
git clone https://github.com/darkAuska/vocab-story-first.git "$env:USERPROFILE\.codex\skills\vocab-story-first"
```

Then restart Codex and invoke:

```text
Use $vocab-story-first ...
```
