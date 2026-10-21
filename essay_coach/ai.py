"""Claude API 调用封装：结构化输出、流式文本输出、友好的中文错误提示。"""

import os
from contextlib import contextmanager
from typing import TypeVar

import anthropic
import streamlit as st
from pydantic import BaseModel, ValidationError

MODEL = "claude-opus-5-5"
# 服务端回退：如果安全分类器拒绝了请求，API 会自动在推荐的备用模型上重跑，
# 避免正常的写作请求因误判而失败。
FALLBACK_BETA = "server-side-fallback-2026-07-01"

EFFORT_LEVELS = {"快速": "low", "标准": "medium", "深入": "high"}

T = TypeVar("T", bound=BaseModel)


class AIError(Exception):
    """给用户看的错误信息。"""


def api_key() -> str:
    key = st.session_state.get("api_key_input", "").strip()
    if key:
        return key
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except FileNotFoundError:  # 没有 secrets.toml
        key = ""
    return key or os.environ.get("ANTHROPIC_API_KEY", "")


def is_ready() -> bool:
    return bool(api_key())


@st.cache_resource(show_spinner=False)
def _client(key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=key, max_retries=3)


def client() -> anthropic.Anthropic:
    """当前 API Key 对应的客户端。后台线程不能读 session_state，要在主线程取好再传进去。"""
    if not is_ready():
        raise AIError("还没有配置 Anthropic API Key，请在左侧边栏填写。")
    return _client(api_key())


def _effort() -> str:
    return EFFORT_LEVELS.get(st.session_state.get("effort_label", "标准"), "medium")


def _request(system: str, messages: list[dict], max_tokens: int, schema: type[BaseModel] | None = None,
             effort: str | None = None) -> dict:
    output_config: dict = {"effort": effort or _effort()}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": anthropic.transform_schema(schema)}
    return {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "output_config": output_config,
        "betas": [FALLBACK_BETA],
        "fallbacks": "default",
    }


def _final_text(message) -> str:
    """取最终回答的文本。

    服务端回退发生在输出中途时，备用模型会接着前一个模型已输出的文字继续写（fallback 块只是分界标记），
    所以要把所有文本块按顺序拼起来，而不是丢掉前半段。
    """
    return "".join(block.text for block in message.content if block.type == "text")


@contextmanager
def _friendly_errors(check_key: bool = True):
    if check_key and not is_ready():
        raise AIError("还没有配置 Anthropic API Key，请在左侧边栏填写。")
    try:
        yield
    except anthropic.AuthenticationError as e:
        raise AIError("API Key 无效，请在左侧边栏检查后重试。") from e
    except anthropic.PermissionDeniedError as e:
        raise AIError("这个 API Key 没有访问该模型的权限。") from e
    except anthropic.RateLimitError as e:
        raise AIError("请求太频繁或额度不足，请稍等片刻再试。") from e
    except anthropic.BadRequestError as e:
        raise AIError(f"请求被拒绝：{e.message}") from e
    except anthropic.APIStatusError as e:
        raise AIError(f"AI 服务暂时不可用（{e.status_code}），请稍后重试。") from e
    except anthropic.APIConnectionError as e:
        raise AIError("无法连接到 AI 服务，请检查网络后重试。") from e
    except anthropic.APIError as e:
        raise AIError("AI 服务返回了错误，请稍后重试。") from e
    except AIError:
        raise
    except Exception as e:  # 流式传输中途断网等传输层错误（Streamlit 的控制流异常是 BaseException，不受影响）
        raise AIError("和 AI 服务的连接中断了，请重试。") from e


def structured(system: str, user: str, schema: type[T], max_tokens: int = 32000, effort: str | None = None,
               client: anthropic.Anthropic | None = None) -> T:
    """让 Claude 按 schema 输出 JSON，并解析成 pydantic 对象。effort 为空时使用侧边栏设置。

    在后台线程里调用时必须传入 client 和 effort（线程里不能读 session_state）。
    """
    with _friendly_errors(check_key=client is None):
        c = client or _client(api_key())
        with c.beta.messages.stream(
            **_request(system, [{"role": "user", "content": user}], max_tokens, schema, effort or _effort())
        ) as stream:
            message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise AIError("AI 没有完成这次请求（被安全策略拦截）。请检查内容后重试。")
    if message.stop_reason is None:
        raise AIError("回复没有完整传回来，请重试。")
    if message.stop_reason == "max_tokens":
        raise AIError("AI 的回复太长被截断了。请缩短文章，或分段提交。")
    try:
        return schema.model_validate_json(_final_text(message))
    except ValidationError as e:
        raise AIError("AI 返回的格式有误，请再试一次。") from e


def stream_markdown(placeholder, system: str, messages: list[dict], max_tokens: int = 16000,
                    effort: str | None = None) -> str:
    """流式输出 Markdown 文本到 placeholder，返回最终文本。"""
    placeholder.markdown("_老师正在思考…_")
    shown = ""
    with _friendly_errors():
        with _client(api_key()).beta.messages.stream(**_request(system, messages, max_tokens, effort=effort)) as stream:
            for event in stream:
                if event.type == "text":  # 回退时备用模型接着写，已显示的内容保留
                    shown += event.text
                    placeholder.markdown(shown + " ▌")
            message = stream.get_final_message()

    if message.stop_reason == "refusal":
        placeholder.empty()
        raise AIError("AI 没有完成这次请求（被安全策略拦截）。请换个说法再试。")
    text = _final_text(message)
    if message.stop_reason is None or not text.strip():
        placeholder.empty()
        raise AIError("AI 没有给出完整的回复，请重试。")
    if message.stop_reason == "max_tokens":
        text += "\n\n_（回复过长，已截断）_"
    placeholder.markdown(text)
    return text
