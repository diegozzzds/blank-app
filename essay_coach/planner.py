"""学习大纲（学习计划）：AI 生成，程序校验。

研究表明，完全由大模型自由生成的学习路径经常不合格（如 PersonaPath 评测中最好模型的通过率约 30%），
所以这里的做法是：
1. 程序先根据目标、诊断结果和技能图谱算出每个技能点的“需要程度”和可学顺序（候选清单）；
2. Claude 在候选清单内挑选、排序，写出每周目标（用“学会某个策略”来表述，而不是分数目标）、
   原因说明、作文任务等；
3. 程序校验并修复 AI 的输出：只保留图谱里的技能点、保证前置技能先学、每周不超过 4 个技能点、
   最需要的技能必须出现、每两周一次独立检测作文。没有 API Key 时直接使用程序生成的版本。
"""

from datetime import date, timedelta

from pydantic import BaseModel, Field

from . import mastery, store
from .schemas import KCId
from .skills import CRITERIA, KCS, topo_order

MAX_KCS_PER_WEEK = 4
DEFAULT_WEEKS = 8

# 目标考试 → 评分标准（rubrics.py 的 key 相同）
EXAMS = {
    "ielts": "雅思 IELTS Writing Task 2",
    "general": "通用学术议论文（含托福、校内写作）",
    "ap_argument": "AP English Language · Argument",
    "personal": "申请文书 Personal Statement",
}


def weeks_available(profile: dict) -> int:
    exam = profile.get("exam_date")
    if exam:
        try:
            days = (date.fromisoformat(exam) - store.study_day()).days
            return max(2, min(16, days // 7))
        except ValueError:
            pass
    return DEFAULT_WEEKS


# 学习者语料研究：基础阶段最常见、最影响理解的是主谓一致、单复数、时态与动词形式、句子边界、中式句型；
# 中高级阶段错误集中在搭配、冠词的泛指用法、限定语气、连接词、语体和反驳（得分权重也更多在篇章层）。
BASIC_FOCUS = {"sv_agree", "noun_number", "verb_tense", "sent_boundary", "chinglish_struct"}
ADVANCED_FOCUS = {"collocation", "hedging", "transitions", "register", "word_precision", "counterargument",
                  "critical_questions"}


def level_weight(level: str | None, kc: str) -> float:
    """没有诊断证据时，按学生水平调整先验：低水平先打基础，高水平侧重高阶问题。"""
    basic = level in ("初中", "高中")
    if kc in BASIC_FOCUS:
        return 1.3 if basic else 0.9
    if kc in ADVANCED_FOCUS:
        return 0.8 if basic else 1.25
    return 1.0


def need_scores(progress: dict) -> dict[str, float]:
    """每个技能点的需要程度：没掌握的程度 × 诊断证据/先验（按水平调整）× 薄弱维度权重。"""
    level = (progress.get("profile") or {}).get("level")
    diag = progress.get("diagnostic") or {}
    weak_kcs = set(diag.get("weak_kcs", []))
    strong_kcs = set(diag.get("strong_kcs", []))
    crit_gap = diag.get("criterion_gap", {})  # 维度 -> 0–1，越大越弱
    scores = {}
    for k, kc in KCS.items():
        st = progress["kc"].get(k) or {}
        tier = st.get("tier", "new")
        not_mastered = 1 - mastery.TIER_RANK[tier] / (len(mastery.TIERS) - 1)
        evidence = 1.5 if k in weak_kcs else (0.2 if k in strong_kcs else (0.4 + 0.5 * kc.prior) * level_weight(level, k))
        crit = max((crit_gap.get(c, 0.5) for c in kc.criteria), default=0.5)
        scores[k] = round(not_mastered * evidence * (0.5 + crit), 3)
    return scores


def baseline_plan(progress: dict) -> dict:
    """确定性的基准计划：按依赖顺序，每周挑需要程度最高的可学技能，句子/段落/篇章层交错。"""
    profile = progress.get("profile") or {}
    n_weeks = weeks_available(profile)
    need = need_scores(progress)
    order = topo_order()
    # 已学会的、以及诊断显示不需要练的技能，都视为前置条件已满足（否则它们的后续技能永远排不进计划）
    mastered = {k for k, st in progress["kc"].items() if mastery.TIER_RANK[st.get("tier", "new")] >= mastery.TIER_RANK["learned"]}
    mastered |= {k for k in KCS if need[k] <= 0.15}
    planned: set[str] = set()
    weeks = []
    per_week = 3
    for w in range(n_weeks):
        available = [k for k in order if k not in planned and k not in mastered
                     and all(p in mastered or p in planned for p in KCS[k].prereqs)]
        available.sort(key=lambda k: -need[k])
        chosen: list[str] = []
        for level in ("sentence", "paragraph", "essay"):  # 每层先挑一个，形成交错
            for k in available:
                if KCS[k].level == level and k not in chosen and need[k] > 0.15:
                    chosen.append(k)
                    break
        for k in available:
            if len(chosen) >= per_week:
                break
            if k not in chosen and need[k] > 0.15:
                chosen.append(k)
        if not chosen and w == 0:
            # 诊断显示各项都不错：仍然安排一周，挑需要程度最高的（全都学会了就复习最弱的）
            pool = available or sorted(KCS, key=lambda k: mastery.mastery_pct(progress, k))
            chosen = sorted(pool, key=lambda k: -need[k])[:per_week] if available else pool[:per_week]
        if not chosen:
            break
        planned.update(chosen)
        weeks.append({
            "title": "、".join(KCS[k].name for k in chosen),
            "kcs": chosen,
            "goals": [f"学会：{KCS[k].desc}" for k in chosen],
            "why": "根据诊断结果和技能依赖关系自动安排。",
            "lesson_focus": KCS[chosen[0]].name,
            "essay_task": "",
            "checkpoint": (w + 1) % 2 == 0,
        })
    return {"overview": "按技能依赖与诊断结果自动生成的基础计划。", "weeks": weeks,
            "daily_routine": "每天先做到期复习，再练本周技能。", "source": "baseline"}


# ---------------- AI 生成 ----------------

class WeekPlan(BaseModel):
    title: str = Field(description="本周主题（中文，简短）")
    kcs: list[KCId] = Field(description="本周技能点 id，只能来自候选清单，2–4 个")
    goals: list[str] = Field(description="本周学习目标，用“学会/能够 + 具体策略”表述，不写分数目标")
    why: str = Field(description="为什么这周练这些（结合诊断结果）")
    lesson_focus: str = Field(description="本周微课重点")
    essay_task: str = Field(description="本周作文任务：题目类型或一道英文题目")
    checkpoint: bool = Field(description="本周末是否安排独立检测作文")


class StudyPlan(BaseModel):
    overview: str = Field(description="整体计划说明，3–5 句话")
    weeks: list[WeekPlan]
    daily_routine: str = Field(description="每天怎么安排时间")
    milestones: list[str] = Field(description="2–4 个阶段性里程碑")


def validate_plan(progress: dict, plan: StudyPlan) -> tuple[dict, list[str]]:
    """校验并修复 AI 的计划。返回 (计划, 修复说明)。"""
    notes: list[str] = []
    need = need_scores(progress)
    mastered = {k for k, st in progress["kc"].items() if mastery.TIER_RANK[st.get("tier", "new")] >= mastery.TIER_RANK["learned"]}
    mastered |= {k for k in KCS if need[k] <= 0.15}
    requested = [k for w in plan.weeks for k in w.kcs if k in KCS]
    planned: set[str] = set()
    weeks = []
    carry: list[str] = []
    n_weeks = weeks_available(progress.get("profile") or {})
    ai_weeks = plan.weeks[:n_weeks]
    for i, w in enumerate(ai_weeks):
        kcs = []
        for k in carry + w.kcs:
            if k not in KCS:
                notes.append(f"第 {i + 1} 周：去掉了图谱中不存在的技能“{k}”。")
                continue
            if k in planned or k in kcs:
                continue
            kcs.append(k)
        # 同一周内可以同时学前置技能和后续技能：反复扫描，直到没有新的技能可以加入
        ok: list[str] = []
        pending = list(kcs)
        changed = True
        while changed and pending and len(ok) < MAX_KCS_PER_WEEK:
            changed = False
            for k in list(pending):
                if len(ok) >= MAX_KCS_PER_WEEK:
                    break
                if all(p in mastered or p in planned or p in ok for p in KCS[k].prereqs):
                    ok.append(k)
                    pending.remove(k)
                    changed = True
        carry = pending
        if i + 1 < len(ai_weeks):  # 最后一周顺延不了，统一在下面的“未能安排”里说明
            for k in carry:
                notes.append(f"第 {i + 1} 周：{KCS[k].name} 的前置技能还没安排或本周已满，顺延到下一周。")
        planned.update(ok)
        weeks.append({**w.model_dump(), "kcs": ok, "checkpoint": w.checkpoint or (i + 1) % 2 == 0})
    # 最需要的技能必须出现
    top = [k for k in sorted(need, key=lambda k: -need[k]) if k not in mastered][:6]
    for k in top + carry:
        if k in planned:
            continue
        for i, w in enumerate(weeks):
            prereq_ok = all(p in mastered or any(p in x["kcs"] for x in weeks[:i + 1]) for p in KCS[k].prereqs)
            if prereq_ok and len(w["kcs"]) < MAX_KCS_PER_WEEK:
                w["kcs"].append(k)
                planned.add(k)
                notes.append(f"把高优先级技能“{KCS[k].name}”加入第 {i + 1} 周。")
                break
    for w, orig in zip(weeks, ai_weeks):
        if set(w["kcs"]) != set(orig.kcs):  # 技能被校验改动过：标题和目标按实际安排重写，避免和内容对不上
            w["title"] = "、".join(KCS[k].name for k in w["kcs"])
            w["goals"] = [f"学会：{KCS[k].desc}" for k in w["kcs"]]
            if w["kcs"]:
                w["lesson_focus"] = KCS[w["kcs"][0]].name
    weeks = [w for w in weeks if w["kcs"]]
    placed = {k for w in weeks for k in w["kcs"]}
    dropped = [k for k in dict.fromkeys(requested) if k not in placed]
    if dropped:
        notes.append("未能安排：" + "、".join(KCS[k].name for k in dropped) + "（前置技能没有排进计划，或计划周数不够）。")
    if not weeks:
        return baseline_plan(progress), ["AI 计划无法通过校验，已使用程序生成的基础计划。"]
    return {"overview": plan.overview, "weeks": weeks, "daily_routine": plan.daily_routine,
            "milestones": plan.milestones, "source": "ai"}, notes


def candidates_table(progress: dict) -> str:
    need = need_scores(progress)
    lines = ["id | 技能 | 层级 | 维度 | 前置 | 当前等级 | 需要程度"]
    for k in topo_order():
        kc = KCS[k]
        tier = (progress["kc"].get(k) or {}).get("tier", "new")
        lines.append(f"{k} | {kc.name} | {kc.level} | {'/'.join(CRITERIA[c] for c in kc.criteria)} | "
                     f"{','.join(kc.prereqs) or '-'} | {mastery.TIERS[tier][0]} | {need[k]}")
    return "\n".join(lines)


def generate_plan(progress: dict) -> tuple[dict, list[str]]:
    from . import ai, prompts

    system, user = prompts.plan_request(progress, candidates_table(progress), baseline_plan(progress))
    plan = ai.structured(system, user, StudyPlan, max_tokens=16000, effort="medium")
    return validate_plan(progress, plan)


def install_plan(progress: dict, plan: dict) -> None:
    import uuid

    old = progress.get("plan") or {}
    plan["id"] = uuid.uuid4().hex[:8]
    plan["created"] = store.today()
    plan["current_week"] = 0
    plan["history"] = old.get("history", []) + ([{"created": old.get("created"), "weeks": len(old.get("weeks", []))}]
                                                 if old else [])
    progress["plan"] = plan


def current_week(progress: dict) -> dict | None:
    plan = progress.get("plan")
    if not plan or not plan["weeks"]:
        return None
    return plan["weeks"][min(plan.get("current_week", 0), len(plan["weeks"]) - 1)]


def week_progress(progress: dict, week: dict) -> float:
    """本周技能的平均完成度：已学会及以上算完成。"""
    if not week["kcs"]:
        return 0.0
    done = 0.0
    for k in week["kcs"]:
        st = progress["kc"].get(k) or {}
        rank = mastery.TIER_RANK[st.get("tier", "new")]
        done += 1.0 if rank >= mastery.TIER_RANK["learned"] else min(0.9, st.get("ema", 0.0))
    return done / len(week["kcs"])


def week_start(progress: dict, index: int) -> date:
    created = date.fromisoformat((progress.get("plan") or {}).get("created", store.today()))
    return created + timedelta(days=7 * index)
