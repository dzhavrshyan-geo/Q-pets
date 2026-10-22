# -*- coding: utf-8 -*-
"""Позы и анимации питомца (без Qt).

Поза — словарь чисел: где руки, куда повёрнута голова и смотрят глаза,
где кружка и телефон, насколько видны значки (Zzz, ноты, лампочка).
Координаты — в логической сцене 320×240 (см. drawing.py).
Анимация — функция времени t → поза. При смене анимации поза плавно
перетекает из старой в новую, поэтому кружка или телефон, брошенные
на полпути, сами возвращаются на стол.
"""

import math
import random

BASE = {
    # Руки (левая/правая со стороны зрителя) — по умолчанию на клавиатуре
    "hlx": 137.0, "hly": 181.0, "hrx": 163.0, "hry": 181.0,
    # Голова: поворот (-1 — к окну, +1 — к монитору), наклон в градусах, сдвиг
    "turn": 0.35, "tilt": 0.0, "hdy": 0.0,
    # Корпус
    "bdx": 0.0, "bdy": 0.0,
    # Лицо: взгляд, открытость глаз (>1 — вытаращены), брови, улыбка, рот, язык
    "lookx": 0.7, "looky": 0.15, "eyes": 1.0, "brow": 0.0,
    "smile": 0.25, "mouth": 0.0, "tongue": 0.0,
    # Кружка (центр) и наклон
    "mugx": 80.0, "mugy": 174.0, "mugrot": 0.0,
    # Телефон: центр, наклон, 0 — лежит на столе, 1 — в руках; свечение экрана на лице
    "phx": 103.0, "phy": 192.0, "phrot": 0.0, "phup": 0.0, "glow": 0.0,
    # Компьютерная мышь
    "msx": 203.0, "msy": 187.0,
    # Значки над головой
    "zzz": 0.0, "notes": 0.0, "quest": 0.0, "bulb": 0.0, "sweat": 0.0,
    "hearts": 0.0, "excl": 0.0,
    # Тигрёнок: 1 — довольный (глаза-дуги, рот открыт)
    "tiger": 0.0,
}

MUG_DESK = (BASE["mugx"], BASE["mugy"])
PHONE_DESK = (BASE["phx"], BASE["phy"])


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def smooth(x):
    x = clamp(x)
    return x * x * (3.0 - 2.0 * x)


def mix(a, b, k):
    return {key: a[key] + (b[key] - a[key]) * k for key in a}


def pulse(t, start, end, fade=0.4):
    """1 между start и end, с плавным появлением и исчезанием."""
    return smooth((t - start) / fade) * (1.0 - smooth((t - end) / fade))


def pose(**changes):
    p = dict(BASE)
    p.update(changes)
    return p


def keyframes(*frames):
    """Кадры (время, изменения) → функция t → поза.

    Незаданные в кадре значения берутся из предыдущего кадра,
    между кадрами — плавный переход.
    """
    full = []
    current = dict(BASE)
    for time, changes in frames:
        current = dict(current, **changes)
        full.append((time, current))

    def at(t, pet=None):
        if t <= full[0][0]:
            return dict(full[0][1])
        for (t0, a), (t1, b) in zip(full, full[1:]):
            if t < t1:
                return mix(a, b, smooth((t - t0) / (t1 - t0)))
        return dict(full[-1][1])
    return at


# ---------------------------------------------------------------- работа

def typing(t, pet):
    beat = t * 15.0
    return pose(
        hlx=137 + 2.0 * math.sin(t * 3.1), hly=181 - 3.2 * max(0.0, math.sin(beat)),
        hrx=163 + 2.0 * math.sin(t * 2.6 + 1), hry=181 - 3.2 * max(0.0, math.sin(beat + math.pi)),
        turn=0.45, lookx=0.9 + 0.1 * math.sin(t * 2.0), looky=0.25,
        brow=-0.5, smile=0.05, hdy=0.6 * math.sin(t * 7.0), bdy=0.4 * math.sin(t * 7.0),
    )


def mouse(t, pet):
    mx = 203 + 3.5 * math.sin(t * 2.3) + 1.5 * math.sin(t * 5.1)
    my = 186.5 + 2.0 * math.sin(t * 3.7)
    return pose(
        hrx=mx, hry=my - 2, msx=mx, msy=my,
        hlx=138, hly=182,
        turn=0.5, lookx=0.75 + 0.25 * math.sin(t * 0.9), looky=0.05 + 0.3 * math.sin(t * 1.3),
        brow=-0.25, smile=0.2,
    )


_focus_cycle = keyframes(
    (0.0, {}),
    (4.0, {}),
    (4.8, {"hrx": 156, "hry": 120, "tilt": 6, "brow": -0.3, "smile": 0.0}),
    (8.0, {}),
    (8.8, {"hrx": 163, "hry": 181, "tilt": 0, "brow": 0, "smile": 0.25}),
    (12.0, {}),
)


def focus(t, pet):
    """Ничего не нажимают, но работа идёт: читает экран, подпирает голову."""
    p = _focus_cycle(t % 12.0)
    p["turn"] = 0.45
    p["lookx"] = 0.7 + 0.25 * math.sin(t * 1.6)
    p["looky"] = 0.1 + 0.15 * math.sin(t * 0.7)
    p["hdy"] += 0.8 * math.sin(t * 0.9)
    return p


def thinking(t, pet):
    """QGIS занят (рисует карту, считает инструмент) — ждёт и барабанит пальцами."""
    finger = int(t * 8) % 4
    return pose(
        hrx=203, hry=185, msx=203, msy=187,
        hlx=126 + finger * 2.5, hly=179 - 2.5 * abs(math.sin(t * 16.0)),
        turn=0.55, lookx=1.0, looky=0.2, brow=-0.7, smile=-0.35,
        bdx=2.0, hdy=1.0, sweat=smooth((t - 4.0) / 0.6),
    )


# ---------------------------------------------------------------- свои дела

window = keyframes(
    (0.0, {}),
    (1.2, {"turn": -0.9, "lookx": -1.0, "looky": -0.45, "brow": 0.3, "smile": 0.45,
           "hlx": 145, "hly": 120, "tilt": -7}),
    (2.0, {"eyes": 0.8}),
    (6.5, {"eyes": 0.75, "smile": 0.6}),
    (7.4, {"eyes": 1.0}),
    (8.4, {"turn": 0.35, "lookx": 0.7, "looky": 0.15, "brow": 0, "smile": 0.25,
           "hlx": 137, "hly": 181, "tilt": 0}),
    (9.0, {}),
)

_phone_frames = keyframes(
    (0.0, {}),
    (0.9, {"hlx": 104, "hly": 189, "lookx": -0.4, "looky": 0.8, "turn": -0.1}),
    (1.9, {"phx": 150, "phy": 147, "phup": 1.0, "glow": 1.0,
           "hlx": 141, "hly": 156, "hrx": 159, "hry": 156,
           "lookx": 0.0, "looky": 1.0, "turn": 0.0, "hdy": 3.0, "smile": 0.3}),
    (5.0, {}),
    (5.6, {"smile": 0.9, "mouth": 0.35, "brow": 0.4}),
    (6.8, {}),
    (7.4, {"smile": 0.3, "mouth": 0.0, "brow": 0.0}),
    (10.0, {}),
    (11.0, {"phx": PHONE_DESK[0], "phy": PHONE_DESK[1], "phup": 0.0, "glow": 0.0,
            "hlx": 105, "hly": 189, "hrx": 163, "hry": 181, "hdy": 0.0,
            "lookx": -0.3, "looky": 0.8}),
    (11.8, {"hlx": 137, "hly": 181, "lookx": 0.7, "looky": 0.15, "turn": 0.35, "smile": 0.25}),
)


def phone(t, pet):
    p = _phone_frames(t)
    if 2.0 < t < 10.0:
        # листает ленту большим пальцем
        p["hry"] += 2.0 * max(0.0, math.sin(t * 4.0))
        p["hdy"] += 0.4 * math.sin(t * 1.3)
    return p


_mug_hand = (MUG_DESK[0] + 9, MUG_DESK[1] + 2)

coffee = keyframes(
    (0.0, {}),
    (0.9, {"hlx": _mug_hand[0], "hly": _mug_hand[1], "lookx": -0.6, "looky": 0.7, "turn": -0.2}),
    (2.0, {"mugx": 141, "mugy": 106, "mugrot": -32, "hlx": 150, "hly": 111,
           "lookx": 0.0, "looky": 0.3, "turn": 0.0, "eyes": 0.0, "tilt": -4, "smile": 0.2}),
    (4.0, {}),
    (4.8, {"mugx": 128, "mugy": 140, "mugrot": 0, "hlx": 136, "hly": 142,
           "eyes": 1.0, "tilt": 0, "smile": 0.8, "brow": 0.4, "lookx": -0.3, "looky": 0.5}),
    (6.0, {}),
    (7.0, {"mugx": MUG_DESK[0], "mugy": MUG_DESK[1], "hlx": _mug_hand[0], "hly": _mug_hand[1],
           "smile": 0.4, "brow": 0.0}),
    (7.8, {"hlx": 137, "hly": 181, "lookx": 0.7, "looky": 0.15, "turn": 0.35, "smile": 0.25}),
)

stretch = keyframes(
    (0.0, {}),
    (1.1, {"hlx": 116, "hly": 44, "hrx": 184, "hry": 44, "eyes": 0.0, "mouth": 1.0,
           "hdy": -2, "bdy": -3, "turn": 0.0, "brow": 0.6, "tilt": 0}),
    (2.6, {"tilt": 4}),
    (3.0, {"tilt": -2}),
    (3.9, {"hlx": 137, "hly": 181, "hrx": 163, "hry": 181, "eyes": 1.0, "mouth": 0.0,
           "hdy": 0, "bdy": 0, "turn": 0.35, "brow": 0, "tilt": 0}),
    (4.6, {}),
)

_tiger_frames = keyframes(
    (0.0, {}),
    (1.0, {"hlx": 106, "hly": 140, "turn": -0.35, "lookx": -0.6, "looky": 0.8,
           "smile": 0.85, "brow": 0.3, "tiger": 1.0, "tilt": -5}),
    (8.2, {}),
    (9.2, {"hlx": 137, "hly": 181, "turn": 0.35, "lookx": 0.7, "looky": 0.15,
           "smile": 0.25, "brow": 0, "tiger": 0.0, "tilt": 0}),
)


def tiger(t, pet):
    """Гладит тигрёнка, а тот жмурится от удовольствия."""
    p = _tiger_frames(t)
    k = pulse(t, 1.0, 8.2)
    p["hlx"] += 6.0 * math.sin(t * 3.2) * k
    p["hly"] += 1.5 * math.sin(t * 6.4) * k
    p["hearts"] = pulse(t, 2.0, 7.8)
    return p


_daydream_frames = keyframes(
    (0.0, {}),
    (1.2, {"hrx": 157, "hry": 120, "turn": -0.2, "lookx": -0.4, "looky": -0.7,
           "eyes": 0.75, "smile": 0.65, "brow": 0.35}),
    (9.0, {}),
    (10.0, {"hrx": 163, "hry": 181, "turn": 0.35, "lookx": 0.7, "looky": 0.15,
            "eyes": 1.0, "smile": 0.25, "brow": 0}),
)


def daydream(t, pet):
    """Подпёрла щёку и мечтает под музыку в наушниках."""
    p = _daydream_frames(t)
    k = pulse(t, 1.2, 9.0)
    p["tilt"] = 7.0 * k + 5.0 * math.sin(t * 2.4) * k
    p["notes"] = k
    return p


_ponder_frames = keyframes(
    (0.0, {}),
    (1.0, {"hrx": 153, "hry": 117, "turn": 0.3, "lookx": 0.6, "looky": -0.8, "brow": 0.5,
           "smile": 0.0}),
    (6.6, {}),
    (7.2, {"smile": 0.85, "brow": 0.8, "eyes": 1.15, "looky": -0.2}),
    (9.0, {}),
    (10.0, {"hrx": 163, "hry": 181, "turn": 0.35, "lookx": 0.7, "looky": 0.15,
            "smile": 0.25, "brow": 0, "eyes": 1.0}),
)


def ponder(t, pet):
    """Задумчиво чешет подбородок — и тут приходит идея."""
    p = _ponder_frames(t)
    p["hrx"] += 3.0 * math.sin(t * 3.5) * pulse(t, 1.0, 6.6)
    p["quest"] = pulse(t, 2.0, 6.6)
    p["bulb"] = pulse(t, 7.0, 9.4)
    p["hdy"] += 1.5 * math.sin(t * 6.0) * pulse(t, 7.2, 8.4, 0.2)  # кивает
    return p


def nap(t, pet):
    breath = math.sin(t * 1.4)
    return pose(
        hlx=136, hly=170, hrx=164, hry=170,
        turn=0.0, tilt=12.0, hdy=9.0 + breath, bdy=2.0 + 0.6 * breath,
        eyes=0.0, smile=0.2, mouth=0.12 + 0.08 * breath, lookx=0, looky=0.5, zzz=1.0,
    )


def wake(t, pet):
    return pose(eyes=1.3, brow=1.0, mouth=0.35, smile=0.0, turn=0.0, lookx=0.0, looky=0.0,
                excl=pulse(t, 0.0, 0.8, 0.15), hdy=-2.0)


def wave(t, pet):
    """Помахать, когда по питомцу щёлкнули."""
    return pose(
        hrx=192 + 7.0 * math.sin(t * 13.0), hry=76 + 2.0 * math.sin(t * 26.0),
        turn=0.0, lookx=0.0, looky=0.0, smile=1.0, mouth=0.35, brow=0.6, tilt=-4.0,
    )


class Activity:
    def __init__(self, func, duration=None, blend=0.45, screen="map"):
        self.func = func
        self.duration = duration  # None — повторяется, пока не сменят
        self.blend = blend
        self.screen = screen


ACTIVITIES = {
    "typing": Activity(typing, blend=0.3, screen="typing"),
    "mouse": Activity(mouse, blend=0.3, screen="pan"),
    "focus": Activity(focus, blend=0.5),
    "thinking": Activity(thinking, blend=0.4, screen="busy"),
    "window": Activity(window, 9.0),
    "phone": Activity(phone, 11.8),
    "coffee": Activity(coffee, 7.8),
    "stretch": Activity(stretch, 4.6),
    "tiger": Activity(tiger, 9.2),
    "daydream": Activity(daydream, 10.0),
    "ponder": Activity(ponder, 10.0),
    "nap": Activity(nap, blend=1.2, screen="sleep"),
    "wake": Activity(wake, 0.9, blend=0.15, screen="sleep"),
    "wave": Activity(wave, 1.8, blend=0.25),
}

IDLE_COMMON = ["window", "phone", "coffee", "stretch"]


class Animator:
    """Проигрывает анимации и плавно переводит одну в другую."""

    def __init__(self, pet, rng=None):
        self.pet = pet
        self.rng = rng or random.Random()
        self.name = None
        self.start = 0.0
        self.from_pose = None
        self.next_blink = None
        self.blink_until = -1.0

    def play(self, name, now):
        if name == self.name:
            return
        self.from_pose = self.pose(now) if self.name else None
        self.name = name
        self.start = now

    @property
    def activity(self):
        return ACTIVITIES[self.name]

    def elapsed(self, now):
        return now - self.start

    def finished(self, now):
        duration = self.activity.duration
        return duration is not None and self.elapsed(now) >= duration

    def pose(self, now):
        t = self.elapsed(now)
        p = self.activity.func(t, self.pet)
        p.update(self.pet.get("poses", {}).get(self.name, {}))
        blend = self.activity.blend
        if self.from_pose is not None and t < blend:
            p = mix(self.from_pose, p, smooth(t / blend))
        return p

    def blink(self, now):
        """Множитель открытости глаз: иногда питомец моргает."""
        if self.next_blink is None:
            self.next_blink = now + self.rng.uniform(1.5, 4.0)
        if now >= self.next_blink:
            self.blink_until = now + 0.14
            self.next_blink = now + self.rng.uniform(2.5, 6.0)
        return 0.0 if now < self.blink_until else 1.0
