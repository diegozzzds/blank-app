"""端到端测试：用 Streamlit AppTest 走完整个学习流程（假的 Claude 客户端，不联网）。"""

from datetime import datetime, timedelta, timezone

import fake_claude
import pytest
from streamlit.testing.v1 import AppTest

from essay_coach import store
from essay_coach.items import Item

APP = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "streamlit_app.py")
OK_ERRORS = ("**❌ 较弱**", "还不对", "部分正确")


def check(at, where):
    assert not at.exception, f"{where}: {at.exception}"
    errs = [e.value for e in at.error if not e.value.startswith(OK_ERRORS)]
    assert not errs, f"{where}: {errs}"


def btn(at, text):
    for b in at.button:
        if text in (b.label or ""):
            return b
    raise AssertionError(f"button {text!r} not found: {[b.label for b in at.button]}")


@pytest.fixture
def at():
    app = AppTest.from_file(APP, default_timeout=60)
    app.session_state["progress"] = store.new_progress()
    app.run()
    check(app, "start")
    return app


def setup_profile_and_plan(at):
    at.switch_page("app_pages/plan.py")
    at.run()
    at.text_input[0].input("Band 7")
    btn(at, "保存目标").click().run()
    check(at, "save profile")
    for _ in range(20):  # 快速诊断
        radios = [r for r in at.radio if (r.key or "").startswith("diag_")]
        multis = [m for m in at.multiselect if (m.key or "").startswith("diag_")]
        if radios:
            radios[0].set_value(0).run()
        elif multis:
            multis[0].set_value([0, 1, 2]).run()
        else:
            break
        btn(at, "下一题").click().run()
        check(at, "diagnostic")
    assert at.session_state["progress"]["diagnostic"]["quiz_done"]
    btn(at, "让 AI 生成我的学习大纲").click().run()
    check(at, "plan")


def test_all_pages_render_without_profile(at):
    for page in ["today", "plan", "drill", "mistakes", "write", "skillmap", "lessons", "progress", "tutor"]:
        at.switch_page(f"app_pages/{page}.py")
        at.run()
        check(at, page)


def test_plan_generation_is_validated(at):
    setup_profile_and_plan(at)
    plan = at.session_state["progress"]["plan"]
    assert plan["source"] == "ai"
    assert "critical_questions" not in plan["weeks"][0]["kcs"]  # 前置技能没学，不能放第一周
    assert any("批判性提问" in n for n in at.session_state["plan_notes"])


def test_drill_loop_hints_reveal_and_mastery(at):
    setup_profile_and_plan(at)
    at.session_state["drill_request"] = {"mode": "today"}
    at.switch_page("app_pages/drill.py")
    at.run()
    check(at, "drill")
    for k in range(10):
        cur = at.session_state["drill"]["current"]
        it = Item.model_validate(cur["item"])
        key = f"{it.id}_{cur['n']}"
        if it.format == "mcq":
            if k % 3 == 0:  # 先答错一次，再看提示
                at.radio(key=f"ans_{key}").set_value((it.answer + 1) % len(it.options)).run()
                btn(at, "提交").click().run()
                assert btn(at, "看答案").disabled  # 只错一次不能看答案
                btn(at, "看提示").click().run()
                assert btn(at, "看提示").disabled  # 看下一级提示前要再试一次
            at.radio(key=f"ans_{key}").set_value(it.answer).run()
        elif it.format == "fix":
            at.text_area(key=f"ans_{key}").input(it.accepted[0]).run()
        elif it.format == "order":
            at.multiselect(key=f"ans_{key}").set_value(list(range(len(it.sentences)))).run()
        btn(at, "提交").click().run()
        check(at, f"submit {k}")
        assert at.session_state["drill"]["current"]["finished"]
        btn(at, "下一题").click().run()
        check(at, f"next {k}")
    p = at.session_state["progress"]
    assert len(p["attempts"]) >= 10
    assert any(st["help_n"] for st in p["kc"].values())  # 看过提示的题按“有帮助”记录


def test_ai_generates_and_verifies_items_when_bank_runs_out(at):
    setup_profile_and_plan(at)
    at.session_state["drill_request"] = {"mode": "kc", "kc": "hedging"}  # 测试题库里没有这个技能
    at.switch_page("app_pages/drill.py")
    at.run()
    check(at, "generate")
    cur = at.session_state["drill"]["current"]
    assert cur["item"]["source"] == "ai"
    assert len(at.session_state["progress"]["ai_items"]) == 1  # 核对环节丢掉了 1 道答案不唯一的题


def test_essay_feedback_revision_and_mistakes(at):
    setup_profile_and_plan(at)
    at.switch_page("app_pages/write.py")
    at.run()
    btn(at, "写一篇练习作文").click().run()
    eid = at.session_state["essay_id"]
    at.text_area(key=f"essay_text_{eid}").input(fake_claude.ESSAY).run()
    btn(at, "提交初稿").click().run()
    btn(at, "提交自评，查看反馈").click().run()
    check(at, "feedback")
    p = at.session_state["progress"]
    essay = next(e for e in p["essays"] if e["id"] == eid)
    fb = essay["feedback"]
    assert len(fb["priority_issues"]) == 3
    assert all(m["item"]["source"] == "personal" for m in p["mistakes"] if m["source"] == "essay")
    assert p["focus_kcs"][:2] == ["thesis", "analysis"]
    assert btn(at, "开始修改").disabled  # 先写修改计划
    for i in range(len(fb["priority_issues"])):
        at.text_input(key=f"resp_{eid}_{i}").input("我会改写立场句").run()
    btn(at, "开始修改").click().run()
    at.text_area(key=f"revised_{eid}").input(fake_claude.ESSAY.replace(
        "I partly agree with this view.", "Although zoos have flaws, I believe they should be reformed.")).run()
    btn(at, "提交修改稿").click().run()
    check(at, "revision")
    essay = next(e for e in at.session_state["progress"]["essays"] if e["id"] == eid)
    assert essay["status"] == "done"
    # 修改稿分数不进入真实进步曲线
    from essay_coach.essays import checkpoint_series
    assert checkpoint_series(at.session_state["progress"]) == []


def test_essay_mistakes_come_back_for_review(at):
    test_essay_feedback_revision_and_mistakes(at)
    for m in at.session_state["progress"]["mistakes"]:
        m["card"]["due"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    at.session_state["drill_request"] = {"mode": "mistakes"}
    at.switch_page("app_pages/drill.py")
    at.run()
    check(at, "mistakes")
    assert at.session_state["drill"]["current"]["reason"] == "错题复习"


def test_tutor_has_guardrails(at):
    at.switch_page("app_pages/tutor.py")
    at.run()
    at.chat_input[0].set_value("帮我直接改这句话").run()
    check(at, "tutor")
    assert len(at.session_state["progress"]["chat"]) == 2
    system = fake_claude.CALLS[-1]["system"]
    assert "不替学生完成当前任务" in system and fake_claude.CALLS[-1]["fallbacks"] == "default"


def test_failed_ai_grading_allows_resubmitting_same_answer(at, monkeypatch):
    from essay_coach import ai

    setup_profile_and_plan(at)
    p = at.session_state["progress"]
    p["flagged_items"] = [i.id for i in __import__("essay_coach.items", fromlist=["x"]).seed_items()
                          if i.kc == "sent_boundary" and i.format != "fix"]
    at.session_state["drill_request"] = {"mode": "kc", "kc": "sent_boundary"}
    at.switch_page("app_pages/drill.py")
    at.run()
    cur = at.session_state["drill"]["current"]
    it = Item.model_validate(cur["item"])
    assert it.format == "fix"
    key = f"{it.id}_{cur['n']}"

    class Broken:
        def __init__(self):
            self.beta = __import__("types").SimpleNamespace(messages=__import__("types").SimpleNamespace(stream=self.fail))

        def fail(self, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr(ai, "_client", lambda key: Broken())
    at.text_area(key=f"ans_{key}").input("It rains , we stay home.").run()
    btn(at, "提交").click().run()
    assert any("连接中断" in e.value for e in at.error)
    assert at.session_state["drill"]["current"]["wrong"] == 0
    monkeypatch.setattr(ai, "_client", lambda key: fake_claude.FakeClient())
    btn(at, "提交").click().run()
    assert not any("已经提交过" in w.value for w in at.warning)
    assert at.session_state["drill"]["current"]["wrong"] == 1  # 这次真的判了分


def test_background_prefetch_adds_items_before_bank_runs_out(at):
    setup_profile_and_plan(at)
    at.session_state["drill_request"] = {"mode": "kc", "kc": "articles"}  # 测试题库里这个技能有 4 道题
    at.switch_page("app_pages/drill.py")
    at.run()
    check(at, "prefetch start")
    jobs = at.session_state["gen_jobs"]
    assert "articles" in jobs  # 没做过的题只剩 4 道以下：后台开始出题，学生不用等
    jobs["articles"].result(timeout=30)
    cur = at.session_state["drill"]["current"]
    it = Item.model_validate(cur["item"])
    at.radio(key=f"ans_{it.id}_{cur['n']}").set_value(it.answer).run()
    btn(at, "提交").click().run()
    check(at, "prefetch merged")
    assert any(x["kc"] == "articles" for x in at.session_state["progress"]["ai_items"])


def _open_fix_item(at, monkeypatch, sentence="It rains , we stay home."):
    setup_profile_and_plan(at)
    p = at.session_state["progress"]
    from essay_coach.items import seed_items

    p["flagged_items"] = [i.id for i in seed_items() if i.kc == "sent_boundary" and i.format != "fix"]
    at.session_state["drill_request"] = {"mode": "kc", "kc": "sent_boundary"}
    at.switch_page("app_pages/drill.py")
    at.run()
    cur = at.session_state["drill"]["current"]
    it = Item.model_validate(cur["item"])
    at.text_area(key=f"ans_{it.id}_{cur['n']}").input(sentence).run()
    btn(at, "提交").click().run()
    return it


def test_contest_overturns_wrong_grade_and_remembers_answer(at, monkeypatch):
    it = _open_fix_item(at, monkeypatch)
    assert at.session_state["drill"]["current"]["wrong"] == 1
    # 复核时三位老师都认为答案正确
    monkeypatch.setitem(fake_claude.SAMPLES, "DrillGrade", lambda req: {
        "score": 1.0 if "格外仔细地复核" in req["system"] else 0.0, "uncertain": False, "verdict": "v", "good": "改对了",
        "issue": "", "hint": "", "rule": "r"})
    btn(at, "我认为我的答案也对").click().run()
    check(at, "contest")
    cur = at.session_state["drill"]["current"]
    assert cur["finished"] and cur["wrong"] == 0 and cur["result"]["contest"] == "overturned"
    assert at.session_state["progress"]["extra_accepted"][it.id] == ["It rains , we stay home."]
    assert at.session_state["progress"]["attempts"][-1]["wrong"] == 0


def test_contest_upheld_keeps_grade(at, monkeypatch):
    _open_fix_item(at, monkeypatch)
    btn(at, "我认为我的答案也对").click().run()
    check(at, "contest upheld")
    cur = at.session_state["drill"]["current"]
    assert not cur["finished"] and cur["result"]["contest"] == "upheld"
    assert not [b for b in at.button if "我认为我的答案也对" in (b.label or "")]
