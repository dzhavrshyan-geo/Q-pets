# -*- coding: utf-8 -*-
"""Гости кабинета (без Qt): начальник-горилла и лиса-шпион за окном.

Начальник время от времени заходит слева с кружкой BOSS. Если застал питомца
за своими делами или спящим — питомец пугается и тут же начинает печатать, а
начальник ворчит. Если питомец работает — начальник даёт задачу и уходит. Если
питомец вышел из кабинета — начальник смотрит на пустой стул и уходит.

Лиса иногда выглядывает из-за деревьев за окном, следит в бинокль и думает
что-нибудь вроде «Всё доложу в центральный аппарат». Если питомец смотрит
в окно или в кабинет заходит начальник — прячется.
"""

import math

BOSS_FIRST = (180.0, 420.0)      # первый визит: через 3–7 мин после запуска
BOSS_INTERVAL = (420.0, 840.0)   # потом каждые 7–14 мин
BOSS_WALK = 2.6
BOSS_TALK = 7.0
BOSS_X_OUT, BOSS_X_IN = -80.0, 56.0

FOX_FIRST = (60.0, 180.0)
FOX_INTERVAL = (150.0, 330.0)    # каждые 2,5–5,5 мин
FOX_VISIT = 10.0

CAUGHT_LINES = [
    "Так-так… Работаем, значит?",
    "Я всё вижу!",
    "Кто это тут отдыхает в рабочее время?",
    "Отчёт сам себя не напишет!",
    "{name}, а сроки-то горят!",
]
TASK_LINES = [
    "{name}, к пятнице нужен проект освоения лесов",
    "Проверь таксацию по 12-му кварталу",
    "Подготовь карту-схему лесного участка",
    "Где отчёт по лесовосстановлению?",
    "Сверь границы лесничества с ЕГРН",
    "Обнови слой выделов после рубок",
    "Посчитай расчётную лесосеку, пожалуйста",
    "Сделай выкопировку к лесной декларации",
    "{name}, глянь атрибуты выделов в 5 квартале",
    "Нужны материалы к лесохозяйственному регламенту",
]
AWAY_LINES = [
    "Опять где-то ходит…",
    "Ну и где мой сотрудник?",
    "Вернётся — пусть зайдёт ко мне",
]
REPLY_LINES = ["Сделаю!", "Будет готово!", "Уже занимаюсь!", "Принято!"]
CAUGHT_REPLY = "Я… я работаю!"

FOX_THOUGHTS = [
    "Всё доложу в центральный аппарат",
    "Так-так, опять кофе пьёт…",
    "Записываю: смотрел в окно",
    "Рослесхоз должен об этом знать!",
    "Подозрительно много перерывов…",
    "Сделаю скриншот для начальства",
    "Интересно, сколько у него выделов?",
    "А лесная декларация подана?",
    "Отчёт по форме 1-ГЛР где?",
    "Ничего, я терпеливая…",
]


def _smooth(x):
    x = 0.0 if x < 0 else 1.0 if x > 1 else x
    return x * x * (3.0 - 2.0 * x)


def _pulse(t, start, end, fade=0.3):
    return _smooth((t - start) / fade) * (1.0 - _smooth((t - end) / fade))


class Boss:

    def __init__(self, rng, now, enabled=True):
        self.rng = rng
        self.enabled = enabled
        self.state = None  # None / "enter" / "talk" / "leave"
        self.start = 0.0
        self.outcome = None  # "caught" / "working" / "away"
        self.line = ""
        self.reply = ""
        self.next_visit = now + rng.uniform(*BOSS_FIRST)

    @property
    def present(self):
        return self.state is not None

    def call(self, now):
        """Позвать начальника прямо сейчас (из меню)."""
        if self.state is None:
            self.next_visit = now

    def update(self, now, brain):
        if self.state is None:
            if self.enabled and now >= self.next_visit:
                self.state, self.start = "enter", now
            return
        t = now - self.start
        if self.state == "enter" and t >= BOSS_WALK:
            self.outcome = brain.boss_check(now)
            name = brain.pet["name"]
            lines = {"caught": CAUGHT_LINES, "working": TASK_LINES, "away": AWAY_LINES}[self.outcome]
            self.line = self.rng.choice(lines).format(name=name)
            self.reply = CAUGHT_REPLY if self.outcome == "caught" else self.rng.choice(REPLY_LINES)
            self.state, self.start = "talk", now
        elif self.state == "talk" and t >= BOSS_TALK:
            brain.boss_left(now)
            self.state, self.start = "leave", now
        elif self.state == "leave" and t >= BOSS_WALK:
            self.state = None
            self.next_visit = now + self.rng.uniform(*BOSS_INTERVAL)

    def render(self, now):
        """Что рисовать: положение, настроение, реплики и их прозрачность."""
        if self.state is None:
            return None
        t = now - self.start
        r = {"walk": 0.0, "say": "", "say_a": 0.0, "reply": "", "reply_a": 0.0, "sip": 0.0,
             "mood": "talk", "shake": 0.0, "t": now}
        if self.state == "enter":
            u = min(1.0, t / BOSS_WALK)
            r["x"] = BOSS_X_OUT + (BOSS_X_IN - BOSS_X_OUT) * _smooth(u * 1.05)
            r["walk"] = 1.0 if u < 0.95 else 0.0
            r["mood"] = "neutral"
        elif self.state == "leave":
            u = min(1.0, t / BOSS_WALK)
            r["x"] = BOSS_X_IN + (BOSS_X_OUT - BOSS_X_IN) * _smooth(u)
            r["walk"] = 1.0
            r["mood"] = "neutral" if self.outcome != "caught" else "stern"
        else:
            r["x"] = BOSS_X_IN
            if self.outcome == "caught":
                # питомец оправдывается, потом начальник ворчит
                r["mood"] = "stern"
                r["reply"], r["reply_a"] = self.reply, _pulse(t, 0.5, 2.0)
                r["say"], r["say_a"] = self.line, _pulse(t, 2.1, BOSS_TALK - 0.4)
            elif self.outcome == "working":
                r["mood"] = "talk"
                r["say"], r["say_a"] = self.line, _pulse(t, 0.3, BOSS_TALK - 2.6)
                r["reply"], r["reply_a"] = self.reply, _pulse(t, BOSS_TALK - 2.3, BOSS_TALK - 0.4)
                r["sip"] = _pulse(t, BOSS_TALK - 2.1, BOSS_TALK - 0.7, 0.4)
            else:
                r["mood"] = "stern"
                r["say"], r["say_a"] = self.line, _pulse(t, 1.4, BOSS_TALK - 0.6)
                r["shake"] = _pulse(t, 0.2, 1.6, 0.2)
        r["talking"] = r["say_a"] > 0.6
        return r


class Fox:

    def __init__(self, rng, now, enabled=True):
        self.rng = rng
        self.enabled = enabled
        self.start = None
        self.duck_at = None
        self.x = 60.0
        self.thought = ""
        self.next_visit = now + rng.uniform(*FOX_FIRST)

    @property
    def present(self):
        return self.start is not None

    def call(self, now):
        if self.start is None:
            self.next_visit = now

    def update(self, now, brain, boss_present):
        if self.start is None:
            if self.enabled and now >= self.next_visit and not boss_present:
                self.start, self.duck_at = now, None
                self.x = self.rng.uniform(30.0, 90.0)
                self.thought = self.rng.choice(FOX_THOUGHTS)
            return
        t = now - self.start
        spotted = brain.animator.name == "window" or boss_present
        if self.duck_at is None and spotted and t > 1.0:
            self.duck_at = now  # заметили — прячется
        done = t >= FOX_VISIT or (self.duck_at is not None and now - self.duck_at >= 0.6)
        if done:
            self.start = None
            self.next_visit = now + self.rng.uniform(*FOX_INTERVAL)

    def render(self, now):
        if self.start is None:
            return None
        t = now - self.start
        rise = _smooth(t / 1.0) * (1.0 - _smooth((t - (FOX_VISIT - 1.0)) / 0.8))
        think = _pulse(t, 2.4, FOX_VISIT - 1.4)
        if self.duck_at is not None:
            k = 1.0 - _smooth((now - self.duck_at) / 0.4)
            rise *= k
            think = 0.0
        return {"x": self.x, "rise": rise, "bino": 2.0 < t < 5.2, "think": self.thought,
                "think_a": think, "t": now, "peek": 0.5 + 0.5 * math.sin(t * 1.3)}
