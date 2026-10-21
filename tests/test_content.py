"""真实题库（essay_coach/content）的质量检查：结构、数量、题型、答案线索。"""

import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from essay_coach.items import Item
from essay_coach.skills import AUTO_GRADED, KCS

CONTENT = Path(__file__).resolve().parents[1] / "essay_coach" / "content"


@pytest.fixture(scope="module")
def bank():
    return [Item.model_validate(x) for x in json.loads((CONTENT / "items.json").read_text(encoding="utf-8"))]


def test_every_item_is_well_formed(bank):
    ids = Counter(i.id for i in bank)
    assert not [k for k, n in ids.items() if n > 1], "题目 id 重复"
    bad = {i.id: i.problems() for i in bank if i.problems()}
    assert not bad
    for i in bank:
        assert i.format in KCS[i.kc].formats, i.id
        assert len(i.hints) >= 2, i.id
        if i.format in ("mcq", "judge"):
            assert len(i.option_explanations) == len(i.options), i.id
        if i.format == "fix":
            assert i.accepted and all(a.strip() != i.content.strip() for a in i.accepted), i.id


def test_every_skill_has_enough_items_offline(bank):
    by_kc = defaultdict(list)
    for i in bank:
        by_kc[i.kc].append(i)
    for k in KCS:
        items = by_kc[k]
        offline = [i for i in items if i.format in AUTO_GRADED or (i.format == "fix" and i.accepted)]
        assert len(items) >= 20, (k, len(items))
        assert len(offline) >= 10, (k, len(offline))


def test_rule_card_for_every_skill():
    cards = json.loads((CONTENT / "rule_cards.json").read_text(encoding="utf-8"))
    assert set(KCS) <= set(cards)
