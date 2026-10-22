"""写作课堂的课程内容。

每节课包含：讲解（content）、范例对比（examples）、小测验（quiz）、练一练（exercise）。
讲解用中文，英文例句保持英文，方便中文母语学生学习英文 essay 写作。
"""

LESSONS = [
    {
        "id": "prompt",
        "icon": "🔎",
        "title": "第 1 课 · 读懂题目",
        "goal": "学会拆解题目，弄清楚“写什么”和“怎么答”，从源头避免跑题。",
        "content": """
### 为什么先读题？
跑题（off-topic）是 essay 里最致命的错误：语言再漂亮，没回答题目也拿不到高分。
动笔前花 2–3 分钟拆题，是最划算的投资。

### 三步拆题法
1. **圈出话题（Topic）**：这篇文章讨论的对象是什么？
2. **找出指令词（Task words）**：题目要你“做什么”——表态？比较？分析原因？
3. **确定范围与限制（Scope）**：留意 *only / all / always / main / in your country* 这类限定词，它们决定了你论证的边界。

### 常见指令词
| 指令词 | 要求你做什么 |
|---|---|
| **To what extent do you agree or disagree?** | 明确表态，并说明同意的**程度**（完全/部分），全文立场一致 |
| **Discuss both views and give your opinion.** | 两方观点都要展开讨论，**并且**给出自己的观点 |
| **Do the advantages outweigh the disadvantages?** | 比较利弊后给出**结论：哪边更重** |
| **Compare / Contrast** | 找出相同点 / 不同点，并说明其意义 |
| **Explain why / What are the causes?** | 分析原因，不要只罗列现象 |
| **Evaluate / Assess** | 判断价值或效果，需要标准和证据 |

### 拆题示范
> *Some people think that universities should **only** offer subjects that lead directly to **jobs**. **To what extent do you agree or disagree?***

- **话题**：大学开设课程的目的
- **指令**：表明立场 + 同意程度
- **限制**：“only” 是绝对化的词——很多高分作文正是抓住它，论证“职业导向很重要，但**只**开这类课不合理”

### 用自己的话复述题目
拆完题后，试着用一句话复述：
*“The question asks me to decide whether universities should limit their courses to job-related subjects, and how strongly I agree.”*
能复述清楚，说明你真的读懂了。
""",
        "examples": [
            {
                "weak": "（题目问利弊哪个更大）文章分别写了两段优点、两段缺点，结尾只说 “It has both advantages and disadvantages.”",
                "strong": "同样写了利弊，但结尾明确判断：“…the benefits of remote work clearly outweigh its drawbacks, provided that companies set clear boundaries.”",
                "why": "“Do the advantages outweigh…” 要求你**做出比较判断**。只罗列不下结论，等于没有回答问题。",
            },
            {
                "weak": "（题目：Should children **under 12** own smartphones?）文章泛泛讨论 “smartphones are bad for teenagers”。",
                "strong": "文章始终聚焦 12 岁以下儿童：注意力发展、家长监管、安全联络需求等。",
                "why": "忽略了范围限制（under 12），论证对象偏移，属于部分跑题。",
            },
        ],
        "quiz": [
            {
                "q": "题目 “To what extent do you agree?” 最核心的要求是？",
                "options": [
                    "客观介绍两方观点，不需要表态",
                    "明确表态并说明同意程度，且全文立场一致",
                    "只要列出尽可能多的论据",
                    "必须完全同意或完全反对",
                ],
                "answer": 1,
                "explain": "“To what extent” 问的是程度：可以完全同意，也可以部分同意，但必须清楚、一致。",
            },
            {
                "q": "下面哪个词最可能是题目中需要特别注意的“限制词”？",
                "options": ["people", "only", "think", "subjects"],
                "answer": 1,
                "explain": "“only” 把论题绝对化了，往往是论证的突破口，也是容易忽略的陷阱。",
            },
        ],
        "exercise": {
            "task": """请拆解下面这道题，写出：① 话题 ② 指令词及要求 ③ 范围/限制词 ④ 用你自己的一句英文复述题目。

> *In many countries, people are spending more and more time on social media. Do the advantages of this trend outweigh the disadvantages?*""",
            "placeholder": "① 话题：...\n② 指令词：...\n③ 限制：...\n④ 复述：The question asks me to ...",
            "criteria": "是否准确识别话题（社交媒体使用时间增加这一趋势）、指令（比较利弊并做出哪边更重的判断）、限制/范围（this trend, more and more time），英文复述是否准确且没有改变题意。",
        },
    },
    {
        "id": "thesis",
        "icon": "🎯",
        "title": "第 2 课 · 写出有力的论点句（Thesis）",
        "goal": "写出一句清晰、可辩论、具体的 thesis statement，让整篇文章有主心骨。",
        "content": """
### Thesis 是什么？
Thesis statement 是你对题目的**直接回答**，通常放在开头段最后一句。整篇文章的每一段都在为它服务。

### 好 thesis 的四个标准
1. **回答问题**：直接回应题目的指令词
2. **可辩论（arguable）**：有人可能不同意——事实陈述不是论点
3. **具体（specific）**：避免 *good / bad / important* 这类空洞的词
4. **预告结构（roadmap，可选）**：暗示接下来的主要理由

### 万能句型（先模仿，再变化）
- *Although* [让步], [你的立场] *because* [理由 1] *and* [理由 2].
- [立场], *as* [理由 1], [理由 2], *and* [理由 3].
- *While* [对方观点有一定道理], *I believe* [你的立场], *since* [核心理由].

### 四种常见错误
| 错误类型 | 例子 | 问题 |
|---|---|---|
| 事实陈述 | *Many students use smartphones.* | 没人会反对，不是论点 |
| 宣布式 | *In this essay, I will talk about smartphones.* | 只说“要写什么”，没有立场 |
| 太宽泛 | *Technology has changed the world.* | 范围太大，一篇文章写不完 |
| 两边倒 | *Smartphones have advantages and disadvantages.* | 没有回答“你怎么看” |
""",
        "examples": [
            {
                "weak": "Homework is a common topic and there are different opinions about it.",
                "strong": "Although homework can reinforce classroom learning, it should be limited in primary schools because young children learn more effectively through play and need sufficient rest.",
                "why": "强版本有明确立场（limited）、限定范围（primary schools）、两个具体理由，还用 Although 处理了对立观点。",
            },
            {
                "weak": "Online learning is good.",
                "strong": "Online learning benefits adult learners more than school children, as adults have the self-discipline and specific goals that independent study requires.",
                "why": "“good” 太空泛。强版本把论点收窄到“对谁更有利”，并给出可论证的理由。",
            },
        ],
        "quiz": [
            {
                "q": "下面哪一句是最好的 thesis？",
                "options": [
                    "In this essay I will discuss whether cities should ban cars.",
                    "Cars are a part of modern life.",
                    "City centres should ban private cars, as doing so would cut air pollution and make streets safer for pedestrians.",
                    "Banning cars has good and bad sides.",
                ],
                "answer": 2,
                "explain": "C 有明确立场、范围（city centres, private cars）和两个具体理由；A 是宣布式，B 是事实，D 两边倒。",
            },
            {
                "q": "“Many teenagers spend hours on video games.” 作为 thesis 的主要问题是？",
                "options": ["太长", "是事实陈述，不可辩论", "语法错误", "用了专业词汇"],
                "answer": 1,
                "explain": "这是一个几乎没人会反驳的事实，无法成为需要论证的观点。",
            },
        ],
        "exercise": {
            "task": """为下面的题目写一句 thesis statement（一句话即可，可以用课上的句型）：

> *Should high schools require students to do community service in order to graduate?*""",
            "placeholder": "Although ..., high schools should ... because ...",
            "criteria": "是否直接回答题目（是否应该把社区服务作为毕业要求）、立场是否明确、是否可辩论、是否具体（有理由，不空泛）、语法是否正确。",
        },
    },
    {
        "id": "structure",
        "icon": "🧱",
        "title": "第 3 课 · 文章结构与大纲",
        "goal": "掌握 essay 的经典结构，学会在动笔前用大纲规划全文。",
        "content": """
### 经典结构：引言 – 主体 – 结论
| 部分 | 功能 | 常见内容 |
|---|---|---|
| **Introduction 引言** | 吸引读者、交代背景、亮出论点 | Hook → Background → **Thesis** |
| **Body paragraphs 主体段（2–4 段）** | 逐条论证 thesis | 每段**一个**中心论点（topic sentence）+ 论据 + 分析 |
| **Counterargument（可选）** | 回应反方，显示思考深度 | 让步 + 反驳 |
| **Conclusion 结论** | 收束全文、升华意义 | 换种说法重申论点 → 总结要点 → 更广的意义 |

> 引言像**漏斗**：从宽泛到具体；结论像**倒漏斗**：从具体回到更大的意义。

### 为什么一定要写大纲？
- 先想清楚逻辑，再考虑语言——写作时就不会“写到哪算哪”
- 能提前发现论点重复、论据不足、段落跑题
- 考试中 5 分钟大纲，往往能省下 15 分钟的返工

### 大纲模板
```
Thesis: ____________________________

I.   Introduction: hook idea + background + thesis
II.  Body 1 — Topic sentence: ___________
       Evidence: ___________   Analysis: ___________
III. Body 2 — Topic sentence: ___________
       Evidence: ___________   Analysis: ___________
IV.  (Counterargument + rebuttal)
V.   Conclusion: restate thesis + so what?
```

### 字数怎么分配？（以 300 词为例）
引言 ~50 词 · 每个主体段 ~80–90 词 · 结论 ~40 词。
**主体段才是得分的主战场**，不要把一半字数花在开头。
""",
        "examples": [
            {
                "weak": "Body 1: Phones are useful.  Body 2: Phones help students.  Body 3: Phones are good for learning.",
                "strong": "Body 1: Phones give instant access to learning resources.  Body 2: Phones support communication with teachers and peers.  Body 3 (counter): Distraction is a real risk, but school policies can manage it.",
                "why": "弱版本三个论点其实是同一个意思换说法；强版本每段角度不同、互不重叠，并处理了反方。",
            },
        ],
        "quiz": [
            {
                "q": "每个主体段应该有几个中心论点？",
                "options": ["越多越好", "一个", "至少三个", "不需要中心论点"],
                "answer": 1,
                "explain": "一段一个中心（one paragraph, one idea），段落的第一句（topic sentence）通常就是它。",
            },
            {
                "q": "引言段的典型顺序是？",
                "options": [
                    "Thesis → Hook → Background",
                    "Background → Thesis → Hook",
                    "Hook → Background → Thesis",
                    "只写 Thesis 即可",
                ],
                "answer": 2,
                "explain": "漏斗结构：先吸引读者，再交代背景，最后亮出论点。",
            },
        ],
        "exercise": {
            "task": """为下面的题目写一个**简要大纲**：一句 thesis + 2–3 个主体段的 topic sentence（每段可附一个论据想法）。

> *Is it better for students to learn online or in a traditional classroom?*""",
            "placeholder": "Thesis: ...\nBody 1: ... (evidence: ...)\nBody 2: ...\nBody 3: ...",
            "criteria": "Thesis 是否明确回答题目；各主体段论点是否都支撑 thesis、互不重叠、角度清晰；论据想法是否具体可行；整体逻辑顺序是否合理。",
        },
    },
    {
        "id": "peel",
        "icon": "🧩",
        "title": "第 4 课 · 主体段写法（PEEL）",
        "goal": "用 PEEL 结构写出论证充分的主体段，学会“分析”而不只是“举例”。",
        "content": """
### PEEL 四步
| 字母 | 含义 | 作用 | 常用句式 |
|---|---|---|---|
| **P** | Point 论点 | 段首 topic sentence，说清这段要证明什么 | *One major benefit of … is that …* |
| **E** | Evidence 论据 | 数据、例子、研究、事实 | *For example, … / According to …* |
| **E** | Explain 分析 | 解释论据**为什么**能证明论点 | *This shows that … because … / As a result, …* |
| **L** | Link 回扣 | 连回 thesis 或过渡到下一段 | *Therefore, … / This is why …* |

### 示范段落（标注版）
> **[P]** *One major advantage of free public transport is that it reduces traffic congestion.*
> **[E]** *When Tallinn, Estonia, made buses free for residents in 2013, many residents reported using public transport more often.*
> **[E]** *This matters because every person who switches from a car to a bus removes a vehicle from the road, and fewer cars at peak hours means shorter, more predictable journeys for everyone — including those who still drive.*
> **[L]** *Free transport, therefore, benefits the whole city, not only its passengers.*

### 拉开差距的关键：Explain（分析）
很多学生的段落是 **“论点 + 例子”** 就结束了，读者会问：*So what?*
试试 **“追问三连”**：
1. 这个例子说明了什么？（*This shows that…*）
2. 为什么会这样？（*because…*）
3. 这对论点意味着什么？（*which means…*）

### 论据的类型
- 📊 数据与研究（最有说服力，但**不要编造具体数字**——考试中可以用 “studies suggest…” 这类表达）
- 🌍 真实事例（国家、城市、公司、历史事件）
- 🧠 逻辑推理与假设情境（*If…, then…*）
- 👤 个人经历（议论文中慎用，适合作为补充）
""",
        "examples": [
            {
                "weak": "Reading is important. For example, my friend reads a lot. So reading is good.",
                "strong": "Regular reading strengthens students' writing skills. Learners who read widely are exposed to a greater variety of sentence structures and vocabulary in context. Because they repeatedly see how skilled writers build arguments, they begin to imitate these patterns in their own work, which is why avid readers often write with greater fluency.",
                "why": "弱版本论点空泛、例子太私人、没有分析；强版本论点具体，并用 because / which is why 解释了“为什么阅读能提高写作”。",
            },
        ],
        "quiz": [
            {
                "q": "PEEL 中最常被学生忽略、但最能拉开分数差距的是哪一步？",
                "options": ["Point", "Evidence", "Explain", "Link"],
                "answer": 2,
                "explain": "Explain 把论据和论点连接起来。没有分析，例子就只是“摆在那里”。",
            },
            {
                "q": "下面哪个句子最适合作为主体段的 topic sentence？",
                "options": [
                    "For example, Finland has short school days.",
                    "Shorter school days can improve students' academic performance.",
                    "This is why I think so.",
                    "There are many countries in the world.",
                ],
                "answer": 1,
                "explain": "B 是一个明确、可论证的观点；A 是论据，C 是回扣句，D 与论证无关。",
            },
        ],
        "exercise": {
            "task": """用 PEEL 结构写一个主体段（约 80–120 词），论点是：

> **Point:** *Schools should teach students how to manage money.*

请在写完后自查：你的 Explain 部分是否回答了 “so what?”""",
            "placeholder": "One important reason why schools should teach financial skills is that ...",
            "criteria": "是否包含完整的 PEEL 四部分；论据是否具体可信（不编造精确数据）；分析部分是否解释了论据如何支撑论点；结尾是否回扣；语言是否准确、连贯。",
        },
    },
    {
        "id": "intro_conclusion",
        "icon": "🚪",
        "title": "第 5 课 · 开头与结尾",
        "goal": "写出吸引人又不空洞的开头，以及有力量、不重复的结尾。",
        "content": """
### 开头：Hook → Background → Thesis
**好的 Hook 类型**
- ❓ 引人思考的问题：*What if your next teacher were an algorithm?*
- 📈 令人意外的事实：*The average teenager now spends more time on screens than in school.*（考试中避免编造精确数据）
- 🎬 简短场景：*It is 11 p.m., and a 15-year-old is still finishing her third hour of homework.*
- ⚖️ 对比：*A century ago, children worked in factories; today, many work at their desks until midnight.*

**避免的“万能开头”**（阅卷老师看了几千遍）
- ❌ *With the development of society/technology, …*
- ❌ *Nowadays, more and more people …*
- ❌ *Every coin has two sides.*

### 结尾：Restate → Summarise → So what?
1. **换种说法重申论点**（不要逐字复制 thesis）
2. **简短概括主要理由**
3. **升华**：意义、建议、展望或呼吁（*so what?*）

**结尾的禁忌**
- ❌ 提出新论据（新观点应该在主体段展开）
- ❌ 机械重复：*In conclusion, as I said above, …*
- ❌ 突然改变立场或变得模棱两可
""",
        "examples": [
            {
                "weak": "Nowadays, with the development of technology, more and more people use the Internet. Online shopping has advantages and disadvantages. I will discuss them in this essay.",
                "strong": "A pair of shoes ordered at midnight can now arrive before breakfast. Online shopping has transformed how people buy almost everything, from groceries to furniture. Although it raises concerns about local businesses, I believe its convenience and wider choice make it a positive development for most consumers.",
                "why": "强版本用具体场景作 hook，背景简洁，结尾一句给出了清晰的 thesis；弱版本全是套话，且没有立场。",
            },
            {
                "weak": "In conclusion, as I said above, online shopping is good. Also, it can help the environment because of less driving.",
                "strong": "In short, online shopping saves consumers time and gives them access to a far wider range of products. If retailers and governments work together to support local shops, society can enjoy this convenience without losing the character of its high streets.",
                "why": "弱版本机械重复并在结尾引入新论据（环保）；强版本换种说法重申，并提出建设性展望。",
            },
        ],
        "quiz": [
            {
                "q": "结尾段中最应该避免的是？",
                "options": ["重申论点", "总结主要理由", "提出全新的论据", "提出建议或展望"],
                "answer": 2,
                "explain": "结尾是收束，不是开新话题。新论据应放在主体段充分展开。",
            },
            {
                "q": "以下哪个开头句最容易被阅卷人视为“套话”？",
                "options": [
                    "With the development of society, more and more people care about health.",
                    "Every morning, millions of commuters sit in traffic for over an hour.",
                    "What if robots could do all our housework?",
                    "Fast food is cheaper than ever, yet obesity rates keep climbing.",
                ],
                "answer": 0,
                "explain": "“With the development of society…” 是最常见的模板开头，空泛且无信息量。",
            },
        ],
        "exercise": {
            "task": """为下面的题目写一个**开头段**（约 50–70 词，包含 hook、背景和 thesis）：

> *Some people believe that zoos should be closed because keeping animals in captivity is cruel. To what extent do you agree or disagree?*""",
            "placeholder": "Hook ... Background ... Thesis ...",
            "criteria": "Hook 是否新颖而不套话；背景是否简洁且与题目相关；结尾是否有清楚回答题目的 thesis（含同意程度）；长度是否合适；语言是否准确。",
        },
    },
    {
        "id": "counter",
        "icon": "⚖️",
        "title": "第 6 课 · 反方观点与反驳",
        "goal": "学会“先让步、再反驳”，让论证更全面、更有说服力。",
        "content": """
### 为什么要写反方？
- 展示**批判性思维**：你考虑过不同意见
- 增强**说服力**：提前回应读者心中的疑问
- 在很多评分标准中（如 AP、学术写作），处理反方是高分特征

### 结构：让步（Concede）→ 反驳（Rebut）
1. **公正地陈述**对方观点（不要歪曲成“稻草人”）
2. **承认**其合理之处
3. **反驳**：指出其局限、给出更重要的考量，或提出解决方案

### 常用句式
| 让步 | 反驳 |
|---|---|
| *Admittedly, …* | *However, this overlooks …* |
| *Critics may argue that …* | *Yet this concern can be addressed by …* |
| *It is true that …* | *Nevertheless, the benefits of … outweigh …* |
| *While some believe …* | *…, the evidence suggests otherwise.* |

### 放在哪里？
- **独立成段**：放在结论前（最常见）
- **嵌入段内**：在某个主体段中先让步再反驳
- **放进 thesis**：*Although X, Y because…*

### 常见错误
- 🙅 只写对方观点，**忘了反驳**——等于帮对方论证
- 🙅 让步太多，结果自己的立场变弱
- 🙅 “稻草人”：故意把对方观点说得很荒谬再驳倒
""",
        "examples": [
            {
                "weak": "Some people think homework is useful. But they are wrong.",
                "strong": "Admittedly, homework can help children practise skills they learned in class. However, research on young learners suggests that short, focused practice in school is just as effective, and long assignments at home often increase stress without improving results.",
                "why": "弱版本没解释对方观点，也没给反驳理由；强版本公正让步，再用证据和逻辑反驳。",
            },
        ],
        "quiz": [
            {
                "q": "反方段落最常见的错误是？",
                "options": ["使用 However", "只陈述反方观点而没有反驳", "放在结论前", "篇幅较短"],
                "answer": 1,
                "explain": "不反驳的话，这一段反而在削弱你自己的论点。",
            },
            {
                "q": "下面哪个是“稻草人”式的反方陈述？",
                "options": [
                    "Some argue that uniforms limit students' self-expression.",
                    "Critics claim uniforms are expensive for some families.",
                    "Opponents think students should be allowed to wear anything, even pyjamas, to school.",
                    "Some parents worry that uniforms are uncomfortable in hot weather.",
                ],
                "answer": 2,
                "explain": "C 把反方观点夸张成荒谬的样子，很容易“驳倒”，但缺乏说服力。",
            },
        ],
        "exercise": {
            "task": """你的 thesis 是：

> *Primary schools should ban homework.*

请写 3–4 句话：先公正地陈述一个反方观点并让步，再进行有理有据的反驳。""",
            "placeholder": "Admittedly, ... However, ...",
            "criteria": "反方观点是否公正、合理（非稻草人）；是否有明确的让步；反驳是否有理由或证据支撑；反驳后立场是否依然清晰；连接词使用是否恰当。",
        },
    },
    {
        "id": "cohesion",
        "icon": "🔗",
        "title": "第 7 课 · 衔接与连贯",
        "goal": "让句子与句子、段落与段落之间顺畅过渡，读起来像一个整体。",
        "content": """
### Cohesion vs. Coherence
- **Coherence（连贯）**：思路清楚、逻辑顺序合理——读者知道你为什么从 A 说到 B
- **Cohesion（衔接）**：用语言手段把句子“粘”在一起——连接词、指代、词汇呼应

### 按功能选择连接词
| 功能 | 连接词 |
|---|---|
| 递进 | *Moreover, Furthermore, In addition, Not only… but also…* |
| 转折/对比 | *However, In contrast, On the other hand, Whereas* |
| 因果 | *Therefore, As a result, Consequently, Because of this* |
| 举例 | *For example, For instance, Such as* |
| 让步 | *Although, Even though, Admittedly, Despite* |
| 总结 | *In short, Overall, In conclusion* |

### 比连接词更高级的衔接手段
1. **指代**：用 *this approach / such policies / these changes* 指回上文
2. **词汇链**：用同义词和相关词串联（*pollution → emissions → dirty air*）
3. **旧信息在前，新信息在后**：句首接上一句的结尾，句尾引出新内容

> *Many cities now charge drivers to enter the centre. **This fee** discourages unnecessary trips, and **fewer trips** mean less congestion.*

### 常见问题
- 🙅 **连接词堆砌**：每句都用 *Firstly / Moreover / Furthermore*，反而生硬
- 🙅 **误用**：*On the contrary*（表示“恰恰相反”，否定前文）≠ *On the other hand*（另一方面）
- 🙅 **口语化**：*Besides, And, But, So* 放句首在正式写作中要慎用
""",
        "examples": [
            {
                "weak": "Many students use smartphones in class. Smartphones are distracting. Students cannot focus. Their grades drop.",
                "strong": "Many students use smartphones in class, and these devices are highly distracting. When notifications constantly interrupt them, students struggle to focus on the lesson; as a result, their grades often suffer.",
                "why": "强版本用 these devices 指代、when 引出条件、as a result 表达因果，把四个零散短句连成了有逻辑的整体。",
            },
        ],
        "quiz": [
            {
                "q": "“On the contrary” 的正确用法是？",
                "options": [
                    "引出另一方面的观点（= on the other hand）",
                    "否定前面的说法，表示“恰恰相反”",
                    "表示举例",
                    "表示总结",
                ],
                "answer": 1,
                "explain": "例：*The test wasn't easy. On the contrary, it was extremely difficult.* 想引出另一方面应用 on the other hand。",
            },
            {
                "q": "下面哪种是“指代衔接”？",
                "options": [
                    "Firstly, … Secondly, …",
                    "… a congestion charge. This policy …",
                    "In conclusion, …",
                    "For example, …",
                ],
                "answer": 1,
                "explain": "“This policy” 指回上句的 congestion charge，自然地把两句连起来。",
            },
        ],
        "exercise": {
            "task": """把下面这段“碎片化”的文字改写成连贯的一段（可以合并句子、调整顺序、增加衔接）：

> *Many students use smartphones in class. Smartphones are distracting. Students cannot focus. Their grades drop. Some teachers ban phones. Phones can be useful for research.*""",
            "placeholder": "Although smartphones can be useful ..., ...",
            "criteria": "是否保留原文所有信息且逻辑关系正确（尤其是“手机可用于研究”这一转折）；是否使用多种衔接手段（连接词、指代、复合句）而非堆砌连接词；语言是否准确自然。",
        },
    },
    {
        "id": "language",
        "icon": "🎓",
        "title": "第 8 课 · 学术语言与常见中式英语",
        "goal": "让语言更正式、准确、简洁，避开中国学生最常见的表达错误。",
        "content": """
### 正式 vs. 口语
| 口语 ❌ | 学术 ✅ |
|---|---|
| *a lot of / lots of* | *many, much, a large number of, considerable* |
| *kids* | *children* |
| *stuff, things* | 具体的名词：*equipment, issues, factors* |
| *get better* | *improve* |
| *don't, can't, it's* | *do not, cannot, it is* |
| *you should…*（泛指） | *people / individuals / one should…* |
| *really, very good* | *highly effective, significant* |

### 精确 > 华丽
- *Technology is **good** for education.* → *Technology makes learning materials **more accessible** to students in remote areas.*
- 不要为了“高级”硬塞生僻词，**用错的高级词不如用对的简单词**。

### 简洁：删掉冗余
- *In my personal opinion, I think…* → *I believe…*
- *The reason is because…* → *The reason is that…* / *This is because…*
- *Each and every student* → *Every student*

### 中国学生高频错误 Top 8
1. **双谓语**：*There are many people **think**…* → *Many people **think**…*
2. **Although… but…**：英文只能二选一 → *Although it is hard, **(but)** I…*
3. **逗号连句（comma splice）**：*It is late, we should go.* → *It is late, **so** we should go.* / 用句号或分号
4. ***learn knowledge*** → *acquire knowledge / learn skills*
5. ***discuss about*** → *discuss*（discuss 是及物动词）
6. **主谓一致**：*The number of cars **are** rising.* → *The number of cars **is** rising.*
7. **万能词滥用**：*more and more, nowadays, in a word, with the development of*
8. **名词单复数/可数性**：*informations, advices, homeworks* → *information, advice, homework*

### 句式多样
混合使用简单句、并列句和复合句；适当用定语从句、分词短语、非谓语结构，但**准确优先于复杂**。
""",
        "examples": [
            {
                "weak": "Nowadays, there are a lot of kids play phone games, it's really bad for them.",
                "strong": "Many children now spend a significant amount of time playing games on their phones, which can harm their sleep and concentration.",
                "why": "改掉了双谓语（there are … play）、逗号连句、口语词（a lot of, kids, it's, really bad），并把空泛的 “bad” 具体化。",
            },
            {
                "weak": "Although online classes are convenient, but many students feel lonely.",
                "strong": "Although online classes are convenient, many students feel isolated.",
                "why": "Although 和 but 不能同时使用；isolated 比 lonely 更贴合语境。",
            },
        ],
        "quiz": [
            {
                "q": "下面哪一句是正确的？",
                "options": [
                    "There are many students want to study abroad.",
                    "Many students want to study abroad.",
                    "Although studying abroad is expensive, but many students want to go.",
                    "Many students want to study abroad, it is popular.",
                ],
                "answer": 1,
                "explain": "A 双谓语，C Although…but 连用，D 逗号连句。",
            },
            {
                "q": "“The number of students ___ increasing.” 应填？",
                "options": ["are", "is", "were", "be"],
                "answer": 1,
                "explain": "主语是 the number（单数），所以用 is；对比：A number of students are…",
            },
        ],
        "exercise": {
            "task": """把下面 4 个句子改写成正确、正式的学术英语：

1. *There are many people think that money can buy happiness.*
2. *Although the plan is good, but it costs a lot of money.*
3. *Kids nowadays get lots of homeworks, it's really tiring.*
4. *In my personal opinion, I think we should discuss about this problem.*""",
            "placeholder": "1. ...\n2. ...\n3. ...\n4. ...",
            "criteria": "是否修正了每句的核心错误（1 双谓语；2 Although…but；3 口语词、homework 不可数、逗号连句；4 冗余与 discuss about）；改写是否正式、准确、自然，且没有引入新错误。",
        },
    },
    {
        "id": "revision",
        "icon": "🔁",
        "title": "第 9 课 · 修改策略与如何用好 AI 反馈",
        "goal": "学会系统地修改自己的文章，并把 AI 批改变成真正的进步。",
        "content": """
### 修改的三个层次
| 层次 | 关注点 | 问自己 |
|---|---|---|
| **Revising 修改** | 内容、论点、结构 | 回答题目了吗？论点够有力吗？段落顺序合理吗？ |
| **Editing 编辑** | 句子、用词、衔接 | 句子清楚吗？有没有更准确的词？过渡自然吗？ |
| **Proofreading 校对** | 拼写、标点、格式 | 有没有拼写、单复数、时态、标点错误？ |

> **先大后小**：先改论点和结构，再改句子和词。否则你可能精心润色了一段最后要删掉的话。

### 实用修改技巧
1. **反向大纲（Reverse outline）**：写完后，用一句话概括每段的中心。如果概括不出来，或两段说的是同一件事，就需要重组。
2. **大声朗读**：读起来卡顿的地方，往往就是句子有问题的地方。
3. **放一放再看**：隔一段时间再读，更容易发现问题。
4. **个人错误清单**：记录自己反复犯的错误，下次重点检查。

### 如何用好 AI 批改
- ✅ **先处理“重要”问题**（论点、结构、逻辑），再看语法细节
- ✅ **先理解原因再修改**：看不懂就去“写作导师”页面追问
- ✅ **自己动手改**，再提交给 AI 对比——这样进步最快
- ✅ 对 AI 的建议保持判断：它也可能误解你的意图，你可以不采纳
- ❌ 不要直接复制 AI 的范例改写——那是 AI 的文章，不是你的进步
""",
        "examples": [
            {
                "weak": "拿到批改后，逐个改掉所有拼写和语法错误，然后就提交第二稿。",
                "strong": "拿到批改后，先看最重要的 2–3 个修改任务（例如 thesis 不清、第二段缺少分析），重写这些部分；再处理语言问题；最后把自己常犯的错误记进错误清单。",
                "why": "只改表层错误，分数往往提升有限；先解决结构和论证问题，才能真正提高文章质量。",
            },
        ],
        "quiz": [
            {
                "q": "修改文章的推荐顺序是？",
                "options": [
                    "拼写 → 句子 → 结构",
                    "结构和论点 → 句子和用词 → 拼写标点",
                    "只改语法即可",
                    "从最后一段倒着改",
                ],
                "answer": 1,
                "explain": "先大后小（global → local），避免在会被删掉的内容上浪费时间。",
            },
            {
                "q": "“反向大纲”是指？",
                "options": [
                    "从结论开始写文章",
                    "写完后用一句话概括每段中心，检查结构",
                    "把大纲倒过来写",
                    "让 AI 生成大纲",
                ],
                "answer": 1,
                "explain": "反向大纲是检查段落是否“一段一中心”、是否有重复或跑题的利器。",
            },
        ],
        "exercise": {
            "task": """**反向大纲练习**：从你自己写过的一篇 essay 中粘贴**一个主体段**，然后：

1. 用一句话写出这段的中心意思（反向大纲）
2. 写出你认为这段最需要修改的一个地方，以及你打算怎么改""",
            "placeholder": "【段落】\n...\n\n【一句话中心】\n...\n\n【我打算修改】\n...",
            "criteria": "学生的一句话概括是否准确反映了段落实际内容（如果段落本身中心不清，要指出来）；学生找到的问题是否确实是该段最重要的问题；修改计划是否具体可行；如果有更重要的问题被忽略，要指出。",
        },
    },
]

LESSON_BY_ID = {lesson["id"]: lesson for lesson in LESSONS}
