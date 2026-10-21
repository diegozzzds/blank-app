"""测试用的假 Claude 客户端：按结构化输出的 schema 名返回固定数据，不联网。"""
import json
from types import SimpleNamespace as NS

ESSAY = """Nowadays, with the development of society, more and more people think zoos should be closed. I partly agree with this view.

Firstly, zoos keep animals in small cages. There are many animals feel stressed, it is cruel. For example, elephants walk a lot in the wild.

Secondly, zoos can protect endangered species. Some animals would disappear without zoos. So zoos are useful.

In conclusion, zoos have advantages and disadvantages, we should improve them."""

def crit(scores):
    return [{"name": f"c{i}", "score": s, "comment": "依据"} for i, s in enumerate(scores)]

def feedback():
    return {
        "level_label": "约 Band 5.5", "criteria": crit([5.5, 6, 5.5, 5]),
        "goal": "清楚回答题目", "now": "立场模糊", "next": "重写 thesis",
        "strengths": ["“zoos can protect endangered species” 提出了相关论点"],
        "priority_issues": [
            {"criterion": "Task Response", "kc": "thesis", "quote": "I partly agree with this view.", "problem": "立场模糊",
             "why": "TR 要求清楚立场", "how_to_fix": "说明同意哪一部分", "check_question": "读者能说出你的立场吗？"},
            {"criterion": "Task Response", "kc": "analysis", "quote": "elephants walk a lot in the wild", "problem": "缺分析",
             "why": "论据需要解释", "how_to_fix": "用 because 解释", "check_question": "解释了为什么吗？"},
            {"criterion": "CC", "kc": "transitions", "quote": "Secondly, zoos can protect endangered species.", "problem": "p", "why": "w", "how_to_fix": "h", "check_question": "q"},
        ],
        "error_patterns": [
            {"kc": "chinglish_struct", "pattern": "双谓语", "rule": "一个分句只有一个谓语",
             "instances": [{"quote": "There are many animals feel stressed", "hint": "看 there are 后面"}]},
            {"kc": "sent_boundary", "pattern": "逗号连句", "rule": "两个完整句不能只用逗号连",
             "instances": [{"quote": "zoos have advantages and disadvantages, we should improve them", "hint": "看逗号"}]},
        ],
        "kc_evidence": [{"kc": "thesis", "status": "weak", "note": "n"}, {"kc": "transitions", "status": "demonstrated", "note": "n"}],
    }

SAMPLES = {
    "DrillGrade": lambda req: {"score": 1.0 if "although" in json.dumps(req["messages"]).lower() else 0.3, "uncertain": False,
                               "verdict": "v", "good": "好", "issue": "还缺少让步", "hint": "试试 although", "rule": "规则"},
    "ItemBatch": lambda req: {"items": [
        {"format": "mcq", "difficulty": 3, "instruction": "选出正确的句子", "content": "", "options": ["A x", "B y", "C z"],
         "answer": 2, "option_explanations": ["no", "no", "yes"], "sentences": [], "accepted": [], "criteria": "",
         "hints": ["h1", "h2", "h3"], "explanation": "AI rule", "focus": "f1"}
        for _ in range(1)] + [
        {"format": "mcq", "difficulty": 3, "instruction": "第二题", "content": "c2", "options": ["A", "B"],
         "answer": 0, "option_explanations": ["yes", "no"], "sentences": [], "accepted": [], "criteria": "",
         "hints": ["h1", "h2", "h3"], "explanation": "AI rule 2", "focus": "f2"}]},
    # 盲做：两道题都答对标注的答案；审核：第 2 题不合格
    "ItemSolveBatch": lambda req: {"results": [
        {"index": 1, "choice": 2, "acceptable": [2], "order": [], "correction": "", "unique": True, "note": ""},
        {"index": 2, "choice": 0, "acceptable": [0], "order": [], "correction": "", "unique": True, "note": ""}]},
    "OptionGuessBatch": lambda req: {"results": []},  # 只看选项时猜不出答案
    "ItemCheckBatch": lambda req: {"results": [{"index": 1, "ok": True, "problem": "", "also_accept": []},
                                               {"index": 2, "ok": False, "problem": "答案不唯一", "also_accept": []}]},
    "StudyPlan": lambda req: {"overview": "AI 计划概述", "daily_routine": "每天 20 分钟", "milestones": ["m1", "m2"],
                              "weeks": [{"title": "句子基础", "kcs": ["sent_boundary", "articles", "critical_questions"], "goals": ["学会分清完整句"],
                                         "why": "诊断显示", "lesson_focus": "句子边界", "essay_task": "Agree/disagree", "checkpoint": False},
                                        {"title": "论点", "kcs": ["prompt_analysis", "thesis"], "goals": ["学会写 thesis"],
                                         "why": "w", "lesson_focus": "thesis", "essay_task": "t", "checkpoint": False}]},
    "EssayPrompt": lambda req: {"prompt": "Some people believe that zoos should be closed. To what extent do you agree or disagree?",
                                "question_type": "同意/不同意", "focus_tip": "注意立场"},
    "EssayFeedback": lambda req: feedback(),
    "RevisionCheck": lambda req: {"overall": "有进步", "checks": [{"index": 1, "status": "fixed", "comment": "好"},
                                                                {"index": 2, "status": "partly", "comment": "再加分析"}],
                                  "surface_only": False, "new_problems": [], "criteria": crit([6, 6, 6, 5.5])},
}
CALLS = []

class _Stream:
    def __init__(self, kwargs):
        fmt = kwargs["output_config"].get("format")
        if fmt:
            text = json.dumps(SAMPLES[fmt["schema"]["title"]](kwargs), ensure_ascii=False)
            # 模拟输出中途的服务端回退：备用模型接着前半段继续输出
            cut = len(text) // 3
            self.content = [NS(type="text", text=text[:cut]), NS(type="fallback"), NS(type="text", text=text[cut:])]
        else:
            self.content = [NS(type="text", text="想一想："), NS(type="fallback"), NS(type="text", text="你的立场是什么？")]
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self):
        for b in self.content:
            yield NS(type="content_block_start", content_block=NS(type=b.type))
            if b.type == "text":
                yield NS(type="text", text=b.text)
    def get_final_message(self):
        return NS(content=self.content, stop_reason="end_turn")

class FakeClient:
    def __init__(self):
        self.beta = NS(messages=NS(stream=self._stream))
    def _stream(self, **kwargs):
        CALLS.append(kwargs)
        return _Stream(kwargs)
