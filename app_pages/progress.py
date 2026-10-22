from datetime import timedelta

import altair as alt
import streamlit as st

from essay_coach import essays, mastery, store, ui
from essay_coach.rubrics import RUBRICS
from essay_coach.skills import KCS

progress = store.progress()

st.title("📈 学习进度")
st.caption("这里只把“独立完成”的表现当作进步：看了提示或答案做对、修改稿的分数，都单独显示，不算学会。")

# ---------------- 真实进步：独立作文 ----------------
st.subheader("真实进步：独立完成的作文")
series = essays.checkpoint_series(progress)
rubric_key = essays.rubric_for(progress.get("profile"))
series = [r for r in series if r["rubric"] == rubric_key]
if len(series) >= 2:
    data = [{"第几篇": i + 1, "日期": r["date"][:10], "类型": r["kind"], "得分": r["score"]} for i, r in enumerate(series)]
    chart = (
        alt.Chart(alt.Data(values=data))
        .mark_line(point=alt.OverlayMarkDef(size=90, filled=True), strokeWidth=2)
        .encode(x=alt.X("第几篇:O", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("得分:Q", scale=alt.Scale(domain=[0, RUBRICS[rubric_key]["max"]]),
                        title=f"得分（满分 {RUBRICS[rubric_key]['max']}）"),
                tooltip=["日期:N", "类型:N", "得分:Q"])
        .properties(height=240)
    )
    st.altair_chart(chart, width="stretch")
elif series:
    st.info(f"已有 {len(series)} 篇独立作文（{series[0]['kind']}：{series[0]['score']}）。再写一篇检测作文就能看到趋势。",
            icon=":material/timeline:")
else:
    st.info("还没有独立完成的诊断或检测作文。每两周写一篇检测作文，这里会显示真实的进步曲线。", icon=":material/timeline:")
st.caption("单篇作文的分数波动很大（Bouwer et al. 2015：单篇作文的分数只有约 10% 反映真实写作水平），"
           "请看 3 篇以上的整体趋势。写作进步通常较慢：观察数据显示集中备考约 10–12 周提高半个雅思分数段，个体差异很大。")
st.page_link("app_pages/write.py", label="写一篇检测作文", icon=":material/timer:")

# ---------------- 独立 vs 有帮助 ----------------
st.subheader("独立完成 vs 有帮助")
(solo_ok, solo_n), (help_ok, help_n) = mastery.solo_vs_help(progress)
c1, c2, c3 = st.columns(3)
c1.metric("独立正确率", f"{round(solo_ok / solo_n * 100) if solo_n else 0}%", help=f"{solo_ok}/{solo_n} 题，第一次就做对且没看提示",
          border=True)
c2.metric("有帮助时的正确率", f"{round(help_ok / help_n * 100) if help_n else 0}%",
          help=f"{help_ok}/{help_n} 题，看了提示或重试后做对", border=True)
c3.metric("错题本待巩固", len([m for m in progress["mistakes"] if not m.get("retired")]), border=True)
st.caption("有帮助时做对很正常，但它容易让人以为“已经会了”。掌握度只按独立完成计算。")

# ---------------- 每天练习量 ----------------
st.subheader("最近 30 天")
days = progress["days"]
start = store.study_day() - timedelta(days=29)
rows = [{"日期": (start + timedelta(days=i)).isoformat(),
         "独立做对": days.get((start + timedelta(days=i)).isoformat(), {}).get("solo_correct", 0)} for i in range(30)]
bars = (alt.Chart(alt.Data(values=rows)).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(x=alt.X("日期:O", axis=alt.Axis(labelAngle=-45, labelOverlap=True), title=None),
                y=alt.Y("独立做对:Q", title="每天独立做对的题数"), tooltip=["日期:N", "独立做对:Q"])
        .properties(height=200))
st.altair_chart(bars, width="stretch")

# ---------------- 技能 ----------------
st.subheader("技能掌握")
c1, c2 = st.columns(2)
with c1:
    ui.criteria_radar(progress, key="progress_radar")
with c2:
    counts = {}
    for k in KCS:
        label = mastery.TIERS[(progress["kc"].get(k) or {}).get("tier", "new")][0]
        counts[label] = counts.get(label, 0) + 1
    for label, _ in mastery.TIERS.values():
        st.progress(counts.get(label, 0) / len(KCS), text=f"{label}：{counts.get(label, 0)} 个")
st.page_link("app_pages/skillmap.py", label="查看完整技能图谱", icon=":material/hub:")
