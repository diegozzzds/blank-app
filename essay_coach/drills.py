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

import hashlib
import re
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from . import ai, mastery, store
from .items import Item, rule_cards, seed_items, shuffled_order
from .skills import AUTO_GRADED, FORMATS, KCS

TARGET_P = 0.75
REQUEUE_GAP = 2
MAX_REQUEUE = 2
MISTAKE_RETIRE_REVIEWS = 3


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


def fresh_items(progress: dict, kc: str, exclude: set[str] = frozenset(), ai_ready: bool = True) -> list[Item]:
    """这个学生从没做过的题。"""
    return [i for i in all_items(progress) if i.kc == kc and i.id not in exclude and i.id not in progress["items"]
            and (ai_ready or not needs_ai(i))]


def _last_focus(progress: dict, kc: str) -> str:
    for a in reversed(progress["attempts"][-50:]):
        if a.get("kc") == kc:
            return a.get("focus", "")
    return ""


def pick_item(progress: dict, kc: str, exclude: set[str], ai_ready: bool, allow_repeat: bool = True,
              focus: str = "") -> Item | None:
    """为技能 kc 选一道题：没做过的优先，难度最接近目标正确率。

    focus：再测刚做错的题或复习错题时，优先选同一类错误（同一子类）的新题；
    没指定时，优先换一个和上一题不同的子类（技能内部也交错练习）。
    没做过的题用完时，allow_repeat=False 返回 None（由调用方让 AI 出新题）；
    allow_repeat=True 时重复旧题，最久没见过的优先。
    """
    level = (progress.get("profile") or {}).get("level")
    target = 0.8 if level == "初中" else TARGET_P
    last = "" if focus else _last_focus(progress, kc)

    def focus_rank(i: Item) -> int:
        if focus:
            return 0 if i.focus == focus else 1
        return 1 if last and i.focus == last else 0

    fresh = fresh_items(progress, kc, exclude, ai_ready)
    if fresh:
        return min(fresh, key=lambda i: (focus_rank(i), abs(mastery.p_correct(progress, i) - target), i.id))
    if not allow_repeat:
        return None
    candidates = [i for i in all_items(progress) if i.kc == kc and i.id not in exclude]
    if not ai_ready:
        candidates = [i for i in candidates if not needs_ai(i)]
    if not candidates:
        return None
    seen_at = _last_seen(progress)
    return min(candidates, key=lambda i: (seen_at.get(i.id, ""), focus_rank(i), abs(mastery.p_correct(progress, i) - target),
                                          i.id))


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
        if k in KCS:
            out.append((k, "上篇作文的弱项", None))
    for k in current_week_kcs(progress):
        out.append((k, "本周学习目标", None))
    # 补充最薄弱的可学技能；离线时跳过已经没有可做题目的技能，避免练习提前结束
    seen = set(session["seen"])
    added = 0
    for k in weakest_unlocked(progress, [c[0] for c in out]):
        if added >= 6:
            break
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

    def rank(c):
        return (c[0] in waiting and not c[1].startswith("再测"), _too_repetitive(session, c[0]))

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
            it = pick_item(progress, kc, seen, ai_ready, allow_repeat=allow_repeat, focus=focus_of(kc, reason, mistake))
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
            and len(fresh_items(progress, kc, seen)) <= LOW_WATER]


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
    score: float = Field(description="0–1：1 = 完全达到要求，0.5 = 部分达到，0 = 没有达到")
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


def grade_open(item: Item, response: str, attempt_no: int, hints_used: list[str]) -> DrillGrade:
    from . import prompts

    system, user = prompts.drill_grade_request(item, response, attempt_no, hints_used)
    return ai.structured(system, user, DrillGrade, max_tokens=6000, effort="low")


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
    order: list[str] = Field(description="排序题：按正确顺序排列的句子字母；其他题型为空列表")
    correction: str = Field(description="改错题：改正后的完整句子；其他题型为空字符串")
    unique: bool = Field(description="是否只有一个站得住的答案")
    note: str = Field(description="简短说明；没有则为空字符串")


class ItemSolveBatch(BaseModel):
    results: list[ItemSolve]


GEN_BATCH = 6     # 每次出几道题（核对后通常会少一些）
LOW_WATER = 3     # 某技能没做过的题只剩这么多时，后台提前出新题
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


def _blind_view(n: int, it: Item) -> dict:
    """给盲做的题：去掉答案、解析、提示和参考答案；排序题打乱并标上字母。"""
    view = {"index": n, "format": it.format, "instruction": it.instruction, "content": it.content}
    if it.format in ("mcq", "judge"):
        view["options"] = [f"{i}. {o}" for i, o in enumerate(it.options)]
    elif it.format == "order":
        order = shuffled_order(it, it.id)
        view["sentences"] = [f"{LETTERS[j]}. {it.sentences[i]}" for j, i in enumerate(order)]
        view["_order"] = order
    return view


def _solve_matches(it: Item, view: dict, solve: ItemSolve | None) -> bool:
    if solve is None or not solve.unique:
        return False
    if it.format in ("mcq", "judge"):
        return solve.choice == it.answer
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


def run_generation(client, req: dict) -> list[dict]:
    """出题 → 程序检查 → 盲做比对 → 审核，全部通过的题才返回。

    可以在后台线程里运行：不读 session_state，只做网络请求和计算。
    依据：未经核对的 AI 题目和提示有相当比例不合格（Pardos & Bhandari 2024）；
    让另一个模型不看答案独立作答、与标注答案比对，是发现“答案错误/不唯一”的常用做法。
    """
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
        if it.format not in KCS[kc].formats or it.problems() or len(it.hints) < 2:
            continue
        text = _item_text(it)
        if any(too_similar(text, e) for e in existing):
            continue
        existing.append(text)
        drafts.append(it)
    if not drafts:
        return []
    views = [_blind_view(n, it) for n, it in enumerate(drafts, 1)]
    ssys, suser = prompts.item_solve_request(kc, [{k: v for k, v in x.items() if not k.startswith("_")} for x in views])
    solves = {r.index: r for r in ai.structured(ssys, suser, ItemSolveBatch, max_tokens=6000, effort="low",
                                                client=client).results}
    blind_ok = {n for n, (it, v) in enumerate(zip(drafts, views), 1) if _solve_matches(it, v, solves.get(n))}
    keep = [(n, it) for n, it in enumerate(drafts, 1) if n in blind_ok]
    if not keep:
        return []
    shown = [dict(it.model_dump(exclude={"id", "kc", "source"}), index=i) for i, (_, it) in enumerate(keep, 1)]
    answers = [dict(solves[n].model_dump(), index=i) for i, (n, _) in enumerate(keep, 1)]
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
    if len(mistake["reviews_ok"]) >= MISTAKE_RETIRE_REVIEWS:
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
    kc_st = mastery.record(progress, item, score, assisted, revealed, confident, seconds)
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
                           "missed": missed})
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
