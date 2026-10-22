import streamlit as st

from essay_coach import drills, prompts, store, ui
from essay_coach.lessons import LESSON_BY_ID
from essay_coach.skills import KCS, LEVELS

progress = store.progress()
ss = st.session_state

st.title("📚 微课与规则卡")
st.caption("每个技能一张规则卡；篇章和段落技能还有完整微课（讲解、范例对比、小测验）。学完直接去刷这个技能的题。")

ids = list(KCS)
default = ss.pop("lesson_kc", None)
if default in ids:
    ss["lesson_pick"] = default
pick = st.selectbox("技能", ids, key="lesson_pick",
                    format_func=lambda k: f"{LEVELS[KCS[k].level]} · {KCS[k].name}（{KCS[k].en}）")
kc = KCS[pick]
lesson = LESSON_BY_ID.get(kc.lesson) if kc.lesson else None

st.header(f"{kc.name} · {kc.en}")
st.markdown(f"{ui.tier_label(progress, pick)} {kc.desc}")
if st.button("刷这个技能的题", type="primary", icon=":material/edit_note:"):
    ss["drill_request"] = {"mode": "kc", "kc": pick}
    st.switch_page("app_pages/drill.py")

tabs = ["📌 规则卡"] + (["📖 微课讲解", "🔍 范例对比", "🧩 小测验"] if lesson else []) + ["🙋 提问"]
views = st.tabs(tabs)
i = 0
with views[i]:
    card = drills.kc_rule_card(pick)
    st.markdown(card or kc.desc)
if lesson:
    i += 1
    with views[i]:
        st.info(f"🎯 **学习目标：** {lesson['goal']}")
        st.markdown(lesson["content"])
    i += 1
    with views[i]:
        for n, ex in enumerate(lesson["examples"], 1):
            st.markdown(f"##### 范例 {n}")
            a, b = st.columns(2)
            a.error(f"**❌ 较弱**\n\n{ex['weak']}")
            b.success(f"**✅ 较强**\n\n{ex['strong']}")
            st.markdown(f"💡 **为什么？** {ex['why']}")
    i += 1
    with views[i]:
        st.caption("先自己选，再看解析。")
        for n, q in enumerate(lesson["quiz"]):
            with st.container(border=True):
                choice = st.radio(f"**{n + 1}. {q['q']}**", range(len(q["options"])),
                                  format_func=lambda k, q=q: q["options"][k], index=None, key=f"quiz_{lesson['id']}_{n}")
                if choice is not None:
                    if choice == q["answer"]:
                        st.success(f"回答正确！{q['explain']}")
                    else:
                        st.warning(f"再想想。正确答案是：**{q['options'][q['answer']]}**。{q['explain']}")
i += 1
with views[i]:
    question = st.text_area("对这个技能有什么不明白的？", key=f"ask_{pick}", height=90,
                            placeholder="例如：什么时候可以用 However 开头？")
    clicked = ui.require_ai() and st.button("提问", disabled=not question.strip(), key=f"ask_btn_{pick}")
    box = st.empty()
    answer_key = f"lesson_answer_{pick}"
    if clicked:
        content = (lesson["content"] if lesson else "") + "\n\n" + drills.kc_rule_card(pick)
        reply = ui.stream_ai(box, prompts.lesson_question_system(kc.name, kc.desc, content),
                             [{"role": "user", "content": question}], 6000, effort="low")
        if reply:
            ss[answer_key] = reply
    elif ss.get(answer_key):
        box.markdown(ss[answer_key])
