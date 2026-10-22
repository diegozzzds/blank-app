import streamlit as st

from essay_coach import ai, store
from essay_coach.prompts import FEEDBACK_LANGS

st.set_page_config(page_title="EssayCoach · 英文写作刷题", page_icon="✍️", layout="wide")

pages = {
    "今天": [
        st.Page("app_pages/today.py", title="今日任务", icon=":material/today:", default=True),
    ],
    "学": [
        st.Page("app_pages/plan.py", title="学习大纲", icon=":material/map:"),
        st.Page("app_pages/lessons.py", title="微课与规则卡", icon=":material/menu_book:"),
        st.Page("app_pages/skillmap.py", title="技能图谱", icon=":material/hub:"),
    ],
    "练": [
        st.Page("app_pages/drill.py", title="刷题", icon=":material/edit_note:"),
        st.Page("app_pages/mistakes.py", title="错题本", icon=":material/assignment_late:"),
        st.Page("app_pages/write.py", title="写作文", icon=":material/draw:"),
    ],
    "看": [
        st.Page("app_pages/progress.py", title="学习进度", icon=":material/monitoring:"),
        st.Page("app_pages/tutor.py", title="写作导师", icon=":material/forum:"),
    ],
}
nav = st.navigation(pages)

progress = store.sync()
if progress is None:
    st.skeleton(height=160)
    st.caption("正在读取你保存在这个浏览器里的学习记录…")
    st.button("如果一直停在这里，点这里先开始（读到记录后会自动接上）", on_click=store.start_without_storage)
    st.stop()


def _on_import() -> None:
    upload = st.session_state.get("import_file")
    if upload is None:
        return
    try:
        store.import_json(upload.getvalue())
        st.session_state["import_message"] = ("success", "已导入学习记录。")
    except (ValueError, UnicodeDecodeError) as e:
        st.session_state["import_message"] = ("error", f"导入失败：{e}")
    except Exception:  # noqa: BLE001 - 任何意外都不应让回调报错
        st.session_state["import_message"] = ("error", "导入失败：文件内容无法识别。")


with st.sidebar:
    st.markdown("### ⚙️ 设置")
    if not ai.api_key() or st.session_state.get("api_key_input"):
        st.text_input("Anthropic API Key", type="password", key="api_key_input",
                      help="也可以在 .streamlit/secrets.toml 或环境变量中设置 ANTHROPIC_API_KEY。")
    st.caption("🟢 AI 已连接" if ai.is_ready() else "⚪ 未连接 AI：可以刷种子题库里的自动判分题；AI 判分、出新题、作文批改不可用")
    st.selectbox("反馈语言", list(FEEDBACK_LANGS), key="feedback_lang")
    st.segmented_control("AI 思考深度", list(ai.EFFORT_LEVELS), default="标准", key="effort_label",
                         help="越深入，批改越细致，但等待时间更长。刷题判分固定使用快速模式。")

status = store.status()
if status in ("full", "conflict"):  # 保存失败要放在显眼的地方提示
    st.warning("浏览器存储空间已满，最近的修改没能保存。请在左侧“学习记录”里导出备份。" if status == "full" else
               "另一个标签页也打开了 EssayCoach 并保存了更新的记录。为避免互相覆盖，这个页面的修改暂停保存：请刷新页面载入最新记录"
               "（这里的修改可以先在左侧“学习记录”里导出）。", icon=":material/warning:")

nav.run()

# 学习记录面板放在页面运行之后渲染：导出的文件包含这一次刚保存的内容
with st.sidebar:
    with st.expander("💾 学习记录"):
        status = store.status()
        if status == "blocked":
            st.warning("这个浏览器不允许保存数据（可能是无痕模式或禁用了网站数据），记录只在本次打开期间有效，请记得导出。")
        elif status == "full":
            st.warning("浏览器存储空间已满，最近的修改没能保存。请先导出学习记录备份。")
        elif status == "conflict":
            st.warning("另一个标签页保存了更新的记录，本页暂停保存。请刷新页面。")
        elif status == "waiting":
            st.warning("还没读到浏览器里保存的记录，本次的修改暂时不会保存到浏览器。")
        else:
            st.caption("记录自动保存在这个浏览器里。换设备或清除浏览器数据前请先导出（导出前先点一下页面空白处，让正在输入的文字保存下来）。")
        st.download_button("导出学习记录（JSON）", store.export_json(), file_name="essaycoach_progress.json",
                           mime="application/json", width="stretch")
        if backup := st.session_state.get("_ls_session_backup"):
            st.download_button("下载读取记录前这次练习的备份", backup, file_name="essaycoach_session_backup.json",
                               mime="application/json", width="stretch")
        st.file_uploader("导入学习记录", type="json", key="import_file", on_change=_on_import)
        if msg := st.session_state.pop("import_message", None):
            getattr(st, msg[0])(msg[1])
        if st.button("清空所有记录", width="stretch"):
            st.session_state["confirm_reset"] = True
        if st.session_state.get("confirm_reset"):
            st.warning("确定要清空所有学习记录吗？此操作不能撤销。")
            c1, c2 = st.columns(2)
            if c1.button("确定清空", type="primary"):
                store.reset()
                st.session_state.pop("confirm_reset")
                st.rerun()
            if c2.button("取消"):
                st.session_state.pop("confirm_reset")
                st.rerun()
    store.flush()
