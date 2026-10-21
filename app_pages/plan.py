from datetime import date, timedelta

import streamlit as st

from essay_coach import ai, drills, essays, mastery, planner, store, ui
from essay_coach.items import Item, option_order, seed_items, shuffled_order
from essay_coach.prompts import LEVELS
from essay_coach.skills import KCS

progress = store.progress()
ss = st.session_state

st.title("🗺️ 学习大纲")
st.caption("设定目标 → 诊断 → AI 按技能图谱生成学习计划（程序校验）→ 每天按计划刷题，每两周用一篇独立作文检验真实进步。")

DIAG_KCS = ["sent_boundary", "chinglish_struct", "sv_agree", "articles", "noun_number", "collocation",
            "register", "transitions", "prompt_analysis", "thesis", "topic_sentence", "counterargument"]

profile = progress.get("profile")

# ---------------- 1. 目标 ----------------
with st.expander("① 我的目标", expanded=profile is None, icon=":material/flag:"):
    p = profile or {}
    with st.form("profile"):
        c1, c2 = st.columns(2)
        exam = c1.selectbox("目标考试 / 写作类型", list(planner.EXAMS), format_func=planner.EXAMS.get,
                            index=list(planner.EXAMS).index(p.get("exam", "ielts")))
        target = c2.text_input("目标分数", value=p.get("target", ""), placeholder="如 Band 7 / 5 分 / A")
        c3, c4 = st.columns(2)
        level = c3.selectbox("我现在的水平", LEVELS, index=LEVELS.index(p.get("level", "高中")))
        minutes = c4.slider("每天能练多少分钟", 10, 90, p.get("minutes_per_day", 25), step=5)
        has_date = st.checkbox("已经确定考试日期", value=bool(p.get("exam_date")))
        saved = date.fromisoformat(p["exam_date"]) if p.get("exam_date") else store.study_day() + timedelta(weeks=10)
        exam_date = st.date_input("考试日期", value=max(saved, store.study_day()), min_value=store.study_day(),
                                  help="考试日期已过的话，请改成下一次考试的日期")
        notes = st.text_area("你觉得自己写作最大的困难是什么？（选填）", value=p.get("notes", ""), height=80)
        if st.form_submit_button("保存目标", type="primary"):
            progress["profile"] = {"exam": exam, "target": target.strip(), "level": level, "minutes_per_day": minutes,
                                   "exam_date": exam_date.isoformat() if has_date else None, "notes": notes.strip(),
                                   "created": (profile or {}).get("created", store.now().isoformat())}
            store.save()
            st.rerun()

if not profile:
    st.info("先设定目标，再做诊断。", icon=":material/arrow_upward:")
else:
    diag = progress.get("diagnostic") or {}

    # ---------------- 2. 诊断 ----------------
    with st.expander("② 诊断：找出你最需要练的技能", expanded=not diag.get("quiz_done"), icon=":material/troubleshoot:"):
        st.markdown("**快速诊断题**（12 题，约 8 分钟）：做的过程中不给反馈，做完统一看结果。"
                    "结果只是初步估计，之后会随着刷题自动修正。")
        bank = seed_items()
        if not bank:
            st.warning("种子题库还没有准备好。")
        elif diag.get("quiz_done"):
            right = sum(1 for q in diag["quiz"] if q["correct"])
            st.success(f"已完成快速诊断：{right}/{len(diag['quiz'])} 题正确。", icon=":material/check:")
            st.markdown(" ".join(f"{'✅' if q['correct'] else '❌'} {KCS[q['kc']].name}" for q in diag["quiz"]))
            if st.button("重新诊断"):
                diag["quiz_done"] = False
                ss.pop("diag_quiz", None)
                store.save()
                st.rerun()
        else:
            if "diag_quiz" not in ss:
                picked = []
                for k in DIAG_KCS:
                    cands = [i for i in bank if i.kc == k and i.format in ("mcq", "judge", "order")]
                    if cands:
                        picked.append(min(cands, key=lambda i: abs(i.difficulty - 3)).id)
                ss["diag_quiz"] = {"ids": picked, "i": 0, "answers": {}}
            dq = ss["diag_quiz"]
            items = {i.id: i for i in bank}
            if dq["i"] < len(dq["ids"]):
                item: Item = items[dq["ids"][dq["i"]]]
                st.progress(dq["i"] / len(dq["ids"]), text=f"第 {dq['i'] + 1} / {len(dq['ids'])} 题")
                with st.container(border=True):
                    st.markdown(f"**{item.instruction}**")
                    if item.content:
                        st.markdown(ui.md_escape(item.content))
                    if item.format == "order":
                        order = shuffled_order(item, f"diag-{item.id}")
                        labels = {i: f"{chr(65 + n)}. {item.sentences[i]}" for n, i in enumerate(order)}
                        for i in order:
                            st.markdown(ui.md_escape(labels[i]))
                        ans = st.multiselect("按正确顺序依次选择", order, format_func=lambda i: labels[i][:2],
                                             key=f"diag_{item.id}")
                    else:
                        ans = st.radio("选项", option_order(item, item.id), index=None, key=f"diag_{item.id}",
                                       format_func=lambda i: item.options[i], label_visibility="collapsed")
                    c1, c2 = st.columns([1, 4])
                    incomplete = item.format == "order" and len(ans or []) != len(item.sentences)
                    if c1.button("下一题", type="primary", disabled=ans is None or ans == [] or incomplete,
                                 help="请把所有句子都排进去" if incomplete else None):
                        score, _ = drills.grade_auto(item, ans)
                        dq["answers"][item.id] = score
                        dq["i"] += 1
                        st.rerun()
                    if c2.button("不会，跳过"):
                        dq["answers"][item.id] = 0.0
                        dq["i"] += 1
                        st.rerun()
            else:
                quiz = []
                for iid in dq["ids"]:
                    item = items[iid]
                    score = dq["answers"].get(iid, 0.0)
                    mastery.record(progress, item, score, 0, False)
                    progress["attempts"].append({"t": store.now().isoformat(), "item": iid, "kc": item.kc,
                                                 "format": item.format, "score": score, "hints": 0,
                                                 "revealed": False, "confidence": None, "seconds": 0,
                                                 "mode": "diagnostic"})
                    quiz.append({"kc": item.kc, "correct": score >= 0.8})
                diag.update(quiz=quiz, quiz_done=True,
                            weak_kcs=list(dict.fromkeys(diag.get("weak_kcs", []) + [q["kc"] for q in quiz if not q["correct"]])),
                            strong_kcs=[q["kc"] for q in quiz if q["correct"]])
                progress["diagnostic"] = diag
                ss.pop("diag_quiz")
                store.save()
                st.rerun()

        st.divider()
        st.markdown("**诊断作文**（推荐，需要 AI）：写一篇目标考试题型的作文，AI 会找出论证、结构、语言上的具体弱项。")
        diag_essay = next((e for e in progress["essays"] if e["kind"] == "diagnostic"), None)
        if diag_essay and diag_essay.get("feedback"):
            st.success(f"诊断作文已批改：{diag_essay['feedback']['level_label']}", icon=":material/check:")
        elif diag_essay:
            if st.button("继续写诊断作文", icon=":material/draw:"):
                ss["essay_id"] = diag_essay["id"]
                st.switch_page("app_pages/write.py")
        elif ui.require_ai("写诊断作文需要 AI。没有 AI 也可以直接用快速诊断的结果生成计划。"):
            if st.button("开始写诊断作文", icon=":material/draw:"):
                prompt = ui.run_ai("正在出题…", essays.new_prompt, progress, "diagnostic")
                if prompt:
                    ss["essay_id"] = essays.start_essay(progress, "diagnostic", prompt)["id"]
                    st.switch_page("app_pages/write.py")

    # ---------------- 3. 生成计划 ----------------
    plan = progress.get("plan")
    with st.expander("③ 生成学习大纲", expanded=plan is None, icon=":material/auto_awesome:"):
        if not diag.get("quiz_done") and not (progress.get("diagnostic") or {}).get("essay_level"):
            st.caption("建议先完成诊断，计划会更准确。")
        weeks = planner.weeks_available(profile)
        st.markdown(f"计划长度：**{weeks} 周**（根据考试日期计算；未定日期时默认 {planner.DEFAULT_WEEKS} 周）。")
        st.caption("AI 只能在固定的技能图谱里挑选和排序技能，程序会检查前置关系、每周数量和高优先级技能是否遗漏，"
                   "并把修正过的地方列出来。写作分数提升较慢，建议至少坚持 6–8 周。")
        c1, c2 = st.columns(2)
        if ai.is_ready():
            if c1.button("让 AI 生成我的学习大纲" if not plan else "让 AI 重新规划", type="primary",
                         icon=":material/auto_awesome:"):
                res = ui.run_ai("AI 正在根据你的目标和诊断结果编排计划…", planner.generate_plan, progress)
                if res:
                    new_plan, notes = res
                    planner.install_plan(progress, new_plan)
                    ss["plan_notes"] = notes
                    store.save()
                    st.rerun()
        else:
            c1.caption("未连接 AI：可以先用程序生成的基础计划。")
        if c2.button("使用程序生成的基础计划", icon=":material/account_tree:"):
            planner.install_plan(progress, planner.baseline_plan(progress))
            ss["plan_notes"] = []
            store.save()
            st.rerun()
        if notes := ss.get("plan_notes"):
            with st.expander(f"程序校验修正了 {len(notes)} 处"):
                st.markdown("\n".join(f"- {n}" for n in notes))

    # ---------------- 4. 计划 ----------------
    if plan and not plan["weeks"]:
        st.warning("学习大纲是空的，请在上面重新生成。", icon=":material/warning:")
    elif plan:
        st.subheader("📅 我的学习大纲")
        src = "AI 生成 · 程序已校验" if plan.get("source") == "ai" else "程序生成的基础计划"
        st.caption(f"{src} · 创建于 {plan.get('created', '')}")
        st.markdown(plan["overview"])
        if plan.get("milestones"):
            st.markdown("**里程碑：** " + " → ".join(plan["milestones"]))
        st.markdown(f"**每天：** {plan.get('daily_routine', '')}")

        cur_i = min(plan.get("current_week", 0), len(plan["weeks"]) - 1)
        week_names = [f"第 {i + 1} 周" + (" ◉" if i == cur_i else "") for i in range(len(plan["weeks"]))]
        shown = st.segmented_control("周次", range(len(plan["weeks"])), default=cur_i,
                                     format_func=lambda i: week_names[i], key="plan_week_view")
        shown = shown if shown in range(len(plan["weeks"])) else cur_i  # 重新规划后周数可能变少
        week = plan["weeks"][shown]
        with st.container(border=True):
            start = planner.week_start(progress, shown)
            st.markdown(f"### {week['title']}")
            st.caption(f"{start.isoformat()} 起" + (" · 本周末独立检测作文" if week.get("checkpoint") else ""))
            pct = planner.week_progress(progress, week)
            st.progress(pct, text=f"本周技能完成度 {round(pct * 100)}%（技能达到“已学会”算完成）")
            st.markdown("**本周学习目标**")
            st.markdown("\n".join(f"- {g}" for g in week["goals"]))
            st.markdown(f"**为什么练这些：** {week['why']}")
            for k in week["kcs"]:
                with st.container(border=True):
                    a, b, c = st.columns([3, 2, 1], vertical_alignment="center")
                    a.markdown(f"**{KCS[k].name}**（{KCS[k].en}）{ui.tier_label(progress, k)}  \n{KCS[k].desc}")
                    b.progress(mastery.mastery_pct(progress, k) / 100, text=f"掌握度 {mastery.mastery_pct(progress, k)}%")
                    if c.button("练", key=f"plan_drill_{shown}_{k}", icon=":material/edit_note:"):
                        ss["drill_request"] = {"mode": "kc", "kc": k}
                        st.switch_page("app_pages/drill.py")
            with st.expander("调整这一周的技能", icon=":material/tune:"):
                st.caption("计划可以自己调整：觉得某个技能已经会了、或想先练别的，就在这里改（最多 4 个）。")
                chosen = st.multiselect("本周技能", list(KCS), default=week["kcs"], max_selections=planner.MAX_KCS_PER_WEEK,
                                        format_func=lambda k: f"{KCS[k].name}（{KCS[k].en}）",
                                        key=f"adjust_{plan.get('id', plan.get('created'))}_{shown}")
                if st.button("保存调整", key=f"adjust_save_{shown}", disabled=not chosen or chosen == week["kcs"]):
                    week["kcs"] = chosen
                    week["adjusted"] = True
                    store.save()
                    st.rerun()
            if week.get("lesson_focus"):
                st.markdown(f"**微课重点：** {week['lesson_focus']}")
            if week.get("essay_task"):
                st.markdown(f"**本周作文：** {ui.md_escape(week['essay_task'])}")
            c1, c2 = st.columns(2)
            if shown == cur_i and cur_i < len(plan["weeks"]) - 1:
                if c1.button("完成本周，进入下一周", icon=":material/skip_next:",
                             help="建议本周技能完成度达到 80% 以上再进入下一周"):
                    plan["current_week"] = cur_i + 1
                    ss.pop("plan_week_view", None)  # 让周次切换到新的当前周
                    store.save()
                    st.rerun()
            if shown == cur_i:
                if c2.button("今天按计划刷题", type="primary", icon=":material/play_arrow:"):
                    ss["drill_request"] = {"mode": "today"}
                    st.switch_page("app_pages/drill.py")
        if plan.get("current_week", 0) >= len(plan["weeks"]) - 1 and planner.week_progress(progress, plan["weeks"][-1]) >= 0.8:
            st.success("计划快完成了！写一篇检测作文，然后让 AI 根据新结果重新规划。", icon=":material/emoji_events:")
