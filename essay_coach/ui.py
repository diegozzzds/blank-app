"""通用界面组件。尽量使用公开组件：
- 原文高亮：st-annotated-text（Apache-2.0）
- 修改对比：redlines（MIT）
- 标签、图表、技能图谱：Streamlit 内置的 st.badge / st.echarts_chart / st.mermaid_chart
"""

import re

import streamlit as st
from annotated_text import annotated_text, annotation
from redlines import Redlines

from . import ai, mastery
from .skills import CRITERIA, FORMATS, KCS, LEVELS

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|~$:])")

MARK_COLORS = {
    "priority": "rgba(139, 92, 246, 0.30)",
    "grammar": "rgba(239, 68, 68, 0.28)",
    "lexis": "rgba(245, 158, 11, 0.30)",
    "coherence": "rgba(59, 130, 246, 0.28)",
    "argument": "rgba(16, 185, 129, 0.28)",
    "task": "rgba(236, 72, 153, 0.26)",
}
LEVEL_COLORS = {"sentence": "orange", "paragraph": "blue", "essay": "violet"}


def md_escape(text: str) -> str:
    """学生文字不能被当作 Markdown / LaTeX（$…$）/ :color[] 指令解析。"""
    return _MD_SPECIAL.sub(r"\\\1", text)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", text))


def require_ai(message: str = "这个功能需要 AI。请先在左侧边栏填写 Anthropic API Key。") -> bool:
    if ai.is_ready():
        return True
    st.info(message, icon=":material/key:")
    return False


def run_ai(spinner: str, fn, *args, **kwargs):
    """执行 AI 调用，出错时显示中文提示并返回 None。"""
    try:
        with st.spinner(spinner):
            return fn(*args, **kwargs)
    except ai.AIError as e:
        st.error(str(e))
        return None


def stream_ai(placeholder, *args, **kwargs) -> str | None:
    try:
        return ai.stream_markdown(placeholder, *args, **kwargs)
    except ai.AIError as e:
        st.error(str(e))
        return None


def kc_badge(kc: str, with_level: bool = False) -> None:
    k = KCS.get(kc)
    if not k:
        return
    st.badge(f"{k.name} · {k.en}", color=LEVEL_COLORS[k.level], icon=":material/target:")
    if with_level:
        st.badge(LEVELS[k.level], color="gray")


def tier_label(progress: dict, kc: str) -> str:
    """掌握等级的 Markdown 徽章，可以直接嵌进文字里。"""
    tier = (progress["kc"].get(kc) or {}).get("tier", "new")
    label, color = mastery.TIERS[tier]
    return f":{color}-badge[{label}]"


def format_label(fmt: str) -> str:
    return FORMATS.get(fmt, fmt)


def locate(text: str, quotes: list[str]) -> list[tuple[int, int, int]]:
    """为每个引用在原文中找到不重叠的位置（允许空白差异），返回 (start, end, 引用序号)。"""
    spans: list[tuple[int, int, int]] = []
    for idx, quote in enumerate(quotes):
        words = quote.strip().strip("\"'“”").split()
        if not words:
            continue
        pattern = re.compile(r"\s+".join(map(re.escape, words)))
        for m in pattern.finditer(text):
            s, e = m.span()
            if all(e <= a or s >= b for a, b, _ in spans):
                spans.append((s, e, idx))
                break
    return sorted(spans)


def annotated_essay(text: str, marks: list[tuple[str, str, str]]) -> set[int]:
    """marks：[(引用, 标签, 颜色类别)]。按段落渲染高亮原文，返回成功定位的序号。"""
    spans = locate(text, [m[0] for m in marks])
    located = {i for *_, i in spans}
    bounds = [(m.start(), m.end()) for m in re.finditer(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*", text)] \
        if re.search(r"\n\s*\n", text) else [(m.start(), m.end()) for m in re.finditer(r"[^\n]+", text)]
    with st.container(border=True):
        for start, end in bounds:
            if not text[start:end].strip():
                continue
            parts, cur = [], start
            for s, e, idx in spans:
                if s >= start and e <= end:
                    parts.append(md_escape(text[cur:s]))
                    _, label, cat = marks[idx]
                    parts.append(annotation(md_escape(text[s:e]), label,
                                            background=MARK_COLORS.get(cat, MARK_COLORS["priority"])))
                    cur = e
            parts.append(md_escape(text[cur:end]))
            annotated_text(*[p for p in parts if p])
    return located


def show_diff(old: str, new: str) -> None:
    """词级别对比：删除划线、新增加粗（redlines）。"""
    with st.container(border=True):
        st.markdown(Redlines(md_escape(old), md_escape(new), markdown_style="streamlit").output_markdown)


def criteria_radar(progress: dict, key: str) -> None:
    """五个通用维度的平均掌握度雷达图（Streamlit 内置 ECharts）。"""
    values = []
    for c in CRITERIA:
        ks = [k for k, kc in KCS.items() if c in kc.criteria]
        values.append(round(sum(mastery.mastery_pct(progress, k) for k in ks) / len(ks)))
    st.echarts_chart({
        "radar": {"indicator": [{"name": CRITERIA[c], "max": 100} for c in CRITERIA], "radius": "65%"},
        "tooltip": {},
        "series": [{"type": "radar", "areaStyle": {"opacity": 0.25}, "symbolSize": 8,
                    "data": [{"value": values, "name": "平均掌握度 %"}]}],
    }, height=300, key=key)


def mermaid_skill_map(progress: dict, level: str, highlight: set[str] | None = None) -> str:
    """某一层的技能图谱 Mermaid 源码（跨层的前置技能画成虚线框）。只从图谱数据生成，不使用 AI 输出的 Mermaid。"""
    styles = {
        "new": "fill:#6b728022,stroke:#6b7280",
        "learning": "fill:#f59e0b33,stroke:#f59e0b",
        "learned": "fill:#3b82f633,stroke:#3b82f6",
        "retained": "fill:#8b5cf633,stroke:#8b5cf6",
        "transferred": "fill:#16a34a44,stroke:#16a34a",
    }
    safe = lambda s: s.replace('"', "'").replace("\n", " ")  # noqa: E731
    nodes = [k for k, kc in KCS.items() if kc.level == level]
    external = sorted({p for k in nodes for p in KCS[k].prereqs if KCS[p].level != level}, key=list(KCS).index)
    lines = ["graph LR"]
    for k in nodes:
        pct = mastery.mastery_pct(progress, k)
        star = " ★" if highlight and k in highlight else ""
        lines.append(f'  {k}["{safe(KCS[k].name)}{star}<br/>{pct}%"]')
    for k in external:
        lines.append(f'  {k}(["{safe(KCS[k].name)}（{LEVELS[KCS[k].level]}）"])')
    for k in nodes:
        for p in KCS[k].prereqs:
            lines.append(f"  {p} {'-.->' if p in external else '-->'} {k}")
    for tier, style in styles.items():
        lines.append(f"  classDef {tier} {style}")
    lines.append("  classDef external fill:none,stroke:#9ca3af,stroke-dasharray:4 3")
    for tier in styles:
        ids = [k for k in nodes if (progress["kc"].get(k) or {}).get("tier", "new") == tier]
        if ids:
            lines.append(f"  class {','.join(ids)} {tier}")
    if external:
        lines.append(f"  class {','.join(external)} external")
    return "\n".join(lines)
