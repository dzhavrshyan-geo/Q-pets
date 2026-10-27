# -*- coding: utf-8 -*-
"""Викторина по Лесоустроительной инструкции (без Qt): выбор вопросов и подсчёт очков.

Вопросы — в quiz_questions.py: у каждого id, текст, четыре варианта ответа
(первый — правильный) и ссылка на пункт инструкции. При показе варианты
перемешиваются. Вопросы не повторяются, пока не будут заданы все.
"""

import random

from .quiz_questions import QUESTIONS

LETTERS = "ABCD"


class Quiz:

    def __init__(self, questions=None, seen=(), rng=None):
        self.questions = list(QUESTIONS if questions is None else questions)
        self.by_id = {q["id"]: q for q in self.questions}
        self.seen = [i for i in seen if i in self.by_id]
        self.rng = rng or random.Random()

    @property
    def available(self):
        return bool(self.questions)

    def next(self):
        """Следующий вопрос: {"id", "q", "options" (перемешаны), "answer" (индекс), "ref"}."""
        if not self.questions:
            return None
        fresh = [q for q in self.questions if q["id"] not in self.seen]
        if not fresh:
            self.seen = []  # всё пройдено — начинаем заново
            fresh = list(self.questions)
        q = self.rng.choice(fresh)
        self.seen.append(q["id"])
        order = list(range(4))
        self.rng.shuffle(order)
        return {"id": q["id"], "q": q["q"], "options": [q["options"][i] for i in order],
                "answer": order.index(0), "ref": q.get("ref", "")}


def parse_ids(text):
    """Строка «3,17,42» из настроек → [3, 17, 42]."""
    out = []
    for part in str(text or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def format_ids(ids):
    return ",".join(str(i) for i in ids)
