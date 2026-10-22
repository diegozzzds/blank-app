# EssayCoach 设计依据：怎样才能真正学会写 essay

这份文档说明 EssayCoach 的每个主要设计来自哪些研究，以及证据有多强。目标只有一个：**让学生在没有 AI 帮助时也能写得更好**，而不只是让当前这篇作文变好看。

## 调研方法

- 分 5 个方向检索论文：写作教学、写作反馈与 AI 批改、刷题的学习科学、AI 辅导的利弊与学习动机、诊断与学习路径。每个方向由一个研究 agent 检索并阅读原文（优先元分析、随机对照实验和高被引综述），共整理出 125 条发现。
- 每个方向再由一个独立的核实 agent 逐条查找原文（出版社页面、DOI、Crossref、Semantic Scholar、全文 PDF），核对作者、年份、刊名和效应量是否与原文一致，并把夸大的结论降级。
- 结果：**106 条直接核实通过，19 条修正了引用信息或措辞**（例如更正作者列表、指出某个结论只对六年级学生成立），**没有一条被推翻，也没有找不到出处的**。
- 证据强度：**强** = 多项元分析或大样本随机对照实验一致；**中** = 单个元分析或若干实验；**弱** = 小样本、个案或会议摘要；**不一** = 研究结论不一致。

> 重要的局限：大部分写作教学证据来自英语母语的中小学课堂，很多学习科学证据来自数学或词汇学习。把它们用到“中国学生自学英文 essay + AI 辅导”这个场景，属于有根据的推断，还没有被直接检验。

---

## 一、总表：研究结论 → 应用里的做法

| 研究结论 | 证据 | EssayCoach 的做法 |
|---|---|---|
| 写作策略教学效果最大（青少年 ES≈0.82，SRSD≈1.17）；按“达标”而不是按时间推进 | 强 | 技能拆成 33 个知识点；掌握等级按达标判断，不按做题数量 |
| 句子合并训练提升写作质量（ES≈0.50），传统孤立语法教学没有帮助甚至略有负面（ES≈−0.32） | 强 | 题库以句子合并、找错改错、改写为主，不出语法术语题；语法从学生自己的错误里教 |
| 具体的论证目标（立场、理由、反方、反驳）比笼统的“说服读者”效果好；“说服”指令反而减少反方论证 | 中 | 写议论文时显示“论证要素清单”；题目和提示不以“说服”作为目标 |
| 中国 EFL 学生很少写反方与反驳，而这两项和高分相关；明确教学有效 | 中 | “反方与反驳”“批判性提问”在规划中优先级高（先验权重 0.9 / 0.8） |
| 检索练习（先自己做）比重复阅读记得牢；间隔复习效果稳定，二语学习同样适用 | 强 | 每题先作答；错题和技能按 FSRS 间隔复习；间隔不超过离考试天数的 20% |
| 交错练习更难但记得更久，尤其是相似的规则 | 中 | “今日任务”混合多个技能，同一技能不连续出现 3 次以上 |
| 题目难度要自适应、成功率偏高（理论约 85%，实际系统中学生觉得 65–75% 最合适） | 中 | Elo 同时估计学生能力和题目难度，选题对准约 75% 的预计正确率（初中 80%） |
| 连续重新学习（同一次练习里做到对，之后隔几天再做）显著提升长期保持 | 强 | 做错的技能隔 2 题后用同类新题再测；错题在不同日子独立做对 3 次才移出错题本 |
| 高把握的错误最容易被纠正 | 中 | 答题前问“有多大把握”；有把握却答错时特别提示，并更早再测 |
| 详细的反馈（解释原因）比只给对错有效 | 强 | 每个选项都有解析；开放题由 AI 说明做对了什么、问题在哪、规则是什么 |
| 练习时的表现不等于学会；有 AI 帮助时的正确率会制造“学会了”的错觉 | 强 | 掌握度只按独立完成计算；进度页并列显示“独立正确率”和“有帮助时的正确率” |
| 不加限制的 GPT 辅导提高练习成绩，但撤掉 AI 后考试成绩下降 17%；只给提示的版本基本消除了这种伤害 | 强 | “先尝试 → 逐级提示（每级之间要再试一次）→ 最后才看答案”写在代码里；AI 不改写学生当前的句子 |
| 反馈信息量越高效果越好（高信息反馈 d≈0.99，纯对错 d≈0.24）；针对人的表扬或批评效果最差 | 强 | 反馈卡片：引用原文 + 问题 + 原因 + 修改策略 + 自查问题；只做引用原文的具体肯定 |
| ChatGPT 反馈最大的弱点是不会抓重点；反馈过多会让水平较低的学生不知所措 | 中 | 每篇最多 3 个重点问题 + 3 类错误模式（初中最多 2 个），先在心里列全再挑最重要的 |
| 反馈后必须修改，效果更好；只看修改稿进步不代表学会，要看新文章 | 中 | 每条反馈写下修改计划后才能修改；AI 逐条检查是否真的改好；修改稿分数不进入进步曲线 |
| 自评和对照能提升写作；学生要学会判断自己的文章 | 强 | 看反馈前先给自己打分，再对照 AI 估计；“当考官”题型练习按标准评文 |
| LLM 打分和人类的一致性一般，对英语学习者更低，偏向中间分数；给参照样本是提高准确度的主要手段 | 中 | 分数用区间展示并标注“估计”；评分提示中加入雅思公开评分描述的分档参照 |
| 完全由 LLM 自由生成的学习路径经常不合格 | 弱 | 学习大纲：程序先算候选清单，AI 只能在固定技能图谱里挑选和排序，程序再校验修复并列出修改 |
| 单篇作文分数很不可靠，约 10% 的差异反映真实水平 | 强 | 每两周一篇独立检测作文，看多篇的趋势；进度页提示不要看单篇 |
| 具体的近期学习目标 + 进度反馈比“尽力而为”好；记录进度有助于达成目标 | 强 | 每周目标用“学会某个策略”表述；首页和进度页记录并显示进度 |
| 排行榜、强制徽章、按数量计分可能降低内在动机；连胜能维持投入，能补签会减少断签带来的流失 | 中 | 不做排行榜；连续学习按“每天完成至少 10 题（不含看答案的题）”计算，每 7 天可以补签一次 |
| 未经核对的 AI 生成提示有相当比例不合格 | 中 | AI 出的新题先由另一次调用逐题核对，答案不唯一或有错误的直接丢弃；学生可以一键报告问题题目 |

---

## 二、分主题说明

### 1. 练什么：写作教学里真正有效的成分

- **策略教学效果最大。** Graham & Perin (2007) 对 4–12 年级的元分析中，策略教学的效应量为 0.82；Graham, McKeown, Kiuhara & Harris (2012) 中 SRSD 为 1.17。SRSD 的关键是：示范策略、记住策略、有支持地练习、独立使用，**按达标推进而不是按时间推进**。大学生和中国 EFL 本科生的研究也有效果，但不能自动改善语法（MacArthur et al. 2015；Teng & Zhang 2020）。
  → EssayCoach 把篇章和段落技能做成“规则卡 + 微课 + 刷题”，掌握等级要求连续独立答对，而不是做满多少题。
- **句子合并有效，孤立语法教学无效。** 句子合并 ES≈0.50；传统语法教学 ES≈−0.32（Graham & Perin 2007），Koster et al. (2015) 也是负值。在语境中把语法当作表达选择来教是有帮助的（Myhill et al. 2012）。
  → 不出“这是什么词性”之类的题；语言类技能都用真实句子来练，作文里的错误直接变成“改你自己的句子”。
- **具体的论证目标。** 给出细化目标（立场、2–3 个理由和论据、反方观点及反驳）明显提高议论文质量（Ferretti, MacArthur & Dowdy 2000，六年级有效、四年级无效）；只说“说服读者”反而减少反方论证（Nussbaum & Kardash 2005）。论证-反方整合的图式和标准教学有效（Nussbaum & Schraw 2007）；大学生学习用“批判性问题”修改论证，文章质量更高（Song & Ferretti 2013）。
- **中国学生的特殊弱项。** 中国 EFL 大学生的议论文很少出现反方观点和反驳（Qin & Karabacak 2010），而这两项与高利害考试的分数正相关，明确教学有效（Liu & Stapleton 2014）。
- **过程写作本身效果有限。** 只是“计划—起草—修改”的循环，效应量约 0.34，对写作困难的学生帮助不明显（Graham & Sandmel 2011）；单纯多写不能可靠地提高写作水平。
  → 作文流程里嵌入针对弱项的刷题和微课，而不是只让学生反复写。

### 2. 怎么刷：练习的学习科学

- **检索练习和间隔复习。** 先测试比重复阅读记得牢（Roediger & Karpicke 2006）；间隔应随需要保持的时间加长，间隔太长的损失比太短小（Cepeda et al. 2006）；二语学习中间隔练习有中到大的效果（Kim & Webb 2022）。复杂任务上测试效应可能变小（van Gog & Sweller 2015），所以整篇作文之外还要练拆分出来的子技能。
- **交错练习。** 交错学习相似的类别有助于区分和迁移（Brunmair & Richter 2019）；二语语法中交错练习时错误更多，但一周后记得更牢（Nakata & Suzuki 2019）。
- **连续重新学习。** 一次练习里做到对，再隔几天重复几轮，显著提高考试成绩和长期保持（Rawson, Dunlosky & Sciartelli 2013）；做错的题应该很快再出现，但不要紧接着出现（Mettler, Massey & Kellman 2016）。
- **难度与能力估计。** 学习的最佳成功率理论上约 85%（Wilson et al. 2019），在实际的自适应练习系统里学生觉得 65–75% 最合适；Elo 评分可以同时估计学生能力和题目难度，并能处理选择题的猜测（Pelánek 2016）。个性化复习优于固定间隔（Lindsey et al. 2014）；FSRS 预测记忆的效果优于半衰期回归。
- **掌握标准。** 掌握学习对较弱的学生帮助更大（Kulik, Kulik & Bangert-Drowns 1990）；“连续答对 N 题”是简单可用的掌握判断，但容易受失误影响（Kelly et al. 2015，证据弱）。
  → EssayCoach 的“已学会”要求独立正确率的指数平均 ≥ 0.85 且连续独立答对 4 道不同的题；之后还要隔天复习两次都对才算“已巩固”，在独立作文里用对才算“已迁移”。
- **反馈与错误。** 详细解释优于只给正确答案，后者又优于只说对错（Van der Kleij et al. 2015）；高把握的错误更容易被纠正（Metcalfe 2017）。
- **整体任务为主，子技能为辅。** 4C/ID 模型：以由易到难的完整任务为主线，只对需要自动化的子技能做拆分练习（Costa et al. 2022）。
  → 每周有作文任务，刷题针对最近一篇作文暴露的弱项（focus_kcs 在选题中优先）。
- **表现 ≠ 学习。** 学生会把流畅、容易的练习误当作学会了（Soderstrom & Bjork 2015）；练习测试和间隔练习是效用最高的学习方法（Dunlosky et al. 2013）。

### 3. 反馈怎么给：AI 批改的有效做法

- **自动反馈有效，但效应量有水分。** AWE 元分析报告 g≈0.86，对 EFL、大学生和议论文更大（Zhai & Ma 2023），但这些研究异质性大；更严格的估计是 g≈0.55，且波动范围极大（Fleckenstein, Liebenow & Meyer 2023）；学校层面电脑反馈约 0.38（Graham, Hebert & Harris 2015）。
- **LLM 反馈。** 对 459 名中学 EFL 学生的随机实验中，GPT-3.5 反馈对修改表现的提升很小（d≈0.19），但明显提高了任务动机和积极情绪（Meyer et al. 2024）。ChatGPT 反馈接近但略低于受训的人类反馈，最大弱点是**不会抓最关键的问题**（Steiss et al. 2024）。
- **反馈要有信息量。** 高信息反馈 d≈0.99，纯纠正 d≈0.46，奖惩 d≈0.24（Wisniewski, Zierer & Hattie 2020）；反馈要回答“目标是什么、现在怎样、下一步做什么”，针对人的反馈效果最差（Hattie & Timperley 2007）；反馈要分小块、在学生尝试之后给出、少用分数比较（Shute 2008）；书面评语优于分数（Koenka et al. 2021）。
- **二语纠错反馈。** 书面纠错能持久地提高语法准确性，直接、间接、元语言提示的效果大体相近（Kang & Han 2015；Brown, Liu & Norouzian 2023）；综合纠错在新文章中也有效，直接纠正对语法错误更有效（Van Beuningen, De Jong & Kuiken 2012）；反馈后要求重写效果更好（Shintani, Ellis & Suzuki 2014）。
- **学生要真正用上反馈。** 反馈只有被学生采取行动时才有价值（Carless & Boud 2018）；一名水平较低的中国学生面对大量自动纠错时不知所措、不信任机器，还会删掉句子来回避错误（Zhang & Hyland 2018）；用 Grammarly 的中国学生大多只是照着改，而不是学习（Ranalli 2021）。
- **修改不等于学会。** 修改稿变好并不能说明学会了，常常不能迁移到新文章（Stevenson & Phakiti 2014；Truscott & Hsu 2008）。
  → EssayCoach：限量反馈 → 学生逐条写修改计划 → 修改 → AI 检查是否真的改好、是否只改了表面 → 修改稿分数不算进步，进步只看独立完成的新作文。
- **AI 打分的可靠性。** LLM 整体打分与受训人类只有一般到中等的一致性，对英语学习者更低，分数会向中间压缩，只适合低利害的形成性使用（Tate et al. 2024）；没有参照样本时 GPT-4 的 CEFR 评级甚至不如只看文章长度，给每档一个参照后明显改善（Yancey et al. 2023）；开源模型对语法维度系统性偏严（Kucia et al. 2026）。
  → 分数用区间展示并标注“估计”，评分提示里加入公开评分描述的分档参照，并在文档中说明局限。

### 4. AI 的边界：帮忙但不代劳

- **不加限制的 AI 会伤害学习。** 近 1000 名高中生的实验中，自由使用 GPT-4 让练习成绩提高 48%，但撤掉 AI 后的考试成绩下降 17%；只给提示、不给答案的“GPT Tutor”基本消除了这种伤害（Bastani et al. 2025, PNAS）。
- **写作中的“元认知懒惰”。** ChatGPT 帮助修改让作文分数提高，但知识和迁移没有提高（Fan et al. 2025）；用 LLM 写作的学生对自己文章的记忆和拥有感更差，先独立写再用 AI 的顺序更好（Kosmyna et al. 2025，小样本、未经同行评议）。
- **先尝试再看解释更好。** 学生先尝试再看 LLM 的解释，学习效果比直接看答案好（Kumar et al. 2025）；先解决问题再听讲解（productive failure）对概念学习更好（Sinha & Kapur 2021）。
- **结构化的 AI 辅导有效。** 由代码控制顺序、提示词中有专家写的分步解答的 AI 辅导，在随机实验中优于课堂主动学习（Kestin et al. 2025）；按步骤反馈的智能辅导系统接近人类辅导（VanLehn 2011）。
- **求助会被滥用。** 学生常常连点提示直到看到答案，或者完全不求助；“钻系统空子”与学习差显著相关（Aleven et al. 2003；Baker et al. 2004）。
  → 每看一级提示前都要再试一次；答错两次或看完提示后才能看答案；看答案算作没做对，并要求用自己的话解释一遍（自我解释有效：Bisra et al. 2018）。
- **感觉学会 ≠ 真的学会。** 学生对“学到多少”的感觉不可靠，费力的主动学习感觉更差但效果更好（Deslauriers et al. 2019）。
- **AI 生成的内容要核对。** LLM 生成的提示能带来与人类相当的学习效果，但相当比例通不过质量检查（Pardos & Bhandari 2024）。

### 5. 学习大纲与诊断

- **固定技能图谱 + AI 个性化。** LLM 生成的学习计划存在内容编造和不透明的问题，加上解释和用户控制后更好用（Chun et al. 2025, PlanGlow，证据弱）。
  → 技能图谱固定、带版本号；AI 只能在候选清单里挑选和排序；程序校验并列出修正；学生可以手动调整每周技能。
- **诊断要具体。** 有详细描述的诊断量表比考试用的笼统量表可靠得多（Knoch 2009）；从学生真实错误中构建的客观题库能精确定位语言问题（Xie 2020）；二语写作比母语写作更依赖语言知识和流利度（Schoonen et al. 2011）。
  → 快速诊断题 + 诊断作文（AI 给出各技能点的证据），之后随刷题不断修正估计。
- **单篇作文不可靠。** 不同评分者、题目和文体之间，只有约 10% 的分数差异反映个人写作水平，至少需要多篇文章才能得出可靠结论（Bouwer et al. 2015）。
- **目标与进度监测。** 具体而有挑战的目标优于“尽力而为”，复杂任务上用学习目标和近期子目标更好（Locke & Latham 2002）；记录并监测目标进度能提高达成率（Harkin et al. 2016）。
- **不要高估计划的作用。** 小规模实验中有效的“制定计划”类干预，规模化后效果小一个数量级（Kizilcec et al. 2020）。
- **写作分数提升慢。** 观察数据显示，集中备考约 10–12 周雅思写作提高约半个分数段，个体差异很大（Kang et al. 2021，观察性研究）。
  → 计划默认 8 周，提醒至少坚持 6–8 周。

### 6. 动机

- 游戏化对学习有小到中等的正面效果，但对动机的效果不稳定（Sailer & Homner 2020）；排行榜、强制徽章、按数量计分可能降低内在动机和考试成绩（Hanus & Fox 2015）。
- 看得见的连胜会增加持续投入，断签会减少投入，能补签可以缓解（Silverman & Barasch 2022）。
- 可预期的控制性奖励会削弱内在动机，信息性的正面反馈会增强（Deci, Koestner & Ryan 1999）；单独的成长型思维干预平均效果很小（Sisk et al. 2018）。
  → 不做排行榜和积分；连续学习按“有意义的练习”计算并允许补签；反馈重信息量，不说空洞的鼓励。

---

## 三、目前的局限与待验证的问题

- **没有在真实学生身上测过效果。** 这些设计都有研究依据，但组合在一起、用于中国学生自学英文 essay，效果需要实际检验。建议：每 2–4 周用新题目做一篇独立作文，盲评打分，看长期趋势；对反馈格式等做 A/B 测试。
- **AI 打分没有本地校准。** 研究建议用 30–50 篇由人类评分的中国学生作文作为“金标准”，每次换模型或改提示词后检查一致性和偏差。目前只做了分档参照和区间展示。
- **种子题库由 AI 编写并经过 AI 核对**，没有经过人类教师审校；学生可以报告有问题的题目，被报告的题目不会再出现。
- **AI 打分对中文母语学生的一致性**：已有研究发现 GPT-4 对中文母语作者的作文与人类评分的一致性较低（Yancey et al. 2023），当前 Claude 模型是否有同样问题尚未验证。
- **刷题的提升能否迁移到整篇作文**：自适应难度在其他学科有随机实验证据（如 Chung et al. 2026，预印本），在写作中尚未被检验，所以 EssayCoach 用独立作文而不是刷题正确率来衡量“已迁移”。

---

## 参考文献（按主题）

**写作教学**
- Graham, S., & Perin, D. (2007). A meta-analysis of writing instruction for adolescent students. *Journal of Educational Psychology, 99*(3), 445–476. https://doi.org/10.1037/0022-0663.99.3.445
- Graham, S., McKeown, D., Kiuhara, S., & Harris, K. R. (2012). A meta-analysis of writing instruction for students in the elementary grades. *Journal of Educational Psychology, 104*(4), 879–896. https://doi.org/10.1037/a0029185
- Graham, S., Kim, Y.-S. G., Cao, Y., et al. (2023). A meta-analysis of writing treatments for students in grades 6–12. *Journal of Educational Psychology*. https://doi.org/10.1037/edu0000819
- MacArthur, C. A., Philippakos, Z. A., & Ianetta, M. (2015). Self-regulated strategy instruction in college developmental writing. *Journal of Educational Psychology, 107*(3), 855–867. https://doi.org/10.1037/edu0000011
- Teng, L. S., & Zhang, L. J. (2020). Empowering learners in the second/foreign language classroom: Can self-regulated learning strategies-based writing instruction make a difference? *Journal of Second Language Writing, 48*, 100701. https://doi.org/10.1016/j.jslw.2019.100701
- Saddler, B., & Graham, S. (2005). The effects of peer-assisted sentence-combining instruction on the writing performance of more and less skilled young writers. *Journal of Educational Psychology, 97*(1), 43–54. https://doi.org/10.1037/0022-0663.97.1.43
- Myhill, D. A., Jones, S. M., Lines, H., & Watson, A. (2012). Re-thinking grammar: The impact of embedded grammar teaching on students' writing and students' metalinguistic understanding. *Research Papers in Education*. https://doi.org/10.1080/02671522.2011.637640
- Ferretti, R. P., MacArthur, C. A., & Dowdy, N. S. (2000). The effects of an elaborated goal on the persuasive writing of students with learning disabilities and their normally achieving peers. *Journal of Educational Psychology, 92*(4), 694–702. https://doi.org/10.1037/0022-0663.92.4.694
- Nussbaum, E. M., & Kardash, C. M. (2005). The effects of goal instructions and text on the generation of counterarguments during writing. *Journal of Educational Psychology, 97*(2), 157–169. https://doi.org/10.1037/0022-0663.97.2.157
- Nussbaum, E. M., & Schraw, G. (2007). Promoting argument–counterargument integration in students' writing. *Journal of Experimental Education, 76*(1), 59–92. https://doi.org/10.3200/JEXE.76.1.59-92
- Song, Y., & Ferretti, R. P. (2013). Teaching critical questions about argumentation through the revising process. *Reading and Writing, 26*(1), 67–90. https://doi.org/10.1007/s11145-012-9381-8
- Qin, J., & Karabacak, E. (2010). The analysis of Toulmin elements in Chinese EFL university argumentative writing. *System, 38*(3), 444–456. https://doi.org/10.1016/j.system.2010.06.012
- Liu, F., & Stapleton, P. (2014). Counterargumentation and the cultivation of critical thinking in argumentative writing: Investigating washback from a high-stakes test. *System, 45*, 117–128. https://doi.org/10.1016/j.system.2014.05.005
- Graham, S., & Sandmel, K. (2011). The process writing approach: A meta-analysis. *The Journal of Educational Research, 104*(6), 396–407. https://doi.org/10.1080/00220671.2010.488703
- Kellogg, R. T. (2008). Training writing skills: A cognitive developmental perspective. *Journal of Writing Research, 1*(1), 1–26. https://doi.org/10.17239/jowr-2008.01.01.1

**反馈与 AI 批改**
- Graham, S., Hebert, M., & Harris, K. R. (2015). Formative assessment and writing: A meta-analysis. *The Elementary School Journal, 115*(4), 523–547. https://doi.org/10.1086/681947
- Zhai, N., & Ma, X. (2023). The effectiveness of automated writing evaluation on writing quality: A meta-analysis. *Journal of Educational Computing Research, 61*(4), 875–900. https://doi.org/10.1177/07356331221127300
- Fleckenstein, J., Liebenow, L. W., & Meyer, J. (2023). Automated feedback and writing: A multi-level meta-analysis of effects on students' performance. *Frontiers in Artificial Intelligence, 6*, 1162454. https://pmc.ncbi.nlm.nih.gov/articles/PMC10351274/
- Meyer, J., Jansen, T., Schiller, R., Liebenow, L. W., Steinbach, M., Horbach, A., & Fleckenstein, J. (2024). Using LLMs to bring evidence-based feedback into the classroom. *Computers and Education: Artificial Intelligence, 6*, 100199. https://doi.org/10.1016/j.caeai.2023.100199
- Steiss, J., Tate, T., Graham, S., Cruz, J., Hebert, M., Wang, J., Moon, Y., Tseng, W., Warschauer, M., & Olson, C. B. (2024). Comparing the quality of human and ChatGPT feedback of students' writing. *Learning and Instruction, 91*, 101894. https://doi.org/10.1016/j.learninstruc.2024.101894
- Wisniewski, B., Zierer, K., & Hattie, J. (2020). The power of feedback revisited: A meta-analysis of educational feedback research. *Frontiers in Psychology, 10*, 3087. https://pmc.ncbi.nlm.nih.gov/articles/PMC6987456
- Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of Educational Research, 77*(1), 81–112. https://doi.org/10.3102/003465430298487
- Shute, V. J. (2008). Focus on formative feedback. *Review of Educational Research, 78*(1), 153–189. https://doi.org/10.3102/0034654307313795
- Koenka, A. C., Linnenbrink-Garcia, L., Moshontz, H., Atkinson, K. M., Sanchez, C. E., & Cooper, H. (2021). A meta-analysis on the impact of grades and comments on academic motivation and achievement. *Educational Psychology*. https://doi.org/10.1080/01443410.2019.1659939
- Kang, E., & Han, Z. (2015). The efficacy of written corrective feedback in improving L2 written accuracy: A meta-analysis. *The Modern Language Journal, 99*(1), 1–18. https://doi.org/10.1111/modl.12189
- Brown, D., Liu, Q., & Norouzian, R. (2023). Effectiveness of written corrective feedback in developing L2 accuracy: A Bayesian meta-analysis. *Language Teaching Research*. https://doi.org/10.1177/13621688221147374
- Van Beuningen, C. G., De Jong, N. H., & Kuiken, F. (2012). Evidence on the effectiveness of comprehensive error correction in second language writing. *Language Learning, 62*(1), 1–41. https://doi.org/10.1111/j.1467-9922.2011.00674.x
- Shintani, N., Ellis, R., & Suzuki, W. (2014). Effects of written feedback and revision on learners' accuracy in using two English grammatical structures. *Language Learning, 64*(1), 103–131. https://doi.org/10.1111/lang.12029
- Carless, D., & Boud, D. (2018). The development of student feedback literacy: Enabling uptake of feedback. *Assessment & Evaluation in Higher Education, 43*(8), 1315–1325. https://doi.org/10.1080/02602938.2018.1463354
- Zhang, Z. (V.), & Hyland, K. (2018). Student engagement with teacher and automated feedback on L2 writing. *Assessing Writing, 36*, 90–102. https://doi.org/10.1016/j.asw.2018.02.004
- Ranalli, J. (2021). L2 student engagement with automated feedback on writing: Potential for learning and issues of trust. *Journal of Second Language Writing, 52*, 100816. https://doi.org/10.1016/j.jslw.2021.100816
- Stevenson, M., & Phakiti, A. (2014). The effects of computer-generated feedback on the quality of writing. *Assessing Writing, 19*, 51–65. https://doi.org/10.1016/j.asw.2013.11.007
- Tate, T. P., Steiss, J., Bailey, D. H., Graham, S., Moon, Y., Ritchie, D., Tseng, W., & Warschauer, M. (2024). Can AI provide useful holistic essay scoring? *Computers and Education: Artificial Intelligence, 7*, 100255. https://doi.org/10.1016/j.caeai.2024.100255
- Yancey, K. P., LaFlair, G. T., Verardi, A. R., & Burstein, J. (2023). Rating short L2 essays on the CEFR scale with GPT-4. *Proceedings of BEA 2023*. https://aclanthology.org/2023.bea-1.49/
- Kucia, F. J., Chakraborty, A., & Wróblewska, A. (2026). LLM essay scoring under holistic and analytic rubrics: Prompt effects and bias. *ICCS 2026*. https://arxiv.org/abs/2604.00259

**练习的学习科学**
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning. *Psychological Science, 17*(3), 249–255. https://doi.org/10.1111/j.1467-9280.2006.01693.x
- Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis. *Psychological Bulletin, 132*(3), 354–380. https://doi.org/10.1037/0033-2909.132.3.354
- Kim, S. K., & Webb, S. (2022). The effects of spaced practice on second language learning: A meta-analysis. *Language Learning, 72*(1), 269–319. https://doi.org/10.1111/lang.12479
- van Gog, T., & Sweller, J. (2015). Not new, but nearly forgotten: The testing effect decreases or even disappears as the complexity of learning materials increases. *Educational Psychology Review, 27*(2), 247–264. https://doi.org/10.1007/s10648-015-9310-x
- Brunmair, M., & Richter, T. (2019). Similarity matters: A meta-analysis of interleaved learning and its moderators. *Psychological Bulletin, 145*(11), 1029–1052. https://doi.org/10.1037/bul0000209
- Nakata, T., & Suzuki, Y. (2019). Mixing grammar exercises facilitates long-term retention. *The Modern Language Journal, 103*(3), 629–647. https://doi.org/10.1111/modl.12581
- Rawson, K. A., Dunlosky, J., & Sciartelli, S. M. (2013). The power of successive relearning. *Educational Psychology Review, 25*(4), 523–548. https://doi.org/10.1007/s10648-013-9240-4
- Mettler, E., Massey, C. M., & Kellman, P. J. (2016). A comparison of adaptive and fixed schedules of practice. *Journal of Experimental Psychology: General, 145*(7), 897–917. https://doi.org/10.1037/xge0000170
- Wilson, R. C., Shenhav, A., Straccia, M., & Cohen, J. D. (2019). The Eighty Five Percent Rule for optimal learning. *Nature Communications, 10*, 4646. https://doi.org/10.1038/s41467-019-12552-4
- Pelánek, R. (2016). Applications of the Elo rating system in adaptive educational systems. *Computers & Education, 98*, 169–179. https://doi.org/10.1016/j.compedu.2016.03.017
- Lindsey, R. V., Shroyer, J. D., Pashler, H., & Mozer, M. C. (2014). Improving students' long-term knowledge retention through personalized review. *Psychological Science, 25*(3), 639–647. https://pubmed.ncbi.nlm.nih.gov/24444515/
- Ye, J., Su, J., & Cao, Y. (2022). A stochastic shortest path algorithm for optimizing spaced repetition scheduling (FSRS). *KDD 2022*. https://doi.org/10.1145/3534678.3539081
- Kulik, C.-L. C., Kulik, J. A., & Bangert-Drowns, R. L. (1990). Effectiveness of mastery learning programs: A meta-analysis. *Review of Educational Research, 60*(2), 265–299. https://doi.org/10.3102/00346543060002265
- Kelly, K., Wang, Y., Thompson, T., & Heffernan, N. (2015). Defining mastery: Knowledge tracing versus N-consecutive correct responses. *EDM 2015* (poster).
- Van der Kleij, F. M., Feskens, R. C. W., & Eggen, T. J. H. M. (2015). Effects of feedback in a computer-based learning environment on students' learning outcomes: A meta-analysis. *Review of Educational Research, 85*(4), 475–511. https://doi.org/10.3102/0034654314564881
- Metcalfe, J. (2017). Learning from errors. *Annual Review of Psychology, 68*, 465–489. https://doi.org/10.1146/annurev-psych-010416-044022
- Costa, J. M., Miranda, G. L., & Melo, M. (2022). Four-component instructional design (4C/ID) model: A meta-analysis on use and effect. *Learning Environments Research, 25*(2), 445–463. https://doi.org/10.1007/s10984-021-09373-y
- Soderstrom, N. C., & Bjork, R. A. (2015). Learning versus performance: An integrative review. *Perspectives on Psychological Science, 10*(2), 176–199. https://pubmed.ncbi.nlm.nih.gov/25910388/
- Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013). Improving students' learning with effective learning techniques. *Psychological Science in the Public Interest, 14*(1), 4–58. https://doi.org/10.1177/1529100612453266
- Macnamara, B. N., Hambrick, D. Z., & Oswald, F. L. (2014). Deliberate practice and performance in music, games, sports, education, and professions: A meta-analysis. *Psychological Science, 25*(8), 1608–1618. https://pubmed.ncbi.nlm.nih.gov/24986855/

**AI 辅导、求助与动机**
- Bastani, H., Bastani, O., Sungu, A., Ge, H., Kabakcı, Ö., & Mariman, R. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *PNAS, 122*(26), e2422633122. https://doi.org/10.1073/pnas.2422633122
- Fan, Y., Tang, L., Le, H., Shen, K., Tan, S., Zhao, Y., Shen, Y., Li, X., & Gašević, D. (2025). Beware of metacognitive laziness. *British Journal of Educational Technology, 56*(2), 489–530. https://doi.org/10.1111/bjet.13544
- Kosmyna, N., Hauptmann, E., Yuan, Y. T., et al. (2025). Your Brain on ChatGPT: Accumulation of cognitive debt when using an AI assistant for essay writing task. arXiv:2506.08872. https://arxiv.org/abs/2506.08872
- Kumar, H., Rothschild, D. M., Goldstein, D. G., & Hofman, J. M. (2025). Math education with large language models: Peril or promise? *AIED 2025*. https://www.microsoft.com/en-us/research/publication/math-education-with-large-language-models-peril-or-promise/
- Kestin, G., Miller, K., Klales, A., Milbourne, T., & Ponti, G. (2025). AI tutoring outperforms in-class active learning: An RCT. *Scientific Reports, 15*. https://doi.org/10.1038/s41598-025-97652-6
- Jurenka, I., Kunesch, M., McKee, K. R., Gillick, D., et al. (2024). Towards responsible development of generative AI for education: An evaluation-driven approach (LearnLM). arXiv:2407.12687. https://arxiv.org/abs/2407.12687
- VanLehn, K. (2011). The relative effectiveness of human tutoring, intelligent tutoring systems, and other tutoring systems. *Educational Psychologist, 46*(4), 197–221. https://doi.org/10.1080/00461520.2011.611369
- Roscoe, R. D., & McNamara, D. S. (2013). Writing Pal: Feasibility of an intelligent writing strategy tutor in the high school classroom. *Journal of Educational Psychology, 105*(4), 1010–1025. https://eric.ed.gov/?id=EJ1054373
- Aleven, V., Stahl, E., Schworm, S., Fischer, F., & Wallace, R. (2003). Help seeking and help design in interactive learning environments. *Review of Educational Research, 73*(3), 277–320. https://eric.ed.gov/?id=EJ782605
- Baker, R. S., Corbett, A. T., Koedinger, K. R., & Wagner, A. Z. (2004). Off-task behavior in the Cognitive Tutor classroom. *CHI 2004*. https://doi.org/10.1145/985692.985741
- Bisra, K., Liu, Q., Nesbit, J. C., Salimi, F., & Winne, P. H. (2018). Inducing self-explanation: A meta-analysis. *Educational Psychology Review, 30*(3), 703–725. https://doi.org/10.1007/s10648-018-9434-x
- Sinha, T., & Kapur, M. (2021). When problem solving followed by instruction works: Evidence for productive failure. *Review of Educational Research, 91*(5), 761–798. https://doi.org/10.3102/00346543211019105
- Deslauriers, L., McCarty, L. S., Miller, K., Callaghan, K., & Kestin, G. (2019). Measuring actual learning versus feeling of learning in response to being actively engaged in the classroom. *PNAS, 116*(39), 19251–19257. https://doi.org/10.1073/pnas.1821936116
- Pardos, Z. A., & Bhandari, S. (2024). ChatGPT-generated help produces learning gains equivalent to human tutor-authored help on mathematics skills. *PLOS ONE, 19*(5), e0304013. https://doi.org/10.1371/journal.pone.0304013
- Sailer, M., & Homner, L. (2020). The gamification of learning: A meta-analysis. *Educational Psychology Review, 32*(1), 77–112. https://doi.org/10.1007/s10648-019-09498-w
- Hanus, M. D., & Fox, J. (2015). Assessing the effects of gamification in the classroom. *Computers & Education, 80*, 152–161. https://doi.org/10.1016/j.compedu.2014.08.019
- Silverman, J., & Barasch, A. (2022). On or off track: How (broken) streaks affect consumer decisions. *Journal of Consumer Research, 49*(6), 1095–1117. https://doi.org/10.1093/jcr/ucac029
- Deci, E. L., Koestner, R., & Ryan, R. M. (1999). A meta-analytic review of experiments examining the effects of extrinsic rewards on intrinsic motivation. *Psychological Bulletin, 125*(6), 627–668. https://doi.org/10.1037/0033-2909.125.6.627
- Sisk, V. F., Burgoyne, A. P., Sun, J., Butler, J. L., & Macnamara, B. N. (2018). To what extent and under which circumstances are growth mind-sets important to academic achievement? *Psychological Science, 29*(4), 549–571. https://doi.org/10.1177/0956797617739704

**诊断与学习路径**
- IELTS (2023). Writing Task 2 Band Descriptors (public version, updated May 2023). https://ielts.org/cdn/ielts-guides/ielts-writing-band-descriptors.pdf
- Council of Europe (2020). *Common European Framework of Reference for Languages: Companion Volume*.
- Knoch, U. (2009). Diagnostic assessment of writing: A comparison of two rating scales. *Language Testing, 26*(2), 275–304. https://doi.org/10.1177/0265532208101008
- Xie, Q. (2020). Diagnosing linguistic problems in English academic writing of university students: An item bank approach. *Language Assessment Quarterly, 17*(2), 183–203. https://doi.org/10.1080/15434303.2019.1691214
- Schoonen, R., van Gelderen, A., Stoel, R. D., Hulstijn, J., & de Glopper, K. (2011). Modeling the development of L1 and EFL writing proficiency of secondary school students. *Language Learning, 61*(1), 31–79. https://doi.org/10.1111/j.1467-9922.2010.00590.x
- Bouwer, R., Béguin, A., Sanders, T., & van den Bergh, H. (2015). Effect of genre on the generalizability of writing scores. *Language Testing, 32*(1), 83–100. https://doi.org/10.1177/0265532214542994
- Locke, E. A., & Latham, G. P. (2002). Building a practically useful theory of goal setting and task motivation. *American Psychologist, 57*(9), 705–717. https://doi.org/10.1037/0003-066x.57.9.705
- Harkin, B., Webb, T. L., Chang, B. P. I., Prestwich, A., Conner, M., Kellar, I., Benn, Y., & Sheeran, P. (2016). Does monitoring goal progress promote goal attainment? A meta-analysis. *Psychological Bulletin, 142*(2), 198–229. https://doi.org/10.1037/bul0000025
- Kizilcec, R. F., Reich, J., Yeomans, M., Dann, C., Brunskill, E., Lopez, G., Turkay, S., Williams, J. J., & Tingley, D. (2020). Scaling up behavioral science interventions in online education. *PNAS, 117*(26), 14900–14905. https://doi.org/10.1073/pnas.1921417117
- Chun, J., Zhao, Y., Chen, H., & Xia, M. (2025). PlanGlow: Personalized study planning with an explainable and controllable LLM-driven system. *Learning@Scale 2025*. https://arxiv.org/abs/2504.12452
- Chung, A. T.-H., Zhang, B., Kung, L.-C., Bastani, H., & Bastani, O. (2026). Effective personalized AI tutors via LLM-guided reinforcement learning. arXiv:2608.16907 (preprint). https://arxiv.org/abs/2608.16907
- Kang, O., Ahn, H., Yaw, K., & Chung, S.-Y. (2021). Investigation of relationships between learner background, linguistic progression, and score gain on IELTS. *IELTS Research Reports Online Series, 2021/1*.
