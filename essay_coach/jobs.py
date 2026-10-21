"""后台出题：学生答题的同时提前为快用完题的技能生成新题，题目用完时不用干等。

线程里只做网络请求和计算（drills.run_generation），不碰 st.* 和 session_state；
结果在下一次页面运行时由主线程合并进学习记录（collect）。
"""

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout

import streamlit as st

from . import ai, drills

MAX_RUNNING = 2
WAIT_SECONDS = 150


@st.cache_resource(show_spinner=False)
def _pool() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=4, thread_name_prefix="essaycoach-gen")


def _jobs() -> dict[str, Future]:
    return st.session_state.setdefault("gen_jobs", {})


def running(kc: str) -> bool:
    return kc in _jobs()


def running_kcs() -> list[str]:
    return list(_jobs())


def submit(progress: dict, kc: str, force: bool = False) -> bool:
    """为技能 kc 开始后台出题；已经在出、或同时出题太多（force=True 时不限）时不重复提交。"""
    jobs = _jobs()
    if kc in jobs or (len(jobs) >= MAX_RUNNING and not force) or not ai.is_ready():
        return False
    req = drills.generation_request(progress, kc)
    jobs[kc] = _pool().submit(drills.run_generation, ai.client(), req)
    return True


def collect(progress: dict) -> tuple[list[str], dict[str, str]]:
    """合并已经完成的后台任务。返回 (出到新题的技能, {失败或一道都没通过核对的技能: 原因})。"""
    ok, failed = [], {}
    jobs = _jobs()
    for kc, fut in list(jobs.items()):
        if not fut.done():
            continue
        del jobs[kc]
        try:
            raw = fut.result()
        except ai.AIError as e:
            failed[kc] = str(e)
            continue
        except Exception:  # noqa: BLE001 - 后台出题失败不影响刷题，只是这次不再为这个技能自动出题
            failed[kc] = "出题时出了意外错误。"
            continue
        if drills.add_generated(progress, raw):
            ok.append(kc)
        else:
            failed[kc] = "新出的题没有通过核对。"
    return ok, failed


def wait(progress: dict, kc: str) -> tuple[list[str], dict[str, str]]:
    """等某个技能的后台出题完成（题目真的用完时才调用）。"""
    fut = _jobs().get(kc)
    if fut is not None:
        try:
            fut.result(timeout=WAIT_SECONDS)
        except FutureTimeout:
            pass
        except Exception:  # noqa: BLE001 - 错误在 collect 里统一处理
            pass
    return collect(progress)
