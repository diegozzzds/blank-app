import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def fixture_bank(monkeypatch):
    """所有测试使用 tests/fixtures 里的小题库，并把 Claude 客户端换成假的。"""
    import fake_claude
    from essay_coach import ai, items

    monkeypatch.setattr(items, "CONTENT_DIR", Path(__file__).parent / "fixtures")
    items.seed_items.cache_clear()
    items.rule_cards.cache_clear()
    monkeypatch.setattr(ai, "_client", lambda key: fake_claude.FakeClient())
    from essay_coach import drills

    monkeypatch.setattr(drills, "SHUFFLE_FOR_SOLVER", False)  # 假客户端的盲做答案按原始选项顺序写
    fake_claude.CALLS.clear()
    yield
    items.seed_items.cache_clear()
    items.rule_cards.cache_clear()
