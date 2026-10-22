import streamlit as st

from essay_coach import drills, mastery, planner, store, ui
from essay_coach.skills import CRITERIA, GRAPH_VERSION, KCS, LEVELS

progress = store.progress()
ss = st.session_state

st.title("🧠 技能图谱")
st.caption(f"英文 essay 写作拆成 {len(KCS)} 个技能点，箭头表示“先学 → 后学”。颜色表示掌握等级，★ 是本周计划里的技能。"
           f"（图谱版本 {GRAPH_VERSION}）")

with st.container(horizontal=True):
    for tier, (label, color) in mastery.TIERS.items():
        st.badge(label, color=color)
st.caption("未开始 → 练习中 → 已学会（独立正确率 ≥85% 且连续独立答对 4 题）→ 已巩固（隔天复习两次都对）→ 已迁移（在独立作文里用对）")

week = planner.current_week(progress)
highlight = set(week["kcs"]) if week else None
for tab, level in zip(st.tabs(list(LEVELS.values())), LEVELS):
    with tab:
        st.mermaid_chart(ui.mermaid_skill_map(progress, level, highlight))
st.caption("虚线框是其他层的前置技能。")

c1, c2 = st.columns([1, 1])
with c1:
    st.markdown("**各维度平均掌握度**")
    ui.criteria_radar(progress, key="skill_radar")
with c2:
    counts = {label: 0 for label, _ in mastery.TIERS.values()}
    for k in KCS:
        counts[mastery.TIERS[(progress["kc"].get(k) or {}).get("tier", "new")][0]] += 1
    st.markdown("**掌握等级分布**")
    for label, n in counts.items():
        st.progress(n / len(KCS), text=f"{label}：{n} 个")

st.subheader("技能清单")
rows = []
for k, kc in KCS.items():
    stt = progress["kc"].get(k) or {}
    nxt = mastery.next_review(progress, k)
    ret = mastery.retention_now(progress, k)
    rows.append({
        "技能": kc.name, "英文": kc.en, "层级": LEVELS[kc.level], "维度": "、".join(CRITERIA[c] for c in kc.criteria),
        "等级": mastery.TIERS[stt.get("tier", "new")][0], "掌握度": mastery.mastery_pct(progress, k),
        "记忆保持": round(ret * 100) if ret is not None else None,
        "独立正确": f"{stt.get('solo_ok', 0)}/{stt.get('solo_n', 0)}",
        "下次复习": nxt.date().isoformat() if nxt else "", "可学": "✅" if mastery.is_unlocked(progress, k) else "🔒",
    })
st.dataframe(rows, hide_index=True, width="stretch", column_config={
    "掌握度": st.column_config.ProgressColumn("掌握度", min_value=0, max_value=100, format="%d%%"),
    "记忆保持": st.column_config.ProgressColumn("记忆保持", min_value=0, max_value=100, format="%d%%",
                                            help="按遗忘曲线估计的现在还记得的概率"),
})

pick = st.selectbox("选一个技能", list(KCS), format_func=lambda k: f"{KCS[k].name}（{KCS[k].en}）")
kc = KCS[pick]
with st.container(border=True):
    st.markdown(f"**{kc.name}** · {kc.en} {ui.tier_label(progress, pick)}  \n{kc.desc}")
    if kc.prereqs:
        st.caption("先学：" + "、".join(KCS[p].name for p in kc.prereqs))
    if not mastery.is_unlocked(progress, pick):
        st.caption("🔒 前置技能还没练到一半，建议先练前置技能（也可以直接练）。")
    a, b = st.columns(2)
    if a.button("练这个技能", type="primary", icon=":material/edit_note:"):
        ss["drill_request"] = {"mode": "kc", "kc": pick}
        st.switch_page("app_pages/drill.py")
    if b.button("看规则卡和微课", icon=":material/menu_book:"):
        ss["lesson_kc"] = pick
        st.switch_page("app_pages/lessons.py")
    if drills.kc_rule_card(pick):
        with st.expander("规则卡"):
            st.markdown(drills.kc_rule_card(pick))
