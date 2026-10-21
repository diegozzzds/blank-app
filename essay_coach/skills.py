"""技能图谱：英文 essay 写作拆成的知识点（KC），以及它们的先后依赖。

学习大纲、刷题、错题本、掌握度都以这里的 KC 为单位。图谱是固定的、带版本号的：
AI 生成学习大纲时只能从这里挑选和排序，不能自己发明技能点（见 planner.py）。

criteria 用五个通用维度，便于映射到不同考试的评分标准：
  task 切题与立场 · argument 论证与分析 · coherence 结构与衔接 · lexis 词汇 · grammar 语法
prior：中国学生在该技能上出问题的先验可能（0–1），诊断信息不足时用来排序。
"""

from dataclasses import dataclass, field

GRAPH_VERSION = "2026.10-1"

LEVELS = {"sentence": "句子层", "paragraph": "段落层", "essay": "篇章层"}

CRITERIA = {
    "task": "切题与立场",
    "argument": "论证与分析",
    "coherence": "结构与衔接",
    "lexis": "词汇",
    "grammar": "语法",
}

# 各考试评分维度与通用维度的对应关系
EXAM_CRITERIA = {
    "ielts": {"Task Response": ["task", "argument"], "Coherence & Cohesion": ["coherence"],
              "Lexical Resource": ["lexis"], "Grammatical Range & Accuracy": ["grammar"]},
    "general": {"Thesis & Focus": ["task"], "Organization": ["coherence"], "Evidence & Analysis": ["argument"],
                "Language & Style": ["lexis"], "Grammar & Mechanics": ["grammar"]},
    "ap_argument": {"Thesis": ["task"], "Evidence & Commentary": ["argument", "coherence"],
                    "Sophistication": ["argument", "lexis"]},
    "personal": {"Authenticity & Voice": ["lexis"], "Storytelling & Structure": ["coherence"],
                 "Reflection & Insight": ["argument", "task"], "Language & Mechanics": ["grammar"]},
}

FORMATS = {
    "mcq": "选择题",
    "fix": "找错改错",
    "combine": "句子合并",
    "rewrite": "改写",
    "write": "限定写作",
    "order": "排序",
    "judge": "当考官",
}
AUTO_GRADED = {"mcq", "order", "judge"}


@dataclass(frozen=True)
class KC:
    id: str
    level: str
    name: str
    en: str
    criteria: tuple[str, ...]
    desc: str
    formats: tuple[str, ...]
    prereqs: tuple[str, ...] = field(default_factory=tuple)
    prior: float = 0.5
    lesson: str | None = None  # 对应 lessons.py 里的微课


_KCS = [
    # ---------- 句子层 · 语法 ----------
    KC("sent_boundary", "sentence", "句子边界", "Sentence boundaries", ("grammar",),
       "分清完整句：避免逗号连句（comma splice）、粘连句和残缺句。", ("mcq", "fix"), prior=0.9),
    KC("chinglish_struct", "sentence", "中式句型", "Chinglish structures", ("grammar",),
       "避免双谓语（There are many people think…）、Although…but、Because…so 等中式结构。",
       ("mcq", "fix"), prior=0.9, lesson="language"),
    KC("sv_agree", "sentence", "主谓一致", "Subject–verb agreement", ("grammar",),
       "主语和谓语在单复数上保持一致，注意 the number of / each / 长主语。", ("mcq", "fix"), prior=0.7),
    KC("verb_tense", "sentence", "时态与动词形式", "Verb tense & form", ("grammar",),
       "议论文以一般现在时为主，正确使用完成时、被动语态和情态动词后的原形。", ("mcq", "fix"), prior=0.7),
    KC("articles", "sentence", "冠词", "Articles", ("grammar",),
       "a / an / the / 零冠词的选择：泛指、特指、可数单数名词前不能没有限定词。", ("mcq", "fix"), prior=0.85),
    KC("noun_number", "sentence", "名词单复数与可数性", "Noun number & countability", ("grammar",),
       "information、advice、homework 等不可数名词；可数名词复数；many/much 的搭配。", ("mcq", "fix"), prior=0.8),
    KC("punctuation", "sentence", "标点规范", "Punctuation", ("grammar",),
       "引导语后的逗号、分号连接两个完整句、所有格撇号、列举中的逗号。", ("mcq", "fix"),
       prereqs=("sent_boundary",), prior=0.6),
    KC("combining", "sentence", "句子合并与从句", "Sentence combining", ("grammar", "coherence"),
       "用从句、分词短语、同位语把短句合并成逻辑清楚的复合句。", ("combine", "mcq"),
       prereqs=("sent_boundary",), prior=0.7),
    KC("parallelism", "sentence", "平行结构", "Parallel structure", ("grammar",),
       "并列成分保持相同的语法形式（to do…and to do / doing…and doing）。", ("mcq", "fix"),
       prereqs=("combining",), prior=0.5),
    # ---------- 句子层 · 词汇 ----------
    KC("collocation", "sentence", "词语搭配", "Collocation", ("lexis",),
       "用地道的搭配：acquire knowledge（不是 learn knowledge）、make progress、discuss（不加 about）。",
       ("mcq", "fix"), prior=0.85),
    KC("word_precision", "sentence", "用词精确", "Precise word choice", ("lexis",),
       "用具体准确的词替换 good / bad / thing / big 等空泛词。", ("mcq", "rewrite"), prior=0.8, lesson="language"),
    KC("register", "sentence", "学术语体", "Academic register", ("lexis",),
       "避免缩写、口语词（kids, a lot of, stuff）和泛指的 you，使用正式表达。", ("mcq", "rewrite"),
       prereqs=("word_precision",), prior=0.75, lesson="language"),
    KC("concision", "sentence", "简洁表达", "Concision", ("lexis",),
       "删除冗余：In my personal opinion, I think… → I believe…", ("rewrite", "mcq"),
       prereqs=("register",), prior=0.6),
    KC("hedging", "sentence", "限定语气", "Hedging", ("lexis", "argument"),
       "用 may / tend to / arguably / in many cases 避免绝对化断言，让论证更严谨。", ("mcq", "rewrite"),
       prereqs=("register",), prior=0.7),
    KC("paraphrase", "sentence", "同义改写", "Paraphrasing", ("lexis",),
       "用自己的话改写题目和观点，不照抄原题。", ("rewrite", "mcq"),
       prereqs=("word_precision",), prior=0.7),
    # ---------- 段落层 ----------
    KC("transitions", "paragraph", "连接词", "Transitions", ("coherence",),
       "按逻辑关系选择连接词（转折、因果、递进、让步），避免堆砌和误用。", ("mcq", "fix", "order"),
       prior=0.7, lesson="cohesion"),
    KC("referencing", "paragraph", "指代衔接", "Referencing & cohesion", ("coherence",),
       "用 this approach / such policies 等指代和词汇链把句子连起来。", ("mcq", "rewrite", "order"),
       prereqs=("transitions",), prior=0.6, lesson="cohesion"),
    KC("topic_sentence", "paragraph", "主题句", "Topic sentences", ("coherence", "task"),
       "段首用一句话提出本段中心论点，并与 thesis 呼应。", ("mcq", "write", "judge"),
       prereqs=("thesis",), prior=0.6, lesson="peel"),
    KC("unity", "paragraph", "段落一致性", "Paragraph unity", ("coherence",),
       "一段只讲一个中心，找出并删除跑题句。", ("mcq", "judge"),
       prereqs=("topic_sentence",), prior=0.5, lesson="peel"),
    KC("support_evidence", "paragraph", "论据支撑", "Supporting evidence", ("argument",),
       "为论点提供具体、相关的例子、事实或推理。", ("mcq", "write", "judge"),
       prereqs=("topic_sentence",), prior=0.6, lesson="peel"),
    KC("evidence_quality", "paragraph", "论据质量", "Evidence quality", ("argument",),
       "判断论据是否相关、充分、可信；区分事实、例子、个人经历和假设。", ("mcq", "judge"),
       prereqs=("support_evidence",), prior=0.6),
    KC("analysis", "paragraph", "分析与推理", "Analysis & warrants", ("argument",),
       "解释论据“为什么”能证明论点（This shows… because… which means…）。", ("write", "mcq", "judge"),
       prereqs=("support_evidence",), prior=0.85, lesson="peel"),
    KC("para_closing", "paragraph", "段落收束", "Closing a paragraph", ("coherence",),
       "段末回扣论点或过渡到下一段，而不是简单重复。", ("mcq", "write", "judge"),
       prereqs=("analysis",), prior=0.5, lesson="peel"),
    # ---------- 篇章层 ----------
    KC("prompt_analysis", "essay", "读题", "Prompt analysis", ("task",),
       "拆解话题、指令词和限制词，避免跑题。", ("mcq", "write"), prior=0.7, lesson="prompt"),
    KC("question_types", "essay", "题型与完整回应", "Question types", ("task",),
       "识别 agree/disagree、discuss both views、advantages/disadvantages、two-part 等题型并回应所有部分。",
       ("mcq", "judge"), prereqs=("prompt_analysis",), prior=0.7, lesson="prompt"),
    KC("thesis", "essay", "论点句", "Thesis statements", ("task",),
       "写出回答题目、可辩论、具体的 thesis，全文立场一致。", ("mcq", "write", "judge"),
       prereqs=("prompt_analysis",), prior=0.7, lesson="thesis"),
    KC("introduction", "essay", "开头段", "Introductions", ("task", "coherence"),
       "Hook → 背景 → thesis，避免套话开头。", ("mcq", "write", "order"),
       prereqs=("thesis",), prior=0.6, lesson="intro_conclusion"),
    KC("conclusion", "essay", "结尾段", "Conclusions", ("coherence",),
       "换种说法重申论点、总结理由、升华意义，不引入新论据。", ("mcq", "write", "judge"),
       prereqs=("thesis",), prior=0.5, lesson="intro_conclusion"),
    KC("organization", "essay", "篇章结构", "Essay organization", ("coherence",),
       "段落顺序合理、分段清楚、每段功能明确。", ("order", "mcq"),
       prereqs=("topic_sentence",), prior=0.5, lesson="structure"),
    KC("planning", "essay", "5 分钟提纲", "Planning", ("coherence", "task"),
       "动笔前用几分钟列出 thesis 和每段要点。", ("write", "mcq", "order"),
       prereqs=("thesis", "topic_sentence"), prior=0.6, lesson="structure"),
    KC("counterargument", "essay", "反方与反驳", "Counterargument & rebuttal", ("argument",),
       "公正陈述反方观点并让步，再有理有据地反驳。", ("write", "mcq", "judge"),
       prereqs=("thesis", "support_evidence"), prior=0.9, lesson="counter"),
    KC("critical_questions", "essay", "批判性提问", "Critical questions", ("argument",),
       "用关键问题检查论证漏洞：例子有代表性吗？因果成立吗？有没有其他解释？", ("mcq", "write", "judge"),
       prereqs=("analysis", "counterargument"), prior=0.8),
    KC("examiner", "essay", "当考官", "Assessing writing", ("task", "argument", "coherence"),
       "用评分标准评价一段文字，找出最影响得分的问题。", ("judge",),
       prereqs=("thesis", "support_evidence", "transitions"), prior=0.6, lesson="revision"),
]

KCS: dict[str, KC] = {k.id: k for k in _KCS}


def _check_graph() -> None:
    for kc in _KCS:
        for p in kc.prereqs:
            assert p in KCS, f"{kc.id} 的前置技能 {p} 不存在"
        assert set(kc.formats) <= set(FORMATS), kc.id
    # 检查没有环
    seen: dict[str, int] = {}

    def visit(k: str) -> None:
        if seen.get(k) == 1:
            raise AssertionError(f"技能图谱有环：{k}")
        if seen.get(k) == 2:
            return
        seen[k] = 1
        for p in KCS[k].prereqs:
            visit(p)
        seen[k] = 2

    for k in KCS:
        visit(k)


_check_graph()


def topo_order() -> list[str]:
    """按依赖排序（前置技能在前），同层内保持定义顺序。"""
    order, done = [], set()

    def visit(k: str) -> None:
        if k in done:
            return
        for p in KCS[k].prereqs:
            visit(p)
        done.add(k)
        order.append(k)

    for k in KCS:
        visit(k)
    return order


def label(kc_id: str) -> str:
    kc = KCS.get(kc_id)
    return f"{kc.name}（{kc.en}）" if kc else kc_id
