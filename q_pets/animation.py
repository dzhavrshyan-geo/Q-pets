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
    # Лягушонок: очки сняты (в руках), муха и язык; лев: распушённая и взъерошенная грива
    "glassoff": 0.0, "fly": 0.0, "flyx": 236.0, "flyy": 52.0, "ftongue": 0.0,
    "puff": 0.0, "ruffle": 0.0,
    # Вещи для общих занятий: мячики для жонглирования, бумажный комок, гантель,
    # ручка, которую крутят в пальцах
    "jug": 0.0, "pbx": 150.0, "pby": 140.0, "pbvis": 0.0, "dumb": 0.0, "spin": 0.0,
    # Надписи: «Апчхи!», «Р-р-р!»
    "achoo": 0.0, "roar": 0.0,
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
    (2.2, {"phx": 150, "phy": 147, "phup": 1.0, "phback": 1.0, "glow": 1.0,
           "hlx": 141, "hly": 156, "hrx": 159, "hry": 156,
           "lookx": 0.0, "looky": 1.0, "turn": 0.0, "hdy": 3.0, "smile": 0.3,
           **elbows(left=(120, 166), right=(180, 166))}),
    (5.0, {}),
    (5.6, {"smile": 0.9, "mouth": 0.35, "brow": 0.4}),
    (6.8, {}),
    (7.4, {"smile": 0.3, "mouth": 0.0, "brow": 0.0}),
    (10.0, {}),
    (10.6, {"phx": 112, "phy": 174, "phup": 0.4, "phback": 0.0, "glow": 0.0, "hlx": 113, "hly": 172,
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


# ------------------------------------------------- ещё занятия для всех

_call_frames = keyframes(
    (0.0, {}),
    (0.9, {"hlx": 104, "hly": 189, "lookx": -0.4, "looky": 0.8, "turn": -0.1}),
    (1.4, {"phx": 112, "phy": 166, "phup": 0.6, "hlx": 113, "hly": 172}),
    (2.0, {"phx": 124, "phy": 84, "phup": 1.0, "phback": 1.0, "phrot": -14, "hlx": 126, "hly": 93,
           "tilt": -6, "turn": -0.2, "lookx": 0.4, "looky": 0.1, **elbows(left=(110, 132))}),
    (8.6, {}),
    (9.2, {"phx": 112, "phy": 170, "phup": 0.5, "phback": 0.0, "phrot": 0, "hlx": 113, "hly": 177,
           "lew": 0.0,
           "tilt": 0, "rew": 0.0, "hrx": KEYS_R[0], "hry": KEYS_R[1]}),
    (9.8, {"phx": PHONE_DESK[0], "phy": PHONE_DESK[1], "phup": 0.0, "hlx": 105, "hly": 189}),
    (10.6, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE}),
)


def call(t, pet):
    """Говорит по телефону и жестикулирует свободной рукой."""
    p = _call_frames(t)
    k = pulse(t, 2.0, 8.6, 0.4)
    talk = max(0.0, math.sin(t * 9.0)) * (0.5 + 0.5 * math.sin(t * 0.9) > 0.15)
    p["mouth"] = 0.28 * talk * k
    p["hrx"] += (174 + 9 * math.sin(t * 1.7) - p["hrx"]) * k
    p["hry"] += (150 + 10 * math.sin(t * 2.3) - p["hry"]) * k
    p["rew"] = max(p["rew"], k)
    p["rex"], p["rey"] = 190, 166
    p["brow"] = 0.5 * max(0.0, math.sin(t * 0.7)) * k
    p["smile"] = 0.25 + 0.4 * math.sin(t * 0.5) * k
    return p


def juggle(t, pet):
    """Жонглирует шишками."""
    k = pulse(t, 0.0, 7.2, 0.8)
    p = pose()
    p.update(
        hlx=137 + (134 - 137) * k, hly=181 + (150 - 181) * k - 5.0 * max(0.0, math.sin(t * 6.3)) * k,
        hrx=163 + (166 - 163) * k, hry=181 + (150 - 181) * k
        - 5.0 * max(0.0, math.sin(t * 6.3 + math.pi)) * k,
        turn=0.35 * (1 - k), lookx=0.7 * (1 - k) + 0.5 * math.sin(t * 3.15) * k,
        looky=0.15 + (-0.7 - 0.15) * k, smile=0.25 + 0.5 * k, tongue=0.6 * k,
        jug=pulse(t, 0.9, 6.9, 0.3), lew=k, lex=116, ley=160, rew=k, rex=184, rey=160,
    )
    p["smile"] += 0.3 * pulse(t, 6.9, 8.0, 0.3)
    return p


_paper_ball_frames = keyframes(
    (0.0, {}),
    (0.6, {"hlx": 145, "hly": 148, "hrx": 156, "hry": 148, "turn": 0.0, "lookx": 0.0,
           "looky": 0.9, "brow": -0.4, **elbows(left=(120, 166), right=(180, 166))}),
    (0.8, {"pbvis": 1.0, "pbx": 150.5, "pby": 146}),
    (1.8, {}),
    (2.4, {"hrx": 186, "hry": 112, "pbx": 186, "pby": 107, "hlx": KEYS_L[0], "hly": KEYS_L[1],
           "lew": 0.0, "lookx": 1.0, "looky": 0.4, "turn": 0.5, "tongue": 0.8, "brow": -0.5,
           **elbows(right=(196, 148))}),
    (2.9, {"hrx": 180, "hry": 118, "pbx": 180, "pby": 113}),
    (3.1, {"hrx": 198, "hry": 108, "tongue": 0.0}),
)


def paper_ball(t, pet):
    """Комкает бумажку и бросает её в корзину — попал!"""
    p = _paper_ball_frames(t)
    if t > 2.9:
        u = clamp((t - 2.9) / 1.0)
        p["pbx"] = 180 + 170 * u
        p["pby"] = 113 - 40 * math.sin(math.pi * u * 0.8) + 120 * u * u
        p["pbvis"] = 1.0 - smooth((u - 0.9) / 0.1)
        p["lookx"] = clamp((p["pbx"] - 150) / 60.0, -1.0, 1.0)
        p["looky"] = clamp((p["pby"] - 90) / 40.0, -1.0, 1.0)
    win = pulse(t, 4.0, 5.2, 0.25)
    p["hrx"] += (188 - p["hrx"]) * win
    p["hry"] += (92 - 4 * math.sin(t * 14) - p["hry"]) * win
    p["smile"] += (1.0 - p["smile"]) * win
    p["mouth"] = max(p["mouth"], 0.3 * win)
    back = smooth((t - 5.4) / 0.8)
    for key, value in HANDS_ON_KEYS.items():
        p[key] += (value - p[key]) * back
    for key, value in LOOK_SCREEN.items():
        p[key] += (value - p[key]) * back
    p["smile"] += (0.25 - p["smile"]) * smooth((t - 6.2) / 0.8)
    p["brow"] *= 1 - back
    return p


yawn = keyframes(
    (0.0, {}),
    (0.7, {"hlx": 147, "hly": 110, "eyes": 0.3, "turn": 0.0, "lookx": 0.0, **elbows(left=(124, 160))}),
    (1.2, {"mouth": 1.0, "eyes": 0.0, "hdy": -1.5, "tilt": -4, "brow": 0.6}),
    (2.6, {}),
    (3.2, {"mouth": 0.0, "eyes": 0.6, "hdy": 0.0, "tilt": 3, "brow": 0.0}),
    (3.6, {"tilt": -3}),
    (4.0, {"tilt": 0, "eyes": 1.0, **HANDS_ON_KEYS, **LOOK_SCREEN}),
    (4.6, {}),
)

_sneeze_frames = keyframes(
    (0.0, {}),
    (1.3, {"hdy": -3.0, "tilt": -7, "eyes": 0.0, "mouth": 0.45, "brow": 0.8, "turn": 0.0,
           "lookx": 0.0, "bdy": -1.0, "hrx": 164, "hry": 118, **elbows(right=(180, 154))}),
    (1.45, {"hdy": 4.0, "tilt": 7, "mouth": 0.6, "bdy": 1.5, "hrx": 158, "hry": 102}),
    (2.4, {"mouth": 0.0, "hdy": 1.0, "tilt": 2, "bdy": 0.0, "eyes": 0.5, "brow": 0.3}),
    (3.4, {}),
    (4.0, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE}),
)


def sneeze(t, pet):
    """«А-а-апчхи!» — и вытирает нос."""
    p = _sneeze_frames(t)
    p["achoo"] = pulse(t, 1.4, 2.6, 0.15)
    wipe = pulse(t, 2.4, 3.4, 0.2)
    p["hrx"] += 3.5 * math.sin(t * 16.0) * wipe
    return p


_dumbbell_frames = keyframes(
    (0.0, {}),
    (0.8, {"hrx": 182, "hry": 196, "lookx": 0.6, "looky": 1.0, "turn": 0.4}),
    (1.0, {"dumb": 1.0}),
    (1.7, {"hrx": 176, "hry": 162, "lookx": 0.8, "looky": 0.4, "turn": 0.5, "brow": -0.7,
           "smile": -0.2, **elbows(right=(190, 160))}),
    (6.2, {}),
    (6.8, {"hrx": 182, "hry": 196, "rew": 0.0, "smile": 0.8, "brow": 0.3}),
    (7.0, {"dumb": 0.0}),
    (7.8, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE}),
)


def dumbbell(t, pet):
    """Качает бицепс гантелей."""
    p = _dumbbell_frames(t)
    k = pulse(t, 1.7, 6.2, 0.2)
    lift = max(0.0, math.sin((t - 1.7) * 2.6))
    p["hry"] -= 34.0 * lift * k
    p["hrx"] -= 5.0 * lift * k
    p["mouth"] = 0.15 * lift * k
    p["sweat"] = pulse(t, 4.6, 6.6, 0.3)
    p["bdx"] = -1.0 * lift * k
    return p


def pen_spin(t, pet):
    """Крутит ручку в пальцах, обдумывая задачу."""
    k = pulse(t, 0.0, 5.4, 0.6)
    p = pose(turn=0.45, lookx=0.8, looky=0.0 + 0.2 * math.sin(t * 0.8), brow=-0.2 + 0.3 * k)
    p["hrx"] += (168 - p["hrx"]) * k
    p["hry"] += (158 - p["hry"]) * k
    p["rew"] = k
    p["rex"], p["rey"] = 186, 162
    p["spin"] = pulse(t, 0.5, 5.2, 0.2)
    return p


nod_off = keyframes(
    (0.0, {}),
    (2.6, {"eyes": 0.1, "hdy": 5.5, "tilt": 9, "lookx": 0.3, "looky": 0.6, "brow": 0.2,
           "mouth": 0.12}),
    (2.7, {"eyes": 1.35, "hdy": -2.0, "tilt": 0, "brow": 1.0, "excl": 1.0, "mouth": 0.3,
           "bdy": -2.0, "lookx": 0.0, "looky": 0.0, "turn": 0.0}),
    (3.4, {"tilt": -6, "excl": 0.0, "mouth": 0.0, "bdy": 0.0}),
    (3.8, {"tilt": 6}),
    (4.2, {"tilt": -3}),
    (4.8, {**LOOK_SCREEN, **NEUTRAL_FACE}),
    (5.4, {}),
)


# ------------------------------------------------- уходит из кадра и возвращается

WALK_AWAY = 262.0  # насколько отходит вправо (за край кадра)
STAND_UP = -22.0
SHOULDER_Y_ANIM = 128.0  # высота плеч, как в drawing.py


def _walk_hands(p, t, sway=1.0):
    """Руки свисают вдоль тела и качаются при ходьбе."""
    swing = 6.0 * math.sin(t * 9.0) * sway
    sx = 150.0 + p["bdx"]
    sy = SHOULDER_Y_ANIM + p["bdy"]
    return {"hlx": sx - 21 + swing, "hly": sy + 46, "hrx": sx + 21 - swing, "hry": sy + 46,
            "lew": 0.0, "rew": 0.0}


def leave(t, pet):
    """Встаёт, поворачивается и уходит вправо за край кадра."""
    stand = smooth(t / 0.8)
    walk = clamp((t - 1.1) / 2.3) ** 1.15
    p = pose(bdy=STAND_UP * stand, bdx=WALK_AWAY * walk,
             turn=0.35 + 0.65 * smooth((t - 0.8) / 0.3), lookx=1.0 * smooth((t - 0.8) / 0.3),
             looky=0.0, smile=0.35)
    p["hdy"] = -1.5 * abs(math.sin(t * 9.0)) * (walk > 0)
    push = {"hlx": 130.0, "hly": 170.0 + STAND_UP * stand * 0.3,
            "hrx": 170.0, "hry": 170.0 + STAND_UP * stand * 0.3}
    hang = _walk_hands(p, t, sway=1.0 if walk > 0 else 0.0)
    k = smooth((t - 0.7) / 0.5)
    for key in ("hlx", "hly", "hrx", "hry"):
        p[key] = push[key] + (hang[key] - push[key]) * k
    return p


def gone(t, pet):
    p = pose(bdy=STAND_UP, bdx=WALK_AWAY, turn=1.0)
    p.update(_walk_hands(p, 0.0, 0.0))
    return p


def come_back(t, pet):
    """Возвращается из-за правого края кадра и садится за стол."""
    walk = 1.0 - clamp(t / 2.3) ** 0.9
    sit = smooth((t - 2.3) / 0.8)
    p = pose(bdx=WALK_AWAY * walk, bdy=STAND_UP * (1.0 - sit),
             turn=-1.0 + 1.35 * smooth((t - 2.2) / 0.5), lookx=-1.0 + 1.7 * smooth((t - 2.2) / 0.5),
             looky=0.0 + 0.15 * sit, smile=0.4)
    p["hdy"] = -1.5 * abs(math.sin(t * 9.0)) * (walk > 0.001)
    hang = _walk_hands(p, t, sway=1.0 if walk > 0.001 else 0.0)
    k = smooth((t - 2.4) / 0.9)
    for key in ("hlx", "hly", "hrx", "hry"):
        p[key] = hang[key] + (BASE[key] - hang[key]) * k
    return p


# ------------------------------------------------- когда заходит начальник

def startle(t, pet):
    """Начальник застал врасплох: подпрыгивает от испуга."""
    jump = math.sin(math.pi * clamp(t / 0.5))
    return pose(
        bdy=-7.0 * jump, hdy=-2.0 * jump, eyes=1.4, brow=1.0, mouth=0.45, smile=-0.3,
        turn=-0.6, lookx=-1.0, looky=-0.4, excl=pulse(t, 0.0, 0.9, 0.1), sweat=1.0,
        hlx=130, hly=124, hrx=170, hry=124, **elbows(left=(112, 150), right=(188, 150)),
    )


def fake_typing(t, pet):
    """Изо всех сил делает вид, что работал всё это время, и косится на начальника."""
    p = typing(t * 1.5, pet)
    glance = pulse(t % 3.0, 1.6, 2.3, 0.15)
    p["turn"] += (-0.5 - p["turn"]) * glance
    p["lookx"] += (-1.0 - p["lookx"]) * glance
    p["looky"] += (-0.3 - p["looky"]) * glance
    p["sweat"] = 1.0
    p["smile"] = -0.25 + 0.6 * glance
    p["brow"] = -0.2 + 0.7 * glance
    return p


def listen(t, pet):
    """Слушает начальника и кивает."""
    nod = max(0.0, math.sin(t * 2.3)) ** 4
    return pose(turn=-0.75, lookx=-1.0, looky=-0.45, hdy=1.8 * nod, smile=0.35, brow=0.25)


# ------------------------------------------------- любимые дела Семы и Дениса

def fly(t, pet):
    """Лягушонок следит за мухой… и ловит её языком."""
    p = pose()
    catch = 6.0
    if t < catch:
        u = t / catch
        fx = 300 - 90 * u + 26 * math.sin(t * 2.3)
        fy = 30 + 30 * u + 16 * math.sin(t * 3.7)
    else:
        fx = 210 - 4 * math.sin(catch * 2.3)
        fy = 60 + 16 * math.sin(catch * 3.7)
    tongue = blip(t, catch + 0.1, 0.18) if t < catch + 0.1 else max(0.0, 1.0 - (t - catch - 0.1) / 0.3)
    if t >= catch + 0.1:
        # муха на кончике языка едет в рот
        mx, my = 150.0, 97.0
        fx = mx + (fx - mx) * tongue
        fy = my + (fy - my) * tongue
    hx, hy = 150.0, 86.0
    follow = 1.0 - smooth((t - 6.6) / 0.6)
    p.update(
        fly=1.0 if t < catch + 0.4 else 0.0, flyx=fx, flyy=fy,
        ftongue=tongue if t > catch - 0.1 else 0.0,
        lookx=clamp((fx - hx) / 50.0, -1, 1) * follow + 0.7 * (1 - follow),
        looky=clamp((fy - hy) / 35.0, -1, 1) * follow + 0.15 * (1 - follow),
        turn=clamp((fx - hx) / 90.0, -1, 1) * follow + 0.35 * (1 - follow),
        brow=-0.6 * pulse(t, 4.6, catch, 0.3),
        mouth=0.0, smile=0.25 + 0.75 * pulse(t, 6.6, 9.0, 0.3),
        eyes=1.0 - 0.95 * pulse(t, 6.7, 8.2, 0.2),
    )
    # довольно гладит живот
    belly = pulse(t, 7.0, 8.8, 0.4)
    p["hrx"] += (152 - p["hrx"]) * belly
    p["hry"] += (152 + 2 * math.sin(t * 7) - p["hry"]) * belly
    p["rew"] = belly
    p["rex"], p["rey"] = 180, 166
    p["fly"] = p["fly"] * clamp((t - 0.2) / 0.4)
    return p


glasses = keyframes(
    (0.0, {}),
    (0.8, {"hlx": 133, "hly": 74, "hrx": 167, "hry": 74, "turn": 0.0, "lookx": 0.0, "looky": 0.0,
           **elbows(left=(112, 124), right=(188, 124))}),
    (1.0, {"glassoff": 1.0}),
    (1.6, {"hlx": 144, "hly": 142, "hrx": 156, "hry": 142, "eyes": 0.55, "brow": -0.4,
           "looky": 0.8, **elbows(left=(118, 166), right=(182, 166))}),
    (2.0, {"mouth": 0.35}),
    (2.4, {"mouth": 0.0}),
    (5.0, {}),
    (5.6, {"hlx": 145, "hly": 112, "hrx": 155, "hry": 112, "looky": 0.4, "eyes": 0.6,
           **elbows(left=(122, 160), right=(178, 160))}),
    (6.4, {"hlx": 133, "hly": 74, "hrx": 167, "hry": 74, "looky": 0.0,
           **elbows(left=(112, 124), right=(188, 124))}),
    (6.6, {"glassoff": 0.0, "eyes": 1.0, "brow": 0.2}),
    (7.4, {"hlx": KEYS_L[0], "hly": KEYS_L[1], "lew": 0.0, "hrx": 150, "hry": 72,
           **elbows(right=(176, 120))}),
    (8.0, {"smile": 0.8}),
    (8.8, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE}),
)


def clean_glasses(t, pet):
    """Снимает очки, дышит на них, протирает и надевает обратно."""
    p = glasses(t)
    wipe = pulse(t, 2.4, 5.0, 0.2)
    p["hlx"] += 4.0 * math.sin(t * 10.0) * wipe
    p["hrx"] -= 3.0 * math.sin(t * 10.0) * wipe
    return p


def mane(t, pet):
    """Ерошит и распушает гриву, потом встряхивает головой."""
    k = pulse(t, 0.0, 5.0, 0.8)
    p = pose(turn=0.0, lookx=0.0, looky=-0.2, eyes=1.0 - 0.95 * k, smile=0.25 + 0.6 * k)
    p["hlx"] += (121 - p["hlx"]) * k
    p["hly"] += (82 + 4 * math.sin(t * 13) - p["hly"]) * k
    p["hrx"] += (179 - p["hrx"]) * k
    p["hry"] += (82 - 4 * math.sin(t * 13) - p["hry"]) * k
    p.update(lew=k, lex=104, ley=124, rew=k, rex=196, rey=124)
    p["ruffle"] = pulse(t, 0.6, 5.0, 0.4)
    shake = pulse(t, 5.0, 6.4, 0.2)
    p["tilt"] = 9.0 * math.sin(t * 16.0) * shake
    p["puff"] = pulse(t, 4.6, 7.0, 0.5)
    p["smile"] += 0.5 * pulse(t, 6.2, 7.6, 0.3)
    return p


roar = keyframes(
    (0.0, {}),
    (0.8, {"bdy": -2.0, "hdy": -2.0, "eyes": 1.2, "brow": -0.5, "turn": 0.0, "lookx": 0.0,
           "looky": 0.0}),
    (1.3, {"mouth": 1.0, "puff": 1.0, "roar": 1.0, "eyes": 0.35, "brow": -1.0, "bdy": -3.0,
           "hlx": 121, "hly": 98, "hrx": 179, "hry": 98, **elbows(left=(106, 136), right=(194, 136))}),
    (2.6, {}),
    (3.0, {"mouth": 0.0, "puff": 0.25, "roar": 0.0, "eyes": 0.6, "brow": 0.6, "bdy": 0.0,
           "hdy": 0.0, "smile": 0.7, "hlx": KEYS_L[0], "hly": KEYS_L[1], "lew": 0.0,
           "hrx": 167, "hry": 62, **elbows(right=(196, 106)), "tilt": 6}),
    (4.4, {}),
    (5.2, {**HANDS_ON_KEYS, **LOOK_SCREEN, **NEUTRAL_FACE, "puff": 0.0}),
)


def roar_shy(t, pet):
    """Грозно рычит «Р-р-р!» — и сам смущается."""
    p = roar(t)
    k = pulse(t, 3.0, 4.4, 0.3)
    p["hrx"] += 3.0 * math.sin(t * 16) * k  # смущённо чешет затылок
    return p



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
    "pen_spin": Activity(pen_spin, 6.0),
    "nod_off": Activity(nod_off, nod_off.duration),
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
    "call": Activity(call, _call_frames.duration),
    "juggle": Activity(juggle, 8.0),
    "paper_ball": Activity(paper_ball, 7.0),
    "yawn": Activity(yawn, yawn.duration),
    "sneeze": Activity(sneeze, _sneeze_frames.duration),
    "dumbbell": Activity(dumbbell, _dumbbell_frames.duration),
    # уходит из кадра: встаёт и уходит → пусто → возвращается
    "leave": Activity(leave, 3.4, blend=0.4),
    "gone": Activity(gone, blend=0.05),
    "return": Activity(come_back, 3.3, blend=0.05),
    # любимые дела
    "tiger": Activity(tiger, _tiger_frames.duration),
    "tiger_play": Activity(tiger_play, _tiger_play_frames.duration),
    "daydream": Activity(daydream, _daydream_frames.duration),
    "dance": Activity(dance, 9.2),
    "ponder": Activity(ponder, _ponder_frames.duration),
    "plane": Activity(plane, 9.4),
    "fly": Activity(fly, 9.4),
    "glasses": Activity(clean_glasses, glasses.duration),
    "mane": Activity(mane, 7.8),
    "roar": Activity(roar_shy, roar.duration),
    # реакции и сон
    "nap": Activity(nap, blend=1.2, screen="sleep"),
    "wake": Activity(wake, 0.9, blend=0.15, screen="sleep"),
    "wave": Activity(wave, 1.8, blend=0.25),
    "saved": Activity(saved, saved.duration, blend=0.2, screen="saved"),
    "oops": Activity(oops, oops.duration, blend=0.2, screen="undo"),
    # начальник в кабинете
    "startle": Activity(startle, 1.0, blend=0.12),
    "fake_typing": Activity(fake_typing, blend=0.25, screen="typing"),
    "listen": Activity(listen, blend=0.5),
}

FOCUS = ["read", "chin", "scratch", "lean", "notes", "neck", "pen_spin", "nod_off"]
IDLE_COMMON = ["window", "phone", "coffee", "stretch", "banana", "read_doc", "selfie",
               "relax", "board", "call", "juggle", "paper_ball", "yawn", "sneeze", "dumbbell"]
AWAY = ["leave", "gone", "return"]
# Эти занятия не прерываются нажатиями — сначала доигрываются до конца
REACTIONS = ["wave", "wake", "saved", "oops", "startle", "leave", "return"]


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
