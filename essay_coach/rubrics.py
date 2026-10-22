"""评分标准（rubric）定义，以及根据各项分数计算总分的规则。"""

import math

RUBRICS = {
    "general": {
        "name": "通用学术 Essay（百分制）",
        "max": 100,
        "aggregate": "sum",
        "criteria": [
            {"name": "Thesis & Focus 论点与切题", "max": 20,
             "desc": "是否准确回答题目；thesis 是否清晰、可辩论、具体；全文是否始终围绕论点。"},
            {"name": "Organization 结构与逻辑", "max": 20,
             "desc": "开头/主体/结尾是否完整；段落是否一段一中心；段落顺序与过渡是否合理。"},
            {"name": "Evidence & Analysis 论据与分析", "max": 25,
             "desc": "论据是否具体、相关、可信；是否解释了论据如何支撑论点；是否处理了反方观点。"},
            {"name": "Language & Style 语言与文风", "max": 20,
             "desc": "用词是否准确、多样、符合学术语体；句式是否多样；表达是否简洁清楚。"},
            {"name": "Grammar & Mechanics 语法与规范", "max": 15,
             "desc": "语法、拼写、标点、大小写是否正确；错误是否影响理解。"},
        ],
    },
    "ielts": {
        "name": "IELTS Writing Task 2（雅思大作文，9 分制）",
        "max": 9,
        "aggregate": "ielts",
        "criteria": [
            {"name": "Task Response 任务回应", "max": 9,
             "desc": "是否回应题目所有部分；立场是否清晰一致；观点是否充分展开并有支撑。"},
            {"name": "Coherence & Cohesion 连贯与衔接", "max": 9,
             "desc": "信息与观点的逻辑组织；分段是否合理；衔接手段使用是否恰当、不机械。"},
            {"name": "Lexical Resource 词汇丰富度", "max": 9,
             "desc": "词汇范围、准确性与搭配；不常用词汇的使用；拼写与构词错误。"},
            {"name": "Grammatical Range & Accuracy 语法多样性与准确性", "max": 9,
             "desc": "句式结构的多样性；复杂句的使用；语法与标点的准确性。"},
        ],
    },
    "ap_argument": {
        "name": "AP English Language · Argument（6 分制）",
        "max": 6,
        "aggregate": "sum",
        "criteria": [
            {"name": "Row A · Thesis 论点", "max": 1,
             "desc": "是否有一个可辩护的、回应题目的 thesis（0 或 1 分）。"},
            {"name": "Row B · Evidence & Commentary 论据与评论", "max": 4,
             "desc": "是否提供具体相关的论据，并通过评论（commentary）解释论据如何支撑论证推理（0–4 分）。"},
            {"name": "Row C · Sophistication 思辨深度", "max": 1,
             "desc": "是否展现复杂理解：如把握论题的复杂性与张力、置于更广阔语境、或文风生动有效（0 或 1 分）。"},
        ],
    },
    "personal": {
        "name": "申请文书 Personal Statement（百分制）",
        "max": 100,
        "aggregate": "sum",
        "criteria": [
            {"name": "Authenticity & Voice 真实与个人声音", "max": 25,
             "desc": "是否真实、具体、有个人特色；读者能否“听见”作者本人。"},
            {"name": "Storytelling & Structure 叙事与结构", "max": 25,
             "desc": "开头是否吸引人；叙事节奏与结构是否清晰；细节是否生动（show, don't tell）。"},
            {"name": "Reflection & Insight 反思与洞察", "max": 30,
             "desc": "是否展现成长、价值观与思考深度；经历与“我是谁/想做什么”之间的联系是否清楚。"},
            {"name": "Language & Mechanics 语言与规范", "max": 20,
             "desc": "语言是否自然、准确、简洁；语法拼写是否正确。"},
        ],
    },
}

ESSAY_TYPES = [
    "议论文 Argumentative",
    "说明文 Expository",
    "比较对照 Compare & Contrast",
    "因果分析 Cause & Effect",
    "问题–解决 Problem–Solution",
    "利弊讨论 Advantages & Disadvantages",
    "文学/文本分析 Literary Analysis",
    "记叙/个人陈述 Narrative / Personal",
]


def _round_ielts(value: float) -> float:
    """雅思总分：四项平均分四舍五入到最近的 0.5（.25 进位到 .5，.75 进位到下一个整数）。"""
    return math.floor(value * 2 + 0.5) / 2


def normalize_scores(rubric_key: str, criteria: list[dict]) -> tuple[list[dict], float]:
    """把 AI 给出的分项分数对齐到 rubric（名称、满分、范围），并按规则计算总分。

    AI 偶尔会改动标准名称或给出越界的分数，这里统一以 rubric 为准。
    """
    rubric = RUBRICS[rubric_key]
    fixed = []
    for i, spec in enumerate(rubric["criteria"]):
        item = criteria[i] if i < len(criteria) else {"score": 0, "comment": "（AI 未给出该项评价）"}
        score = min(max(float(item.get("score", 0)), 0.0), float(spec["max"]))
        if rubric["aggregate"] == "ielts":
            score = round(score * 2) / 2
        fixed.append({"name": spec["name"], "max_score": spec["max"], "score": score,
                      "comment": item.get("comment", "")})

    scores = [c["score"] for c in fixed]
    if rubric["aggregate"] == "ielts":
        total = _round_ielts(sum(scores) / len(scores))
    else:
        total = round(sum(scores), 1)
    return fixed, total


def format_score(rubric_key: str, score: float) -> str:
    if RUBRICS[rubric_key]["aggregate"] == "ielts":
        return f"{score:.1f}"
    return f"{score:g}"
