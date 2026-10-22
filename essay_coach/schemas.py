"""作文反馈相关的结构化输出模型。

反馈规则来自研究（见 docs/RESEARCH.md）：
- 最多 3 个“重点问题”（高阶：切题、论证、结构）+ 最多 3 类“错误模式”（每类最多 3 处），其余只记录不展示；
- 每条反馈包含：维度、引用原文、问题、原因（规则/评分描述）、修改策略（不写改好的句子）、自查问题；
- 按“目标 → 现状 → 下一步”组织；只做针对任务的、引用原文的肯定，不做针对人的表扬或批评；
- 分数是估计值，用区间展示。
所有字段必填、无默认值，数值范围写在描述里，越界值在代码中校正。
"""

from typing import Literal

from pydantic import BaseModel, Field

from .skills import KCS

# 技能点 id 用枚举约束：结构化输出只能从技能图谱里选，AI 不能自己发明
KCId = Literal[tuple(KCS)]


class CriterionEstimate(BaseModel):
    name: str = Field(description="评分维度名称，与评分标准的名称和顺序一致")
    score: float = Field(description="该维度的估计得分（在 0 与该维度满分之间）")
    comment: str = Field(description="依据：结合原文说明为什么在这一档，以及上一档需要做到什么")


class PriorityIssue(BaseModel):
    criterion: str = Field(description="对应的评分维度")
    kc: KCId = Field(description="对应的技能点 id，来自给定的技能清单")
    quote: str = Field(description="从原文逐字复制的片段（3–30 个词），用于定位")
    problem: str = Field(description="问题是什么")
    why: str = Field(description="为什么是问题：对应的规则或评分描述")
    how_to_fix: str = Field(description="修改策略：怎么想、怎么改；不要写出改好的句子或段落")
    check_question: str = Field(description="学生改完后用来自查的一个问题")


class ErrorInstance(BaseModel):
    quote: str = Field(description="从原文逐字复制的出错片段（2–20 个词）")
    hint: str = Field(description="简短提示，指出问题方向，不写改正结果")


class ErrorPattern(BaseModel):
    kc: KCId = Field(description="对应的技能点 id，来自给定的技能清单")
    pattern: str = Field(description="错误模式名称，如“逗号连句”")
    rule: str = Field(description="一句话规则")
    instances: list[ErrorInstance] = Field(description="最多 3 处例子")


class KCEvidence(BaseModel):
    kc: KCId = Field(description="技能点 id")
    status: Literal["demonstrated", "weak", "missing"] = Field(
        description="demonstrated=文中正确运用了；weak=用了但有明显问题；missing=应该有但没有")
    note: str = Field(description="依据（简短）")


class EssayFeedback(BaseModel):
    level_label: str = Field(description="简短的水平标签，如 “约 Band 6”")
    criteria: list[CriterionEstimate]
    goal: str = Field(description="目标：这类文章要做到什么（结合学生目标）")
    now: str = Field(description="现状：这篇文章目前做到了什么、差在哪里（2–3 句）")
    next: str = Field(description="下一步：最值得先做的一件事")
    strengths: list[str] = Field(description="最多 2 条，必须引用原文、针对任务，不做空泛表扬")
    priority_issues: list[PriorityIssue] = Field(description="最多 3 个，最重要的在前，优先高阶问题")
    error_patterns: list[ErrorPattern] = Field(description="最多 3 类反复出现的语言错误")
    kc_evidence: list[KCEvidence] = Field(description="文中能判断的技能点证据，8–15 条")


class IssueCheck(BaseModel):
    index: int = Field(description="对应的重点问题序号（从 1 开始）")
    status: Literal["fixed", "partly", "not_fixed"]
    comment: str = Field(description="结合新稿原文说明；没改好时给提示，不写改好的句子")


class RevisionCheck(BaseModel):
    overall: str = Field(description="对这次修改的总体评价（2–3 句）")
    checks: list[IssueCheck]
    surface_only: bool = Field(description="是否只改了表面（换词、改语法），没有处理重点问题")
    new_problems: list[str] = Field(description="修改中新出现的问题；没有则为空列表")
    criteria: list[CriterionEstimate]


class EssayPrompt(BaseModel):
    prompt: str = Field(description="英文作文题目（完整题干）")
    question_type: str = Field(description="题型（中文），如“同意/不同意”")
    focus_tip: str = Field(description="结合本周技能的一句写作提醒（中文）；检测作文留空")


class DiagnosticSummary(BaseModel):
    summary: str = Field(description="诊断总结（中文，3–4 句）")
    strengths: list[str]
    priorities: list[str] = Field(description="最需要提升的 3 个方面")
