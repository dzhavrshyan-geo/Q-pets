# -*- coding: utf-8 -*-
"""Позы и анимации питомца (без Qt).

Поза — словарь чисел: где руки и локти, куда повёрнута голова и смотрят глаза,
где кружка, телефон, банан и прочие вещи, насколько видны значки (Zzz, ноты,
лампочка). Координаты — в логической сцене 320×240 (см. drawing.py).
Анимация — функция времени t → поза. При смене анимации поза плавно
перетекает из старой в новую, поэтому вещи, брошенные на полпути,
сами возвращаются на место.

Руки «мультяшные»: рука — плавная дуга от плеча к кисти. Локоть по умолчанию
свисает вниз и наружу (lb/rb — сила изгиба); для точных поз локоть задаётся
явно (lew/lex/ley — вес и точка, см. elbows()).
"""

import math
import random

BASE = {
    # Кисти (левая/правая со стороны зрителя) — по умолчанию на клавиатуре
    "hlx": 137.0, "hly": 181.0, "hrx": 163.0, "hry": 181.0,
    # Локти: сила изгиба и явная точка с весом (0 — локоть считается сам)
    "lb": 1.0, "rb": 1.0,
    "lew": 0.0, "lex": 116.0, "ley": 160.0, "rew": 0.0, "rex": 184.0, "rey": 160.0,
    # 1 — руки за головой (рисуются позади неё)
    "armsback": 0.0,
    # Жесты: большой палец вверх, «мир», ручка в правой руке
    "rthumb": 0.0, "rpeace": 0.0, "pen": 0.0,
    # Голова: поворот (-1 — к окну, +1 — к монитору), наклон в градусах, сдвиг
    "turn": 0.35, "tilt": 0.0, "hdy": 0.0,
    # Корпус
    "bdx": 0.0, "bdy": 0.0,
    # Лицо: взгляд, открытость глаз (>1 — вытаращены), подмигивание, брови, улыбка, рот, язык
    "lookx": 0.7, "looky": 0.15, "eyes": 1.0, "wink": 0.0, "brow": 0.0,
    "smile": 0.25, "mouth": 0.0, "tongue": 0.0,
    # Кружка (центр) и наклон
    "mugx": 80.0, "mugy": 174.0, "mugrot": 0.0,
    # Телефон: центр, наклон, 0 — лежит, 1 — в руках; задняя крышка к зрителю; свет экрана на лице
    "phx": 103.0, "phy": 192.0, "phrot": 0.0, "phup": 0.0, "phback": 0.0, "glow": 0.0,
    # Компьютерная мышь
    "msx": 203.0, "msy": 187.0,
    # Банан: центр, наклон, сколько съедено, очищен ли, видимость
    "bnx": 214.0, "bny": 171.0, "bnrot": 80.0, "bnbite": 0.0, "bnpeel": 0.0, "bnvis": 1.0,
    # Распечатка (или книга) со стопки: центр, 0 — лежит в стопке, 1 — в руках
    "rdx": 54.0, "rdy": 166.0, "rdup": 0.0,
    # Бумажный самолётик
    "plx": 152.0, "ply": 140.0, "plrot": 0.0, "plvis": 0.0,
    # Игрушка-дразнилка для тигрёнка (в левой руке)
    "toy": 0.0,
    # Значки и эффекты
    "zzz": 0.0, "notes": 0.0, "quest": 0.0, "bulb": 0.0, "sweat": 0.0,
    "hearts": 0.0, "excl": 0.0, "dots": 0.0, "check": 0.0, "boardcheck": 0.0, "flash": 0.0,
    # Тигрёнок: довольный (глаза-дуги) и ловит лапами
    "tiger": 0.0, "tpaw": 0.0,
}

KEYS_L = (BASE["hlx"], BASE["hly"])
KEYS_R = (BASE["hrx"], BASE["hry"])
MUG_DESK = (BASE["mugx"], BASE["mugy"])
PHONE_DESK = (BASE["phx"], BASE["phy"])
BANANA_DESK = (BASE["bnx"], BASE["bny"], BASE["bnrot"])
READ_SPOT = (BASE["rdx"], BASE["rdy"])
STICKY = (192.0, 170.0)  # стикеры на столе — для заметок
HAND_SPEED = 160.0  # пикс./с: быстрее руки при смене занятия не двигаются


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


def blip(t, at, width=0.18):
    """Короткая вспышка около момента at."""
    return max(0.0, 1.0 - abs(t - at) / width)


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
        unknown = set(changes) - set(BASE)
        assert not unknown, unknown
        current = dict(current, **changes)
        full.append((time, current))

    def at(t, pet=None):
        if t <= full[0][0]:
            return dict(full[0][1])
        for (t0, a), (t1, b) in zip(full, full[1:]):
            if t < t1:
                return mix(a, b, smooth((t - t0) / (t1 - t0)))
        return dict(full[-1][1])
    at.duration = full[-1][0]
    return at


def rotate(dx, dy, degrees):
    a = math.radians(degrees)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


# ------------------------------------------------- готовые кусочки поз

def elbows(left=None, right=None):
    """Явные локти: elbows(left=(x, y)) — левый локоть в точке, None — не трогать."""
    d = {}
    if left is not None:
        d.update(lew=1.0, lex=left[0], ley=left[1])
    if right is not None:
        d.update(rew=1.0, rex=right[0], rey=right[1])
    return d


FREE_ELBOWS = {"lew": 0.0, "rew": 0.0}
HANDS_ON_KEYS = {"hlx": KEYS_L[0], "hly": KEYS_L[1], "hrx": KEYS_R[0], "hry": KEYS_R[1],
                 "lew": 0.0, "rew": 0.0, "lb": 1.0, "rb": 1.0}
LOOK_SCREEN = {"turn": 0.35, "lookx": 0.7, "looky": 0.15}
NEUTRAL_FACE = {"eyes": 1.0, "brow": 0.0, "smile": 0.25, "mouth": 0.0, "tilt": 0.0, "hdy": 0.0,
                "bdx": 0.0, "bdy": 0.0, "wink": 0.0}


def mug_in_left(x, y, rot):
    """Кружка в левой руке: держит за ручку."""
    dx, dy = rotate(9.0, 1.0, rot)
    return {"mugx": x, "mugy": y, "mugrot": rot, "hlx": x + dx, "hly": y + dy}


def banana_in_right(x, y, rot, **extra):
    """Банан в правой руке: держит за нижний конец."""
    dx, dy = rotate(0.0, 7.0, rot)
    d = {"bnx": x, "bny": y, "bnrot": rot, "hrx": x + dx, "hry": y + dy}
    d.update(extra)
    return d


# ---------------------------------------------------------------- работа

def typing(t, pet):
    beat = t * 15.0
    p = pose(
        hlx=137 + 2.0 * math.sin(t * 3.1), hly=181 - 3.2 * max(0.0, math.sin(beat)),
        hrx=163 + 2.0 * math.sin(t * 2.6 + 1), hry=181 - 3.2 * max(0.0, math.sin(beat + math.pi)),
        turn=0.45, lookx=0.9 + 0.1 * math.sin(t * 2.0), looky=0.25,
        brow=-0.5, smile=0.05, hdy=0.6 * math.sin(t * 7.0), bdy=0.4 * math.sin(t * 7.0),
    )
    # время от времени — с размаху по Enter
    phase = t % 3.4
    if phase > 2.85:
        k = math.sin(math.pi * (phase - 2.85) / 0.55)
        p["hrx"] = 163 + 9.0 * k
        p["hry"] = 181 - 11.0 * max(0.0, math.sin(math.pi * (phase - 2.85) / 0.45))
        p["brow"] = -0.5 + 0.8 * k
    # и поглядывает на клавиатуру
    glance = pulse(t % 5.0, 1.6, 2.1, 0.15)
    p["looky"] += 0.8 * glance
    p["lookx"] -= 0.6 * glance
    return p


def mouse(t, pet):
    mx = 203 + 3.5 * math.sin(t * 2.3) + 1.5 * math.sin(t * 5.1)
    my = 186.5 + 2.0 * math.sin(t * 3.7)
    click = blip(t % 1.3, 0.65, 0.12)
    return pose(
        hrx=mx, hry=my - 2 + 1.5 * click, msx=mx, msy=my,
        hlx=138, hly=182,
        turn=0.5, lookx=0.75 + 0.25 * math.sin(t * 0.9), looky=0.05 + 0.3 * math.sin(t * 1.3),
        brow=-0.25 + 0.3 * click, smile=0.2,
    )


def scroll(t, pet):
    """Крутит колёсико — карта на мониторе приближается и отдаляется."""
    return pose(
        hrx=203, hry=184.5 + 0.8 * math.sin(t * 22.0), msx=203, msy=186.5,
        hlx=138, hly=182, turn=0.5, lookx=0.9, looky=0.1,
        eyes=1.0 + 0.15 * math.sin(t * 2.0), brow=0.35, smile=0.15, bdx=1.5,
    )


_waiting = keyframes(
    (0.0, {}),
    (6.0, {}),
    (7.0, {"hlx": 163, "hly": 151, "hrx": 137, "hry": 153, "msx": 203, "msy": 187,
           "bdy": -1.5, "bdx": 0.0, "brow": -0.5, "smile": -0.2,
           **elbows(left=(117, 160), right=(183, 160))}),
)


def thinking(t, pet):
    """QGIS занят: сперва барабанит пальцами, потом ждёт, скрестив руки, и вздыхает."""
    finger = int(t * 8) % 4
    drum = pose(
        hrx=203, hry=185, msx=203, msy=187,
        hlx=126 + finger * 2.5, hly=179 - 2.5 * abs(math.sin(t * 16.0)),
        turn=0.55, lookx=1.0, looky=0.2, brow=-0.7, smile=-0.35, bdx=2.0, hdy=1.0,
    )
    if t < 6.0:
        p = drum
    else:
        p = mix(drum, _waiting(t), smooth(t - 6.0))
        p["hdy"] += 0.7 * math.sin(t * 7.0)  # притопывает
        # каждые 6 с косится на зрителя: «ну сколько можно…»
        sigh = pulse((t - 7.0) % 6.0, 2.0, 3.6, 0.3) if t > 9.0 else 0.0
        p["turn"] += (0.0 - p["turn"]) * sigh
        p["lookx"] += (0.0 - p["lookx"]) * sigh
        p["mouth"] = 0.25 * sigh
        p["dots"] = sigh
    p["sweat"] = smooth((t - 4.0) / 0.6)
    return p


# ------------------------------------------------- работает без нажатий

def read(t, pet):
    """Читает с экрана: глаза бегут по строчкам."""
    line = (t * 0.9) % 1.0
    row = int(t * 0.9) % 4
    return pose(
        turn=0.45, lookx=0.45 + 0.55 * smooth(line * 1.25), looky=-0.1 + row * 0.12,
        hdy=0.5 * math.sin(t * 0.9), brow=-0.15,
    )


chin = keyframes(
    (0.0, {}),
    (0.9, {"hrx": 156, "hry": 120, "tilt": 7, "brow": -0.3, "smile": 0.0,
           "turn": 0.4, "lookx": 0.85, "looky": 0.05, **elbows(right=(176, 166))}),
    (5.6, {"lookx": 0.95, "looky": 0.25}),
    (6.5, {**HANDS_ON_KEYS, "tilt": 0, "brow": 0, "smile": 0.25}),
    (7.0, {}),
)


scratch = keyframes(
    (0.0, {}),
    (0.8, {"hrx": 166, "hry": 62, "brow": 0.5, "smile": -0.1, "mouth": 0.12,
           "lookx": 0.4, "looky": -0.5, "tilt": 5, **elbows(right=(198, 104))}),
    (3.2, {}),
    (4.0, {**HANDS_ON_KEYS, "brow": 0, "smile": 0.25, "mouth": 0, "tilt": 0, **LOOK_SCREEN}),
)


def scratch_head(t, pet):
    p = scratch(t)
    k = pulse(t, 0.8, 3.2, 0.2)
    p["hrx"] += 3.0 * math.sin(t * 18.0) * k
    p["hry"] += 1.5 * math.sin(t * 9.0) * k
    p["quest"] = 0.8 * pulse(t, 1.0, 3.2)
    return p


lean = keyframes(
    (0.0, {}),
    (0.9, {"bdx": 4.0, "hdy": 3.0, "turn": 0.65, "lookx": 1.0, "looky": 0.2,
           "eyes": 0.55, "brow": -0.9, "smile": -0.1}),
    (3.8, {"eyes": 0.5}),
    (4.4, {"eyes": 1.15, "brow": 0.6, "smile": 0.5, "bdx": 0.0, "hdy": 0.0}),
    (5.2, {**NEUTRAL_FACE, **LOOK_SCREEN}),
)


_notes = keyframes(
    (0.0, {}),
    (0.8, {"hrx": STICKY[0] - 1, "hry": STICKY[1] - 3, "pen": 1.0, "lookx": 0.6, "looky": 1.0,
           "turn": 0.5, "hdy": 2.0, "brow": -0.3, **elbows(right=(190, 146))}),
    (4.6, {}),
    (5.4, {**HANDS_ON_KEYS, "pen": 0.0, "hdy": 0.0, "brow": 0.0, **LOOK_SCREEN}),
)


def notes(t, pet):
    """Записывает что-то на стикер."""
    p = _notes(t)
    k = pulse(t, 0.9, 4.6, 0.2)
    p["hrx"] += (2.5 * math.sin(t * 9.0) + ((t * 1.2) % 1.0) * 4.0 - 2.0) * k
    p["hry"] += 1.2 * math.sin(t * 15.0) * k
    return p


def neck(t, pet):
    """Разминает шею."""
    k = pulse(t, 0.0, 3.4, 0.5)
    return pose(
        tilt=12.0 * math.sin(t * 2.4) * k, hdy=1.5 * abs(math.sin(t * 2.4)) * k,
        eyes=1.0 - k, smile=0.25 + 0.3 * k, turn=0.35 * (1 - k), lookx=0.7 * (1 - k),
    )


# ---------------------------------------------------------------- свои дела

window = keyframes(
    (0.0, {}),
    (1.2, {"turn": -0.9, "lookx": -1.0, "looky": -0.45, "brow": 0.3, "smile": 0.45,
           "hlx": 145, "hly": 120, "tilt": -7, **elbows(left=(124, 166))}),
    (2.0, {"eyes": 0.8}),
    (6.5, {"eyes": 0.75, "smile": 0.6}),
    (7.4, {"eyes": 1.0}),
    (8.4, {**HANDS_ON_KEYS, **NEUTRAL_FACE, **LOOK_SCREEN}),
    (9.0, {}),
)

_phone_frames = keyframes(
    (0.0, {}),
    (0.9, {"hlx": 104, "hly": 189, "lookx": -0.4, "looky": 0.8, "turn": -0.1}),
    (1.4, {"phx": 112, "phy": 174, "phup": 0.4, "hlx": 113, "hly": 172}),
    (2.2, {"phx": 150, "phy": 147, "phup": 1.0, "glow": 1.0,
           "hlx": 141, "hly": 156, "hrx": 159, "hry": 156,
           "lookx": 0.0, "looky": 1.0, "turn": 0.0, "hdy": 3.0, "smile": 0.3,
           **elbows(left=(120, 166), right=(180, 166))}),
    (5.0, {}),
    (5.6, {"smile": 0.9, "mouth": 0.35, "brow": 0.4}),
    (6.8, {}),
    (7.4, {"smile": 0.3, "mouth": 0.0, "brow": 0.0}),
    (10.0, {}),
    (10.6, {"phx": 112, "phy": 174, "phup": 0.4, "glow": 0.0, "hlx": 113, "hly": 172,
            "hrx": KEYS_R[0], "hry": KEYS_R[1], "hdy": 0.0, "lookx": -0.3, "looky": 0.8,
            **FREE_ELBOWS}),
    (11.2, {"phx": PHONE_DESK[0], "phy": PHONE_DESK[1], "phup": 0.0, "hlx": 105, "hly": 189}),
    (12.0, {**HANDS_ON_KEYS, **LOOK_SCREEN, "smile": 0.25}),
)


def phone(t, pet):
    p = _phone_frames(t)
    k = pulse(t, 2.2, 10.0, 0.2)
    # листает ленту большим пальцем
    p["hry"] += 2.0 * max(0.0, math.sin(t * 4.0)) * k
    p["hdy"] += 0.4 * math.sin(t * 1.3) * k
    return p


_coffee_frames = keyframes(
    (0.0, {}),
    (0.9, {**mug_in_left(*MUG_DESK, 0), "lookx": -0.6, "looky": 0.7, "turn": -0.2}),
    (1.7, {**mug_in_left(122, 150, 0), "lookx": -0.4, "looky": 0.6, "turn": -0.1,
           **elbows(left=(116, 168))}),
    (2.4, {**mug_in_left(135, 113, 0), "lookx": -0.2, "looky": 0.6, "turn": 0.0,
           "mouth": 0.22, "smile": 0.0, **elbows(left=(120, 158))}),
    (3.2, {}),
    (3.8, {**mug_in_left(139, 108, 24), "eyes": 0.0, "mouth": 0.0, "smile": 0.2, "tilt": -4,
           **elbows(left=(121, 156))}),
    (5.2, {}),
    (5.9, {**mug_in_left(124, 142, 0), "eyes": 1.0, "tilt": 0, "smile": 0.9, "brow": 0.45,
           "lookx": -0.3, "looky": 0.5, **elbows(left=(114, 168))}),
    (7.0, {}),
    (7.9, {**mug_in_left(*MUG_DESK, 0), "smile": 0.4, "brow": 0.0, **FREE_ELBOWS}),
    (8.6, {**HANDS_ON_KEYS, **LOOK_SCREEN, "smile": 0.25}),
)


def coffee(t, pet):
    """Дует на горячий кофе, отпивает с закрытыми глазами и довольно выдыхает."""
    p = _coffee_frames(t)
    p["mouth"] += 0.06 * math.sin(t * 12.0) * pulse(t, 2.4, 3.2, 0.1)  # дует
    return p


stretch = keyframes(
    (0.0, {}),
    (0.6, {"hlx": 140, "hly": 150, "hrx": 160, "hry": 150}),
    (1.3, {"hlx": 114, "hly": 44, "hrx": 186, "hry": 44,
           "eyes": 0.0, "mouth": 1.0, "hdy": -2, "bdy": -3, "turn": 0.0, "brow": 0.6}),
    (2.6, {"tilt": 5}),
    (3.1, {"tilt": -3}),
    (3.9, {"hlx": 140, "hly": 150, "hrx": 160, "hry": 150,
           "eyes": 1.0, "mouth": 0.0, "hdy": 0, "bdy": 0, "tilt": 0, "brow": 0, "smile": 0.5}),
    (4.7, {**HANDS_ON_KEYS, **LOOK_SCREEN, "smile": 0.25}),
)

_BD = BANANA_DESK
_banana_frames = keyframes(
    (0.0, {}),
    (0.9, {**banana_in_right(*_BD), "lookx": 1.0, "looky": 0.6, "turn": 0.5, "smile": 0.6,
           "brow": 0.4}),
    (1.8, {**banana_in_right(178, 128, -10), "lookx": 0.6, "looky": 0.0, "turn": 0.3,
           **elbows(right=(186, 166))}),
    (2.3, {"hlx": 176, "hly": 120, **elbows(left=(140, 162))}),
    (3.3, {"hlx": 170, "hly": 140, "bnpeel": 1.0}),
    (3.9, {"hlx": KEYS_L[0], "hly": KEYS_L[1], "lew": 0.0,
           **banana_in_right(163, 103, -40), "lookx": 0.3, "looky": 0.3, "turn": 0.2,
           "smile": 0.3, **elbows(right=(184, 156))}),
    (4.2, {"mouth": 0.5}),
    (4.4, {"mouth": 0.0, "bnbite": 0.3}),
    (5.4, {"mouth": 0.5}),
    (5.6, {"mouth": 0.0, "bnbite": 0.6}),
    (6.6, {"mouth": 0.5}),
    (6.8, {"mouth": 0.0, "bnbite": 0.9}),
    (7.8, {**banana_in_right(178, 128, 20), "smile": 0.9, "eyes": 0.7,
           **elbows(right=(188, 162))}),
    (8.4, {**banana_in_right(205, 228, 120), "bnvis": 0.0, "rew": 0.0}),
    (8.6, {"bnx": _BD[0], "bny": _BD[1], "bnrot": _BD[2], "bnbite": 0.0, "bnpeel": 0.0,
           "hrx": KEYS_R[0], "hry": KEYS_R[1]}),
    (9.4, {**LOOK_SCREEN, **NEUTRAL_FACE}),
    (10.4, {"bnvis": 1.0}),
)


def banana(t, pet):
    """Чистит банан и ест его, довольно жуя; шкурку — в корзину."""
    p = _banana_frames(t)
    k = pulse(t, 4.0, 7.6, 0.2)
    p["mouth"] = max(p["mouth"], 0.18 * k * max(0.0, math.sin(t * 9.0)))  # жуёт
    p["hdy"] += 0.6 * math.sin(t * 9.0) * k
    return p


_read_frames = keyframes(
    (0.0, {}),
    (1.0, {"hlx": READ_SPOT[0] + 4, "hly": READ_SPOT[1] + 2, "lookx": -1.0, "looky": 0.7,
           "turn": -0.5, "bdx": -3.0}),
    (1.9, {"rdx": 104, "rdy": 148, "rdup": 0.7, "hlx": 92, "hly": 152, "bdx": -1.0,
           **elbows(left=(104, 172))}),
    (2.6, {"rdx": 150, "rdy": 141, "rdup": 1.0, "hlx": 135, "hly": 147, "hrx": 165, "hry": 147,
           "bdx": 0.0, "turn": 0.0, "lookx": 0.0, "looky": 0.85, "hdy": 2.0,
           **elbows(left=(118, 168), right=(182, 168))}),
    (5.6, {}),
    (6.2, {"brow": 0.7, "eyes": 1.15, "mouth": 0.2}),
    (7.0, {"brow": 0.2, "eyes": 1.0, "mouth": 0.0, "smile": 0.6}),
    (8.4, {}),
    (9.2, {"rdx": 104, "rdy": 148, "rdup": 0.7, "hlx": 92, "hly": 152,
           "hrx": KEYS_R[0], "hry": KEYS_R[1], "rew": 0.0, "lookx": -0.8, "looky": 0.5,
           "turn": -0.4, "hdy": 0.0, "bdx": -1.0, **elbows(left=(104, 172))}),
    (10.0, {"rdx": READ_SPOT[0], "rdy": READ_SPOT[1], "rdup": 0.0,
            "hlx": READ_SPOT[0] + 4, "hly": READ_SPOT[1] + 2, "bdx": -3.0, "lew": 0.0}),
    (10.9, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE}),
)


def read_doc(t, pet):
    """Берёт со стопки распечатку (или книгу) и читает."""
    p = _read_frames(t)
    k = pulse(t, 2.6, 8.4, 0.3)
    line = (t * 0.7) % 1.0
    p["lookx"] += (-0.5 + line) * 0.8 * k
    p["looky"] += (int(t * 0.7) % 3) * 0.08 * k
    return p


_selfie_frames = keyframes(
    (0.0, {}),
    (0.9, {"hlx": 104, "hly": 189, "lookx": -0.4, "looky": 0.8, "turn": -0.1}),
    (1.5, {"phx": 112, "phy": 160, "phup": 0.7, "hlx": 113, "hly": 166}),
    (2.2, {"phx": 108, "phy": 70, "phup": 1.0, "phback": 1.0, "phrot": -8,
           "hlx": 109, "hly": 79, "lookx": -0.9, "looky": -0.9, "turn": -0.4,
           "smile": 0.6, **elbows(left=(103, 112))}),
    (2.8, {"hrx": 182, "hry": 84, "rpeace": 1.0, "tilt": -9, "smile": 1.0, "wink": 1.0,
           "tongue": 0.6, **elbows(right=(198, 124))}),
    (5.4, {}),
    (6.0, {"hrx": KEYS_R[0], "hry": KEYS_R[1], "rpeace": 0.0, "rew": 0.0, "tilt": 0,
           "wink": 0.0, "tongue": 0.0, "phx": 128, "phy": 128, "phrot": 0, "hlx": 129,
           "hly": 136, "lookx": -0.4, "looky": 0.6, "turn": -0.2,
           **elbows(left=(112, 160))}),
    (7.2, {"hearts": 0.0, "smile": 0.9}),
    (7.8, {"phx": 112, "phy": 170, "phup": 0.6, "phback": 0.0, "hlx": 113, "hly": 177,
           "lew": 0.0}),
    (8.4, {"phx": PHONE_DESK[0], "phy": PHONE_DESK[1], "phup": 0.0, "hlx": 105, "hly": 189}),
    (9.2, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE}),
)


def selfie(t, pet):
    """Селфи с «мир» и подмигиванием — со вспышкой."""
    p = _selfie_frames(t)
    p["flash"] = blip(t, 3.6, 0.15) + blip(t, 4.7, 0.15)
    return p


relax = keyframes(
    (0.0, {}),
    (0.6, {"hlx": 132, "hly": 112, "hrx": 168, "hry": 112}),
    (0.7, {"armsback": 1.0}),
    (1.4, {"hlx": 127, "hly": 76, "hrx": 173, "hry": 76,
           "bdy": -2.0, "hdy": -1.0, "turn": 0.0, "lookx": 0.0, "looky": -0.2,
           "eyes": 0.0, "smile": 0.75, **elbows(left=(104, 94), right=(196, 94))}),
    (6.0, {}),
    (6.6, {"hlx": 132, "hly": 112, "hrx": 168, "hry": 112, "eyes": 1.0,
           "bdy": 0.0, "hdy": 0.0, **FREE_ELBOWS}),
    (6.7, {"armsback": 0.0}),
    (7.4, {**HANDS_ON_KEYS, **LOOK_SCREEN, "smile": 0.25}),
)


board = keyframes(
    (0.0, {}),
    (1.0, {"turn": 0.75, "lookx": 1.0, "looky": -1.0, "brow": 0.3, "tilt": 4}),
    (1.8, {"hrx": 202, "hry": 66, **elbows(right=(198, 112))}),
    (2.6, {"hry": 70}),
    (3.0, {"hry": 64, "boardcheck": 1.0, "smile": 0.8}),
    (3.6, {"hdy": 2.0}),
    (3.9, {"hdy": -1.0}),
    (4.2, {"hdy": 1.5}),
    (4.6, {"hdy": 0.0}),
    (5.4, {**HANDS_ON_KEYS, **LOOK_SCREEN, "brow": 0.0, "tilt": 0, "boardcheck": 0.0}),
    (6.0, {"smile": 0.4}),
)


# ------------------------------------------------- любимые дела питомцев

_tiger_frames = keyframes(
    (0.0, {}),
    (1.0, {"hlx": 106, "hly": 140, "turn": -0.35, "lookx": -0.6, "looky": 0.8,
           "smile": 0.85, "brow": 0.3, "tiger": 1.0, "tilt": -5, **elbows(left=(120, 166))}),
    (8.2, {}),
    (9.2, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE, "tiger": 0.0}),
)


def tiger(t, pet):
    """Гладит тигрёнка, а тот жмурится от удовольствия."""
    p = _tiger_frames(t)
    k = pulse(t, 1.0, 8.2)
    p["hlx"] += 6.0 * math.sin(t * 3.2) * k
    p["hly"] += 1.5 * math.sin(t * 6.4) * k
    p["hearts"] = pulse(t, 2.0, 7.8)
    return p


_tiger_play_frames = keyframes(
    (0.0, {}),
    (1.0, {"hlx": 108, "hly": 108, "toy": 1.0, "turn": -0.4, "lookx": -0.7, "looky": 0.6,
           "smile": 0.9, "brow": 0.4, "tilt": -4, **elbows(left=(110, 146))}),
    (1.6, {"tpaw": 1.0}),
    (8.0, {}),
    (8.6, {"tpaw": 0.0}),
    (9.4, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE, "toy": 0.0}),
)


def tiger_play(t, pet):
    """Дразнит тигрёнка игрушкой на верёвочке, тот ловит её лапами."""
    p = _tiger_play_frames(t)
    k = pulse(t, 1.0, 8.4, 0.3)
    p["hlx"] += 7.0 * math.sin(t * 2.2) * k
    p["hly"] += 4.0 * math.sin(t * 4.4) * k
    p["mouth"] = 0.3 * k * max(0.0, math.sin(t * 2.2))  # смеётся
    return p


_daydream_frames = keyframes(
    (0.0, {}),
    (1.2, {"hrx": 157, "hry": 120, "turn": -0.2, "lookx": -0.4, "looky": -0.7,
           "eyes": 0.75, "smile": 0.65, "brow": 0.35, **elbows(right=(177, 166))}),
    (9.0, {}),
    (10.0, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE}),
)


def daydream(t, pet):
    """Подпёрла щёку и мечтает под музыку в наушниках."""
    p = _daydream_frames(t)
    k = pulse(t, 1.2, 9.0)
    p["tilt"] = 7.0 * k + 5.0 * math.sin(t * 2.4) * k
    p["notes"] = k
    return p


def dance(t, pet):
    """Танцует на стуле под музыку в наушниках."""
    k = pulse(t, 0.0, 8.4, 0.8)
    beat = t * 4.2
    p = pose()
    p.update(
        hlx=137 + (136 - 137) * k, hly=181 + (150 - 181) * k - 9.0 * max(0.0, math.sin(beat)) * k,
        hrx=163 + (164 - 163) * k, hry=181 + (150 - 181) * k
        - 9.0 * max(0.0, math.sin(beat + math.pi)) * k,
        bdx=3.0 * math.sin(beat / 2) * k, tilt=8.0 * math.sin(beat / 2) * k,
        hdy=1.5 * abs(math.sin(beat)) * k, eyes=1.0 - k, smile=0.25 + 0.75 * k,
        mouth=0.25 * k, turn=0.35 * (1 - k), lookx=0.7 * (1 - k), notes=k,
        lew=k, lex=114, ley=152, rew=k, rex=186, rey=152,
    )
    return p


_ponder_frames = keyframes(
    (0.0, {}),
    (1.0, {"hrx": 153, "hry": 117, "turn": 0.3, "lookx": 0.6, "looky": -0.8, "brow": 0.5,
           "smile": 0.0, **elbows(right=(175, 165))}),
    (6.6, {}),
    (7.2, {"smile": 0.85, "brow": 0.8, "eyes": 1.15, "looky": -0.2}),
    (9.0, {}),
    (10.0, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE}),
)


def ponder(t, pet):
    """Задумчиво чешет подбородок — и тут приходит идея."""
    p = _ponder_frames(t)
    p["hrx"] += 3.0 * math.sin(t * 3.5) * pulse(t, 1.0, 6.6)
    p["quest"] = pulse(t, 2.0, 6.6)
    p["bulb"] = pulse(t, 7.0, 9.4)
    p["hdy"] += 1.5 * math.sin(t * 6.0) * pulse(t, 7.2, 8.4, 0.2)  # кивает
    return p


_plane_frames = keyframes(
    (0.0, {}),
    (0.8, {"hlx": 145, "hly": 146, "hrx": 158, "hry": 146, "plx": 152, "ply": 140,
           "lookx": 0.0, "looky": 0.9, "turn": 0.0, "brow": -0.3,
           **elbows(left=(120, 168), right=(180, 168))}),
    (1.2, {"plvis": 1.0}),
    (2.4, {}),
    (3.0, {"hrx": 182, "hry": 108, "plx": 186, "ply": 101, "plrot": -15,
           "hlx": KEYS_L[0], "hly": KEYS_L[1], "lew": 0.0, "lookx": 0.8, "looky": -0.6,
           "turn": 0.4, "brow": 0.2, "smile": 0.5, **elbows(right=(196, 146))}),
    (3.4, {"hrx": 176, "hry": 116}),
    (3.7, {"hrx": 196, "hry": 92}),
)


def plane(t, pet):
    """Складывает бумажный самолётик и запускает его через весь кабинет."""
    p = _plane_frames(t)
    if t >= 3.7:
        u = clamp((t - 3.7) / 3.2)
        p["plx"] = 196 - 230 * u
        p["ply"] = 92 - 34 * math.sin(math.pi * u) + 18 * u + 4 * math.sin(u * 14)
        p["plrot"] = 180 + 25 * math.cos(math.pi * u) - 12 * math.sin(u * 14)
        p["plvis"] = 1.0 - smooth((u - 0.85) / 0.15)
        follow = clamp((p["plx"] - 150) / 60.0, -1.0, 1.0)
        back = smooth((t - 4.3) / 0.8)
        p["hrx"] += (KEYS_R[0] - p["hrx"]) * back
        p["hry"] += (KEYS_R[1] - p["hry"]) * back
        p["rew"] *= 1.0 - back
        p["lookx"] = follow
        p["looky"] = clamp((p["ply"] - 80) / 30.0, -1.0, 0.6)
        p["turn"] = 0.8 * follow
        p["smile"] = 0.5 + 0.4 * u
        p["mouth"] = 0.25 * pulse(t, 4.0, 5.6, 0.3)
        settle = smooth((t - 7.4) / 1.0)
        for key in ("lookx", "looky", "turn"):
            p[key] += (BASE[key] - p[key]) * settle
        p["smile"] += (0.25 - p["smile"]) * smooth((t - 8.6) / 0.8)
        p["brow"] = 0.2 * (1 - settle)
    return p


# ---------------------------------------------------------------- реакции, сон

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
        hrx=193 + 7.0 * math.sin(t * 13.0), hry=78 + 2.0 * math.sin(t * 26.0),
        turn=0.0, lookx=0.0, looky=0.0, smile=1.0, mouth=0.35, brow=0.6, tilt=-4.0,
        **elbows(right=(196, 128)),
    )


saved = keyframes(
    (0.0, {}),
    (0.35, {"hrx": 188, "hry": 106, "rthumb": 1.0, "turn": 0.0, "lookx": 0.0,
            "looky": 0.0, "smile": 1.0, "wink": 1.0, "brow": 0.5, "check": 1.0,
            **elbows(right=(194, 146))}),
    (1.6, {}),
    (2.0, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE, "rthumb": 0.0, "check": 0.0}),
)

oops = keyframes(
    (0.0, {}),
    (0.4, {"hrx": 154, "hry": 82, "eyes": 1.0, "brow": 0.9, "mouth": 0.3, "smile": -0.4,
           "turn": 0.0, "lookx": 0.0, "tilt": 6, "hdy": 2.0, "sweat": 1.0,
           **elbows(right=(178, 150))}),
    (1.5, {}),
    (2.0, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE, "sweat": 0.0}),
)


class Activity:
    def __init__(self, func, duration=None, blend=0.45, screen="map"):
        self.func = func
        self.duration = duration  # None — повторяется, пока не сменят
        self.blend = blend
        self.screen = screen


ACTIVITIES = {
    # работа
    "typing": Activity(typing, blend=0.3, screen="typing"),
    "mouse": Activity(mouse, blend=0.3, screen="pan"),
    "scroll": Activity(scroll, blend=0.3, screen="zoom"),
    "thinking": Activity(thinking, blend=0.4, screen="busy"),
    # работа без нажатий
    "read": Activity(read, 6.0, blend=0.5),
    "chin": Activity(chin, chin.duration),
    "scratch": Activity(scratch_head, scratch.duration),
    "lean": Activity(lean, lean.duration),
    "notes": Activity(notes, _notes.duration),
    "neck": Activity(neck, 4.2),
    # свои дела
    "window": Activity(window, window.duration),
    "phone": Activity(phone, _phone_frames.duration),
    "coffee": Activity(coffee, _coffee_frames.duration),
    "stretch": Activity(stretch, stretch.duration),
    "banana": Activity(banana, _banana_frames.duration),
    "read_doc": Activity(read_doc, _read_frames.duration),
    "selfie": Activity(selfie, _selfie_frames.duration),
    "relax": Activity(relax, relax.duration),
    "board": Activity(board, board.duration),
    # любимые дела
    "tiger": Activity(tiger, _tiger_frames.duration),
    "tiger_play": Activity(tiger_play, _tiger_play_frames.duration),
    "daydream": Activity(daydream, _daydream_frames.duration),
    "dance": Activity(dance, 9.2),
    "ponder": Activity(ponder, _ponder_frames.duration),
    "plane": Activity(plane, 9.4),
    # реакции и сон
    "nap": Activity(nap, blend=1.2, screen="sleep"),
    "wake": Activity(wake, 0.9, blend=0.15, screen="sleep"),
    "wave": Activity(wave, 1.8, blend=0.25),
    "saved": Activity(saved, saved.duration, blend=0.2, screen="saved"),
    "oops": Activity(oops, oops.duration, blend=0.2, screen="undo"),
}

FOCUS = ["read", "chin", "scratch", "lean", "notes", "neck"]
IDLE_COMMON = ["window", "phone", "coffee", "stretch", "banana", "read_doc", "selfie",
               "relax", "board"]
REACTIONS = ["wave", "wake", "saved", "oops"]


class Animator:
    """Проигрывает анимации и плавно переводит одну в другую."""

    def __init__(self, pet, rng=None):
        self.pet = pet
        self.rng = rng or random.Random()
        self.name = None
        self.start = 0.0
        self.blend = 0.0
        self.from_pose = None
        self.next_blink = None
        self.blink_until = -1.0

    def play(self, name, now):
        if name == self.name:
            return
        self.from_pose = self.pose(now) if self.name else None
        self.name = name
        self.start = now
        self.blend = self.activity.blend
        if self.from_pose is not None:
            # далёкие руки (например, поднятые вверх) возвращаются не рывком
            target = self.activity.func(0.0, self.pet)
            reach = max(math.hypot(self.from_pose[x] - target[x], self.from_pose[y] - target[y])
                        for x, y in (("hlx", "hly"), ("hrx", "hry")))
            self.blend = max(self.blend, min(1.0, reach / HAND_SPEED))

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
        blend = self.blend
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
