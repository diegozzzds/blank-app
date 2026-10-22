# ✍️ EssayCoach · 英文 essay 刷题与写作教练

一个基于研究设计的英文 essay 学习应用（Streamlit + Claude）。核心思路：**把写作拆成技能点来刷题、按遗忘规律复习、用独立完成的作文检验真实进步**，AI 负责出题、判分、诊断和规划，但不替学生写。

设计依据见 [docs/RESEARCH.md](docs/RESEARCH.md)：调研了 5 个方向的 125 条研究发现，每条都经过独立核实。

## 学习流程

1. **学习大纲（AI 生成，程序校验）**：设定目标考试、分数和日期 → 12 题快速诊断 + 诊断作文 → AI 在固定的技能图谱（33 个技能点）里挑选、排序，生成每周计划 → 程序检查前置关系、每周数量和遗漏，并列出修正。学生可以手动调整每周技能。
2. **刷题（一直刷）**：每天“今日任务” = 到期错题 + 到期技能复习 + 上篇作文的弱项 + 本周技能，交错出现。
   - 题型：选择题、找错改错、句子合并、改写、限定写作、排序、当考官。
   - 先作答 → 答错后逐级看提示（每级之间要再试一次）→ 答错两次或看完提示才能看答案。
   - Elo 估计能力和题目难度，选题对准约 75% 的预计正确率；种子题做完后 AI 按需出新题，并由第二次调用核对答案。
3. **错题本**：做错的题、作文里的语言错误（变成“改你自己的句子”）按 FSRS 间隔复习，不同日子独立做对 3 次才移出。
4. **写作文**：练习作文 / 限时独立检测作文 / 诊断作文。独立写 → 自评打分 → AI 反馈（最多 3 个重点问题 + 3 类错误模式，原文高亮）→ 每条写下修改计划 → 修改 → AI 检查是否真的改好。
5. **进度**：掌握度只按独立完成计算（未开始 → 练习中 → 已学会 → 已巩固 → 已迁移）；真实进步看独立作文的趋势，修改稿分数不算。

另外还有：每个技能的规则卡与微课、技能图谱、写作导师（只引导、不代写）。

## 运行

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

API Key（三选一）：`.streamlit/secrets.toml`（参考 `.streamlit/secrets.toml.example`）、环境变量 `ANTHROPIC_API_KEY`，或运行后在侧边栏填写。
**没有 API Key 也能用**：可以刷种子题库里的自动判分题、看规则卡和微课、用程序生成的基础计划；AI 判分、出新题、作文批改需要 Key。

学习记录保存在浏览器 localStorage 里（关掉页面再打开不会丢），侧边栏可以导出 / 导入 JSON。

运行测试（使用假的 Claude 客户端和 `tests/fixtures` 小题库，不联网）：

```bash
pip install pytest
python -m pytest tests
```

## 使用的公开组件

| 用途 | 组件 |
|---|---|
| 作文原文高亮 | [st-annotated-text](https://github.com/tvst/st-annotated-text)（Apache-2.0） |
| 修改前后对比 | [redlines](https://github.com/houfu/redlines)（MIT） |
| 浏览器存储 | [streamlit_js_eval](https://github.com/aghasemi/streamlit_js_eval)（MIT） |
| 间隔复习算法 | [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)（MIT） |
| 标签、指标卡、技能图谱、雷达图 | Streamlit 内置 `st.badge` / `st.metric` / `st.mermaid_chart` / `st.echarts_chart`；进度图用 Altair |

## 代码结构

```
streamlit_app.py        入口：导航、侧边栏设置、学习记录同步
app_pages/              today 今日任务 · plan 学习大纲 · drill 刷题 · mistakes 错题本 · write 写作文
                        skillmap 技能图谱 · lessons 微课与规则卡 · progress 学习进度 · tutor 写作导师
essay_coach/
  skills.py             技能图谱（33 个技能点、前置关系、评分维度）
  items.py              题目格式与种子题库加载
  content/              种子题库 items.json 与规则卡 rule_cards.json
  mastery.py            Elo 能力估计、掌握等级、FSRS 复习卡片
  drills.py             选题、判分、提示阶梯、错题本、AI 出题与核对
  planner.py            学习大纲：候选清单、基础计划、AI 计划校验
  essays.py             作文流程、反馈限量、错误进入错题本、迁移证据
  store.py              浏览器存储同步、导入导出
  ai.py                 Claude 调用（结构化输出、流式输出、服务端回退、中文错误提示）
  prompts.py / schemas.py / rubrics.py / lessons.py / ui.py
docs/RESEARCH.md        研究依据
```

## AI 调用说明

- 模型：`claude-opus-5-5`；判分和出题核对用低思考深度，作文批改和规划用侧边栏设置的深度。
- 需要结构化结果的调用都使用 JSON Schema 结构化输出；分数在代码中按评分标准截断并汇总。
- 开启了服务端回退（`fallbacks: "default"`）：请求被安全分类器误拦时自动换推荐的备用模型重试。
- 局限：AI 打分没有用本地人工评分数据校准，因此以区间显示并标注“估计”；种子题库由 AI 编写并经 AI 核对，学生可以一键报告有问题的题目。
