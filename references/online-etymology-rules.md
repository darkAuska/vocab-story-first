# 联网词根词源要求

这份规则用于生成每日背单词故事后的“目标词小结”。如果本地红宝书词条没有给出明确词根、助记或历史词源，不能写“本地没有”就结束，必须联网查询高置信来源后补全。

## 高置信来源优先级

1. 词源 / 历史渊源优先：
   - Online Etymology Dictionary: https://www.etymonline.com/
   - Merriam-Webster Dictionary / Word History: https://www.merriam-webster.com/
2. 发音优先：
   - Cambridge Dictionary: https://dictionary.cambridge.org/
   - Merriam-Webster Dictionary: https://www.merriam-webster.com/
3. 释义、例句和搭配辅助：
   - Cambridge Dictionary
   - Merriam-Webster Dictionary
   - Oxford Learner's Dictionaries，如果可访问

## 写法要求

- “词根/助记”必须来自可解释的构词成分、前缀、后缀、词根或可靠词源线索。
- “历史渊源/词源”必须说明来自哪个语言阶段或来源，例如 Latin、Old French、Greek、Old English 等，但输出解释必须用中文。源语言名称可写成“拉丁语（Latin）”“古法语（Old French）”，原始词形如 `dilutus`、`ambicion` 可以保留。
- 面向中国学习者，`词根/助记` 和 `历史渊源/词源` 两列不能整段英文输出；必须改写为中文说明，例如“源自拉丁语……”“原义是……”“可记为……”。
- 如果多个来源说法不完全一致，以 Online Etymology Dictionary 和 Merriam-Webster 为主，并写成保守表述。
- 不确定时写“据 Etymonline / Merriam-Webster 记载，可能来自……”，不要编造确定结论。
- 每个词的小结至少保留一个来源名或来源链接，方便复查。

## CN 行格式

CN 行必须以中文为主，英文只能放在括号里。人物名、道具、桥段名要优先中文化。

正确示例：

```md
CN: 模拟器在实验桌上方打出“减少、削弱”（diminish），真由理说如果冈部继续嘴硬不关心，这条“第二轮假想路线”（if line）就会失败。
```

不要这样写：

```md
CN: 模拟器在实验桌上方打出 diminish（减少、削弱），Mayuri 说如果 Okabe 继续嘴硬不关心，这条二周目 if 线就会失败。
```

## 小结表格式

每幕目标词小结建议包含：

| word | pronunciation | 中文提示 | 词根/助记 | 例句 | 历史渊源/词源 | source / 资料依据 |
|---|---|---|---|---|---|---|

其中 `source / 资料依据` 不能只放链接，必须同时写出链接对应的具体内容摘要。注意：不要整页复制词典网页原文；应改写成中文学习笔记，保留必要的原始词形、年代、来源语言和短摘。

- Etymonline：写明本词查到的词源依据，例如“源自拉丁语 dilutus；1550 年代已有相关用法”。
- Cambridge：写明本词查到的发音、释义或例句依据，例如“发音 /daɪˈluːt/；例句 After the stock is done...”。
- 最后保留 URL，方便复查。
- 如果需要更详细，使用“详细中文转述版”：把网页中的词源链、义项变化、构词成分、发音、核心释义、搭配和例句用途全部转写成中文说明；只保留少量必要英文短摘，不复制整页内容。

`词根/助记` 和 `历史渊源/词源` 示例：

```md
| dilute | /daɪˈluːt/ | 稀释；冲淡 | 据 Etymonline：源自拉丁语 dilutus / diluere，可按“冲洗、稀释、减弱”理解；dis- 有“分开”义。 | ... | 据 Etymonline：16 世纪 50 年代已有“削弱、减弱力量”的比喻义，后来发展出“加水使变稀”的字面义。 | Etymonline 摘要：源自拉丁语 dilutus；Cambridge 摘要：发音 /daɪˈluːt/，例句 After the stock is done...；链接：... |
```
## 原始网址保留规则

- 每个联网查询到的词条都必须保留原始网页 URL，尤其是 Etymonline 的具体词条页、Cambridge 的具体词条页、Merriam-Webster 的具体词条页。
- 不允许只写来源名称，也不允许只放网站首页；如果抓取到的是具体词条页，就保留具体词条页地址。
- 可以把网页内容改写成中文学习笔记，但 `source / 资料依据` 栏必须同时包含：来源名称、中文资料摘要、原始 URL。
