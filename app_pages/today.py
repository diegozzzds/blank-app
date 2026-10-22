import streamlit as st

from essay_coach import ai, drills, mastery, planner, store, ui
from essay_coach.skills import KCS

progress = store.progress()
ss = st.session_state

st.title("✍️ EssayCoach · 今日任务")

if not progress.get("profile"):
    st.markdown(
        "用**刷题 + 写作 + 间隔复习**练英文 essay：\n"
        "1. 设定目标、做一次诊断；\n"
        "2. AI 按技能图谱生成你的学习大纲；\n"
        "3. 每天刷 15–25 分钟：到期复习 + 本周技能，做错的会在之后几天再出现；\n"
        "4. 每周写作文，AI 只挑最重要的问题给反馈，你修改后再检查；\n"
        "5. 每两周一篇独立检测作文，看真实进步。"
    )
    st.page_link("app_pages/plan.py", label="开始：设定目标并诊断", icon=":material/flag:")
else:
    day = progress["days"].get(store.today(), {"items": 0, "solo_correct": 0})
    goal = drills.daily_goal(progress)
    due_m = len(drills.due_mistakes(progress, ai_ready=ai.is_ready()))
    due_k = len(mastery.due_kcs(progress))
    streak, met = drills.streak(progress)
    week = planner.current_week(progress)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("今日已做", f"{day['items']} / {goal}", help="每天完成至少 10 题（不含看答案的题）算一天", border=True)
    c2.metric("今日独立做对", day["solo_correct"], border=True)
    c3.metric("待复习", due_m + due_k, help=f"错题 {due_m} 道 · 到期技能 {due_k} 个", border=True)
    c4.metric("连续学习", f"{streak} 天", help="每天完成至少 10 题（不含看答案的题）算一天；每连续 7 天可以补签 1 天，偶尔断一天不会清零", border=True)

    with st.container(border=True):
        left, right = st.columns([3, 1], vertical_alignment="center")
        if day["items"] < goal:
            left.markdown(f"**今天还差 {goal - day['items']} 题。** 先做到期复习，再练本周技能。")
        else:
            left.markdown("**今天的目标已完成 🎉** 想多练可以继续，复习会在之后几天自动安排。")
        if right.button("开始今日练习", type="primary", icon=":material/play_arrow:", width="stretch"):
            ss["drill_request"] = {"mode": "today"}
            st.switch_page("app_pages/drill.py")
        if due_m:
            if st.button(f"只复习错题（{due_m} 道到期）", icon=":material/assignment_late:"):
                ss["drill_request"] = {"mode": "mistakes"}
                st.switch_page("app_pages/drill.py")

    if not progress.get("plan"):
        st.info("还没有学习大纲。去“学习大纲”页面做诊断并生成计划，练习会更有针对性。", icon=":material/map:")
        st.page_link("app_pages/plan.py", label="生成学习大纲", icon=":material/map:")
    elif week:
        plan = progress["plan"]
        with st.container(border=True):
            st.markdown(f"#### 第 {plan.get('current_week', 0) + 1} 周 · {week['title']}")
            pct = planner.week_progress(progress, week)
            st.progress(pct, text=f"本周技能完成度 {round(pct * 100)}%")
            for g in week["goals"]:
                st.markdown(f"- {g}")
            cols = st.columns(len(week["kcs"]) or 1)
            for col, k in zip(cols, week["kcs"]):
                with col:
                    st.markdown(f"**{KCS[k].name}** {ui.tier_label(progress, k)}")
                    st.caption(f"掌握度 {mastery.mastery_pct(progress, k)}%")
                    if st.button("练", key=f"today_kc_{k}", icon=":material/edit_note:"):
                        ss["drill_request"] = {"mode": "kc", "kc": k}
                        st.switch_page("app_pages/drill.py")
            if week.get("essay_task"):
                st.markdown(f"**本周作文：** {ui.md_escape(week['essay_task'])}")
            if week.get("checkpoint"):
                st.caption("本周末安排一篇独立检测作文（限时、不用帮助），用来检验真实进步。")
            st.page_link("app_pages/write.py", label="去写作文", icon=":material/draw:")

    focus = [k for k in progress.get("focus_kcs", []) if k in KCS]
    if focus:
        st.markdown("**上篇作文暴露的弱项：** " + " ".join(f"{KCS[k].name} {ui.tier_label(progress, k)}" for k in focus))

    with st.expander("为什么这样练？", icon=":material/psychology:"):
        st.markdown(
            "- **先做再看提示**：自己回忆和尝试的过程才是学习发生的地方（检索练习）。\n"
            "- **隔几天再复习**：间隔复习比集中重复记得更久，所以错题会在 1 天、几天、几周后再出现。\n"
            "- **混着练**：不同技能交错出现会觉得更难，但更能学会“什么时候用哪个规则”。\n"
            "- **只算独立做对的**：看了提示或答案做对，不等于学会；掌握度只按独立完成计算。\n"
            "- **用作文检验**：技能真正学会，要在独立写的新作文里用对才算“已迁移”。"
        )
