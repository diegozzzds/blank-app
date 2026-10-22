from datetime import datetime, timezone

import streamlit as st

from essay_coach import ai, essays, store, ui
from essay_coach.rubrics import RUBRICS, format_score
from essay_coach.skills import KCS

progress = store.progress()
ss = st.session_state

st.title("✍️ 写作文")
st.caption("先独立写，再自评，然后看 AI 反馈（只挑最重要的问题）。每条反馈写下你的修改计划后再修改，AI 会检查是否真的改好了。")

KIND_HELP = {
    "practice": "练习本周技能。写完后有反馈和修改。",
    "checkpoint": "独立检测：限时、不用任何帮助，分数进入“真实进步”曲线。",
    "diagnostic": "诊断：找出你最需要练的技能，用来生成学习大纲。",
}
REVISION_LABELS = {"fixed": "✅ 改好了", "partly": "🟡 改了一部分", "not_fixed": "❌ 还没改好"}
TIME_LIMIT_MIN = {"ielts": 40, "general": 40, "ap_argument": 40, "personal": 60}
# 细化的论证目标（Ferretti et al. 2000；Nussbaum & Kardash 2005：具体目标比“说服读者”更能带出反方论证）
ARGUMENT_GOALS = ["一句话明确回答题目的立场（thesis）", "2–3 个理由，每个都有具体论据", "解释论据为什么能支撑理由",
                  "至少一个反方观点", "对反方观点的反驳", "结尾重申立场并总结理由"]

# ---------------- 选择 / 新建 ----------------
open_essays = [e for e in progress["essays"] if e["status"] != "done"]
if "essay_id" not in ss and open_essays:
    ss["essay_id"] = open_essays[-1]["id"]

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    new_kind = None
    if c1.button("写一篇练习作文", icon=":material/edit:", width="stretch"):
        new_kind = "practice"
    if c2.button("独立检测作文（限时）", icon=":material/timer:", width="stretch"):
        new_kind = "checkpoint"
    if not any(e["kind"] == "diagnostic" for e in progress["essays"]):
        if c3.button("诊断作文", icon=":material/troubleshoot:", width="stretch"):
            new_kind = "diagnostic"
    if new_kind:
        prompt = ui.run_ai("正在出题…", essays.new_prompt, progress, new_kind) if ai.is_ready() \
            else essays.new_prompt(progress, new_kind)
        if prompt:
            e = essays.start_essay(progress, new_kind, prompt)
            ss["essay_id"] = e["id"]
            st.rerun()
    if progress["essays"]:
        ids = [e["id"] for e in reversed(progress["essays"])]
        by_id = {e["id"]: e for e in progress["essays"]}
        current = ss.get("essay_id") if ss.get("essay_id") in by_id else ids[0]
        ss["essay_id"] = st.selectbox(
            "我的作文", ids, index=ids.index(current),
            format_func=lambda i: f"{essays.KIND_LABELS[by_id[i]['kind']]} · {by_id[i]['created'][:10]} · "
                                  f"{by_id[i]['prompt'][:50]}…")

essay = next((e for e in progress["essays"] if e["id"] == ss.get("essay_id")), None)
if essay is None:
    st.info("点上面的按钮开始写一篇。", icon=":material/arrow_upward:")
else:
    rubric = RUBRICS[essay["rubric"]]
    st.badge(essays.KIND_LABELS[essay["kind"]], color={"practice": "blue", "checkpoint": "violet", "diagnostic": "orange"}[essay["kind"]])
    st.caption(KIND_HELP[essay["kind"]] + f" · 评分标准：{rubric['name']}")
    with st.container(border=True):
        st.markdown(f"**题目**{('（' + essay['type'] + '）') if essay.get('type') else ''}")
        st.markdown(ui.md_escape(essay["prompt"]))
        if essay.get("tip") and essay["kind"] == "practice":
            st.caption(f"💡 {essay['tip']}")

    # ---------------- 写作 ----------------
    if essay["status"] == "writing":
        if essay["kind"] == "checkpoint":
            limit = TIME_LIMIT_MIN.get(essay["rubric"], 40)
            st.warning(f"独立检测：请在 {limit} 分钟内完成，不要使用导师或其他工具。这样分数才能反映你的真实水平。",
                       icon=":material/timer:")

            @st.fragment(run_every="1s")
            def _timer() -> None:
                started = datetime.fromisoformat(essay["started"])
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                left = limit * 60 - elapsed
                if left > 0:
                    st.markdown(f"⏱️ 剩余 **{int(left // 60)}:{int(left % 60):02d}**")
                else:
                    st.markdown("⏱️ **时间到**，请尽快提交。")

            _timer()
        if essay["rubric"] != "personal":
            with st.expander("论证要素清单（写完逐项自查）", expanded=essay["kind"] == "practice",
                             icon=":material/checklist:"):
                for n, g in enumerate(ARGUMENT_GOALS):
                    st.checkbox(g, key=f"goal_{essay['id']}_{n}")
        key = f"essay_text_{essay['id']}"
        if key not in ss:
            ss[key] = essay["text"]
        text = st.text_area("我的文章（段落之间空一行）", key=key, height=420)
        if text != essay["text"]:
            essay["text"] = text
            store.save()
        n = ui.word_count(text)
        st.caption(f"英文词数：**{n}**" + ("（雅思大作文要求至少 250 词）" if essay["rubric"] == "ielts" else ""))
        if st.button("提交初稿", type="primary", disabled=n < 50, help="至少 50 个英文单词", icon=":material/send:"):
            essay["submitted"] = store.now().isoformat()
            essay["status"] = "self"
            store.save()
            st.rerun()

    # ---------------- 自评 ----------------
    elif essay["status"] == "self":
        st.markdown(ui.md_escape(essay["text"]).replace("\n", "  \n"))
        st.subheader("先给自己打分")
        st.caption("看反馈前先自评，能帮你学会判断自己的文章（研究显示自评 + 对照反馈比只看反馈更有效）。")
        with st.form(f"self_{essay['id']}"):
            scores = {}
            for c in rubric["criteria"]:
                step = 0.5 if rubric["aggregate"] == "ielts" else 1.0
                scores[c["name"]] = st.slider(c["name"], 0.0, float(c["max"]), float(c["max"]) * 0.6, step=step,
                                              help=c["desc"])
            biggest = st.text_input("我觉得这篇最大的问题是…")
            ok = st.form_submit_button("提交自评，查看反馈", type="primary")
        if ok:
            essay["self"] = {"scores": scores, "biggest": biggest}
            store.save()
            if ui.require_ai("AI 反馈需要连接 AI。"):
                fb = ui.run_ai("老师正在认真阅读，通常需要 30–90 秒…", essays.request_feedback, progress, essay)
                if fb:
                    st.rerun()
        elif essay.get("self") and ai.is_ready() and st.button("重新获取反馈"):
            if ui.run_ai("老师正在认真阅读…", essays.request_feedback, progress, essay):
                st.rerun()

    # ---------------- 反馈 ----------------
    if essay["status"] in ("feedback", "revising", "done") and essay.get("feedback"):
        fb = essay["feedback"]
        step = 0.5 if rubric["aggregate"] == "ielts" else round(rubric["max"] * 0.05)
        lo, hi = max(0, fb["overall"] - step), min(rubric["max"], fb["overall"] + step)
        st.subheader("📋 反馈")
        m1, m2, m3 = st.columns(3)
        m1.metric("分数估计", f"{format_score(essay['rubric'], lo)}–{format_score(essay['rubric'], hi)}",
                  help="AI 打分有误差，所以显示区间。真实进步看独立检测作文的趋势。", border=True)
        m2.metric("水平", fb["level_label"], border=True)
        if essay.get("self"):
            self_total = sum(essay["self"]["scores"].values())
            if rubric["aggregate"] == "ielts":
                self_total = round(self_total / len(rubric["criteria"]) * 2) / 2
            m3.metric("我的自评", format_score(essay["rubric"], self_total),
                      delta=format_score(essay["rubric"], self_total - fb["overall"]) if self_total != fb["overall"] else None,
                      delta_color="off", help="自评与 AI 估计的差距", border=True)

        with st.expander("各维度：自评 vs AI 估计", expanded=False):
            rows = []
            for c in fb["criteria"]:
                mine = (essay.get("self") or {}).get("scores", {}).get(c["name"])
                rows.append({"维度": c["name"], "我的自评": mine, "AI 估计": c["score"], "满分": c["max_score"],
                             "依据": c["comment"]})
            st.dataframe(rows, hide_index=True, width="stretch")

        g1, g2, g3 = st.columns(3)
        with g1.container(border=True):
            st.markdown(f"**🎯 目标**\n\n{fb['goal']}")
        with g2.container(border=True):
            st.markdown(f"**📍 现状**\n\n{fb['now']}")
        with g3.container(border=True):
            st.markdown(f"**➡️ 下一步**\n\n{fb['next']}")
        if fb["strengths"]:
            st.markdown("**做得好的地方：** " + "；".join(fb["strengths"]))

        marks = [(x["quote"], f"重点{i}", "priority") for i, x in enumerate(fb["priority_issues"], 1)]
        for pat in fb["error_patterns"]:
            cat = KCS[pat["kc"]].criteria[0] if pat["kc"] in KCS else "grammar"
            marks += [(inst["quote"], pat["pattern"], cat) for inst in pat["instances"]]
        st.markdown("**原文标注**")
        ui.annotated_essay(essay["text"], marks)

        st.markdown("### 重点问题（最多 3 个）")
        responses = essay.setdefault("responses", [""] * len(fb["priority_issues"]))
        while len(responses) < len(fb["priority_issues"]):
            responses.append("")
        for i, issue in enumerate(fb["priority_issues"]):
            with st.container(border=True):
                with st.container(horizontal=True):
                    st.badge(f"重点 {i + 1}", color="violet")
                    st.badge(issue["criterion"], color="gray")
                    ui.kc_badge(issue["kc"])
                st.markdown(f"> {ui.md_escape(issue['quote'])}")
                st.markdown(f"**问题：** {issue['problem']}")
                st.markdown(f"**为什么：** {issue['why']}")
                st.markdown(f"**怎么改：** {issue['how_to_fix']}")
                st.markdown(f"**改完自查：** {issue['check_question']}")
                if essay["status"] == "feedback":
                    new = st.text_input("你打算怎么改？（如果不同意，写下理由）", value=responses[i],
                                        key=f"resp_{essay['id']}_{i}")
                    if new != responses[i]:
                        responses[i] = new
                        store.save()
                elif responses[i]:
                    st.caption(f"我的计划：{responses[i]}")
        if fb["error_patterns"]:
            st.markdown("### 语言错误模式")
            st.caption("这些句子已经加入错题本，会以“改你自己的句子”的形式在之后几天出现。")
            for pi, pat in enumerate(fb["error_patterns"]):
                with st.container(border=True):
                    st.markdown(f"**{pat['pattern']}** · {KCS[pat['kc']].name}  \n{pat['rule']}")
                    for inst in pat["instances"]:
                        st.markdown(f"- “{ui.md_escape(inst['quote'])}” — {inst['hint']}")
                    if st.button("练这个技能", key=f"pat_{essay['id']}_{pi}"):
                        ss["drill_request"] = {"mode": "kc", "kc": pat["kc"]}
                        st.switch_page("app_pages/drill.py")

        if essay["status"] == "feedback":
            ready = all(len(r.strip()) >= 4 for r in responses[:len(fb["priority_issues"])])
            c1, c2 = st.columns([1, 2])
            if c1.button("开始修改", type="primary", disabled=not ready, icon=":material/edit_note:",
                         help="先给每个重点问题写下你的修改计划"):
                essay["revised"] = essay["text"]
                essay["status"] = "revising"
                store.save()
                st.rerun()
            if essay["kind"] != "practice" and c2.button("不修改，结束这篇"):
                essay["status"] = "done"
                store.save()
                st.rerun()
            if not ready:
                st.caption("给每个重点问题写下修改计划后才能开始修改——先想清楚再动手，改得更有效。")

    # ---------------- 修改 ----------------
    if essay["status"] == "revising":
        st.subheader("✏️ 修改")
        if essay.get("revision"):
            rc = essay["revision"]
            if rc["surface_only"]:
                st.warning("上次修改主要是换词或改语法，还没有处理重点问题。对照上面的“怎么改”再试一次。",
                           icon=":material/warning:")
            with st.container(border=True):
                st.markdown(f"**上次检查结果：** {rc['overall']}")
                for chk in rc["checks"]:
                    idx = chk["index"] - 1
                    title = fb["priority_issues"][idx]["problem"] if 0 <= idx < len(fb["priority_issues"]) else f"问题 {chk['index']}"
                    st.markdown(f"- {REVISION_LABELS[chk['status']]} **{title}** — {chk['comment']}")
            if st.button("先到这里，结束这篇", help="可以先去练相关技能，之后在新作文里用上"):
                essay["status"] = "done"
                store.save()
                st.rerun()
        key = f"revised_{essay['id']}"
        if key not in ss:
            ss[key] = essay["revised"] or essay["text"]
        revised = st.text_area("修改稿", key=key, height=420)
        if revised != essay["revised"]:
            essay["revised"] = revised
            store.save()
        with st.expander("看看我改了哪些地方"):
            ui.show_diff(essay["text"], revised)
        if ui.require_ai() and st.button("提交修改稿", type="primary", disabled=revised.strip() == essay["text"].strip(),
                                         icon=":material/send:"):
            if ui.run_ai("老师正在检查你的修改…", essays.request_revision_check, progress, essay):
                st.rerun()

    # ---------------- 修改结果 ----------------
    if essay.get("revision") and essay["status"] == "done":
        rc = essay["revision"]
        st.subheader("🔍 修改效果")
        st.markdown(rc["overall"])
        for chk in rc["checks"]:
            idx = chk["index"] - 1
            title = fb["priority_issues"][idx]["problem"] if 0 <= idx < len(fb["priority_issues"]) else f"问题 {chk['index']}"
            st.markdown(f"- {REVISION_LABELS[chk['status']]} **{title}** — {chk['comment']}")
        if rc["new_problems"]:
            st.markdown("**新出现的问题：** " + "；".join(rc["new_problems"]))
        st.caption(f"修改稿估计：{format_score(essay['rubric'], rc['overall_score'])} / {rubric['max']}"
                   "（修改稿的分数不计入进步曲线——真实进步看独立完成的新作文）")
        with st.expander("修改对比"):
            ui.show_diff(essay["text"], essay["revised"])
        kcs = list(dict.fromkeys(x["kc"] for x in fb["priority_issues"]))
        if kcs:
            st.markdown("**接下来练：**")
            cols = st.columns(len(kcs))
            for col, k in zip(cols, kcs):
                if col.button(KCS[k].name, key=f"after_{essay['id']}_{k}", icon=":material/edit_note:"):
                    ss["drill_request"] = {"mode": "kc", "kc": k}
                    st.switch_page("app_pages/drill.py")
