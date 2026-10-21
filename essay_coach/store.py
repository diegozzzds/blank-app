"""学习记录的存储：保存在浏览器 localStorage（关掉页面再打开不会丢），并支持导出/导入 JSON。

做法（已在多页面应用中测试）：每次运行时在入口调用 sync()：
- 第一次运行从 localStorage 读取记录（浏览器回传前返回 None，页面先显示加载中）；
- 页面里修改记录后调用 save()，下一次运行（或本次运行结束时的 flush()）把数据写回浏览器，
  写入组件一直挂载到浏览器确认为止，避免丢更新。
自动化测试中没有浏览器：预先在 st.session_state["progress"] 放好记录即可。

多个标签页：记录带一个修订号 rev。写入前在浏览器里比较，如果别的标签页已经保存了更新的版本，
这个标签页就暂停写入并提示刷新，而不是把对方的记录覆盖掉。
"""

import copy
import json
from datetime import date, datetime, timedelta, timezone

import streamlit as st

from .skills import KCS

LS_KEY = "essaycoach.progress.v2"
SCHEMA_VERSION = 2
MAX_LOAD_TRIES = 4

DEFAULT = {
    "version": SCHEMA_VERSION,
    "profile": None,       # 目标考试、目标分数、考试日期、每天时间、水平
    "diagnostic": None,    # 诊断结果
    "plan": None,          # AI 生成并经过校验的学习大纲
    "kc": {},              # 技能点状态：掌握度、复习卡片……
    "items": {},           # 题目难度（Elo）：item_id -> {"b", "n"}
    "ai_items": [],        # AI 生成的新题
    "mistakes": [],        # 错题本
    "attempts": [],        # 作答记录
    "essays": [],          # 作文（含诊断、练习、检测）
    "days": {},            # 每日统计：日期 -> {"items", "solo_correct"}
    "chat": [],            # 写作导师对话
    "focus_kcs": [],       # 最近一篇作文暴露的弱项，刷题时优先
    "flagged_items": [],   # 学生报告有问题的题目，不再出现
    "extra_accepted": {},  # 复核后认定正确的答案：item_id -> [答案]
    "rev": 0,              # 修订号：防止多个标签页互相覆盖
}
MAX_ATTEMPTS = 3000
MAX_AI_ITEMS = 500
MAX_CHAT = 200
MAX_RETIRED_MISTAKES = 300


# 学习日按北京时间划分（中国没有夏令时，固定 UTC+8），所有“今天/每天第一题/连续天数”都用它
STUDY_TZ = timezone(timedelta(hours=8))


def now() -> datetime:
    return datetime.now(timezone.utc)


def study_day(when: datetime | None = None) -> date:
    when = when or now()
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(STUDY_TZ).date()


def today() -> str:
    return study_day().isoformat()


def new_progress() -> dict:
    return copy.deepcopy(DEFAULT)


def _migrate(data: dict) -> dict:
    """把读到/导入的记录整理成当前格式：类型不对的字段换成默认值，去掉技能图谱里已经不存在的技能点。"""
    fresh = new_progress()
    if not isinstance(data, dict):
        return fresh
    for key, default in DEFAULT.items():
        if key == "version":
            continue
        value = data.get(key, default)
        ok = (value is None or isinstance(value, dict)) if default is None else isinstance(value, type(default))
        fresh[key] = copy.deepcopy(value if ok else default)
    fresh["kc"] = {k: v for k, v in fresh["kc"].items() if k in KCS and isinstance(v, dict)}
    fresh["focus_kcs"] = [k for k in fresh["focus_kcs"] if k in KCS]
    fresh["mistakes"] = [m for m in fresh["mistakes"]
                         if isinstance(m, dict) and m.get("kc") in KCS and isinstance(m.get("card"), dict)]
    fresh["attempts"] = [a for a in fresh["attempts"] if isinstance(a, dict) and "item" in a]
    fresh["essays"] = [e for e in fresh["essays"] if isinstance(e, dict) and {"id", "status", "text"} <= set(e)]
    fresh["ai_items"] = [x for x in fresh["ai_items"] if isinstance(x, dict) and x.get("kc") in KCS]
    fresh["chat"] = [m for m in fresh["chat"] if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    plan = fresh["plan"]
    if plan is not None:
        if not isinstance(plan.get("weeks"), list):
            fresh["plan"] = None
        else:
            plan["weeks"] = [dict(w, kcs=[k for k in w.get("kcs", []) if k in KCS])
                             for w in plan["weeks"] if isinstance(w, dict)]
    fresh["version"] = SCHEMA_VERSION
    return fresh


def _has_data(p: dict) -> bool:
    return bool(p.get("attempts") or p.get("essays") or p.get("profile"))


def _js_eval(expr: str, key: str):
    from streamlit_js_eval import streamlit_js_eval

    return streamlit_js_eval(js_expressions=expr, key=key)


def sync() -> dict | None:
    """在入口每次运行时调用。返回学习记录；浏览器还没回传时返回 None。"""
    ss = st.session_state
    with st.sidebar:  # 组件 iframe 很小，放在侧边栏不影响主区域布局
        if ("progress" not in ss or ss.get("_ls_unavailable")) and not ss.get("_ls_blocked"):
            ss["_ls_tries"] = ss.get("_ls_tries", 0) + 1
            raw = _js_eval("(() => { try { return JSON.stringify({v: localStorage.getItem(" + json.dumps(LS_KEY)
                           + ")}); } catch (e) { return JSON.stringify({err: String(e)}); } })()", "ls_load")
            if raw is None:
                if "progress" in ss:
                    return ss["progress"]  # 仍在等待浏览器：继续用本次会话的记录，暂不写入
                if ss["_ls_tries"] < MAX_LOAD_TRIES:
                    return None
                # 浏览器迟迟没有回应：先用空记录让页面可用，但暂停写入，
                # 避免浏览器其实有旧记录时被这份空记录覆盖
                ss["progress"] = new_progress()
                ss["_ls_unavailable"] = True
                return ss["progress"]
            late = ss.pop("_ls_unavailable", False)
            try:
                reply = json.loads(raw)
            except (ValueError, TypeError):
                reply = {}
            if reply.get("err"):  # 浏览器禁止访问存储：本次照常使用，但不保存到浏览器
                ss["_ls_blocked"] = True
                ss.setdefault("progress", new_progress())
                return ss["progress"]
            try:
                stored = reply.get("v")
                loaded = _migrate(json.loads(stored)) if stored else None
            except (ValueError, TypeError):
                loaded = None
            if loaded is not None:
                if late and _has_data(ss.get("progress") or {}):
                    # 浏览器的记录来晚了：以浏览器里的为准，本次会话做的练习留一份备份供下载
                    ss["_ls_session_backup"] = json.dumps(ss["progress"], ensure_ascii=False, indent=1)
                if late:  # 等待期间攒下的写入作废，不能覆盖浏览器里的记录
                    ss.pop("_ls_pending", None)
                    ss.pop("_ls_mounted_ver", None)
                ss["progress"] = loaded
                ss["_ls_base_rev"] = loaded.get("rev", 0)
                if late:
                    st.toast("已读取这个浏览器里保存的学习记录。")
            elif "progress" not in ss:
                ss["progress"] = new_progress()
                ss["_ls_base_rev"] = 0
        ss["_ls_mounted_ver"] = None  # 本次运行还没有挂载写入组件
        flush()
    return ss["progress"]


def flush() -> None:
    """把未确认的修改写回浏览器。入口在运行开始（sync）和结束时各调用一次，同一版本每次运行只挂载一次。"""
    ss = st.session_state
    pending = ss.get("_ls_pending")
    if (not pending or pending[0] == ss.get("_ls_mounted_ver") or ss.get("_ls_unavailable")
            or ss.get("_ls_blocked") or ss.get("_ls_conflict")):
        return
    ver, payload, rev = pending
    ss["_ls_mounted_ver"] = ver
    base = ss.get("_ls_base_rev", 0)
    key = json.dumps(LS_KEY)
    # 比较并写入：浏览器里的修订号比本页读到的新，说明别的标签页保存过，返回 -2 不写
    js = ("(() => { try { const cur = localStorage.getItem(" + key + "); "
          "const r = cur ? (JSON.parse(cur).rev || 0) : 0; if (r > " + str(base) + ") return -2; "
          "localStorage.setItem(" + key + ", " + json.dumps(payload) + "); return 1; } catch (e) { return -1; } })()")
    ok = _js_eval(js, f"ls_save_{ver}")
    if ok in (1, -1, -2) and ss.get("_ls_pending", (None,))[0] == ver:
        del ss["_ls_pending"]
        ss["_ls_write_error"] = ok == -1  # -1：通常是浏览器存储空间满了
        if ok == 1:
            ss["_ls_base_rev"] = rev
        elif ok == -2:
            ss["_ls_conflict"] = True


def status() -> str:
    """存储状态：ok / waiting（还在等浏览器）/ blocked（浏览器禁止存储）/ conflict（别的标签页保存了更新的记录）/ full（写入失败）。"""
    ss = st.session_state
    if ss.get("_ls_blocked"):
        return "blocked"
    if ss.get("_ls_conflict"):
        return "conflict"
    if ss.get("_ls_write_error"):
        return "full"
    if ss.get("_ls_unavailable"):
        return "waiting"
    return "ok"


def start_without_storage() -> None:
    """浏览器一直没有回应时，让学生先开始用（本次不读写浏览器存储，之后读到再接上）。"""
    st.session_state["progress"] = new_progress()
    st.session_state["_ls_unavailable"] = True
    st.session_state["_ls_base_rev"] = 0


def progress() -> dict:
    ss = st.session_state
    if "progress" not in ss:
        ss["progress"] = new_progress()
    return ss["progress"]


def save() -> None:
    """标记学习记录已修改，稍后写回浏览器。"""
    ss = st.session_state
    p = progress()
    p["attempts"] = p["attempts"][-MAX_ATTEMPTS:]
    p["chat"] = p["chat"][-MAX_CHAT:]
    retired = [m for m in p["mistakes"] if m.get("retired")]
    if len(retired) > MAX_RETIRED_MISTAKES:
        drop = {id(m) for m in retired[:len(retired) - MAX_RETIRED_MISTAKES]}
        p["mistakes"] = [m for m in p["mistakes"] if id(m) not in drop]
    if len(p["ai_items"]) > MAX_AI_ITEMS:
        keep = {m.get("item_id") for m in p["mistakes"] if not m.get("retired")}
        extra = len(p["ai_items"]) - MAX_AI_ITEMS
        dropped = 0
        kept = []
        for it in p["ai_items"]:
            if dropped < extra and it["id"] not in keep:
                dropped += 1
                continue
            kept.append(it)
        p["ai_items"] = kept
    ver = ss.get("_ls_ver", 0) + 1
    ss["_ls_ver"] = ver
    p["rev"] = ss.get("_ls_base_rev", p.get("rev", 0)) + 1
    ss["_ls_pending"] = (ver, json.dumps(p, ensure_ascii=False), p["rev"])


def export_json() -> str:
    return json.dumps(progress(), ensure_ascii=False, indent=1)


WIDGET_PREFIXES = ("essay_text_", "revised_", "resp_", "ans_", "conf_", "explain_", "adjust_", "goal_", "diag_")
SESSION_KEYS = ("drill", "essay_id", "diag_quiz", "plan_week_view", "plan_notes")


def _reset_widgets() -> None:
    ss = st.session_state
    for key in [k for k in ss if isinstance(k, str) and k.startswith(WIDGET_PREFIXES)]:
        del ss[key]
    for key in SESSION_KEYS:
        ss.pop(key, None)


def import_json(raw: bytes) -> None:
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("kc"), dict) or not isinstance(data.get("attempts"), list):
        raise ValueError("这不是 EssayCoach 的学习记录文件。")
    st.session_state["progress"] = _migrate(data)
    _reset_widgets()  # 旧的输入框内容不能覆盖刚导入的记录
    save()


def reset() -> None:
    st.session_state["progress"] = new_progress()
    _reset_widgets()
    save()
