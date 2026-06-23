# 场景自然融入规则

这份规则用于避免背单词故事变成“词表伪装成剧情”。正文必须先像正常小说或游戏剧情，再让目标词自然进入环境、动作、对话、心理活动和任务细节。

## 核心原则

1. 场景先行，词汇后融入。先写发生了什么，再决定目标词放在哪里。
2. 目标词不能支配人物情绪。禁止写“大家的情绪因为这些词变得明显”“这些词让气氛改变”。
3. 禁止把目标词简单塞进 `keyword`、`route log`、`list`、`heading`、`margin note`、`prompt`、`word file` 这类容器里凑覆盖。
4. 每个目标词必须在英文句子里承担真实语法功能：名词就做物品/概念/事件，动词就写动作，形容词就写状态，副词就修饰动作。
5. 如果某个词太抽象，就放进角色对话、争论、承诺、误会、任务报告或心理判断里，而不是让人物讨论“这个词本身”。

## 正确示例

```md
EN: Kurisu **diluted** the coffee with hot water because the lab had gone **dim**, and Okabe's dramatic voice began to **diminish** when Mayuri called his plan **amateur**. What **amazed** Kurisu was not the experiment, but the fact that he had remembered how she liked her coffee.
CN: 红莉栖往咖啡里加热水把它“冲淡”（dilute），因为实验室灯光已经变得“昏暗”（dim）；真由理说冈部的计划太“业余”（amateur）时，他夸张的声音也慢慢“减弱”（diminish）了。真正让红莉栖“惊讶”（amaze）的不是实验，而是他居然记得她喜欢怎样的咖啡。
```

## 错误示例

```md
EN: The route log listed **dilute**, **dim**, **diminish**, **amateur**, and **amaze**.
CN: 路线日志列出了这些词。
```

这类写法只是把词放进容器，没有融入剧情。

## 生成要求

- 每个英文自然段应有正常动作链：环境变化 -> 人物行动 -> 对话或误会 -> 情绪后果。
- 目标词要散落在动作链里，不要集中成列表。
- 中文翻译要解释剧情，同时把英文目标词放在中文释义后的括号里。
- 如果为了覆盖率不得不牺牲自然度，优先少量增加自然段，而不是把词堆成一串。
