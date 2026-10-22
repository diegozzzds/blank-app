"""刷题引擎：选题、判分、提示阶梯、错题本、AI 出新题。

选题顺序（每次只出一题）：
  1. 本次练习中做错的技能：间隔至少 2 题后用“同类新题”再测（最多再测 2 次）
  2. 到期的错题（successive relearning：不同日期独立答对 3 次才移出错题本）
  3. 到期的技能复习（FSRS）
  4. 学习大纲本周的技能
  5. 其他已解锁、掌握度最低的技能
  同一技能不连续出现 3 次以上（交错练习）；题目难度对准预计正确率约 75%（Wilson et al. 2019 的“85% 规则”，
  对写作这类复杂技能取得更低一些）。

作答规则（“先尝试，再提示，最后才看答案”）：
  第一次提交前不能看提示；答错后可以逐级看 3 个提示；答错两次或看完提示后才能看答案；
  看答案算作没答对，会进入错题本，并在本次练习稍后用同类新题再测。
"""

import difflib
import hashlib
import random
import re
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from . import ai, mastery, store
from .items import Item, length_cue, rule_cards, seed_items, shuffled_order
from .skills import AUTO_GRADED, FORMATS, KCS

TARGET_P = 0.75
REQUEUE_GAP = 2
MAX_REQUEUE = 2
MISTAKE_RETIRE_REVIEWS = 3
# 这些错误到很高水平还会反复出现（学习者语料研究：冠词、搭配、语气、语体、连接词），错题要多攒一天才移出
PERSISTENT_KCS = {"articles", "collocation", "hedging", "register", "transitions"}


# 没有简单规则、靠大量例子积累的技能（冠词、搭配、用词）：看答案后的自我解释改为可选
PROBABILISTIC_KCS = {"articles", "collocation", "word_precision"}


def retire_after(kc: str) -> int:
    return MISTAKE_RETIRE_REVIEWS + (1 if kc in PERSISTENT_KCS else 0)


# ---------------- 题库 ----------------

def all_items(progress: dict) -> list[Item]:
    flagged = set(progress.get("flagged_items", []))
    items = [i for i in seed_items() if i.id not in flagged]
    for raw in progress["ai_items"]:
        if raw["id"] in flagged:
            continue
        try:
            it = Item.model_validate(raw)
        except ValueError:
            continue
        if not it.problems():
            items.append(it)
    return items


def find_item(progress: dict, item_id: str) -> Item | None:
    for it in all_items(progress):
        if it.id == item_id:
            return it
    for m in progress["mistakes"]:
        if m.get("item") and m["item"]["id"] == item_id:
            return Item.model_validate(m["item"])
    return None


def needs_ai(item: Item) -> bool:
    """开放题需要 AI 判分；改错题有参考答案时可以先精确比对。"""
    if item.format == "fix":
        return not item.accepted
    return item.format not in AUTO_GRADED


def _last_seen(progress: dict) -> dict[str, str]:
    """每道题最近一次作答的时间（ISO 字符串）。"""
    return {a["item"]: a.get("t", "") for a in progress["attempts"]}


def production_needed(progress: dict, kc: str, ai_ready: bool, exclude: set[str] = frozenset()) -> bool:
    """“已学会”是否要求至少一道产出型题目：还有没做过、现在能做的产出型题目时才要求（否则会卡住）。"""
    st = mastery.kc_state(progress, kc)
    return st["streak_prod"] or any(i.format in mastery.PRODUCTION for i in fresh_items(progress, kc, exclude, ai_ready))


def fresh_items(progress: dict, kc: str, exclude: set[str] = frozenset(), ai_ready: bool = True) -> list[Item]:
    """这个学生从没做过的题。"""
    return [i for i in all_items(progress) if i.kc == kc and i.id not in exclude and i.id not in progress["items"]
            and (ai_ready or not needs_ai(i))]


def _last_focus(progress: dict, kc: str) -> str:
    for a in reversed(progress["attempts"][-50:]):
        if a.get("kc") == kc:
            return a.get("focus", "")
    return ""


REVIEW_REASONS = ("错题复习", "到期复习")


def target_p(progress: dict, kc: str, reason: str = "") -> float:
    """目标正确率（区间而不是一个数，Papoušek et al. 2016 的大样本实验；Math Garden 约 0.75）：
    新技能的前几题容易一些（约 0.82），练习中约 0.75，复习约 0.72；初中生整体高 0.05，最高不超过 0.9。"""
    st = mastery.kc_state(progress, kc)
    if reason.startswith(REVIEW_REASONS):
        t = 0.72
    elif st["solo_n"] + st["help_n"] < 4:
        t = 0.82
    else:
        t = TARGET_P
    if (progress.get("profile") or {}).get("level") == "初中":
        t += 0.05
    return min(t, 0.9)


def _score(progress: dict, item: Item, target: float, focus: str, last_focus: str, want_production: bool) -> float:
    """选题打分（越大越好），参考 Pelánek 的自适应练习：难度贴近目标 + 错误类型覆盖 + 题型进阶。"""
    p = mastery.p_correct(progress, item)
    score = -10 * abs(p - target)
    if focus:
        score += 3 if item.focus == focus else 0
    elif last_focus and item.focus == last_focus:
        score -= 1.5  # 技能内部也换着练不同的错误类型
    if item.format in mastery.PRODUCTION:
        # 先认后产（recognition → production）：预计正确率够高才出产出型题目；快学会时主动安排一道
        score += 2.5 if want_production and p >= 0.5 else (-2 if p < 0.6 else 0)
    return score


def pick_item(progress: dict, kc: str, exclude: set[str], ai_ready: bool, allow_repeat: bool = True,
              focus: str = "", reason: str = "") -> Item | None:
    """为技能 kc 选一道题：没做过的优先；在得分和最佳相差不大的至多 3 道里随机选一道
    （“randomesque”，Kingsbury & Zara：让每道题都有机会出现，而不是总出同几道）。

    focus：再测刚做错的题或复习错题时，优先选同一类错误（同一子类）的新题；
    没指定时，优先换一个和上一题不同的子类（技能内部也交错练习）。
    没做过的题用完时，allow_repeat=False 返回 None（由调用方让 AI 出新题）；
    allow_repeat=True 时重复旧题，最久没见过的优先。
    """
    target = target_p(progress, kc, reason)
    last = "" if focus else _last_focus(progress, kc)
    st = mastery.kc_state(progress, kc)
    need = mastery.LEARNED_STREAK_FAST if all(st["first_results"]) else mastery.LEARNED_STREAK
    want_production = not st["streak_prod"] and st["streak"] >= need - 2
    rng = random.Random(f"{kc}|{len(progress['attempts'])}|{len(exclude)}")

    fresh = fresh_items(progress, kc, exclude, ai_ready)
    if fresh:
        scored = sorted(((_score(progress, i, target, focus, last, want_production), i.id, i) for i in fresh),
                        key=lambda x: (-x[0], x[1]))
        near = [x[2] for x in scored if x[0] >= scored[0][0] - 1.0][:3]  # 只在和最佳差不多的几道里随机
        return rng.choice(near)
    if not allow_repeat:
        return None
    candidates = [i for i in all_items(progress) if i.kc == kc and i.id not in exclude]
    if not ai_ready:
        candidates = [i for i in candidates if not needs_ai(i)]
    if not candidates:
        return None
    seen_at = _last_seen(progress)
    return min(candidates, key=lambda i: (seen_at.get(i.id, ""), -_score(progress, i, target, focus, last, False), i.id))


# ---------------- 选题 ----------------

def new_session(mode: str, kc: str | None = None, goal: int = 15) -> dict:
    return {"mode": mode, "kc": kc, "goal": goal, "count": 0, "correct": 0, "requeue": [],
            "recent_kcs": [], "seen": [], "current": None, "log": [], "gen_tried": []}


def current_week_kcs(progress: dict) -> list[str]:
    from .planner import current_week

    week = current_week(progress)
    return [k for k in week["kcs"] if k in KCS] if week else []


def due_mistakes(progress: dict, when: datetime | None = None, ai_ready: bool = True) -> list[dict]:
    """到期的错题。离线时只算有题可出的（自己的句子需要 AI 判分，同类题至少要有一道能自动判分）。"""
    when = when or datetime.now(timezone.utc)
    due = [m for m in progress["mistakes"] if not m.get("retired") and mastery.card_due(m.get("card"), when, progress)]
    if ai_ready:
        return due
    return [m for m in due if pick_item(progress, m["kc"], set(), False) is not None]


def weakest_unlocked(progress: dict, exclude: list[str]) -> list[str]:
    ks = [k for k in KCS if mastery.is_unlocked(progress, k) and k not in exclude]
    return sorted(ks, key=lambda k: (mastery.TIER_RANK[mastery.kc_state(progress, k)["tier"]],
                                     mastery.mastery_pct(progress, k), -KCS[k].prior))


def _too_repetitive(session: dict, kc: str) -> bool:
    return session["recent_kcs"][-2:] == [kc, kc]


DAILY_CAP = 10        # 一天在同一技能上做了这么多题还没学会：先停一停（ASSISTments 的做法），明天再练
STUCK_WRONG = 5       # 今天在同一技能上连续这么多题没做对：先回去看微课 / 规则卡
CONFIRM_AFTER_LEARNED = 3  # 已学会的技能今天做到这么多题就够了：过度练习的收益很小（Rohrer & Taylor 2006）


def _today_attempts(progress: dict, kc: str) -> list[dict]:
    today = store.today()
    out = []
    for a in reversed(progress["attempts"][-200:]):
        if a.get("kc") != kc:
            continue
        try:
            if store.study_day(datetime.fromisoformat(a["t"])).isoformat() != today:
                break
        except (KeyError, ValueError):
            break
        out.append(a)
    return out  # 最近的在前


def rest_reason(progress: dict, kc: str) -> str | None:
    """今天这个技能是否应该先停一停；返回给学生看的原因。"""
    today = _today_attempts(progress, kc)
    ok = [a.get("score", 0) >= 0.8 and not a.get("revealed") and not a.get("hints") and not a.get("wrong")
          for a in today]
    if len(ok) >= STUCK_WRONG and not any(ok[:STUCK_WRONG]):
        return "今天这个技能连续几题都没做对。先回去看看微课和规则卡，或者练练它的前置技能，明天再来。"
    tier = mastery.kc_state(progress, kc)["tier"]
    if mastery.TIER_RANK[tier] < mastery.TIER_RANK["learned"] and len(today) >= DAILY_CAP:
        return "今天这个技能已经练了很多题。分几天练比一次练很多记得更牢，明天再继续。"
    return None


def _enough_today(progress: dict, kc: str) -> bool:
    if rest_reason(progress, kc):
        return True
    tier = mastery.kc_state(progress, kc)["tier"]
    return mastery.TIER_RANK[tier] >= mastery.TIER_RANK["learned"] and len(_today_attempts(progress, kc)) >= CONFIRM_AFTER_LEARNED


def candidate_kcs(progress: dict, session: dict, ai_ready: bool = True) -> list[tuple[str, str, dict | None]]:
    """按优先级返回 (技能, 原因, 关联错题)。"""
    out: list[tuple[str, str, dict | None]] = []
    for r in session["requeue"]:
        if r["after"] <= session["count"]:
            out.append((r["kc"], "再测一次刚才做错的技能", r.get("mistake")))
    if session["mode"] == "kc" and session["kc"]:
        out.append((session["kc"], "指定练习", None))
        return out
    mistakes = due_mistakes(progress, ai_ready=ai_ready)
    for m in mistakes:
        out.append((m["kc"], "错题复习", m))
    if session["mode"] == "mistakes":
        return out
    for k in mastery.due_kcs(progress):
        out.append((k, "到期复习", None))
    for k in progress.get("focus_kcs", []):  # 最近一篇作文暴露的弱项
        if k in KCS and not _enough_today(progress, k):
            out.append((k, "上篇作文的弱项", None))
    for k in current_week_kcs(progress):
        if not _enough_today(progress, k):
            out.append((k, "本周学习目标", None))
    # 补充最薄弱的可学技能；离线时跳过已经没有可做题目的技能，避免练习提前结束
    seen = set(session["seen"])
    added = 0
    for k in weakest_unlocked(progress, [c[0] for c in out]):
        if added >= 6:
            break
        if _enough_today(progress, k):
            continue
        if ai_ready or pick_item(progress, k, seen, False) is not None:
            out.append((k, "薄弱技能", None))
            added += 1
    return out


def next_item(progress: dict, session: dict, ai_ready: bool) -> tuple[Item | None, str, dict | None, str | None]:
    """返回 (题目, 原因, 关联错题, 需要 AI 生成题目的技能)。"""
    seen = set(session["seen"])
    cands = candidate_kcs(progress, session, ai_ready)
    # 刚做错、还在等待再测的技能先不出（保证中间隔开几题）；同一技能不连续出现 3 次（交错练习）
    waiting = {r["kc"] for r in session["requeue"] if r["after"] > session["count"]}
    # 一次练习里复习最多占一半，其余练新内容（Lindsey et al. 2014 的复习 + 新内容混合）
    done_reviews = sum(1 for x in session["log"] if x.get("reason", "").startswith(REVIEW_REASONS))
    review_heavy = session["mode"] == "today" and session["count"] >= 4 and done_reviews * 2 >= session["count"]

    def rank(c):
        return (c[0] in waiting and not c[1].startswith("再测"), review_heavy and c[1].startswith(REVIEW_REASONS),
                _too_repetitive(session, c[0]))

    ordered = sorted(cands, key=rank)
    retest_focus = {r["kc"]: r.get("focus", "") for r in session["requeue"] if r["after"] <= session["count"]}

    def focus_of(kc: str, reason: str, mistake: dict | None) -> str:
        if reason.startswith("再测"):
            return retest_focus.get(kc, "")
        return (mistake or {}).get("focus", "")

    flagged = set(progress.get("flagged_items", []))
    for kc, reason, mistake in ordered:
        if mistake and mistake.get("item") and not mistake.get("personal_done") and mistake["item"]["id"] not in flagged:
            it = Item.model_validate(mistake["item"])
            if it.id not in seen and (ai_ready or not needs_ai(it)):
                return it, reason, mistake, None
    # 先只出没做过的题；都用完了，能出新题就让 AI 出（不重复旧题），出不了才重复最久没见过的旧题
    can_generate = [c for c in ordered if ai_ready and c[0] not in session.get("gen_tried", [])]
    for allow_repeat in (False, True):
        if allow_repeat and can_generate:
            return None, "", None, can_generate[0][0]
        for kc, reason, mistake in ordered:
            it = pick_item(progress, kc, seen, ai_ready, allow_repeat=allow_repeat, focus=focus_of(kc, reason, mistake),
                           reason=reason)
            if it:
                return it, reason, mistake, None
    return None, "", None, None


def low_kcs(progress: dict, session: dict, ai_ready: bool) -> list[str]:
    """接下来要练、但没做过的题快用完的技能（按优先级），用于后台提前出题。"""
    if not ai_ready:
        return []
    seen = set(session["seen"])
    upcoming = list(dict.fromkeys(kc for kc, _, _ in candidate_kcs(progress, session, ai_ready)))[:PREFETCH_KCS]
    return [kc for kc in upcoming if kc not in session.get("gen_tried", [])
            and len(fresh_items(progress, kc, seen)) < LOW_WATER]


# ---------------- 判分 ----------------

_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', " ": " "})


def _clean(text: str) -> str:
    """只统一引号和空白，保留大小写和标点前的空格。"""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip()


def normalize(text: str) -> str:
    """宽松比较：再忽略大小写、标点前的空格和句末句号。只用来判断“是否需要交给 AI”。"""
    t = re.sub(r"\s+([,.;:!?])", r"\1", _clean(text))
    return t.rstrip(".").lower()


class DrillGrade(BaseModel):
    score: float = Field(description="改错/合并：1 或 0；改写/写作：1、0.5 或 0")
    uncertain: bool = Field(description="对这个判断没有把握时为 true")
    verdict: str = Field(description="一句话判断（中文）")
    good: str = Field(description="答案中做对的地方；没有则写空字符串")
    issue: str = Field(description="还有什么问题、为什么；不要写出改正后的句子")
    hint: str = Field(description="下一次尝试的提示：指出方向，不给答案")
    rule: str = Field(description="相关规则，一句话")


def grade_auto(item: Item, response) -> tuple[float, str]:
    if item.format in ("mcq", "judge"):
        ok = response == item.answer
        return (1.0 if ok else 0.0), (item.option_explanations[response] if item.option_explanations
                                      and response is not None and 0 <= response < len(item.options) else "")
    if item.format == "order":
        # response：学生给出的句子顺序（原始下标）。相邻顺序对的比例作为部分得分
        if not response or len(response) != len(item.sentences):
            return 0.0, "请把所有句子都排进去。"
        if list(response) == list(range(len(item.sentences))):
            return 1.0, ""
        pairs = sum(1 for a, b in zip(response, response[1:]) if b == a + 1)
        return round(pairs / (len(item.sentences) - 1) * 0.7, 2), ""
    if item.format == "fix":
        answer = _clean(response or "")
        if answer == _clean(item.content):
            return 0.0, "你还没有修改原句。"
        # 和参考答案完全一致（只允许句末句号不同）才直接判对
        if any(answer.rstrip(".") == _clean(a).rstrip(".") for a in item.accepted):
            return 1.0, ""
        if any(normalize(answer) == normalize(a) for a in item.accepted):
            return -1.0, "和参考答案只差大小写或标点前的空格，请检查一下。"
        return -1.0, ""  # 需要 AI 判断
    return -1.0, ""


BINARY_FORMATS = {"fix", "combine"}


def edit_summary(original: str, response: str) -> list[str]:
    """学生相对原句做了哪些改动（按词比较），给判分老师逐条核对。"""
    a, b = _clean(original).split(), _clean(response).split()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append(f"{' '.join(a[i1:i2]) or '（无）'} → {' '.join(b[j1:j2]) or '（删去）'}")
    return out


def _snap(item: Item, score: float) -> float:
    """分数只用粗的档位（研究发现细分档位的一致性更差）：改错/合并只有对错，改写/写作 0 / 0.5 / 1。"""
    score = min(max(score, 0.0), 1.0)
    if item.format in BINARY_FORMATS:
        return 1.0 if score >= 0.8 else 0.0
    return 1.0 if score >= 0.8 else 0.5 if score >= 0.4 else 0.0


def grade_open(item: Item, response: str, attempt_no: int, hints_used: list[str]) -> DrillGrade:
    """AI 判分。结果在边界上（0.5 档）或老师自己没把握时，再独立判两次取中位数（研究建议的“边界复核”）。"""
    from concurrent.futures import ThreadPoolExecutor

    from . import prompts

    edits = edit_summary(item.content, response) if item.content and item.format in ("fix", "rewrite") else None
    system, user = prompts.drill_grade_request(item, response, attempt_no, hints_used, edits)
    first = ai.structured(system, user, DrillGrade, max_tokens=6000, effort="low")
    borderline = first.uncertain or 0.3 <= first.score < 0.8
    first.score = _snap(item, first.score)
    if not borderline:
        return first
    client = ai.client()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(ai.structured, system, prompts.shuffle_references(user, k), DrillGrade, 6000, "medium",
                               client) for k in (1, 2)]
        more = []
        for f in futures:
            try:
                more.append(f.result())
            except ai.AIError:
                pass
    grades = [first] + [g.model_copy(update={"score": _snap(item, g.score)}) for g in more]
    grades.sort(key=lambda g: g.score)
    pick = grades[len(grades) // 2]
    pick.uncertain = len({g.score for g in grades}) == len(grades)  # 没有多数意见才算“不确定”
    return pick


def contest_grade(item: Item, response: str, hints_used: list[str]) -> tuple[bool, DrillGrade]:
    """学生认为自己的答案也对：用更深入的思考独立复核三次，多数认为正确才改判。"""
    from concurrent.futures import ThreadPoolExecutor

    from . import prompts

    edits = edit_summary(item.content, response) if item.content and item.format in ("fix", "rewrite") else None
    system, user = prompts.drill_grade_request(item, response, 1, hints_used, edits, contested=True)
    client = ai.client()
    with ThreadPoolExecutor(max_workers=3) as pool:
        grades = [f.result() for f in [pool.submit(ai.structured, system, prompts.shuffle_references(user, k), DrillGrade,
                                                   6000, "high", client) for k in range(3)]]
    ok = [g for g in grades if _snap(item, g.score) >= 1.0]
    best = ok[0] if len(ok) >= 2 else min(grades, key=lambda g: g.score)
    return len(ok) >= 2, best


def accept_answer(progress: dict, item: Item, answer: str) -> None:
    """复核后认定正确的答案加入这道题的参考答案（只对这个学生生效），下次同样的答案直接判对。"""
    extra = progress.setdefault("extra_accepted", {}).setdefault(item.id, [])
    if answer.strip() and answer.strip() not in extra:
        extra.append(answer.strip())
    store.save()


def with_extra_accepted(progress: dict, item: Item) -> Item:
    extra = (progress.get("extra_accepted") or {}).get(item.id)
    return item.model_copy(update={"accepted": item.accepted + extra}) if extra else item



# ---------------- AI 出题 ----------------

class ItemDraft(BaseModel):
    format: str
    difficulty: int
    instruction: str
    content: str
    options: list[str]
    answer: int
    option_explanations: list[str]
    sentences: list[str]
    accepted: list[str]
    criteria: str
    hints: list[str]
    explanation: str
    focus: str = Field(description="这道题练的具体错误类型（中文短语）")


class ItemBatch(BaseModel):
    items: list[ItemDraft]


class ItemCheck(BaseModel):
    index: int = Field(description="题目序号（从 1 开始）")
    ok: bool = Field(description="答案唯一正确、英文无误、提示不泄露答案时为 true")
    problem: str = Field(description="有问题时说明问题；没有则为空字符串")
    also_accept: list[str] = Field(description="改错题：其他同样正确的完整改法；其他题型为空列表")


class ItemCheckBatch(BaseModel):
    results: list[ItemCheck]


class ItemSolve(BaseModel):
    index: int = Field(description="题目序号（从 1 开始）")
    choice: int = Field(description="选择题/当考官：所选选项序号（从 0 开始）；其他题型为 -1")
    acceptable: list[int] = Field(description="选择题/当考官：所有站得住的选项序号；其他题型为空列表")
    order: list[str] = Field(description="排序题：按正确顺序排列的句子字母；其他题型为空列表")
    correction: str = Field(description="改错题：改正后的完整句子；其他题型为空字符串")
    unique: bool = Field(description="是否只有一个站得住的答案")
    note: str = Field(description="简短说明；没有则为空字符串")


class ItemSolveBatch(BaseModel):
    results: list[ItemSolve]


class OptionGuess(BaseModel):
    index: int = Field(description="题目序号（从 1 开始）")
    choice: int = Field(description="只看选项就能确定的答案序号；不能确定填 -1")
    note: str = Field(description="凭什么判断；不能确定时为空字符串")


class OptionGuessBatch(BaseModel):
    results: list[OptionGuess]


SHUFFLE_FOR_SOLVER = True  # 两次盲做用不同的选项顺序（测试里可以关掉，方便写固定答案）


GEN_BATCH = 8     # 每次出几道题（核对后通常只留下一半多：Duolingo 的出题流程保留约 58%）
LOW_WATER = 5     # 某技能没做过的题少于这么多时，后台提前出新题（研究建议保持至少 5 道没见过的题）
PREFETCH_KCS = 4  # 只为接下来最可能出现的几个技能提前出题，避免浪费
LETTERS = "ABCDEFGH"


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", text.lower()))


def too_similar(a: str, b: str, threshold: float = 0.8) -> bool:
    """两段英文的词重合度过高（Jaccard），视为重复题。"""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return a.strip() == b.strip()
    return len(wa & wb) / len(wa | wb) >= threshold


def _item_text(it) -> str:
    return " ".join([it.content, " ".join(it.options), " ".join(it.sentences)]) or it.instruction


def generation_request(progress: dict, kc: str, n: int = GEN_BATCH) -> dict:
    """在主线程里准备出题请求（这里会读学生状态和 session_state）；真正的网络请求见 run_generation。"""
    from . import prompts

    st = mastery.kc_state(progress, kc)
    # 目标难度：让预计正确率接近 TARGET_P（θ - b ≈ 1.1）
    target_b = st["theta"] - 1.1
    difficulty = int(min(5, max(1, round(target_b / 0.8 + 3))))
    bank = [i for i in seed_items() if i.kc == kc]
    examples = list({i.format: i for i in reversed(bank)}.values())[:3]  # 每种题型一个示例
    existing = [_item_text(i) for i in all_items(progress) if i.kc == kc]
    personal = [m["text"] for m in progress["mistakes"]
                if m["kc"] == kc and m.get("text") and m.get("format", "fix") not in AUTO_GRADED][-5:]
    system, user = prompts.item_generation_request(kc, n, difficulty, examples, [t[:160] for t in existing[-40:]],
                                                   personal, (progress.get("profile") or {}).get("level", "高中"))
    return {"kc": kc, "system": system, "user": user, "existing": existing}


def _blind_view(n: int, it: Item, variant: str = "a", with_content: bool = True) -> dict:
    """给盲做的题：去掉答案、解析、提示和参考答案；选项和排序句按 variant 打乱并重新编号。"""
    view = {"index": n, "format": it.format, "instruction": it.instruction}
    if with_content:
        view["content"] = it.content
    if it.format in ("mcq", "judge"):
        perm = list(range(len(it.options)))
        if SHUFFLE_FOR_SOLVER:
            random.Random(f"solve|{variant}|{it.id}").shuffle(perm)
        view["options"] = [f"{j}. {it.options[i]}" for j, i in enumerate(perm)]
        view["_perm"] = perm
    elif it.format == "order":
        order = shuffled_order(it, f"{variant}|{it.id}")
        view["sentences"] = [f"{LETTERS[j]}. {it.sentences[i]}" for j, i in enumerate(order)]
        view["_order"] = order
    return view


def _public(view: dict) -> dict:
    return {k: v for k, v in view.items() if not k.startswith("_")}


def _solve_matches(it: Item, view: dict, solve: ItemSolve | None) -> bool:
    if solve is None or not solve.unique:
        return False
    if it.format in ("mcq", "judge"):
        perm = view["_perm"]
        key = perm.index(it.answer)  # 正确答案在这次展示里的序号
        return solve.choice == key and sorted(set(solve.acceptable) | {solve.choice}) == [key]
    if it.format == "order":
        order = view["_order"]
        try:
            picked = [order[LETTERS.index(x.strip()[:1].upper())] for x in solve.order]
        except (ValueError, IndexError):
            return False
        return picked == list(range(len(it.sentences)))
    if it.format == "fix":
        return normalize(solve.correction) != normalize(it.content)  # 盲做者至少要能发现错误
    return True


def _needs_content(it: Item) -> bool:
    """段落、篇章层的选择题必须读材料才能答：用“只看选项”测试检查有没有线索。"""
    return it.format in ("mcq", "judge") and bool(it.content.strip()) and KCS[it.kc].level != "sentence"


def run_generation(client, req: dict) -> list[dict]:
    """出题 → 程序检查 → 两次独立盲做 + “只看选项”测试 → 审核，全部通过的题才返回。

    可以在后台线程里运行：不读 session_state，只做网络请求和计算。
    依据：未经核对的 AI 题目和提示有相当比例不合格（Pardos & Bhandari 2024）；研究建议让另一个模型
    不看答案、用不同的选项顺序独立作答多次，逐个选项判断是否站得住，答案唯一且与标注一致才保留；
    必须读材料才能答的题，如果只看选项就能猜出答案，说明有线索，要丢掉。
    """
    from concurrent.futures import ThreadPoolExecutor

    from . import prompts

    kc = req["kc"]
    batch = ai.structured(req["system"], req["user"], ItemBatch, max_tokens=16000, effort="medium", client=client)
    existing = list(req["existing"])
    drafts: list[Item] = []
    for d in batch.items:
        digest = hashlib.sha1(f"{kc}|{d.content}|{d.instruction}|{d.options}".encode()).hexdigest()[:10]
        try:
            it = Item(id=f"ai-{kc}-{digest}", kc=kc, source="ai", **d.model_dump())
        except ValueError:
            continue
        if it.format not in KCS[kc].formats or it.problems() or len(it.hints) < 2 or length_cue(it):
            continue
        if it.format in ("mcq", "judge") and len(it.option_explanations) != len(it.options):
            continue  # 每个选项都要有解析（答错时要告诉学生为什么错）
        text = _item_text(it)
        if any(too_similar(text, e) for e in existing):
            continue
        existing.append(text)
        drafts.append(it)
    if not drafts:
        return []
    va = [_blind_view(n, it, "a") for n, it in enumerate(drafts, 1)]
    vb = [_blind_view(n, it, "b") for n, it in enumerate(drafts, 1)]
    content_items = [(n, it) for n, it in enumerate(drafts, 1) if _needs_content(it)]
    vo = {n: _blind_view(n, it, "o", with_content=False) for n, it in content_items}

    def solve(views):
        sys_, user = prompts.item_solve_request(kc, [_public(v) for v in views])
        return {r.index: r for r in ai.structured(sys_, user, ItemSolveBatch, max_tokens=6000, effort="low",
                                                  client=client).results}

    def guess():
        if not vo:
            return {}
        sys_, user = prompts.options_only_request(kc, [_public(v) for v in vo.values()])
        return {r.index: r for r in ai.structured(sys_, user, OptionGuessBatch, max_tokens=3000, effort="low",
                                                  client=client).results}

    with ThreadPoolExecutor(max_workers=3) as pool:  # 三次核对互相独立，同时进行
        fa, fb, fo = pool.submit(solve, va), pool.submit(solve, vb), pool.submit(guess)
        sa, sb, so = fa.result(), fb.result(), fo.result()

    keep = []
    for n, it in enumerate(drafts, 1):
        if not (_solve_matches(it, va[n - 1], sa.get(n)) and _solve_matches(it, vb[n - 1], sb.get(n))):
            continue
        g = so.get(n)
        if n in vo and g is not None and 0 <= g.choice < len(it.options) and vo[n]["_perm"][g.choice] == it.answer:
            continue  # 不看材料也能选对：题目有线索
        keep.append((n, it))
    if not keep:
        return []
    shown = [dict(it.model_dump(exclude={"id", "kc", "source"}), index=i) for i, (_, it) in enumerate(keep, 1)]
    answers = [dict(sa[n].model_dump(exclude={"acceptable"}), index=i) for i, (n, _) in enumerate(keep, 1)]
    for a, (n, it) in zip(answers, keep):  # 换回原始序号，审核者看到的才对得上
        if it.format in ("mcq", "judge"):
            a["choice"] = va[n - 1]["_perm"][sa[n].choice]
        elif it.format == "order":
            a["order"] = [str(va[n - 1]["_order"][LETTERS.index(x.strip()[:1].upper())]) for x in sa[n].order]
    vsys, vuser = prompts.item_check_request(kc, shown, answers)
    checks = {c.index: c for c in ai.structured(vsys, vuser, ItemCheckBatch, max_tokens=6000, effort="low",
                                                client=client).results}
    made = []
    for i, (_, it) in enumerate(keep, 1):
        c = checks.get(i)
        if c is None or not c.ok:  # 核对失败或漏掉的题一律不用（宁可少出题）
            continue
        if it.format == "fix":
            extra = [a for a in c.also_accept if a.strip() and normalize(a) != normalize(it.content)]
            it = it.model_copy(update={"accepted": list(dict.fromkeys(it.accepted + extra))})
        made.append(it.model_dump())
    return made


def add_generated(progress: dict, raw: list[dict]) -> list[Item]:
    """把核对通过的新题加入题库（主线程调用）。"""
    existing = {x["id"] for x in progress["ai_items"]} | {i.id for i in seed_items()}
    made = []
    for r in raw:
        try:
            it = Item.model_validate(r)
        except ValueError:
            continue
        if it.id not in existing and not it.problems():
            existing.add(it.id)
            made.append(it)
    progress["ai_items"].extend(i.model_dump() for i in made)
    store.save()
    return made


def generate_items(progress: dict, kc: str, n: int = GEN_BATCH) -> list[Item]:
    """同步出题（等待结果）。刷题页通常用 jobs 在后台提前出题。"""
    return add_generated(progress, run_generation(ai.client(), generation_request(progress, kc, n)))


# ---------------- 记录作答 ----------------

def _day_stats(progress: dict) -> dict:
    return progress["days"].setdefault(store.today(), {"items": 0, "solo_correct": 0})


def add_mistake(progress: dict, kc: str, text: str, note: str, source: str,
                item: Item | None = None, personal_item: dict | None = None) -> dict:
    when = store.now()
    card = mastery.review_card(progress, None, mastery.Rating.Again, when)
    card["due"] = (when + timedelta(days=1)).isoformat()
    m = {
        "id": hashlib.sha1(f"{kc}|{text}|{when.isoformat()}".encode()).hexdigest()[:12],
        "kc": kc, "text": text, "note": note, "source": source,
        "item_id": item.id if item else (personal_item or {}).get("id"),
        "item": personal_item, "personal_done": False,
        "format": item.format if item else (personal_item or {}).get("format", "fix"),
        "focus": item.focus if item else (personal_item or {}).get("focus", ""),
        "created": when.isoformat(), "card": card, "reviews_ok": [], "retired": False,
    }
    progress["mistakes"].append(m)
    return m


def review_mistake(progress: dict, mistake: dict, item: Item, correct: bool, solo: bool,
                   when: datetime | None = None) -> None:
    when = when or store.now()
    day = store.study_day(when).isoformat()
    if mistake.get("item") and item.id == mistake["item"]["id"] and correct:
        mistake["personal_done"] = True
    rating = mastery.Rating.Good if (correct and solo) else mastery.Rating.Again
    mistake["card"] = mastery.review_card(progress, mistake["card"], rating, when)
    if correct and solo and (not mistake["reviews_ok"] or mistake["reviews_ok"][-1] < day):
        mistake["reviews_ok"].append(day)
    if not (correct and solo):
        mistake["reviews_ok"] = []
    if len(mistake["reviews_ok"]) >= retire_after(mistake["kc"]):
        mistake["retired"] = True


def answer_text(item: Item, response) -> str:
    """把学生的作答转成可读文字（写进错题本）。"""
    if item.format in ("mcq", "judge"):
        chosen = item.options[response] if isinstance(response, int) and 0 <= response < len(item.options) else "（未作答）"
        return f"{item.content}\n我的选择：{chosen}".strip()
    if item.format == "order":
        order = [item.sentences[i] for i in (response or []) if 0 <= i < len(item.sentences)]
        return "我的顺序：" + " / ".join(order)
    return str(response or "")


def finish_item(progress: dict, session: dict, item: Item, score: float, hints: int, revealed: bool,
                confidence: str | None, seconds: float, mistake: dict | None, answer: str, wrong: int = 0) -> dict:
    """一道题结束（答对或看了答案）时调用：更新掌握度、错题本、本次练习队列。

    hints：看了几级提示；wrong：答错了几次后才做对。两者都算“有帮助”。
    """
    correct = score >= 0.8 and not revealed
    assisted = hints + wrong
    solo = assisted == 0 and not revealed
    missed = not correct or wrong > 0  # 中途答错过，即使后来改对了，也要再测
    confident = {"有把握": True, "不太确定": False, "猜的": False}.get(confidence or "")
    kc_st = mastery.record(progress, item, score, assisted, revealed, confident, seconds,
                           require_production=production_needed(progress, item.kc, session.get("ai_ready", True),
                                                                exclude=set(session["seen"]) | {item.id}))
    progress["attempts"].append({
        "t": store.now().isoformat(), "item": item.id, "kc": item.kc, "format": item.format,
        "focus": item.focus, "score": round(score, 2), "hints": hints, "wrong": wrong, "revealed": revealed,
        "confidence": confidence,
        "seconds": round(seconds, 1), "mode": session["mode"],
    })
    day = _day_stats(progress)
    day["items"] += 1
    day["done"] = day.get("done", 0) + int(not revealed)  # 连续学习天数只算没看答案的题
    day["solo_correct"] += int(correct and solo)

    if mistake:
        review_mistake(progress, mistake, item, correct, solo)
    elif not correct or hints >= 2 or (wrong and confident):
        add_mistake(progress, item.kc, answer, item.explanation[:200], "drill", item=item)

    session["count"] += 1
    session["correct"] += int(correct and solo)
    session["seen"].append(item.id)
    session["recent_kcs"].append(item.kc)
    session["requeue"] = [r for r in session["requeue"] if not (r["kc"] == item.kc and r["after"] <= session["count"] - 1)]
    if missed:
        times = sum(1 for x in session["log"] if x["kc"] == item.kc and x.get("missed", not x["correct"]))
        if times < MAX_REQUEUE:
            # 有把握却答错（高信心错误）更早再测（Metcalfe 2017：这类错误最容易被纠正）
            gap = 1 if confident else REQUEUE_GAP
            session["requeue"].append({"kc": item.kc, "after": session["count"] + gap, "focus": item.focus})
    session["log"].append({"kc": item.kc, "item": item.id, "correct": correct, "solo": solo, "score": score,
                           "missed": missed, "reason": (session.get("current") or {}).get("reason", "")})
    store.save()
    return kc_st


def flag_item(progress: dict, item_id: str) -> None:
    progress.setdefault("flagged_items", []).append(item_id)
    for m in progress["mistakes"]:  # 被报告的“自己的句子”题不再出现，错题改用同类题复习
        if m.get("item") and m["item"]["id"] == item_id:
            m["personal_done"] = True
    store.save()


# ---------------- 连续学习天数 ----------------

MEANINGFUL_ITEMS = 10


def _qualifies(progress: dict, d) -> bool:
    rec = progress["days"].get(d.isoformat(), {})
    return rec.get("done", rec.get("items", 0)) >= MEANINGFUL_ITEMS


def streak(progress: dict) -> tuple[int, bool]:
    """连续学习天数：每天完成至少 10 题（不含看答案的题）才算；每连续 7 天可以用 1 次“补签”跳过一天。
    今天还没达标时从昨天算起。返回 (天数, 今天是否已达标)。"""
    today = store.study_day()
    met_today = _qualifies(progress, today)
    d = today if met_today else today - timedelta(days=1)
    count = freezes = 0
    for _ in range(3650):
        if _qualifies(progress, d):
            count += 1
        elif freezes < 1 + count // 7 and _qualifies(progress, d - timedelta(days=1)):
            freezes += 1  # 只断了一天、前一天有练习：用补签接上
        else:
            break
        d -= timedelta(days=1)
    return count, met_today


def daily_goal(progress: dict) -> int:
    minutes = (progress.get("profile") or {}).get("minutes_per_day", 20)
    return max(MEANINGFUL_ITEMS, int(minutes * 0.8))


def kc_rule_card(kc: str) -> str:
    return rule_cards().get(kc, "")


FORMAT_LABELS = FORMATS
