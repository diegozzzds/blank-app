"""刷题题目的统一格式，以及种子题库的加载。

种子题库（content/items.json）由人工规则 + 多轮核对生成，离线也能刷题；
AI 按需生成的新题使用同样的格式（见 drills.py），两者一起进入题库。

格式说明（format）：
  mcq     选择题：options + answer + option_explanations
  judge   当考官：给一段文字，选出评价/最主要问题；字段同 mcq
  order   排序：sentences 按正确顺序存放，出题时打乱
  fix     找错改错：content 是含错句，accepted 是正确改法（可精确比对，必要时 AI 判分）
  combine 句子合并：content 是若干短句（每行一句），accepted 是参考答案，AI 判分
  rewrite 改写：content 是原文，instruction 说明改写要求，accepted 是参考答案，AI 判分
  write   限定写作：instruction 给任务，criteria 是判分要点，accepted 是示范答案，AI 判分
"""

import json
import random
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from .skills import KCS

CONTENT_DIR = Path(__file__).parent / "content"


class Item(BaseModel):
    id: str
    kc: str
    format: str
    difficulty: int = Field(description="1–5：1≈A2，2≈B1，3≈B1+/B2，4≈B2+，5≈C1")
    instruction: str = Field(description="题目要求（中文）")
    content: str = Field(default="", description="展示给学生的英文材料")
    options: list[str] = Field(default_factory=list)
    answer: int = -1
    option_explanations: list[str] = Field(default_factory=list)
    sentences: list[str] = Field(default_factory=list)
    accepted: list[str] = Field(default_factory=list)
    criteria: str = ""
    hints: list[str] = Field(default_factory=list, description="由浅入深的提示，不能直接给出答案")
    explanation: str = Field(default="", description="讲解：规则 + 为什么")
    focus: str = Field(default="", description="这道题练的具体错误类型（技能下的子类），如“泛指复数名词前不用 the”")
    source: str = "seed"

    @field_validator("kc")
    @classmethod
    def _known_kc(cls, v: str) -> str:
        if v not in KCS:
            raise ValueError(f"未知技能点 {v}")
        return v

    def problems(self) -> list[str]:
        """结构检查，返回问题列表（空列表 = 可用）。"""
        p = []
        if self.format not in KCS[self.kc].formats and self.format not in ("mcq",):
            p.append(f"{self.kc} 不使用 {self.format} 题型")
        if self.format in ("mcq", "judge"):
            if len(self.options) < 2 or not 0 <= self.answer < len(self.options):
                p.append("选项或答案缺失")
            if len(set(self.options)) != len(self.options):
                p.append("选项重复")
            if self.option_explanations and len(self.option_explanations) != len(self.options):
                p.append("选项解析数量与选项不一致")
        elif self.format == "order":
            if len(self.sentences) < 3:
                p.append("排序题至少需要 3 句")
        elif self.format in ("fix", "combine", "rewrite"):
            # 来自学生作文的“改自己的句子”题没有标准答案，只能由 AI 判分
            if not self.content.strip() or (not self.accepted and self.source != "personal"):
                p.append("缺少原文或参考答案")
        elif self.format == "write":
            if not self.criteria.strip():
                p.append("缺少判分要点")
        else:
            p.append(f"未知题型 {self.format}")
        if not 1 <= self.difficulty <= 5:
            p.append("难度应在 1–5")
        return p


@lru_cache(maxsize=1)
def seed_items() -> tuple[Item, ...]:
    path = CONTENT_DIR / "items.json"
    if not path.exists():
        return ()
    items = [Item.model_validate(x) for x in json.loads(path.read_text(encoding="utf-8"))]
    return tuple(i for i in items if not i.problems())


@lru_cache(maxsize=1)
def rule_cards() -> dict[str, str]:
    path = CONTENT_DIR / "rule_cards.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def shuffled_order(item: Item, seed: str) -> list[int]:
    """排序题的展示顺序（稳定：同一题同一次练习顺序不变），保证不是原顺序。"""
    idx = list(range(len(item.sentences)))
    rng = random.Random(seed)
    for _ in range(10):
        rng.shuffle(idx)
        if idx != sorted(idx):
            break
    return idx


def option_order(item: Item, seed: str) -> list[int]:
    """选择题的展示顺序（稳定：同一题同一次练习顺序不变）。

    题库里正确答案的位置和长短可能有规律（AI 写的题尤其如此），展示时打乱可以去掉位置线索。
    """
    idx = list(range(len(item.options)))
    random.Random(f"options|{seed}").shuffle(idx)
    return idx


def length_cue(item: Item) -> bool:
    """正确选项明显比其他选项都长（或都短）：学生不读题也能猜出答案。

    阈值参考研究建议：相差 ≥ 20% 且 ≥ 5 个字符。题库里曾有一半多的题“选最长的就对”。
    """
    if item.format not in ("mcq", "judge") or len(item.options) < 2 or not 0 <= item.answer < len(item.options):
        return False
    key = len(item.options[item.answer])
    others = [len(o) for i, o in enumerate(item.options) if i != item.answer]
    longest = key >= 1.2 * max(others) and key - max(others) >= 5
    shortest = key <= 0.8 * min(others) and min(others) - key >= 5
    return longest or shortest
