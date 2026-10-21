from datetime import datetime, timezone

import streamlit as st

from essay_coach import ai, drills, mastery, store, ui
from essay_coach.skills import KCS

progress = store.progress()
ss = st.session_state

st.title("📕 错题本")
st.caption("做错的题和作文里的语言错误都会进入错题本。它们会在 1 天、几天、几周后以“同类新题”再出现；"
           "在不同的日子里独立做对 3 次，才会移出错题本。")

mistakes = progress["mistakes"]
active = [m for m in mistakes if not m.get("retired")]
retired = [m for m in mistakes if m.get("retired")]
due = drills.due_mistakes(progress, ai_ready=ai.is_ready())

c1, c2, c3 = st.columns(3)
c1.metric("待巩固", len(active), border=True)
c2.metric("今天到期", len(due), border=True)
c3.metric("已移出", len(retired), border=True)

if due and st.button(f"复习今天到期的 {len(due)} 道错题", type="primary", icon=":material/play_arrow:"):
    ss["drill_request"] = {"mode": "mistakes"}
    st.switch_page("app_pages/drill.py")

if not mistakes:
    st.info("还没有错题。去刷题或写一篇作文吧。", icon=":material/info:")
else:
    kcs = sorted({m["kc"] for m in active}, key=lambda k: list(KCS).index(k) if k in KCS else 99)
    pick = st.pills("按技能筛选", kcs, selection_mode="multi", format_func=lambda k: KCS[k].name if k in KCS else k)
    show_retired = st.toggle("显示已移出的错题", value=False)
    rows = [m for m in (mistakes if show_retired else active) if not pick or m["kc"] in pick]
    now = datetime.now(timezone.utc)
    for m in sorted(rows, key=lambda m: mastery.effective_due(m["card"], progress)):
        due_at = mastery.effective_due(m["card"], progress)  # 考试日期临近时复习会提前
        when = "今天到期" if due_at <= now else f"{(due_at - now).days + 1} 天后复习"
        with st.container(border=True):
            with st.container(horizontal=True):
                ui.kc_badge(m["kc"])
                if m.get("focus"):
                    st.badge(m["focus"], color="violet")
                st.badge("作文里的句子" if m["source"] == "essay" else "刷题", color="red" if m["source"] == "essay" else "gray")
                st.badge("已移出" if m.get("retired") else when, color="green" if m.get("retired") else "orange")
                st.badge(f"已独立做对 {len(m.get('reviews_ok', []))}/{drills.retire_after(m['kc'])} 天", color="blue")
            if m.get("text"):
                st.markdown(f"> {ui.md_escape(m['text'])}")
            if m.get("note"):
                st.caption(m["note"])
            if st.button("现在练这个技能", key=f"mk_{m['id']}", icon=":material/edit_note:"):
                ss["drill_request"] = {"mode": "kc", "kc": m["kc"]}
                st.switch_page("app_pages/drill.py")
