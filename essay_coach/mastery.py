"""掌握度与复习安排。

- 能力估计：每个技能点一个 Elo 能力值 θ，每道题一个难度 b（Pelánek 2016 的自适应练习做法），
  P(答对) = g + (1 - g)·σ(θ - b)，选择题的 g = 1/选项数（猜对概率）。
- 只用“独立完成”的表现计算掌握度：看了提示、答错后才改对、看了答案，都按“没有独立做对”计入能力值和
  正确率（Bastani et al. 2025：有帮助时的正确率会制造“学会了”的错觉）；这些作答单独统计为“有帮助”。
- 只有“第一次见到的题”才算掌握证据：做过的题再出现时，答对可能只是记住了答案（Chen, West & Zilles 2018），
  所以重复题不计入连续答对、指数平均和复习成功，也不更新题目难度（Papoušek et al. 2014 只用首次作答校准）。
- 三级掌握（参考 Bloom 掌握学习 + ALEKS / ASSISTments 的连续正确标准）：
    已学会 learned：连续独立答对 5 道没见过的不同题目（如果这个技能一开始的 3 题就都独立答对，3 道即可）；
                    技能有产出型题目（改错、合并、改写、写作）时，其中至少 1 道是产出型
    已巩固 retained：学会后，在间隔 ≥ 20 小时的三次复习里首题都独立答对（Rawson & Dunlosky 2011 的连续重新学习）
    已迁移 transferred：在一篇独立完成的作文里用对了这个技能（作文批改给出证据）
- 指数平均按题型加权：产出型题目比选择题提供更多证据（Pelánek & Řihák 2018 的做法），用于判断是否明显退步。
- 复习安排：每个技能点一张 FSRS 卡片（py-fsrs，desired_retention 0.9），每天只用当天该技能的第一题打分，
  间隔不超过离考试天数的 20%（Cepeda et al. 2008：间隔应与保持时长成比例）。
"""

import math
from datetime import datetime, timedelta, timezone

from fsrs import Card, Rating, Scheduler

from .skills import KCS
from .store import study_day

TIERS = {
    "new": ("未开始", "gray"),
    "learning": ("练习中", "orange"),
    "learned": ("已学会", "blue"),
    "retained": ("已巩固", "violet"),
    "transferred": ("已迁移", "green"),
}
TIER_RANK = {k: i for i, k in enumerate(TIERS)}

REVIEW_GAP = timedelta(hours=20)
LEARNED_STREAK = 5
LEARNED_STREAK_FAST = 3   # 一开始就连续答对的学生（已经会了）不用多做
RETAINED_REVIEWS = 3
REPEAT_WEIGHT = 0.25      # 做过的题再出现：只用很小的权重更新能力值
PRODUCTION = {"fix", "combine", "rewrite", "write"}
# 指数平均的权重：选择题信息量小，产出型题目信息量大
EMA_WEIGHT = {"mcq": 0.2, "judge": 0.2, "order": 0.3, "fix": 0.3, "combine": 0.3, "rewrite": 0.4, "write": 0.4}


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def seed_difficulty(level: int, source: str = "seed") -> float:
    """题目标注难度 1–5 → 初始 Elo 难度。

    标注难度是 AI 估计的，和真实难度相关性很弱（An & Wang 2026；BEA 2024 难度预测共享任务），
    所以只作为较弱的先验：种子题（经过多轮核对）每级 0.5，运行时 AI 新题每级 0.25，之后由作答数据校准。
    """
    return (level - 3) * (0.5 if source == "seed" else 0.25)


def kc_state(progress: dict, kc: str) -> dict:
    state = progress["kc"].setdefault(kc, {})
    for key, default in (("theta", 0.0), ("n", 0), ("ema", 0.0), ("streak", 0), ("tier", "new"),
                         ("learned_at", None), ("reviews_ok", []), ("card", None), ("last_day", None),
                         ("solo_n", 0), ("solo_ok", 0), ("help_n", 0), ("help_ok", 0), ("streak_items", []),
                         ("first_results", []), ("streak_prod", False), ("fails", 0)):
        state.setdefault(key, default)
    return state


def item_difficulty(progress: dict, item) -> float:
    rec = progress["items"].get(item.id)
    return rec["b"] if rec else seed_difficulty(item.difficulty, getattr(item, "source", "seed"))


def guess_rate(item) -> float:
    if item.format in ("mcq", "judge") and item.options:
        return 1 / len(item.options)
    return 0.0


def p_correct(progress: dict, item) -> float:
    theta = kc_state(progress, item.kc)["theta"]
    g = guess_rate(item)
    return g + (1 - g) * _sigmoid(theta - item_difficulty(progress, item))


def mastery_pct(progress: dict, kc: str) -> int:
    """在一道中等难度（b=0）开放题上的预计正确率，用于展示。"""
    st = progress["kc"].get(kc)
    if not st or not st.get("n"):
        return 0
    return round(_sigmoid(st["theta"]) * 100)


def outcome_value(score: float, hints: int, revealed: bool) -> float:
    """用于能力估计的结果：只有独立完成才计分（开放题按得分），有帮助或看答案都记 0。"""
    if revealed or hints:
        return 0.0
    return max(0.0, min(score, 1.0))


def _rating(score: float, hints: int, revealed: bool, confident: bool | None, fast: bool) -> Rating:
    if revealed or score < 0.5:
        return Rating.Again
    if hints or score < 0.8:
        return Rating.Hard
    if confident and fast:
        return Rating.Easy
    return Rating.Good


def max_interval_days(progress: dict | None) -> int:
    """最长复习间隔：平时 60 天；设了考试日期时不超过剩余天数的 20%，保证考前至少再复习几轮。"""
    max_days = 60
    exam = ((progress or {}).get("profile") or {}).get("exam_date")
    if exam:
        try:
            days_left = (datetime.fromisoformat(exam).date() - study_day()).days
            max_days = max(1, min(max_days, int(days_left * 0.2)))
        except ValueError:
            pass
    return max_days


def scheduler(progress: dict) -> Scheduler:
    profile = progress.get("profile") or {}
    retention = 0.85 if profile.get("level") in ("初中",) else 0.9
    return Scheduler(desired_retention=retention, learning_steps=(), relearning_steps=(),
                     maximum_interval=max_interval_days(progress), enable_fuzzing=False)


def review_card(progress: dict, card: dict | None, rating: Rating, when: datetime) -> dict:
    c = Card.from_dict(card) if card else Card()
    c, _ = scheduler(progress).review_card(c, rating, when)
    return c.to_dict()


def effective_due(card: dict, progress: dict | None = None) -> datetime:
    """复习到期时间。旧卡片按现在的最长间隔重新封顶；设了考试日期时，排在考试之后的复习提前到考前一天。"""
    due = _parse(card["due"])
    last = _parse(card["last_review"]) if card.get("last_review") else None
    if last is not None:  # 考试日期改近了：以前排得很远的复习也要按新的间隔提前
        due = min(due, last + timedelta(days=max_interval_days(progress)))
    exam = ((progress or {}).get("profile") or {}).get("exam_date")
    if exam:
        try:
            cap = datetime.fromisoformat(exam).replace(tzinfo=timezone.utc) - timedelta(days=1)
        except ValueError:
            return due
        if due > cap and (last is None or last < cap):
            return cap
    return due


def card_due(card: dict | None, when: datetime, progress: dict | None = None) -> bool:
    if not card:
        return False
    return effective_due(card, progress) <= when


def record(progress: dict, item, score: float, hints: int, revealed: bool,
           confident: bool | None = None, seconds: float | None = None, when: datetime | None = None,
           require_production: bool = False) -> dict:
    """记录一次作答，更新能力值、题目难度、掌握等级和复习卡片。返回该技能点的新状态。

    require_production：这个技能现在有可做的产出型题目，“已学会”的连续答对里必须至少有一道产出型题目。
    """
    when = when or datetime.now(timezone.utc)
    day = study_day(when).isoformat()
    st = kc_state(progress, item.kc)
    o = outcome_value(score, hints, revealed)
    solo = hints == 0 and not revealed
    correct = score >= 0.8
    p = p_correct(progress, item)
    first = item.id not in progress["items"]  # 这个学生第一次做这道题

    # Elo：不确定性随作答次数下降；题目难度只用首次作答校准，重复题只小幅更新能力值
    k_student = 1 / (1 + 0.05 * st["n"])
    rec = progress["items"].setdefault(item.id, {"b": item_difficulty(progress, item), "n": 0})
    if first:
        k_item = 1 / (1 + 0.05 * rec["n"])
        st["theta"] += k_student * (o - p)
        rec["b"] -= k_item * (o - p) * 0.5
    else:
        st["theta"] += REPEAT_WEIGHT * k_student * (o - p)
    st["n"] += 1
    rec["n"] += 1
    if first and solo and not correct and p >= 0.9:
        rec["surprise"] = True  # 预计几乎肯定会对却错了：题目可能有问题，留作核查信号

    if solo:
        st["solo_n"] += 1
        st["solo_ok"] += int(correct)
    else:
        st["help_n"] += 1
        st["help_ok"] += int(correct and not revealed)

    # 掌握证据只看第一次见到的题（AI 判 0.8 以上算对）
    good = solo and correct
    if first:
        w = EMA_WEIGHT.get(item.format, 0.3)
        st["ema"] = (1 - w) * st["ema"] + w * (1.0 if good else 0.0)
        if len(st["first_results"]) < LEARNED_STREAK_FAST:
            st["first_results"].append(good)
        st["fails"] = 0 if good else st["fails"] + 1
    if good and first:
        if item.id not in st["streak_items"]:
            st["streak_items"].append(item.id)
        st["streak_prod"] = st["streak_prod"] or item.format in PRODUCTION
    elif not good:
        st["streak_items"] = []
        st["streak_prod"] = False
    st["streak"] = len(st["streak_items"])

    # 每天只用第一题更新复习卡片
    first_today = st["last_day"] != day
    if first_today:
        fast = seconds is not None and seconds < 45
        st["card"] = review_card(progress, st["card"], _rating(score, hints, revealed, confident, fast), when)
        # “隔天复习”：与学会时间、上一次成功复习都至少间隔 REVIEW_GAP，避免跨午夜几分钟就算两天；
        # 复习必须是没见过的题，才能说明记住的是技能而不是这道题
        if st["learned_at"] and good and first:
            last = st["reviews_ok"][-1] if st["reviews_ok"] else st["learned_at"]
            if when - _parse(last) >= REVIEW_GAP:
                st["reviews_ok"].append(when.isoformat())
        elif st["learned_at"] and not good:
            st["reviews_ok"] = []  # 复习没做对：“巩固”要重新攒
        st["last_day"] = day

    _update_tier(st, when, require_production)
    return st


def learned_now(st: dict, require_production: bool = False) -> bool:
    need = LEARNED_STREAK_FAST if (len(st["first_results"]) >= LEARNED_STREAK_FAST and all(st["first_results"])) \
        else LEARNED_STREAK
    return st["streak"] >= need and (st["streak_prod"] or not require_production)


def _update_tier(st: dict, when: datetime, require_production: bool = False) -> None:
    tier = st["tier"]
    if st["n"] and tier == "new":
        tier = "learning"
    if TIER_RANK[tier] < TIER_RANK["learned"] and learned_now(st, require_production):
        tier = "learned"
        st["learned_at"] = when.isoformat()
        st["reviews_ok"] = []
    if tier == "learned" and len(st["reviews_ok"]) >= RETAINED_REVIEWS:
        tier = "retained"
    # 学会后又明显退步（连续两道没见过的题都没能独立做对）：退回练习中，重新达标
    if TIER_RANK[tier] >= TIER_RANK["learned"] and st["fails"] >= 2:
        tier = "learning"
        st["learned_at"] = None
        st["reviews_ok"] = []
    st["tier"] = tier


def mark_transfer(progress: dict, kc: str, demonstrated: bool) -> None:
    """作文批改给出的迁移证据：已巩固的技能在独立作文中用对 → 已迁移；用错 → 降回已学会并安排复习。"""
    if kc not in KCS:
        return
    st = kc_state(progress, kc)
    if demonstrated and st["tier"] == "retained":
        st["tier"] = "transferred"
    elif not demonstrated and st["tier"] in ("retained", "transferred"):
        st["tier"] = "learned"
        st["reviews_ok"] = []
        st["card"] = review_card(progress, st["card"], Rating.Again, datetime.now(timezone.utc))


def is_unlocked(progress: dict, kc: str) -> bool:
    """前置技能都至少“练习中”且掌握度过半，或已学会。"""
    for p in KCS[kc].prereqs:
        st = progress["kc"].get(p)
        if not st:
            return False
        if TIER_RANK[st["tier"]] < TIER_RANK["learned"] and st["ema"] < 0.6:
            return False
    return True


def due_kcs(progress: dict, when: datetime | None = None) -> list[str]:
    when = when or datetime.now(timezone.utc)
    return [k for k, st in progress["kc"].items()
            if k in KCS and st.get("tier") != "new" and card_due(st.get("card"), when, progress)]


def next_review(progress: dict, kc: str) -> datetime | None:
    card = (progress["kc"].get(kc) or {}).get("card")
    return effective_due(card, progress) if card else None


def solo_vs_help(progress: dict) -> tuple[tuple[int, int], tuple[int, int]]:
    solo = sum(s.get("solo_ok", 0) for s in progress["kc"].values()), sum(s.get("solo_n", 0) for s in progress["kc"].values())
    helped = sum(s.get("help_ok", 0) for s in progress["kc"].values()), sum(s.get("help_n", 0) for s in progress["kc"].values())
    return solo, helped


def retention_now(progress: dict, kc: str) -> float | None:
    card = (progress["kc"].get(kc) or {}).get("card")
    if not card:
        return None
    return scheduler(progress).get_card_retrievability(Card.from_dict(card), datetime.now(timezone.utc))


def _parse(stamp: str) -> datetime:
    return ensure_aware(datetime.fromisoformat(stamp))


def ensure_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def days_until(dt: datetime) -> float:
    return (ensure_aware(dt) - datetime.now(timezone.utc)) / timedelta(days=1)
