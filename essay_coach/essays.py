"""作文流程：出题 → 独立写作 → 自评 → AI 反馈（限量）→ 逐条回应 → 修改 → 检查修改效果。

和刷题打通：
- 作文里的语言错误变成“改你自己的句子”题，进入错题本，按间隔复习；
- 重点问题和错误模式对应的技能点成为接下来刷题的重点（focus_kcs）；
- 只有独立完成的初稿（检测作文、练习作文初稿）才作为“已迁移”的证据和真实进步曲线，修改稿的分数不算。
"""

import hashlib
import random
import re
import uuid

from . import ai, mastery, prompts, store
from .drills import add_mistake
from .rubrics import RUBRICS, normalize_scores
from .schemas import EssayFeedback, EssayPrompt, RevisionCheck
from .skills import EXAM_CRITERIA, KCS

MAX_ISSUES = 3
MAX_PATTERNS = 3
MAX_INSTANCES = 3

KIND_LABELS = {"diagnostic": "诊断作文", "practice": "练习作文", "checkpoint": "检测作文"}

OFFLINE_PROMPTS = {
    "ielts": [
        "Some people believe that universities should focus on providing academic skills, while others think they should prepare students for employment. Discuss both views and give your own opinion.",
        "In many countries, people are spending more time on social media. Do the advantages of this trend outweigh the disadvantages?",
        "Some people think that governments should spend more money on public transport rather than building new roads. To what extent do you agree or disagree?",
        "Many young people today prefer to work for themselves rather than for a company. Why is this the case? Is this a positive or negative development?",
        "Some people believe that zoos should be closed because keeping animals in captivity is cruel. To what extent do you agree or disagree?",
        "Online learning is becoming more popular. Is this a positive or negative development for school students?",
    ],
    "general": [
        "Should high schools require students to do community service in order to graduate? Take a position and support it with reasons and examples.",
        "Is it better for students to learn online or in a traditional classroom? Argue for one side.",
        "Should cities ban private cars from their centres? Write an argumentative essay.",
        "Do the benefits of homework outweigh its drawbacks for primary school children?",
    ],
    "ap_argument": [
        "Many people argue that failure is a necessary part of success. Write an essay that argues your position on the value of failure.",
        "Some claim that convenience comes at the cost of meaningful experience. Write an essay that argues your position on this claim.",
    ],
    "personal": [
        "Describe a challenge you faced and what you learned from it about yourself.",
        "Tell us about an idea or experience that changed the way you think.",
    ],
}


def rubric_for(profile: dict | None) -> str:
    exam = (profile or {}).get("exam", "general")
    return exam if exam in RUBRICS else "general"


def new_prompt(progress: dict, kind: str) -> dict:
    profile = progress.get("profile") or {}
    exam = rubric_for(profile)
    from .planner import current_week

    week = current_week(progress)
    kcs = week["kcs"] if week else []
    if ai.is_ready():
        system, user = prompts.essay_prompt_request(exam, kcs, kind)
        p = ai.structured(system, user, EssayPrompt, max_tokens=3000, effort="low")
        return {"prompt": p.prompt, "type": p.question_type, "tip": "" if kind == "checkpoint" else p.focus_tip}
    used = {e["prompt"] for e in progress["essays"]}
    pool = [x for x in OFFLINE_PROMPTS.get(exam, OFFLINE_PROMPTS["general"]) if x not in used] or OFFLINE_PROMPTS[exam]
    return {"prompt": random.choice(pool), "type": "", "tip": ""}


def start_essay(progress: dict, kind: str, prompt: dict) -> dict:
    essay = {
        "id": uuid.uuid4().hex[:10], "kind": kind, "prompt": prompt["prompt"], "type": prompt.get("type", ""),
        "tip": prompt.get("tip", ""), "rubric": rubric_for(progress.get("profile")), "text": "",
        "created": store.now().isoformat(), "started": store.now().isoformat(), "submitted": None,
        "self": None, "feedback": None, "responses": [], "revised": "", "revision": None, "status": "writing",
    }
    progress["essays"].append(essay)
    store.save()
    return essay


def _criterion_gaps(rubric_key: str, criteria: list[dict]) -> dict[str, float]:
    mapping = EXAM_CRITERIA.get(rubric_key, EXAM_CRITERIA["general"])
    gaps: dict[str, list[float]] = {}
    for c in criteria:
        for short, generic in mapping.items():
            if short in c["name"]:  # 评分标准名称带前缀（如 “Row A · Thesis 论点”），用包含关系匹配
                for g in generic:
                    gaps.setdefault(g, []).append(1 - c["score"] / c["max_score"] if c["max_score"] else 0.5)
    return {g: round(sum(v) / len(v), 2) for g, v in gaps.items()}


def _sentence_around(text: str, quote: str) -> str:
    words = quote.split()
    if not words:
        return quote
    m = re.search(r"\s+".join(map(re.escape, words)), text)
    if not m:
        return quote
    start = max(text.rfind(ch, 0, m.start()) for ch in ".!?\n") + 1
    ends = [i for i in (text.find(ch, m.end()) for ch in ".!?\n") if i >= 0]
    end = min(ends) + 1 if ends else len(text)
    return " ".join(text[start:end].split())


def _personal_item(kc: str, sentence: str, pattern: dict, hint: str) -> dict:
    digest = hashlib.sha1(f"{kc}|{sentence}".encode()).hexdigest()[:10]
    return {
        "id": f"me-{kc}-{digest}", "kc": kc, "format": "fix", "difficulty": 3,
        "instruction": f"改正你自己作文里的这句话（{pattern['pattern']}）。",
        "content": sentence, "options": [], "answer": -1, "option_explanations": [], "sentences": [],
        "accepted": [], "criteria": f"改正句中的“{pattern['pattern']}”问题（{pattern['rule']}），其他部分保持原意且没有新错误。",
        "hints": [hint, f"规则：{pattern['rule']}", "逐个检查句子的主干和标点，找出不符合规则的地方。"],
        "explanation": pattern["rule"], "focus": pattern["pattern"], "source": "personal",
    }


def apply_feedback(progress: dict, essay: dict, fb: EssayFeedback) -> dict:
    data = fb.model_dump()
    rubric_key = essay["rubric"]
    data["criteria"], data["overall"] = normalize_scores(rubric_key, data["criteria"])
    # 水平较低的学生每篇只聚焦 2 个重点问题（反馈过多会让学生不知所措：Zhang & Hyland 2018；Shute 2008）
    cap = 2 if (progress.get("profile") or {}).get("level") == "初中" else MAX_ISSUES
    data["priority_issues"] = [x for x in data["priority_issues"] if x["kc"] in KCS][:cap]
    data["error_patterns"] = [dict(x, instances=x["instances"][:MAX_INSTANCES])
                              for x in data["error_patterns"] if x["kc"] in KCS][:MAX_PATTERNS]
    data["kc_evidence"] = [x for x in data["kc_evidence"] if x["kc"] in KCS]
    data["strengths"] = data["strengths"][:2]
    essay["feedback"] = data
    essay["status"] = "feedback"

    # 错误 → 错题本（改自己的句子）
    for pattern in data["error_patterns"]:
        for inst in pattern["instances"]:
            sentence = _sentence_around(essay["text"], inst["quote"])
            item = _personal_item(pattern["kc"], sentence, pattern, inst["hint"])
            if not any(m.get("item_id") == item["id"] for m in progress["mistakes"]):
                add_mistake(progress, pattern["kc"], sentence, f"{pattern['pattern']}：{pattern['rule']}", "essay",
                            personal_item=item)

    # 接下来刷题的重点
    focus = [x["kc"] for x in data["priority_issues"]] + [x["kc"] for x in data["error_patterns"]]
    progress["focus_kcs"] = list(dict.fromkeys(focus))[:5]

    # 独立完成的初稿：迁移证据
    if essay["kind"] in ("checkpoint", "practice", "diagnostic"):
        for ev in data["kc_evidence"]:
            mastery.kc_state(progress, ev["kc"])
            mastery.mark_transfer(progress, ev["kc"], ev["status"] == "demonstrated")

    if essay["kind"] == "diagnostic":
        diag = progress.get("diagnostic") or {}
        weak = [e["kc"] for e in data["kc_evidence"] if e["status"] != "demonstrated"] + focus
        strong = [e["kc"] for e in data["kc_evidence"] if e["status"] == "demonstrated"]
        diag["weak_kcs"] = list(dict.fromkeys(diag.get("weak_kcs", []) + weak))
        diag["strong_kcs"] = [k for k in dict.fromkeys(diag.get("strong_kcs", []) + strong) if k not in weak]
        diag["criterion_gap"] = _criterion_gaps(rubric_key, data["criteria"])
        diag["essay_level"] = data["level_label"]
        diag["summary"] = data["now"]
        progress["diagnostic"] = diag
    store.save()
    return data


def request_feedback(progress: dict, essay: dict) -> dict:
    system, user = prompts.essay_feedback_request(essay["rubric"], essay["prompt"], essay["text"], essay["kind"],
                                                  progress.get("profile") or {})
    fb = ai.structured(system, user, EssayFeedback, max_tokens=32000)
    return apply_feedback(progress, essay, fb)


def request_revision_check(progress: dict, essay: dict) -> dict:
    fb = essay["feedback"]
    system, user = prompts.revision_check_request(essay["rubric"], essay["prompt"], essay["text"],
                                                  fb["priority_issues"], essay["responses"], essay["revised"])
    rc = ai.structured(system, user, RevisionCheck, max_tokens=16000)
    data = rc.model_dump()
    data["criteria"], data["overall_score"] = normalize_scores(essay["rubric"], data["criteria"])
    essay["revision"] = data
    essay["status"] = "done" if not data["surface_only"] else "revising"
    store.save()
    return data


def checkpoint_series(progress: dict) -> list[dict]:
    """真实进步曲线：独立完成的初稿（诊断 + 检测作文）的得分，按时间排列。"""
    rows = []
    for e in progress["essays"]:
        if e["kind"] in ("diagnostic", "checkpoint") and e.get("feedback"):
            rubric = RUBRICS[e["rubric"]]
            rows.append({"date": e["submitted"] or e["created"], "kind": KIND_LABELS[e["kind"]],
                         "score": e["feedback"]["overall"], "max": rubric["max"], "rubric": e["rubric"]})
    return rows
