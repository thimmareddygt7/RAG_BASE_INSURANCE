"""LLM-as-judge for answer correctness and faithfulness, plus a lexical offline stand-in."""

from __future__ import annotations

from app.llm import LLM
from app.text import content_words, numbers

CORRECT_SYSTEM = (
    "You grade answers about insurance policies. Compare the CANDIDATE answer with the GOLD "
    "answer. Reply with exactly one word: CORRECT if the candidate states the same facts and "
    "numbers as the gold answer, otherwise INCORRECT. Ignore citations and wording differences."
)
FAITHFUL_SYSTEM = (
    "You check whether an ANSWER is fully supported by the CONTEXT. Reply with exactly one "
    "word: SUPPORTED if every factual claim in the answer appears in the context, otherwise "
    "UNSUPPORTED."
)


def judge_correct(judge: LLM, question: str, gold: str, answer: str) -> bool:
    reply = judge.complete(CORRECT_SYSTEM,
                           f"QUESTION: {question}\nGOLD: {gold}\nCANDIDATE: {answer}")
    return reply.strip().upper().startswith("CORRECT")


def judge_faithful(judge: LLM, context: str, answer: str) -> bool:
    reply = judge.complete(FAITHFUL_SYSTEM, f"CONTEXT:\n{context}\n\nANSWER: {answer}")
    return reply.strip().upper().startswith("SUPPORTED")


class LexicalJudge:
    """Offline stand-in judge based on word and number overlap. Not a real judge."""

    def complete(self, system: str, user: str) -> str:
        if "GOLD:" in user:
            gold = user.split("GOLD:", 1)[1].split("CANDIDATE:", 1)[0]
            cand = user.split("CANDIDATE:", 1)[1]
            ok = numbers(gold) <= numbers(cand)
            g = set(content_words(gold))
            ok = ok and (not g or len(g & set(content_words(cand))) / len(g) >= 0.5)
            return "CORRECT" if ok else "INCORRECT"
        context, answer = user.split("ANSWER:", 1)
        a = set(content_words(answer))
        ok = numbers(answer) <= numbers(context) and (
            not a or len(a & set(content_words(context))) / len(a) >= 0.6)
        return "SUPPORTED" if ok else "UNSUPPORTED"
