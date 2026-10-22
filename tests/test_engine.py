"""刷题引擎、掌握度、学习大纲校验、存储迁移的单元测试（不联网）。"""

from datetime import datetime, timedelta, timezone

import pytest

from essay_coach import drills, mastery, planner, store
from essay_coach.items import Item, seed_items
from essay_coach.skills import KCS, topo_order

T0 = datetime(2026, 10, 14, 8, tzinfo=timezone.utc)


@pytest.fixture
def progress(monkeypatch):
    monkeypatch.setattr(store, "save", lambda: None)
    p = store.new_progress()
    p["profile"] = {"level": "高中", "exam": "ielts", "minutes_per_day": 20}
    return p


def bank(kc):
    return [i for i in seed_items() if i.kc == kc]


def synth(kc, n, fmt="mcq", start=0):
    """造 n 道不同的题（测试掌握度时每题只能算一次证据）。"""
    base = bank(kc)[0]
    return [base.model_copy(update={"id": f"{kc}-syn-{fmt}-{start + i}", "format": fmt,
                                    "accepted": ["x"] if fmt == "fix" else base.accepted,
                                    "content": base.content or "c"}) for i in range(n)]


def test_skill_graph_is_acyclic_and_ordered():
    order = topo_order()
    assert sorted(order) == sorted(KCS)
    for k in order:
        for p in KCS[k].prereqs:
            assert order.index(p) < order.index(k)


def test_learned_then_retained_then_transferred(progress):
    items = synth("sent_boundary", 10)
    st = mastery.record(progress, items[0], 0.0, 0, False, True, 20, when=T0)  # 一开始错了一题：要连续对 5 题
    for n in range(1, 5):
        st = mastery.record(progress, items[n], 1.0, 0, False, True, 20, when=T0 + timedelta(minutes=n))
    assert st["tier"] == "learning"
    st = mastery.record(progress, items[5], 1.0, 0, False, True, 20, when=T0 + timedelta(minutes=5))
    assert st["tier"] == "learned"
    st = mastery.record(progress, items[1], 1.0, 0, False, True, 20, when=T0 + timedelta(days=2))
    assert st["reviews_ok"] == []  # 复习做的是见过的题：不算巩固
    for n, d in enumerate((3, 5, 8)):
        st = mastery.record(progress, items[6 + n], 1.0, 0, False, True, 20, when=T0 + timedelta(days=d))
    assert st["tier"] == "retained"
    mastery.mark_transfer(progress, "sent_boundary", True)
    assert progress["kc"]["sent_boundary"]["tier"] == "transferred"


def test_assisted_answers_do_not_build_streak(progress):
    item = bank("articles")[0]
    st = mastery.record(progress, item, 1.0, 2, False, None, 60, when=T0)
    assert st["streak"] == 0 and st["help_n"] == 1 and st["solo_n"] == 0
    st = mastery.record(progress, bank("articles")[1], 0.0, 0, True, None, 60, when=T0)
    assert st["ema"] < 0.3


def test_interval_capped_by_exam_date(progress):
    progress["profile"]["exam_date"] = (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat()
    card = None
    when = datetime.now(timezone.utc)
    for _ in range(6):
        card = mastery.review_card(progress, card, mastery.Rating.Easy, when)
        due = datetime.fromisoformat(card["due"])
        assert (due - when).days <= 2  # 10 天 × 20%
        when = due


def test_exam_date_in_past_does_not_crash(progress):
    progress["profile"]["exam_date"] = "2020-01-01"
    card = mastery.review_card(progress, None, mastery.Rating.Good, T0)
    assert card["due"]


def test_wrong_answer_requeues_skill_after_gap(progress):
    session = drills.new_session("kc", "articles")
    first, *_ = drills.next_item(progress, session, ai_ready=False)
    drills.finish_item(progress, session, first, 0.0, 0, True, None, 10, None, "x")
    assert session["requeue"] == [{"kc": "articles", "after": 1 + drills.REQUEUE_GAP, "focus": first.focus}]
    assert len(progress["mistakes"]) == 1
    seen = [first.id]
    for _ in range(3):
        it, reason, *_ = drills.next_item(progress, session, ai_ready=False)
        assert it.id not in seen
        seen.append(it.id)
        drills.finish_item(progress, session, it, 1.0, 0, False, "有把握", 10, None, "")
    assert session["requeue"] == []


def test_confident_error_requeued_sooner(progress):
    session = drills.new_session("kc", "articles")
    it, *_ = drills.next_item(progress, session, ai_ready=False)
    drills.finish_item(progress, session, it, 0.0, 1, False, "有把握", 10, None, "x")
    assert session["requeue"][0]["after"] == session["count"] + 1


def test_mistake_retires_after_three_days(progress):
    item = bank("thesis")[0]
    m = drills.add_mistake(progress, "thesis", "bad thesis", "note", "drill", item=item)
    drills.review_mistake(progress, m, bank("thesis")[1], True, True, when=T0)
    drills.review_mistake(progress, m, bank("thesis")[2], True, True, when=T0 + timedelta(hours=1))  # 同一天不重复计
    assert len(m["reviews_ok"]) == 1
    drills.review_mistake(progress, m, bank("thesis")[1], True, True, when=T0 + timedelta(days=2))
    assert not m["retired"]
    drills.review_mistake(progress, m, bank("thesis")[3], True, True, when=T0 + timedelta(days=6))
    assert m["retired"]


def test_mistake_wrong_review_resets(progress):
    m = drills.add_mistake(progress, "thesis", "bad thesis", "note", "drill", item=bank("thesis")[0])
    drills.review_mistake(progress, m, bank("thesis")[1], True, True, when=T0)
    drills.review_mistake(progress, m, bank("thesis")[2], False, True, when=T0 + timedelta(days=1))
    assert m["reviews_ok"] == [] and not m["retired"]


def test_interleaving_avoids_three_in_a_row(progress):
    progress["plan"] = {"weeks": [{"kcs": ["articles", "sent_boundary"]}], "current_week": 0}
    session = drills.new_session("today")
    kcs = []
    for _ in range(8):
        it, *_ = drills.next_item(progress, session, ai_ready=False)
        kcs.append(it.kc)
        drills.finish_item(progress, session, it, 1.0, 0, False, None, 10, None, "")
    assert not any(kcs[i] == kcs[i + 1] == kcs[i + 2] for i in range(len(kcs) - 2))


def test_fix_grading_normalizes_but_rejects_unchanged():
    item = bank("sent_boundary")[-1]
    assert item.format == "fix"
    assert drills.grade_auto(item, "It is late; we should go home")[0] == 1.0
    assert drills.grade_auto(item, "  It is late,  so we should go home. ")[0] == 1.0
    assert drills.grade_auto(item, "it is late, so we should go home")[0] == -1.0  # 大小写不同：交给 AI
    assert drills.grade_auto(item, "It is late , so we should go home .")[0] == -1.0
    assert drills.grade_auto(item, item.content)[0] == 0.0
    assert drills.grade_auto(item, "It is late, we should went home.")[0] == -1.0  # 需要 AI 判分


def test_order_partial_credit():
    item = next(i for i in seed_items() if i.format == "order")
    assert drills.grade_auto(item, [0, 1, 2])[0] == 1.0
    assert 0 < drills.grade_auto(item, [1, 2, 0])[0] < 1
    assert drills.grade_auto(item, [0, 1])[0] == 0.0


def test_streak_with_freeze(progress):
    today = store.study_day()
    for d in (0, 1, 3, 4):  # 第 2 天没练：用补签
        progress["days"][(today - timedelta(days=d)).isoformat()] = {"items": 12, "solo_correct": 8}
    count, met = drills.streak(progress)
    assert met and count == 4


def test_ai_plan_is_repaired(progress):
    # 结构化输出已经限制了技能 id；这里用 model_construct 绕过校验，测试程序侧的兜底修复
    week = lambda title, kcs: planner.WeekPlan.model_construct(  # noqa: E731
        title=title, kcs=kcs, goals=["g"], why="y", lesson_focus="l", essay_task="e", checkpoint=False)
    bad = planner.StudyPlan.model_construct(overview="o", daily_routine="d", milestones=[], weeks=[
        week("w1", ["critical_questions", "made_up", "articles"]),
        week("w2", ["prompt_analysis", "thesis", "topic_sentence", "support_evidence"]),
    ])
    plan, notes = planner.validate_plan(progress, bad)
    seen: set[str] = set()
    for w in plan["weeks"]:
        assert len(w["kcs"]) <= planner.MAX_KCS_PER_WEEK
        for k in w["kcs"]:
            assert k in KCS
            assert all(p in seen or p in w["kcs"] for p in KCS[k].prereqs)
        seen.update(w["kcs"])
    assert "made_up" not in seen and "critical_questions" not in seen
    assert any("made_up" in n for n in notes)
    assert plan["weeks"][1]["checkpoint"]


def test_baseline_plan_respects_prerequisites(progress):
    plan = planner.baseline_plan(progress)
    seen: set[str] = set()
    for w in plan["weeks"]:
        for k in w["kcs"]:
            assert all(p in seen or p in w["kcs"] for p in KCS[k].prereqs)
        seen.update(w["kcs"])


def test_migrate_keeps_known_keys_only():
    data = {"kc": {"articles": {"tier": "learning"}}, "attempts": [], "evil": "x", "version": 1}
    p = store._migrate(data)
    assert "evil" not in p and p["version"] == store.SCHEMA_VERSION and p["kc"]["articles"]["tier"] == "learning"


def test_items_problem_checks():
    good = bank("articles")[0]
    assert good.problems() == []
    bad = Item(**{**good.model_dump(), "answer": 9})
    assert bad.problems()
    personal = Item(id="me-x", kc="articles", format="fix", difficulty=3, instruction="i", content="I have a apple.",
                    source="personal")
    assert personal.problems() == [] and drills.needs_ai(personal)


def test_personal_fix_that_only_changes_spacing_is_not_called_unchanged():
    item = Item(id="me-1", kc="punctuation", format="fix", difficulty=3, instruction="i",
                content="In my opinion , i believe technology is good.", source="personal")
    assert drills.grade_auto(item, "In my opinion, I believe technology is good.")[0] == -1.0


def test_corrected_after_wrong_attempt_is_still_retested(progress):
    session = drills.new_session("kc", "articles")
    it, *_ = drills.next_item(progress, session, ai_ready=False)
    drills.finish_item(progress, session, it, 1.0, 0, False, "有把握", 10, None, "x", wrong=1)
    assert [(r["kc"], r["after"]) for r in session["requeue"]] == [("articles", session["count"] + 1)]
    assert len(progress["mistakes"]) == 1  # 有把握却答错过：记入错题本
    assert progress["kc"]["articles"]["streak"] == 0


def test_empty_plan_does_not_crash(progress):
    progress["plan"] = {"weeks": [], "current_week": 0}
    session = drills.new_session("today")
    it, *_ = drills.next_item(progress, session, ai_ready=False)
    assert it is not None


def test_strong_student_still_gets_a_plan(progress):
    progress["diagnostic"] = {"strong_kcs": list(KCS), "criterion_gap": {c: 0.1 for c in
                              ("task", "argument", "coherence", "lexis", "grammar")}}
    assert planner.baseline_plan(progress)["weeks"]


def test_retained_needs_real_gap_not_just_midnight(progress):
    items = synth("sent_boundary", 8)
    for n in range(3):  # 一开始就连续答对 3 题：已学会
        mastery.record(progress, items[n], 1.0, 0, False, True, 20, when=T0 + timedelta(minutes=n))
    st = progress["kc"]["sent_boundary"]
    assert st["tier"] == "learned"
    late = T0.replace(hour=15, minute=58)  # 北京时间 23:58
    mastery.record(progress, items[3], 1.0, 0, False, True, 20, when=late + timedelta(days=1))
    mastery.record(progress, items[4], 1.0, 0, False, True, 20, when=late + timedelta(days=1, minutes=5))
    mastery.record(progress, items[5], 1.0, 0, False, True, 20, when=late + timedelta(days=1, minutes=10))
    assert st["tier"] == "learned" and len(st["reviews_ok"]) == 1


def test_streak_freeze_covers_yesterday(progress):
    today = store.study_day()
    for d in range(2, 9):
        progress["days"][(today - timedelta(days=d)).isoformat()] = {"items": 12, "done": 12, "solo_correct": 5}
    count, met = drills.streak(progress)
    assert not met and count == 7


def test_revealed_items_do_not_count_for_streak(progress):
    today = store.study_day()
    progress["days"][today.isoformat()] = {"items": 12, "done": 4, "solo_correct": 0}
    assert drills.streak(progress) == (0, False)


def test_flagged_personal_item_not_served_again(progress):
    personal = {"id": "me-x", "kc": "articles", "format": "fix", "difficulty": 3, "instruction": "i",
                "content": "I have a apple.", "source": "personal"}
    m = drills.add_mistake(progress, "articles", "I have a apple.", "n", "essay", personal_item=personal)
    m["card"]["due"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    drills.flag_item(progress, "me-x")
    it, reason, *_ = drills.next_item(progress, drills.new_session("mistakes"), ai_ready=True)
    assert it.id != "me-x"


def test_offline_due_mistakes_only_counts_servable(progress):
    m = drills.add_mistake(progress, "hedging", "x", "n", "drill")  # 测试题库里没有 hedging 的题
    m["card"]["due"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    assert drills.due_mistakes(progress, ai_ready=False) == []
    assert len(drills.due_mistakes(progress, ai_ready=True)) == 1


def test_answer_text_is_readable():
    item = bank("articles")[0]
    assert item.options[1] in drills.answer_text(item, 1)


def test_assisted_correct_does_not_raise_mastery(progress):
    item = bank("articles")[0]
    before = mastery.kc_state(progress, "articles")["theta"]
    st = mastery.record(progress, item, 1.0, 1, False, None, 30, when=T0)
    assert st["theta"] <= before and st["ema"] == 0.0


def test_ai_score_just_above_threshold_counts_as_correct(progress):
    items = synth("thesis", 3, "write")
    for n in range(3):
        st = mastery.record(progress, items[n], 0.8, 0, False, None, 30, when=T0 + timedelta(minutes=n))
    assert st["streak"] == 3 and st["tier"] == "learned"


def test_failed_review_resets_retention_progress(progress):
    items = synth("sent_boundary", 6)
    for n in range(3):
        mastery.record(progress, items[n], 1.0, 0, False, True, 20, when=T0 + timedelta(minutes=n))
    st = mastery.record(progress, items[3], 1.0, 0, False, True, 20, when=T0 + timedelta(days=2))
    assert len(st["reviews_ok"]) == 1
    st = mastery.record(progress, items[4], 0.0, 0, False, True, 20, when=T0 + timedelta(days=4))
    assert st["reviews_ok"] == [] and st["tier"] == "learned"


def test_old_cards_are_pulled_before_exam(progress):
    card = mastery.review_card(progress, None, mastery.Rating.Good, T0)
    card["due"] = (T0 + timedelta(days=60)).isoformat()
    progress["profile"]["exam_date"] = (T0 + timedelta(days=10)).date().isoformat()
    assert mastery.effective_due(card, progress) < T0 + timedelta(days=10)


def test_requeued_skill_waits_for_intervening_items(progress):
    progress["plan"] = {"weeks": [{"kcs": ["articles", "sent_boundary", "thesis"]}], "current_week": 0}
    session = drills.new_session("today")
    it, *_ = drills.next_item(progress, session, ai_ready=False)
    drills.finish_item(progress, session, it, 0.0, 0, True, None, 10, None, "x")
    nxt, *_ = drills.next_item(progress, session, ai_ready=False)
    assert nxt.kc != it.kc


def test_baseline_schedules_dependents_of_strong_prerequisites(progress):
    progress["diagnostic"] = {"strong_kcs": ["prompt_analysis"], "weak_kcs": ["thesis"],
                              "criterion_gap": {"task": 0.1}}
    plan = planner.baseline_plan(progress)
    assert any("thesis" in w["kcs"] for w in plan["weeks"])


def test_migrate_drops_unknown_skills_and_bad_types():
    data = {"kc": {"gone_skill": {"tier": "learned"}, "articles": {"tier": "learning"}}, "attempts": "oops",
            "plan": {"weeks": [{"kcs": ["gone_skill", "thesis"]}]}, "focus_kcs": ["gone_skill"], "mistakes": [1, 2]}
    p = store._migrate(data)
    assert list(p["kc"]) == ["articles"] and p["attempts"] == [] and p["mistakes"] == []
    assert p["plan"]["weeks"][0]["kcs"] == ["thesis"] and p["focus_kcs"] == []


def test_ap_rubric_maps_to_criteria():
    from essay_coach.essays import _criterion_gaps
    from essay_coach.rubrics import RUBRICS
    crit = [{"name": c["name"], "score": 0, "max_score": c["max"]} for c in RUBRICS["ap_argument"]["criteria"]]
    assert _criterion_gaps("ap_argument", crit)


def test_generated_items_fail_closed(progress, monkeypatch):
    import fake_claude
    made = drills.generate_items(progress, "hedging")
    assert len(made) == 1  # 第 2 题核对未通过
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemCheckBatch", lambda req: {"results": []})  # 核对漏掉了所有题
    assert drills.generate_items(progress, "register") == []


def test_old_cards_respect_shorter_interval_after_exam_moves_closer(progress):
    now = datetime.now(timezone.utc)
    card = mastery.review_card(progress, None, mastery.Rating.Good, now)
    card["due"] = (now + timedelta(days=40)).isoformat()  # 以前没有考试日期时排得很远
    progress["profile"]["exam_date"] = (store.study_day() + timedelta(days=50)).isoformat()
    assert mastery.effective_due(card, progress) <= now + timedelta(days=10, minutes=1)  # 50 天 × 20%


def test_repaired_weeks_get_matching_goals(progress):
    week = lambda title, kcs: planner.WeekPlan.model_construct(  # noqa: E731
        title=title, kcs=kcs, goals=["g"], why="y", lesson_focus="l", essay_task="e", checkpoint=False)
    plan = planner.StudyPlan.model_construct(overview="o", daily_routine="d", milestones=[], weeks=[
        week("w1", ["articles", "sent_boundary"]),
        week("w2", ["prompt_analysis", "thesis", "topic_sentence", "support_evidence", "critical_questions"]),
    ])
    original = [set(w.kcs) for w in plan.weeks]
    plan, notes = planner.validate_plan(progress, plan)
    for w, orig in zip(plan["weeks"], original):
        if set(w["kcs"]) == orig:
            assert w["goals"] == ["g"]  # 没改动的周保留 AI 写的目标
        else:  # 改动过的周：目标按实际安排的技能重写
            assert w["goals"] == [f"学会：{KCS[k].desc}" for k in w["kcs"]]
    assert any(set(w["kcs"]) != o for w, o in zip(plan["weeks"], original))
    assert not any("顺延到下一周" in n and n.startswith(f"第 {len(plan['weeks'])} 周") for n in notes)


class _FakeSt:
    """store 只用到 session_state / sidebar / toast，这里用最小的替身代替真实的 Streamlit 运行时。"""

    def __init__(self):
        import contextlib

        self.session_state = {}
        self.sidebar = contextlib.nullcontext()
        self.toast = lambda *a, **k: None


@pytest.fixture
def browser(monkeypatch):
    fake = _FakeSt()
    calls = []
    replies = {}

    def js_eval(expr, key):
        calls.append((key, expr))
        reply = replies.get(key.split("_")[1] if key.startswith("ls_save") else key)
        return reply(expr) if callable(reply) else reply

    monkeypatch.setattr(store, "st", fake)
    monkeypatch.setattr(store, "_js_eval", js_eval)
    return fake.session_state, calls, replies


def test_late_storage_reply_does_not_overwrite_saved_history(browser):
    import json

    ss, calls, replies = browser
    for _ in range(store.MAX_LOAD_TRIES):
        store.sync()
    assert store.status() == "waiting"
    ss["progress"]["profile"] = {"level": "高中"}
    ss["progress"]["attempts"].append({"item": "x"})
    store.save()
    store.flush()
    saved = dict(store.new_progress(), attempts=[{"item": "old"}] * 5, rev=7)
    replies["ls_load"] = json.dumps({"v": json.dumps(saved)})
    store.sync()
    store.flush()
    assert len(ss["progress"]["attempts"]) == 5 and ss["_ls_session_backup"]
    assert not [k for k, _ in calls if k.startswith("ls_save")]  # 等待期间那份记录没有写进浏览器
    store.save()
    store.flush()
    assert "r > 7" in calls[-1][1]


def test_other_tab_saved_newer_record_pauses_writes(browser):
    import json

    ss, calls, replies = browser
    replies["ls_load"] = json.dumps({"v": json.dumps(dict(store.new_progress(), rev=3))})
    store.sync()
    replies["save"] = 1
    store.save()
    store.flush()
    assert ss["_ls_base_rev"] == 4 and store.status() == "ok"
    replies["save"] = -2  # 另一个标签页已经存了更新的版本
    store.save()
    store.flush()
    assert store.status() == "conflict"
    n = len(calls)
    store.save()
    store.flush()
    assert len(calls) == n  # 冲突后不再写入


def test_save_prunes_chat_and_retired_mistakes(browser):
    ss, *_ = browser
    ss["progress"] = store.new_progress()
    p = ss["progress"]
    p["chat"] = [{"role": "user", "content": str(i)} for i in range(store.MAX_CHAT + 50)]
    p["mistakes"] = [{"kc": "articles", "card": {}, "retired": True, "n": i} for i in range(store.MAX_RETIRED_MISTAKES + 20)]
    p["mistakes"].insert(0, {"kc": "articles", "card": {}, "retired": False, "n": -1})
    store.save()
    assert len(p["chat"]) == store.MAX_CHAT and p["chat"][-1]["content"] == str(store.MAX_CHAT + 49)
    assert sum(m["retired"] for m in p["mistakes"]) == store.MAX_RETIRED_MISTAKES
    assert p["mistakes"][0]["n"] == -1  # 还没移出错题本的错题保留


def _gen_req(progress, kc="hedging"):
    return drills.generation_request(progress, kc)


def test_blind_solver_disagreement_drops_item(progress, monkeypatch):
    import fake_claude

    # 盲做者第 1 题选了别的选项：说明答案可能有问题，这题不能用
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemSolveBatch", lambda req: {"results": [
        {"index": 1, "choice": 0, "acceptable": [0], "order": [], "correction": "", "unique": True, "note": ""},
        {"index": 2, "choice": 0, "acceptable": [0], "order": [], "correction": "", "unique": True, "note": ""}]})
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemCheckBatch", lambda req: {"results": [
        {"index": 1, "ok": True, "problem": "", "also_accept": []}]})
    made = drills.run_generation(fake_claude.FakeClient(), _gen_req(progress))
    assert [m["instruction"] for m in made] == ["第二题"]
    # 审核只看到通过盲做的题
    assert "选出正确的句子" not in json_dump(fake_claude.CALLS[-1]["messages"])


def test_solver_flags_ambiguity(progress, monkeypatch):
    import fake_claude

    monkeypatch.setitem(fake_claude.SAMPLES, "ItemSolveBatch", lambda req: {"results": [
        {"index": 1, "choice": 2, "acceptable": [1, 2], "order": [], "correction": "", "unique": False, "note": "B 也可以"},
        {"index": 2, "choice": 0, "acceptable": [0, 1], "order": [], "correction": "", "unique": False, "note": "两个都对"}]})
    assert drills.run_generation(fake_claude.FakeClient(), _gen_req(progress)) == []


def test_fix_items_gain_reviewer_alternatives(progress, monkeypatch):
    import fake_claude

    fix = {"format": "fix", "difficulty": 3, "instruction": "改正逗号连句", "content": "It rained, we stayed home.",
           "options": [], "answer": -1, "option_explanations": [], "sentences": [],
           "accepted": ["It rained, so we stayed home."], "criteria": "改正逗号连句",
           "hints": ["h1", "h2", "h3"], "explanation": "e", "focus": "逗号连句"}
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemBatch", lambda req: {"items": [fix]})
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemSolveBatch", lambda req: {"results": [
        {"index": 1, "choice": -1, "acceptable": [], "order": [], "correction": "It rained; we stayed home.", "unique": True,
         "note": ""}]})
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemCheckBatch", lambda req: {"results": [
        {"index": 1, "ok": True, "problem": "", "also_accept": ["It rained; we stayed home.", "It rained, we stayed home."]}]})
    made = drills.run_generation(fake_claude.FakeClient(), _gen_req(progress, "sent_boundary"))
    assert made[0]["accepted"] == ["It rained, so we stayed home.", "It rained; we stayed home."]  # 原句不能当答案


def test_generated_items_not_near_duplicates_of_bank(progress, monkeypatch):
    import fake_claude

    seed = bank("articles")[0]
    dup = {"format": "mcq", "difficulty": 3, "instruction": "x", "content": seed.content, "options": seed.options,
           "answer": seed.answer, "option_explanations": [], "sentences": [], "accepted": [], "criteria": "",
           "hints": ["h1", "h2"], "explanation": "e", "focus": "x"}
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemBatch", lambda req: {"items": [dup]})
    assert drills.run_generation(fake_claude.FakeClient(), _gen_req(progress, "articles")) == []


def test_exhausted_skill_asks_for_new_items_instead_of_repeating(progress):
    session = drills.new_session("kc", "articles")
    for it in bank("articles"):  # 这个技能的种子题全都做过了（以前的练习里）
        progress["items"][it.id] = {"b": 0.0, "n": 1}
        progress["attempts"].append({"t": T0.isoformat(), "item": it.id})
    item, _, _, need_gen = drills.next_item(progress, session, ai_ready=True)
    assert item is None and need_gen == "articles"
    session["gen_tried"].append("articles")  # 出题失败：退回到复习最久没见过的旧题
    item, *_ = drills.next_item(progress, session, ai_ready=True)
    assert item is not None and item.kc == "articles"
    offline, *_ = drills.next_item(progress, drills.new_session("kc", "articles"), ai_ready=False)
    assert offline is not None  # 离线时直接复习旧题


def test_repeats_prefer_least_recently_seen(progress):
    items = bank("articles")
    for n, it in enumerate(items):
        progress["items"][it.id] = {"b": 0.0, "n": 1}
        progress["attempts"].append({"t": (T0 + timedelta(days=n)).isoformat(), "item": it.id})
    assert drills.pick_item(progress, "articles", set(), False).id == items[0].id


def test_low_pool_triggers_prefetch(progress):
    session = drills.new_session("kc", "sent_boundary")
    assert drills.low_kcs(progress, session, ai_ready=True) == []  # 还有 5 道没做过
    progress["items"][bank("sent_boundary")[0].id] = {"b": 0.0, "n": 1}
    assert drills.low_kcs(progress, session, ai_ready=True) == ["sent_boundary"]
    assert drills.low_kcs(progress, session, ai_ready=False) == []


def json_dump(x):
    import json

    return json.dumps(x, ensure_ascii=False)


def _with_focus(items, focuses):
    return [it.model_copy(update={"focus": f}) for it, f in zip(items, focuses)]


def test_retest_prefers_same_error_type(progress, monkeypatch):
    items = _with_focus(bank("articles"), ["零冠词", "泛指复数", "零冠词", "泛指复数"])
    monkeypatch.setattr(drills, "seed_items", lambda: tuple(items))
    monkeypatch.setattr(drills, "all_items", lambda p: list(items))
    picked = drills.pick_item(progress, "articles", {items[0].id}, False, focus="零冠词")
    assert picked.id == items[2].id


def test_without_focus_alternates_error_types(progress, monkeypatch):
    items = _with_focus(bank("articles"), ["零冠词", "零冠词", "泛指复数", "泛指复数"])
    monkeypatch.setattr(drills, "all_items", lambda p: list(items))
    progress["attempts"].append({"t": T0.isoformat(), "item": items[0].id, "kc": "articles", "focus": "零冠词"})
    progress["items"][items[0].id] = {"b": 0.0, "n": 1}
    assert drills.pick_item(progress, "articles", set(), False).focus == "泛指复数"


def test_repeated_item_is_not_mastery_evidence(progress):
    item = synth("articles", 1)[0]
    mastery.record(progress, item, 1.0, 0, False, True, 20, when=T0)
    b = progress["items"][item.id]["b"]
    for n in range(1, 6):
        st = mastery.record(progress, item, 1.0, 0, False, True, 20, when=T0 + timedelta(minutes=n))
    assert st["streak"] == 1 and st["tier"] == "learning"  # 同一道题反复做对：不算学会
    assert progress["items"][item.id]["b"] == b  # 题目难度只用第一次作答校准


def test_learned_requires_a_production_item_when_available(progress):
    mcq = synth("sent_boundary", 6)
    for n in range(5):
        st = mastery.record(progress, mcq[n], 1.0 if n else 0.0, 0, False, True, 20, when=T0 + timedelta(minutes=n),
                            require_production=True)
    st = mastery.record(progress, mcq[5], 1.0, 0, False, True, 20, when=T0 + timedelta(minutes=6),
                        require_production=True)
    assert st["streak"] == 5 and st["tier"] == "learning"  # 5 道都是选择题：还要做对一道改错题
    fix = synth("sent_boundary", 1, "fix")[0]
    st = mastery.record(progress, fix, 1.0, 0, False, True, 20, when=T0 + timedelta(minutes=7),
                        require_production=True)
    assert st["tier"] == "learned"


def test_ai_items_start_with_weaker_difficulty_prior(progress):
    seed = synth("articles", 1)[0].model_copy(update={"difficulty": 5})
    ai_item = seed.model_copy(update={"id": "ai-x", "source": "ai"})
    assert mastery.item_difficulty(progress, ai_item) < mastery.item_difficulty(progress, seed)


def _attempt(progress, kc, ok, when=None):
    progress["attempts"].append({"t": (when or store.now()).isoformat(), "item": f"x{len(progress['attempts'])}",
                                 "kc": kc, "score": 1.0 if ok else 0.0, "hints": 0, "wrong": 0, "revealed": False})


def test_stuck_skill_rests_for_today(progress):
    progress["plan"] = {"weeks": [{"kcs": ["articles", "sent_boundary"]}], "current_week": 0}
    for _ in range(drills.STUCK_WRONG):
        _attempt(progress, "articles", False)
    assert drills.rest_reason(progress, "articles")
    kcs = [c[0] for c in drills.candidate_kcs(progress, drills.new_session("today"), ai_ready=False)]
    assert "articles" not in kcs and "sent_boundary" in kcs
    # 昨天的作答不影响今天
    yesterday = drills.new_session("today")
    progress["attempts"].clear()
    for _ in range(drills.STUCK_WRONG):
        _attempt(progress, "articles", False, store.now() - timedelta(days=1))
    assert drills.rest_reason(progress, "articles") is None
    assert "articles" in [c[0] for c in drills.candidate_kcs(progress, yesterday, ai_ready=False)]


def test_daily_cap_and_learned_skills_move_on(progress):
    for n in range(drills.DAILY_CAP):
        _attempt(progress, "articles", n % 2 == 0)
    assert drills.rest_reason(progress, "articles")
    progress["attempts"].clear()
    mastery.kc_state(progress, "sent_boundary")["tier"] = "learned"
    for _ in range(drills.CONFIRM_AFTER_LEARNED):
        _attempt(progress, "sent_boundary", True)
    assert drills._enough_today(progress, "sent_boundary")


def test_reviews_capped_at_half_a_session(progress):
    session = drills.new_session("today")
    session["count"] = 4
    session["log"] = [{"kc": "articles", "reason": "错题复习"}] * 2 + [{"kc": "thesis", "reason": "本周学习目标"}] * 2
    progress["plan"] = {"weeks": [{"kcs": ["sent_boundary"]}], "current_week": 0}
    m = drills.add_mistake(progress, "articles", "x", "n", "drill")
    m["card"]["due"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    it, reason, *_ = drills.next_item(progress, session, ai_ready=False)
    assert reason != "错题复习"


def test_solver_sees_shuffled_options_and_must_reject_other_options(progress, monkeypatch):
    import json as _json

    import fake_claude

    monkeypatch.setattr(drills, "SHUFFLE_FOR_SOLVER", True)
    right = {"C z", "A"}  # 两道假题的正确选项

    def smart(req, also=None):
        items = _json.loads(req["messages"][0]["content"].split("<items>")[1].split("</items>")[0])
        out = []
        for v in items:
            pick = next(int(o.split(". ", 1)[0]) for o in v["options"] if o.split(". ", 1)[1] in right)
            acc = [pick] + ([int(o.split(". ", 1)[0]) for o in v["options"] if o.split(". ", 1)[1] == also] if also else [])
            out.append({"index": v["index"], "choice": pick, "acceptable": acc, "order": [], "correction": "",
                        "unique": True, "note": ""})
        return {"results": out}

    monkeypatch.setitem(fake_claude.SAMPLES, "ItemSolveBatch", smart)
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemCheckBatch", lambda req: {"results": [
        {"index": 1, "ok": True, "problem": "", "also_accept": []}, {"index": 2, "ok": True, "problem": "", "also_accept": []}]})
    assert len(drills.run_generation(fake_claude.FakeClient(), _gen_req(progress))) == 2
    # 盲做者认为另一个选项也站得住：不能用
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemSolveBatch", lambda req: smart(req, also="B y"))
    made = drills.run_generation(fake_claude.FakeClient(), _gen_req(progress))
    assert [m["instruction"] for m in made] == ["第二题"]


def test_length_cue_items_are_rejected(progress, monkeypatch):
    import fake_claude

    cue = {"format": "mcq", "difficulty": 3, "instruction": "选最好的论点句", "content": "",
           "options": ["Yes.", "No.", "Zoos should be reformed rather than closed because they fund conservation."],
           "answer": 2, "option_explanations": ["a", "b", "c"], "sentences": [], "accepted": [], "criteria": "",
           "hints": ["h1", "h2", "h3"], "explanation": "e", "focus": "f"}
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemBatch", lambda req: {"items": [cue]})
    assert drills.run_generation(fake_claude.FakeClient(), _gen_req(progress)) == []


def test_answerable_without_content_is_rejected(progress, monkeypatch):
    import fake_claude

    para = {"format": "judge", "difficulty": 3, "instruction": "这段话最主要的问题是什么？", "content": "A paragraph " * 10,
            "options": ["It lacks a topic sentence.", "It has no evidence at all.", "It wanders off topic here."],
            "answer": 1, "option_explanations": ["a", "b", "c"], "sentences": [], "accepted": [], "criteria": "",
            "hints": ["h1", "h2", "h3"], "explanation": "e", "focus": "f"}
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemBatch", lambda req: {"items": [para]})
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemSolveBatch", lambda req: {"results": [
        {"index": 1, "choice": 1, "acceptable": [1], "order": [], "correction": "", "unique": True, "note": ""}]})
    monkeypatch.setitem(fake_claude.SAMPLES, "ItemCheckBatch", lambda req: {"results": [
        {"index": 1, "ok": True, "problem": "", "also_accept": []}]})
    assert len(drills.run_generation(fake_claude.FakeClient(), _gen_req(progress, "unity"))) == 1
    monkeypatch.setitem(fake_claude.SAMPLES, "OptionGuessBatch", lambda req: {"results": [
        {"index": 1, "choice": 1, "note": "只有它写得最像答案"}]})
    assert drills.run_generation(fake_claude.FakeClient(), _gen_req(progress, "unity")) == []


def test_edit_summary_lists_word_changes():
    edits = drills.edit_summary("It rained, we stayed home.", "It rained, so we stayed home.")
    assert edits == ["（无） → so"]
    assert drills.edit_summary("a b c", "a b c") == []


def test_open_grades_use_coarse_levels_and_borderline_consensus(progress, monkeypatch):
    import fake_claude

    fix = synth("sent_boundary", 1, "fix")[0]
    scores = iter([0.6, 1.0, 1.0])
    monkeypatch.setitem(fake_claude.SAMPLES, "DrillGrade", lambda req: {
        "score": next(scores), "uncertain": False, "verdict": "v", "good": "", "issue": "", "hint": "", "rule": ""})
    g = drills.grade_open(fix, "It rained, so we stayed home.", 1, [])
    assert g.score == 1.0 and not g.uncertain  # 第一次 0.6（改错只有对错 → 0），复核两次都对：取中位数
    assert sum(1 for c in fake_claude.CALLS if c["output_config"].get("format")) == 3
    rewrite = fix.model_copy(update={"format": "rewrite"})
    monkeypatch.setitem(fake_claude.SAMPLES, "DrillGrade", lambda req: {
        "score": 0.62, "uncertain": False, "verdict": "v", "good": "", "issue": "", "hint": "", "rule": ""})
    assert drills.grade_open(rewrite, "x", 1, []).score == 0.5


def test_persistent_error_types_need_an_extra_day():
    assert drills.retire_after("articles") == drills.MISTAKE_RETIRE_REVIEWS + 1
    assert drills.retire_after("sv_agree") == drills.MISTAKE_RETIRE_REVIEWS


def test_level_shifts_priorities_without_diagnostic(progress):
    progress["profile"]["level"] = "初中"
    low = planner.need_scores(progress)
    progress["profile"]["level"] = "雅思/托福备考"
    high = planner.need_scores(progress)
    assert low["sv_agree"] > high["sv_agree"] and high["collocation"] > low["collocation"]
