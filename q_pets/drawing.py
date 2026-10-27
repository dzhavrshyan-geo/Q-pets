# -*- coding: utf-8 -*-
"""Рисование сцены: кабинет, стол, компьютер и сам питомец.

Сцена рисуется в логических координатах 320×240 (масштабирует pet_widget.py).
Слева — окно в лес, справа — монитор с QGIS, в центре за столом — питомец.
Руки — мягкие дуги от плеча к кисти через локоть (arm_curve).
"""

import math
import random

from qgis.PyQt.QtCore import QPointF, QRectF, Qt
from qgis.PyQt.QtGui import (QBrush, QFont, QLinearGradient, QPainter, QPainterPath,
                             QRadialGradient, QTransform)

from .animation import BANANA_DESK, MUG_DESK, PHONE_DESK, STICKY
from .heads import draw_glasses, draw_head, mouth_point
from .paint import C, ellipse, fill, head_center, pen, poly
from .visitors_draw import boss_speech_anchor, draw_boss, draw_bubble, draw_fox, fox_thought_anchor

W, H = 320.0, 240.0
DESK_Y = 164.0      # задний край столешницы
DESK_FRONT = 204.0  # передний край
NECK = (150.0, 116.0)
SHOULDER_DX, SHOULDER_Y = 23.0, 128.0
ARM_LENGTH = 72.0  # длина руки: чем ближе кисть к плечу, тем сильнее изгиб
ELBOW_PULL = (0.6, 1.0)  # куда тянется локоть: наружу и вниз

# Экран монитора: прямоугольник содержимого → четырёхугольник в сцене. Монитор стоит
# справа от питомца и развёрнут к нему: левый край (у питомца) дальше от зрителя и ниже,
# правый ближе и выше, а справа виден торец корпуса
SCREEN_W, SCREEN_H = 120.0, 80.0
BEZEL_QUAD = [(214.0, 72.0), (300.0, 58.0), (300.0, 152.0), (214.0, 139.0)]
SCREEN_QUAD = [(218.0, 76.0), (296.0, 63.5), (296.0, 147.0), (218.0, 135.0)]
MONITOR_SIDE = [(300.0, 58.0), (307.0, 61.5), (307.0, 149.0), (300.0, 152.0)]
MONITOR_TOP = (257.0, 65.0, math.degrees(math.atan2(58.0 - 72.0, 300.0 - 214.0)))

# ====================================================================== сцена

def draw_scene(p, pet, pose, ctx):
    """ctx: t — время (с), screen — режим монитора, hour — час для неба за окном."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    t = ctx["t"]
    has_tiger = "tiger" in pet["specials"]
    # руки за головой — или питомец ушёл за монитор: тогда руки тоже позади вещей на столе
    arms_back = pose["armsback"] > 0.5 or pose["bdx"] > 20
    boss = ctx.get("boss")
    draw_room(p, pet, ctx)
    if boss:
        draw_boss(p, boss)
    draw_chair(p, pet)
    if pet.get("tail"):
        draw_tail(p, pet, pose, t)
    draw_body(p, pet, pose)
    if arms_back:
        draw_arms(p, pet, pose)
    draw_head(p, pet, pose, t)
    if has_tiger:
        draw_tiger(p, pose, t)
    draw_desk(p)
    draw_desk_items(p, pet, pose, ctx)
    draw_props(p, pet, pose, t, held=False)  # вещи, лежащие на столе
    if has_tiger:
        draw_tiger_paws(p, pose, t)
    if arms_back:
        draw_props(p, pet, pose, t, held=True)
    else:
        # слои: руки → вещь в руках → пальцы поверх неё
        # (иначе плечо ложится поверх кружки или книги, и вещь «проходит сквозь» питомца)
        draw_arms(p, pet, pose, hands=False)
        draw_props(p, pet, pose, t, held=True)
        draw_hands(p, pet, pose)
    if pose["toy"] > 0.01:
        draw_toy(p, pose, t)
    if pose["spin"] > 0.01:
        draw_spinning_pen(p, pose, t)
    if pose["jug"] > 0.01:
        draw_juggling(p, pose, t)
    if pose["fly"] > 0.01 or pose["ftongue"] > 0.01:
        draw_fly_and_tongue(p, pet, pose, t)
    draw_overlays(p, pet, pose, t)
    draw_speech(p, pose, ctx)


def draw_speech(p, pose, ctx):
    """Реплики начальника и питомца, мысли лисы."""
    boss, fox = ctx.get("boss"), ctx.get("fox")
    if boss:
        draw_bubble(p, boss["say"], boss_speech_anchor(boss), boss["say_a"])
        hx, hy = head_center(pose)
        draw_bubble(p, boss["reply"], (hx + 20, hy - 30), boss["reply_a"], max_w=90)
    if fox:
        draw_bubble(p, fox["think"], fox_thought_anchor(fox), fox["think_a"], thought=True,
                    max_w=104)


# ---------------------------------------------------------------- комната

def draw_room(p, pet, ctx):
    wall = C(pet["wall"])
    p.fillRect(QRectF(-2000, -2000, 4000, 2000 + DESK_Y + 1), wall)
    # плинтус-полоса и мягкая тень над столом
    g = QLinearGradient(0, DESK_Y - 24, 0, DESK_Y)
    g.setColorAt(0, C(wall.darker(100)))
    g.setColorAt(1, C(wall.darker(112)))
    p.fillRect(QRectF(-2000, DESK_Y - 24, 4000, 25), QBrush(g))
    draw_window(p, ctx)
    draw_board(p)


def sky_colors(hour):
    if 8 <= hour < 17:
        return "#7DBEEB", "#D6EDF8", "day"
    if 6 <= hour < 8 or 17 <= hour < 20:
        return "#7C78B8", "#F7BE8A", "evening"
    return "#141D3B", "#2E3A66", "night"


def draw_window(p, ctx):
    t = ctx["t"]
    x0, y0, x1, y1 = 14.0, 14.0, 106.0, 100.0
    rect = QRectF(x0, y0, x1 - x0, y1 - y0)
    top, bottom, phase = sky_colors(ctx.get("hour", 12))
    p.save()
    p.setClipRect(rect)
    g = QLinearGradient(0, y0, 0, y1)
    g.setColorAt(0, C(top))
    g.setColorAt(1, C(bottom))
    p.fillRect(rect, QBrush(g))
    if phase == "night":
        fill(p, "#FFFFFF")
        for sx, sy in ((24, 22), (40, 30), (57, 19), (75, 27), (92, 21), (33, 41), (84, 39), (66, 36)):
            ellipse(p, sx, sy, 0.8)
        fill(p, "#F4F0D8")
        ellipse(p, 88, 28, 6)
        fill(p, top)
        ellipse(p, 85, 26, 5.5)
    else:
        fill(p, "#FFF4C2" if phase == "day" else "#FFC98A")
        ellipse(p, 86, 30 if phase == "day" else 52, 7)
        for i, (cy, speed, size) in enumerate(((28, 2.2, 1.0), (42, 1.4, 0.7))):
            cx = x0 - 25 + ((t * speed + i * 57) % 140)
            fill(p, C("#FFFFFF", 210))
            ellipse(p, cx, cy, 9 * size, 4 * size)
            ellipse(p, cx + 7 * size, cy - 2 * size, 7 * size, 4.5 * size)
            ellipse(p, cx - 7 * size, cy + 0.5, 6 * size, 3 * size)
    # горы
    far = "#8FA3B8" if phase == "day" else "#7D6E93" if phase == "evening" else "#27304F"
    fill(p, far)
    p.drawPolygon(poly([(x0, 72), (26, 56), (38, 63), (56, 42), (70, 57), (86, 47), (x1, 62),
                        (x1, y1), (x0, y1)]))
    if phase != "night":
        fill(p, "#F4F7FA")
        p.drawPolygon(poly([(56, 42), (51, 48), (55, 47), (58, 50), (61, 46)]))
        p.drawPolygon(poly([(86, 47), (82, 51), (86, 50), (89, 52)]))
    # ели в два ряда
    for row, (base, dark) in enumerate(((92, "#3E6B4A"), (102, "#28503A"))):
        if phase == "night":
            dark = "#152a22"
        fill(p, dark)
        rnd = random.Random(row + 3)
        x = x0 - 6 + row * 4
        while x < x1 + 8:
            h = rnd.uniform(16, 26)
            p.drawPolygon(poly([(x, base - h), (x - 5.5, base), (x + 5.5, base)]))
            x += rnd.uniform(6, 9)
    # птицы
    for i in range(2):
        bx = x0 - 30 + ((t * 9 + i * 9) % 190)
        by = 34 + i * 6 + 2.5 * math.sin(t * 1.7 + i)
        wing = 2.5 * math.sin(t * 9 + i * 2)
        p.setPen(pen("#3B3B45" if phase != "night" else "#9AA3C0", 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath(QPointF(bx - 4, by - wing))
        path.quadTo(QPointF(bx - 2, by - 1), QPointF(bx, by))
        path.quadTo(QPointF(bx + 2, by - 1), QPointF(bx + 4, by - wing))
        p.drawPath(path)
    if ctx.get("fox"):
        draw_fox(p, ctx["fox"])  # лиса выглядывает из-за ёлок
    p.restore()
    # рама, перекладины, подоконник
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen("#F4F0E8", 4.0, Qt.PenCapStyle.SquareCap))
    p.drawRect(rect)
    p.setPen(pen("#F4F0E8", 2.4, Qt.PenCapStyle.FlatCap))
    p.drawLine(QPointF(60, y0), QPointF(60, y1))
    p.drawLine(QPointF(x0, 52), QPointF(x1, 52))
    p.setPen(pen("#CFC7B8", 0.8))
    p.drawRect(QRectF(x0 - 2, y0 - 2, x1 - x0 + 4, y1 - y0 + 4))
    fill(p, "#EFE9DD", "#CFC7B8", 0.8)
    p.drawRect(QRectF(x0 - 7, y1 + 1, x1 - x0 + 14, 5))
    # кактус на подоконнике
    fill(p, "#C9714A", "#9E5534", 0.6)
    p.drawPolygon(poly([(91, 92), (101, 92), (99, 101), (93, 101)]))
    fill(p, "#5E9B5B", "#3F7140", 0.6)
    p.drawRoundedRect(QRectF(93.5, 80, 5, 13), 2.5, 2.5)
    p.drawRoundedRect(QRectF(97.5, 84, 3.5, 6), 1.7, 1.7)


def draw_board(p):
    rect = QRectF(216, 16, 90, 44)
    fill(p, "#C79D6C", "#8B6A45", 2.0)
    p.drawRect(rect)
    # записка «Сегодня»
    p.save()
    p.translate(236, 37)
    p.rotate(-3)
    fill(p, "#FFFDF4", "#D8D2C2", 0.5)
    p.drawRect(QRectF(-16, -18, 32, 37))
    font = QFont()
    font.setPixelSize(5)
    font.setBold(True)
    p.setFont(font)
    p.setPen(pen("#3A3A3A"))
    p.drawText(QRectF(-14, -17, 30, 7), Qt.AlignmentFlag.AlignLeft, "Сегодня:")
    for i in range(4):
        y = -7 + i * 6.5
        p.setPen(pen("#4C9A48", 0.9))
        p.drawLine(QPointF(-13, y), QPointF(-12, y + 1.3))
        p.drawLine(QPointF(-12, y + 1.3), QPointF(-10, y - 1.5))
        p.setPen(pen("#9A9A9A", 0.8))
        p.drawLine(QPointF(-8, y), QPointF(-8 + (19 - i * 3), y))
    p.restore()
    # фото леса и кусочек карты
    g = QLinearGradient(0, 22, 0, 38)
    g.setColorAt(0, C("#9CC8E6"))
    g.setColorAt(1, C("#3F6E46"))
    fill(p, g, "#FFFFFF", 1.2)
    p.drawRect(QRectF(258, 21, 22, 16))
    fill(p, "#2F5A3A")
    for x in (262, 267, 272, 277):
        p.drawPolygon(poly([(x, 27), (x - 3, 37), (x + 3, 37)]))
    fill(p, "#CFE3A0", "#FFFFFF", 1.2)
    p.drawRect(QRectF(284, 25, 18, 24))
    p.setPen(pen("#C9554A", 0.7))
    p.drawPolyline(poly([(285, 33), (291, 31), (296, 38), (301, 36)]))
    p.setPen(pen("#7FA65A", 0.6))
    p.drawPolyline(poly([(289, 26), (290, 40), (294, 48)]))
    p.drawLine(QPointF(285, 43), QPointF(301, 44))
    fill(p, "#D84B4B")
    for x, y in ((236, 20), (269, 22), (293, 26)):
        ellipse(p, x, y, 1.6)


# ---------------------------------------------------------------- стул, хвост

def draw_chair(p, pet):
    g = QLinearGradient(116, 0, 184, 0)
    g.setColorAt(0, C("#2E2E34"))
    g.setColorAt(0.5, C("#3B3B42"))
    g.setColorAt(1, C("#26262B"))
    fill(p, g, "#1A1A1E", 1.0)
    p.drawRoundedRect(QRectF(116, 84, 68, 92), 15, 15)
    kind = pet.get("blanket")
    if not kind:
        return
    path = QPainterPath(QPointF(164, 86))
    path.cubicTo(QPointF(176, 82), QPointF(188, 86), QPointF(190, 96))
    path.lineTo(QPointF(193, 160))
    path.quadTo(QPointF(184, 166), QPointF(174, 160))
    path.lineTo(QPointF(170, 100))
    path.closeSubpath()
    color = {"fuzzy": "#EBAFBF", "penguins": "#F2A9BE", "forest": "#2E4A3A"}[kind]
    fill(p, color, C(color).darker(125), 1.0)
    p.drawPath(path)
    p.save()
    p.setClipPath(path)
    if kind == "fuzzy":
        p.setPen(pen(C("#FFFFFF", 90), 0.8))
        rnd = random.Random(5)
        for _ in range(40):
            x, y = rnd.uniform(166, 194), rnd.uniform(84, 164)
            p.drawLine(QPointF(x, y), QPointF(x + rnd.uniform(-1.5, 1.5), y + 2))
    elif kind == "forest":
        # вязаный плед с ёлочками
        fill(p, "#7E9C86")
        for row in range(5):
            for col in range(2):
                x = 176 + col * 9 + (row % 2) * 4
                y = 100 + row * 13
                p.drawPolygon(poly([(x, y - 5), (x - 3.5, y + 3), (x + 3.5, y + 3)]))
        p.setPen(pen(C("#FFFFFF", 30), 0.8))
        for y in range(88, 164, 4):
            p.drawLine(QPointF(164, y), QPointF(196, y + 1))
    else:
        for row in range(5):
            for col in range(2):
                x = 175 + col * 10 + (row % 2) * 5
                y = 98 + row * 14
                fill(p, "#26262B")
                ellipse(p, x, y, 3.2, 4.2)
                fill(p, "#FFFFFF")
                ellipse(p, x, y + 0.8, 2.0, 3.0)
                fill(p, "#F2A23A")
                ellipse(p, x, y - 1.3, 0.9, 0.6)
    p.restore()


def draw_tail(p, pet, pose, t):
    sway = 3.0 * math.sin(t * 1.3)
    p.save()
    p.translate(pose["bdx"], pose["bdy"])  # хвост уходит вместе с хозяином
    p.setBrush(Qt.BrushStyle.NoBrush)
    if pet.get("kind") == "lion":
        # тонкий плюшевый хвост с кисточкой
        path = QPainterPath(QPointF(176, 158))
        path.cubicTo(QPointF(198, 160), QPointF(204 + sway, 136), QPointF(198 + sway, 120))
        p.setPen(pen(C(pet["fur"]).darker(140), 5.0))
        p.drawPath(path)
        p.setPen(pen(pet["fur"], 3.4))
        p.drawPath(path)
        fill(p, pet["mane"], C(pet["mane"]).darker(130), 0.8)
        p.save()
        p.translate(198 + sway, 118)
        p.rotate(-20 + sway * 3)
        p.drawEllipse(QRectF(-4, -6, 8, 11))
        p.restore()
    else:
        path = QPainterPath(QPointF(176, 158))
        path.cubicTo(QPointF(200, 158 + sway * 0.3), QPointF(206 + sway, 128),
                     QPointF(196 + sway, 116))
        path.quadTo(QPointF(188 + sway, 110), QPointF(186 + sway * 0.8, 118))
        p.setPen(pen(C(pet["fur"]).darker(150), 7.0))
        p.drawPath(path)
        p.setPen(pen(pet["fur"], 5.0))
        p.drawPath(path)
    p.restore()


# ---------------------------------------------------------------- тело

def draw_body(p, pet, pose):
    cx = 150.0 + pose["bdx"]
    top = 117.0 + pose["bdy"]
    fur = C(pet["fur"])
    fill(p, fur)
    ellipse(p, cx, top - 2, 9, 7)  # шея
    # туловище длинное: когда питомец встаёт, ниже стола всё равно не пусто
    bottom = top + 110
    path = QPainterPath(QPointF(cx - 25, bottom))
    path.lineTo(QPointF(cx - 26, top + 14))
    path.quadTo(QPointF(cx - 26, top + 2), QPointF(cx - 13, top))
    path.lineTo(QPointF(cx + 13, top))
    path.quadTo(QPointF(cx + 26, top + 2), QPointF(cx + 26, top + 14))
    path.lineTo(QPointF(cx + 25, bottom))
    path.closeSubpath()
    clothes = pet["clothes"]
    if clothes == "sweater":
        draw_sweater(p, pet, path, cx, top)
    elif clothes == "plush":
        draw_plush_body(p, pet, path, cx, top)
    elif clothes == "suit":
        jacket = C(pet["jacket"])
        fill(p, jacket, jacket.darker(140), 1.0)
        p.drawPath(path)
        fill(p, "#F6F6F3")
        p.drawPolygon(poly([(cx - 9, top), (cx + 9, top), (cx, top + 26)]))
        fill(p, pet["tie"])
        p.drawPolygon(poly([(cx - 2.2, top + 3), (cx + 2.2, top + 3), (cx + 3, top + 22),
                            (cx, top + 26), (cx - 3, top + 22)]))
        p.setPen(pen(C("#4A4A55"), 1.0))
        p.drawLine(QPointF(cx - 9, top + 1), QPointF(cx - 2, top + 30))
        p.drawLine(QPointF(cx + 9, top + 1), QPointF(cx + 2, top + 30))
    else:
        shirt = QLinearGradient(cx - 26, 0, cx + 26, 0)
        shirt.setColorAt(0, C("#DCDCD6"))
        shirt.setColorAt(0.35, C("#F7F7F4"))
        shirt.setColorAt(1, C("#D6D6D0"))
        fill(p, shirt, "#B9B9B2", 1.0)
        p.drawPath(path)
        fill(p, pet["tie"])
        p.drawPolygon(poly([(cx - 2.2, top + 3), (cx + 2.2, top + 3), (cx + 3.2, top + 30),
                            (cx, top + 34), (cx - 3.2, top + 30)]))
        fill(p, "#FFFFFF", "#B9B9B2", 0.8)
        p.drawPolygon(poly([(cx - 10, top - 1), (cx - 1, top + 2), (cx - 6, top + 8)]))
        p.drawPolygon(poly([(cx + 10, top - 1), (cx + 1, top + 2), (cx + 6, top + 8)]))
        p.setPen(pen("#C7C7C0", 0.8))
        p.drawLine(QPointF(cx + 0.5, top + 36), QPointF(cx + 0.5, top + 60))


def draw_sweater(p, pet, path, cx, top):
    """Вязаный свитер с высоким воротом и ёлочкой."""
    knit = C(pet["jacket"])
    fill(p, knit, knit.darker(140), 1.0)
    p.drawPath(path)
    p.save()
    p.setClipPath(path)
    p.setPen(pen(C(knit.lighter(135), 90), 1.0))
    for x in range(int(cx) - 26, int(cx) + 27, 4):
        for y in range(int(top) + 4, int(top) + 70, 5):
            p.drawLine(QPointF(x, y), QPointF(x + 1.5, y + 2.5))
            p.drawLine(QPointF(x + 3, y), QPointF(x + 1.5, y + 2.5))
    p.restore()
    fill(p, "#9FBCA4")
    tx, ty = cx + 11, top + 24
    p.drawPolygon(poly([(tx, ty - 7), (tx - 4, ty), (tx + 4, ty)]))
    p.drawPolygon(poly([(tx, ty - 4), (tx - 5, ty + 4), (tx + 5, ty + 4)]))
    p.drawRect(QRectF(tx - 0.8, ty + 4, 1.6, 2))
    # высокий ворот
    collar = knit.darker(112)
    fill(p, collar, knit.darker(150), 1.0)
    p.drawRoundedRect(QRectF(cx - 16, top - 9, 32, 14), 6, 6)
    p.setPen(pen(C(knit.lighter(140), 120), 0.9))
    for x in range(-13, 14, 3):
        p.drawLine(QPointF(cx + x, top - 7), QPointF(cx + x, top + 3))


def draw_plush_body(p, pet, path, cx, top):
    """Плюшевое тельце со светлым брюшком и значком, как у игрушки."""
    fur = C(pet["fur"])
    g = QLinearGradient(cx - 26, 0, cx + 26, 0)
    g.setColorAt(0, fur.darker(108))
    g.setColorAt(0.4, C(pet["fur_light"]))
    g.setColorAt(1, fur.darker(112))
    fill(p, g, fur.darker(135), 1.0)
    p.drawPath(path)
    fill(p, "#F1DDB2")
    ellipse(p, cx - 1, top + 40, 15, 22)
    # пушок гривы на груди
    fill(p, pet["mane_light"])
    for dx in (-8, -3, 2, 7):
        ellipse(p, cx + dx, top + 2, 5, 4)
    # значок
    fill(p, "#5B5560", "#3A353D", 0.8)
    ellipse(p, cx + 12, top + 27, 6)
    fill(p, "#D99AB0")
    ellipse(p, cx + 12, top + 27, 4.3)
    p.setPen(pen("#3A353D", 0.7))
    p.drawLine(QPointF(cx + 9.5, top + 26), QPointF(cx + 14.5, top + 28))


# ---------------------------------------------------------------- тигрёнок

TIGER = (104.0, 151.0)


def draw_tiger(p, pose, t):
    x, y = TIGER
    happy = pose["tiger"]
    orange = C("#E98A2F")
    # уши
    twitch = 2.0 * max(0.0, math.sin(t * 0.9)) ** 8
    for side in (-1, 1):
        fill(p, orange, "#7A4314", 0.8)
        ellipse(p, x + side * 10, y - 10 - (twitch if side > 0 else 0), 5)
        fill(p, "#2B1C12")
        ellipse(p, x + side * 10, y - 10 - (twitch if side > 0 else 0), 2.3)
    fill(p, orange, "#7A4314", 0.9)
    ellipse(p, x, y, 14, 12.5)
    # полоски
    p.setPen(pen("#2B1C12", 1.6))
    for dx, h in ((-5, 5), (0, 6), (5, 5)):
        p.drawLine(QPointF(x + dx, y - 12), QPointF(x + dx * 0.8, y - 12 + h))
    for side in (-1, 1):
        p.drawLine(QPointF(x + side * 13.5, y - 2), QPointF(x + side * 9.5, y - 1))
        p.drawLine(QPointF(x + side * 13.5, y + 3), QPointF(x + side * 10, y + 3))
    # мордочка
    fill(p, "#FFF6EA")
    ellipse(p, x - 4, y + 5, 5.5, 4.5)
    ellipse(p, x + 4, y + 5, 5.5, 4.5)
    for side in (-1, 1):
        ex, ey = x + side * 5.5, y - 2
        if happy > 0.5:
            p.setPen(pen("#2B1C12", 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath(QPointF(ex - 2.5, ey + 0.5))
            path.quadTo(QPointF(ex, ey - 2.2), QPointF(ex + 2.5, ey + 0.5))
            p.drawPath(path)
        else:
            fill(p, "#FFFFFF")
            ellipse(p, ex, ey, 2.8, 3.0)
            up = -1.0 * pose["tpaw"]
            fill(p, "#3C5A2A")
            ellipse(p, ex + 0.3, ey + 0.3 + up, 2.0)
            fill(p, "#000000")
            ellipse(p, ex + 0.3, ey + 0.3 + up, 1.1)
            fill(p, "#FFFFFF")
            ellipse(p, ex - 0.4, ey - 0.6, 0.6)
    fill(p, "#E77C86")
    p.drawPolygon(poly([(x - 2, y + 2), (x + 2, y + 2), (x, y + 4)]))
    if happy > 0.1:
        fill(p, "#7A2830")
        ellipse(p, x, y + 7.5, 3.0 * happy, 2.6 * happy)
    else:
        p.setPen(pen("#2B1C12", 0.9))
        p.drawLine(QPointF(x, y + 4), QPointF(x, y + 6))


def draw_tiger_paws(p, pose, t):
    """Лапки на краю стола; когда тигрёнок играет — по очереди ловят игрушку."""
    x, _ = TIGER
    for i, dx in enumerate((-7, 7)):
        lift = 14.0 * pose["tpaw"] * abs(math.sin(t * 5.0 + i * 1.6))
        y = DESK_Y + 1 - lift
        fill(p, "#E98A2F", "#7A4314", 0.8)
        p.drawEllipse(QRectF(x + dx - 5, y, 10, 7))
        p.setPen(pen("#2B1C12", 1.0))
        p.drawLine(QPointF(x + dx - 1.5, y + 1), QPointF(x + dx - 1.5, y + 4))
        p.drawLine(QPointF(x + dx + 1.5, y + 1), QPointF(x + dx + 1.5, y + 4))


# ---------------------------------------------------------------- стол и вещи

def draw_desk(p):
    g = QLinearGradient(0, DESK_Y, 0, DESK_FRONT)
    g.setColorAt(0, C("#B48455"))
    g.setColorAt(1, C("#C99A68"))
    p.fillRect(QRectF(-2000, DESK_Y, 4000, DESK_FRONT - DESK_Y), QBrush(g))
    p.fillRect(QRectF(-2000, DESK_FRONT, 4000, 2000), C("#8C6240"))
    p.fillRect(QRectF(-2000, DESK_FRONT, 4000, 2.0), C("#D9AF7F"))
    p.setPen(pen(C("#A0744A", 120), 0.6))
    for y in (172, 183, 195):
        p.drawLine(QPointF(-2000, y), QPointF(2000, y))


def draw_desk_items(p, pet, pose, ctx):
    t = ctx["t"]
    if pet.get("plant") == "cactus":
        draw_cactus(p)
    else:
        draw_plant(p, t)
    extra = pet.get("desk_extra")
    if extra == "folders":
        draw_folders(p)
    elif extra == "books":
        draw_books(p)
    elif extra == "papers":
        draw_paper_stack(p)
    elif extra == "penguin":
        draw_paper_stack(p)
        draw_penguin(p, 40, 195)
    draw_monitor(p, ctx)
    if pet.get("webcam"):
        draw_webcam(p, t)
    draw_keyboard(p, ctx)
    draw_mouse(p, pose)
    draw_sticky(p)


def _moved(pose, keys, spot):
    return any(abs(pose[k] - v) > 0.5 for k, v in zip(keys, spot))


def draw_props(p, pet, pose, t, held):
    """Вещи, которые питомец берёт в руки. held=False — те, что лежат на столе (под руками),
    held=True — те, что в руках или в полёте (над руками, но под пальцами)."""
    mug_held = _moved(pose, ("mugx", "mugy", "mugrot"), MUG_DESK + (0.0,))
    phone_held = pose["phup"] > 0.05 or _moved(pose, ("phx", "phy"), PHONE_DESK)
    banana_held = _moved(pose, ("bnx", "bny", "bnrot"), BANANA_DESK)
    if held:
        draw_read_item(p, pet, pose)
    if banana_held == held:
        draw_banana(p, pose)
    if phone_held == held:
        draw_phone(p, pet, pose)
    if mug_held == held:
        draw_mug(p, pet, pose, t)
    if not held:
        return
    draw_plane(p, pose)
    if pose["glassoff"] > 0.5 and pet.get("glasses"):
        mx, my = (pose["hlx"] + pose["hrx"]) / 2, (pose["hly"] + pose["hry"]) / 2 - 3
        draw_glasses(p, [(mx - 8.5, my), (mx + 8.5, my)], mx, scale=0.62)
    if pose["pbvis"] > 0.02:
        draw_paper_ball(p, pose)
    if pose["dumb"] > 0.5:
        draw_dumbbell(p, pose)


def draw_plant(p, t):
    sway = 1.5 * math.sin(t * 0.8)
    for i, (dx, h, color) in enumerate(((-7, 22, "#4E8F4C"), (0, 30, "#3F7D3F"), (7, 24, "#5AA05A"),
                                        (-3, 18, "#6BB06A"), (4, 19, "#4A8A48"))):
        p.save()
        p.translate(18 + dx * 0.4, 152)
        p.rotate(dx * 3.5 + sway * (1 if i % 2 else -1))
        fill(p, color, C(color).darker(130), 0.6)
        p.drawEllipse(QRectF(-3.2, -h, 6.4, h))
        p.restore()
    fill(p, "#C46B40", "#94502F", 0.8)
    p.drawPolygon(poly([(7, 150), (29, 150), (26, 172), (10, 172)]))
    fill(p, "#D47B4E")
    p.drawRect(QRectF(6, 148, 24, 4))


def draw_cactus(p):
    """Кактус в зелёном горшке с ёлочками."""
    fill(p, "#6E9A4A", "#4A6E30", 0.8)
    p.drawRoundedRect(QRectF(12, 128, 12, 26), 6, 6)
    p.drawRoundedRect(QRectF(5, 136, 7, 11), 3.5, 3.5)
    p.drawRoundedRect(QRectF(7, 142, 7, 5), 2, 2)
    p.drawRoundedRect(QRectF(24, 132, 6, 10), 3, 3)
    p.drawRoundedRect(QRectF(22, 139, 6, 5), 2, 2)
    p.setPen(pen("#F3EBC8", 0.6))
    for x, y in ((14, 133), (18, 131), (21, 136), (15, 141), (20, 145), (8, 139), (27, 135),
                 (17, 149), (13, 146)):
        p.drawLine(QPointF(x, y), QPointF(x - 1.2, y - 1.2))
        p.drawLine(QPointF(x, y), QPointF(x + 1.2, y - 1.2))
    fill(p, "#E98AA6")
    ellipse(p, 18, 128, 2.2)
    fill(p, "#3D5E44", "#2A4230", 0.8)
    p.drawPolygon(poly([(7, 152), (29, 152), (27, 172), (9, 172)]))
    fill(p, "#BFD3C2")
    for x in (13, 18, 23):
        p.drawPolygon(poly([(x, 157), (x - 2.5, 163), (x + 2.5, 163)]))


def draw_webcam(p, t):
    """Веб-камера на мониторе (как у Дениса дома)."""
    x, y, angle = MONITOR_TOP
    p.save()
    p.translate(x, y - 3.5)
    p.rotate(angle)
    fill(p, "#1E1F24", "#0C0C10", 0.6)
    p.drawRoundedRect(QRectF(-11, -4, 22, 8), 3.5, 3.5)
    fill(p, "#3A4A66")
    ellipse(p, 0, 0, 2.6)
    fill(p, "#0C0C10")
    ellipse(p, 0, 0, 1.3)
    fill(p, "#4FC3F7" if int(t * 1.2) % 4 else "#1B6E95")
    ellipse(p, 7.5, 0, 0.9)
    p.restore()


def draw_folders(p):
    colors = ("#9EC6E8", "#F2D36B", "#9BD08E", "#F2A0B4")
    for i, c in enumerate(colors):
        y = 186 - i * 4.2
        fill(p, "#F7F5EF", "#CFC9BB", 0.6)
        p.drawRect(QRectF(36 + i * 0.8, y - 4, 32, 4.2))
        fill(p, c, C(c).darker(125), 0.5)
        p.drawRect(QRectF(33 + i * 0.8, y - 3.6, 9, 3.4))


def draw_books(p):
    colors = ("#2F5B45", "#356B50", "#28503D", "#3E7357")
    for i, c in enumerate(colors):
        y = 188 - i * 6
        x = 32 + (i % 2) * 2
        fill(p, c, C(c).darker(140), 0.7)
        p.drawRect(QRectF(x, y - 6, 34, 6))
        p.setPen(pen("#D9C27A", 0.6))
        p.drawLine(QPointF(x + 6, y - 3), QPointF(x + 24 - i * 2, y - 3))


def draw_paper_stack(p):
    for i in range(5):
        y = 182 - i * 2.2
        fill(p, "#FBFAF5" if i % 2 else "#F1EEE4", "#CFC9BB", 0.5)
        p.drawRect(QRectF(40 + (i % 3) * 0.7, y - 3, 30, 3))


def draw_sticky(p):
    """Стопка стикеров у клавиатуры."""
    x, y = STICKY
    fill(p, "#E8C94A", "#B89A2A", 0.5)
    p.drawPolygon(poly([(x - 6, y - 2), (x + 5, y - 3), (x + 7, y + 3), (x - 4, y + 4)]))
    fill(p, "#FBE27A", "#C9A93A", 0.5)
    p.drawPolygon(poly([(x - 6, y - 3.5), (x + 5, y - 4.5), (x + 7, y + 1.5), (x - 4, y + 2.5)]))
    p.setPen(pen("#9A8A5A", 0.5))
    p.drawLine(QPointF(x - 3, y - 2), QPointF(x + 3, y - 2.6))


def draw_read_item(p, pet, pose):
    """Распечатка карты (или книга) в руках; лёжа она — часть стопки."""
    up = pose["rdup"]
    if up < 0.02:
        return
    x, y = pose["rdx"], pose["rdy"]
    w, h = 32.0, 4.0 + 20.0 * up
    p.save()
    p.translate(x, y)
    if pet.get("read_item") == "book":
        cover = C("#2F5B45")
        fill(p, cover, cover.darker(140), 0.8)
        p.drawRoundedRect(QRectF(-w / 2 - 1.5, -h / 2 - 1, w + 3, h + 2.5), 1.5, 1.5)
        fill(p, "#FBF7EC", "#CFC6B0", 0.5)
        p.drawRect(QRectF(-w / 2, -h / 2, w / 2 - 0.4, h))
        p.drawRect(QRectF(0.4, -h / 2, w / 2 - 0.4, h))
        if up > 0.6:
            p.setPen(pen("#A8A08C", 0.6))
            for i in range(5):
                ly = -h / 2 + 3 + i * 3.4
                p.drawLine(QPointF(-w / 2 + 2, ly), QPointF(-2.5, ly))
                p.drawLine(QPointF(2.5, ly), QPointF(w / 2 - 2 - (i % 2) * 4, ly))
    else:
        fill(p, "#FFFFFF", "#CFC9BB", 0.6)
        p.drawRect(QRectF(-w / 2, -h / 2, w, h))
        if up > 0.6:
            g = QLinearGradient(0, -h / 2, 0, h / 2)
            g.setColorAt(0, C("#BFDE8C"))
            g.setColorAt(1, C("#7DB85A"))
            fill(p, g)
            p.drawRect(QRectF(-w / 2 + 2, -h / 2 + 2, 17, h - 4))
            p.setPen(pen("#C9554A", 0.6))
            p.drawPolyline(poly([(-w / 2 + 3, -2), (-w / 2 + 9, -4), (-w / 2 + 13, 3),
                                 (-w / 2 + 18, 1)]))
            p.setPen(pen("#A9A9A9", 0.7))
            for i in range(4):
                ly = -h / 2 + 4 + i * 4
                p.drawLine(QPointF(4, ly), QPointF(w / 2 - 2 - (i % 2) * 3, ly))
    p.restore()


def banana_outline(bite):
    """Банан вдоль оси y (верхушка сверху), выгнут вправо; bite — сколько откушено."""
    start = clamp01(bite) * 0.82
    left, right = [], []
    steps = 14
    for i in range(steps + 1):
        k = start + (1.0 - start) * i / steps
        cx = 4.5 * math.sin(math.pi * k)
        cy = -11.0 + 22.0 * k
        half = 0.7 + 3.3 * math.sin(math.pi * (0.08 + 0.84 * k)) ** 0.6
        left.append((cx - half, cy))
        right.append((cx + half, cy))
    return left, right, start


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def draw_banana(p, pose):
    vis = pose["bnvis"]
    if vis < 0.02:
        return
    p.save()
    p.setOpacity(vis)
    p.translate(pose["bnx"], pose["bny"])
    p.rotate(pose["bnrot"])
    peeled = pose["bnpeel"]
    left, right, start = banana_outline(pose["bnbite"])
    shape = poly(left + right[::-1])
    if peeled > 0.5:
        fill(p, "#FFF4C8", "#D9C27A", 0.7)  # мякоть
        p.drawPolygon(shape)
        # шкурка снизу и три лепестка, свисающие вниз
        lo = [pt for pt in left if pt[1] > 2]
        ro = [pt for pt in right if pt[1] > 2]
        fill(p, "#F5D03C", "#B8932A", 0.7)
        p.drawPolygon(poly(lo + ro[::-1]))
        for dx, tip in ((-4.5, (-9, 10)), (5.5, (12, 9)), (1.0, (2, 13))):
            path = QPainterPath(QPointF(dx - 1.8, 2))
            path.quadTo(QPointF(dx + tip[0] * 0.3, 8), QPointF(*tip))
            path.quadTo(QPointF(dx + tip[0] * 0.2 + 2, 6), QPointF(dx + 1.8, 2))
            p.drawPath(path)
    else:
        fill(p, "#F5D03C", "#B8932A", 0.8)
        p.drawPolygon(shape)
        p.setPen(pen("#D9B12E", 0.6))
        mid = [((a[0] + b[0]) / 2 + 1, a[1]) for a, b in zip(left, right)]
        p.drawPolyline(poly(mid[2:-2]))
        if start < 0.01:
            fill(p, "#5A4220")
            ellipse(p, left[0][0] + 0.7, -11.0, 0.9)
    fill(p, "#6B5228")
    p.drawRect(QRectF(-1.0, 10.0, 2.0, 2.4))  # хвостик
    p.restore()


def draw_plane(p, pose):
    vis = pose["plvis"]
    if vis < 0.02:
        return
    p.save()
    p.setOpacity(vis)
    p.translate(pose["plx"], pose["ply"])
    p.rotate(pose["plrot"])
    fill(p, "#FFFFFF", "#9A9A9A", 0.7)
    p.drawPolygon(poly([(10, 0), (-8, -6), (-4, 0), (-8, 2)]))
    fill(p, "#E6E6E6", "#9A9A9A", 0.7)
    p.drawPolygon(poly([(10, 0), (-4, 0), (-8, 5), (-5, 1.5)]))
    p.restore()


def draw_toy(p, pose, t):
    """Дразнилка: палочка в левой руке, на верёвочке — помпон с пёрышком."""
    a = pose["toy"]
    hx, hy = pose["hlx"], pose["hly"]
    tip = (hx - 8, hy - 6)
    swing = 5.0 * math.sin(t * 3.0)
    ball = (tip[0] + swing - 2, tip[1] + 24 + 2.0 * math.cos(t * 6.0))
    p.save()
    p.setOpacity(a)
    p.setPen(pen("#8B5A2B", 1.6))
    p.drawLine(QPointF(hx, hy), QPointF(*tip))
    p.setPen(pen("#6A6A6A", 0.6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    string = QPainterPath(QPointF(*tip))
    string.quadTo(QPointF(tip[0] + swing * 0.3, tip[1] + 14), QPointF(*ball))
    p.drawPath(string)
    fill(p, "#4FB6D8")
    p.drawEllipse(QRectF(ball[0] - 1, ball[1] + 1, 2.2, 7))
    fill(p, "#F06EA0", "#C0447A", 0.6)
    ellipse(p, ball[0], ball[1], 3.2)
    p.restore()


def draw_paper_ball(p, pose):
    p.save()
    p.setOpacity(min(1.0, pose["pbvis"]))
    x, y = pose["pbx"], pose["pby"]
    fill(p, "#F4F2EA", "#B8B2A2", 0.7)
    p.drawPolygon(poly([(x - 4.5, y - 1), (x - 2, y - 4.5), (x + 2.5, y - 4), (x + 4.8, y - 0.5),
                        (x + 3, y + 4), (x - 1.5, y + 4.6), (x - 4.6, y + 2)]))
    p.setPen(pen("#B8B2A2", 0.6))
    p.drawLine(QPointF(x - 2, y - 2), QPointF(x + 1, y + 1))
    p.drawLine(QPointF(x + 1, y - 3), QPointF(x - 0.5, y + 2.5))
    p.restore()


def draw_dumbbell(p, pose):
    x, y = pose["hrx"], pose["hry"]
    fill(p, "#5A5F68", "#2E3138", 0.8)
    p.drawRect(QRectF(x - 9, y - 0.9, 18, 1.8))
    for dx in (-9, 6):
        p.drawRoundedRect(QRectF(x + dx, y - 5, 3.4, 10), 1, 1)
        p.drawRoundedRect(QRectF(x + dx + (-1.6 if dx < 0 else 1.6), y - 3.8, 3.4, 7.6), 1, 1)


def draw_spinning_pen(p, pose, t):
    """Ручка крутится вокруг пальцев."""
    x, y = pose["hrx"], pose["hry"] - 2
    a = t * 9.0
    dx, dy = 7.0 * math.cos(a), 7.0 * math.sin(a) * 0.55
    p.save()
    p.setOpacity(pose["spin"])
    p.setPen(pen("#2E4A86", 2.0))
    p.drawLine(QPointF(x - dx, y - dy), QPointF(x + dx, y + dy))
    p.setPen(pen("#D8D8D8", 1.2))
    p.drawLine(QPointF(x + dx * 0.75, y + dy * 0.75), QPointF(x + dx, y + dy))
    p.restore()


def draw_pinecone(p, x, y, angle):
    p.save()
    p.translate(x, y)
    p.rotate(angle)
    fill(p, "#8A5A2E", "#5A3818", 0.6)
    p.drawEllipse(QRectF(-3, -4.2, 6, 8.4))
    p.setPen(pen("#5A3818", 0.5))
    for k in (-2.2, 0.0, 2.2):
        p.drawLine(QPointF(-2.6, k), QPointF(2.6, k + 1.2))
    p.restore()


def draw_juggling(p, pose, t):
    """Три шишки летают по дуге из руки в руку."""
    lx, ly = pose["hlx"], pose["hly"] - 4
    rx, ry = pose["hrx"], pose["hry"] - 4
    p.save()
    p.setOpacity(pose["jug"])
    for i in range(3):
        phase = (t * 0.95 + i / 3.0) % 1.0
        if phase < 0.5:
            u = phase * 2
            x, y = lx + (rx - lx) * u, ly + (ry - ly) * u - 38 * math.sin(math.pi * u)
        else:
            u = (phase - 0.5) * 2
            x, y = rx + (lx - rx) * u, ry + (ly - ry) * u - 10 * math.sin(math.pi * u)
        draw_pinecone(p, x, y, t * 400 + i * 90)
    p.restore()


def draw_fly_and_tongue(p, pet, pose, t):
    mx, my = mouth_point(pet, pose)
    fx, fy = pose["flyx"], pose["flyy"]
    k = pose["ftongue"]
    if k > 0.01:
        tx, ty = mx + (fx - mx) * k, my + (fy - my) * k
        p.setPen(pen("#B4505E", 4.6))
        p.drawLine(QPointF(mx, my), QPointF(tx, ty))
        p.setPen(pen("#E8798A", 3.2))
        p.drawLine(QPointF(mx, my), QPointF(tx, ty))
        fill(p, "#E8798A", "#B4505E", 0.8)
        ellipse(p, tx, ty, 3.4)
    if pose["fly"] > 0.01:
        p.save()
        p.setOpacity(pose["fly"])
        wing = 2.2 + 1.2 * math.sin(t * 60.0)
        fill(p, C("#DCEBFF", 190), C("#8AA0B8", 190), 0.5)
        ellipse(p, fx - 1.6, fy - 2.2, wing * 0.7, wing)
        ellipse(p, fx + 1.6, fy - 2.2, wing * 0.7, wing)
        fill(p, "#1E1E24")
        ellipse(p, fx, fy, 2.2, 1.8)
        fill(p, "#B33A3A")
        ellipse(p, fx + 1.6, fy - 0.4, 0.9)
        p.setPen(pen(C("#6A6A70", 120), 0.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for k2 in range(3):  # жужжит
            a = t * 3 + k2 * 2.1
            p.drawArc(QRectF(fx - 6 - k2 * 2, fy - 6 - k2 * 2, 12 + k2 * 4, 12 + k2 * 4),
                      int(math.degrees(a) * 16), 40 * 16)
        p.restore()


def draw_penguin(p, x, y):
    fill(p, "#F2A23A")
    ellipse(p, x - 3, y + 0.5, 3, 1.4)
    ellipse(p, x + 3, y + 0.5, 3, 1.4)
    fill(p, "#1F1F24", "#000000", 0.6)
    ellipse(p, x, y - 9, 7, 9.5)
    fill(p, "#FFFFFF")
    ellipse(p, x, y - 7.5, 4.5, 7)
    fill(p, "#1F1F24")
    ellipse(p, x, y - 17, 5.5, 5)
    fill(p, "#FFFFFF")
    ellipse(p, x - 2, y - 17.5, 1.5)
    ellipse(p, x + 2, y - 17.5, 1.5)
    fill(p, "#000000")
    ellipse(p, x - 1.8, y - 17.3, 0.8)
    ellipse(p, x + 2.2, y - 17.3, 0.8)
    fill(p, "#F2A23A")
    p.drawPolygon(poly([(x - 1.5, y - 15.5), (x + 1.5, y - 15.5), (x, y - 13.5)]))


def draw_keyboard(p, ctx):
    fill(p, "#2C2E33", "#17181B", 0.8)
    p.drawPolygon(poly([(118, 175), (182, 175), (187, 190), (113, 190)]))
    pressed = set()
    if ctx.get("screen") == "typing":
        rnd = random.Random(int(ctx["t"] * 15))
        pressed = {rnd.randrange(48) for _ in range(2)}
    for row in range(4):
        y = 176.8 + row * 3.3
        shrink = (3 - row) * 1.2
        x_start, x_end = 119.5 - (row * 1.2), 180.5 + (row * 1.2)
        step = (x_end - x_start) / 12.0
        for col in range(12):
            key = row * 12 + col
            fill(p, "#9FD8FF" if key in pressed else "#575B63")
            p.drawRect(QRectF(x_start + col * step + 0.4, y, step - 0.8 - shrink * 0.02, 2.4))
    fill(p, "#575B63")
    p.drawRect(QRectF(136, 190 - 2.7, 28, 1.9))


def draw_mouse(p, pose):
    fill(p, "#33333A", "#1F1F24", 0.6)
    p.drawRoundedRect(QRectF(189, 178, 30, 17), 3, 3)
    x, y = pose["msx"], pose["msy"]
    fill(p, "#E3E6EA", "#9CA1A8", 0.8)
    ellipse(p, x, y, 4.6, 6.2)
    p.setPen(pen("#9CA1A8", 0.6))
    p.drawLine(QPointF(x, y - 6), QPointF(x, y - 1.5))


def draw_mug(p, pet, pose, t):
    x, y, rot = pose["mugx"], pose["mugy"], pose["mugrot"]
    if abs(rot) < 8:
        # пар над горячим кофе
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(2):
            ph = (t * 0.6 + i * 0.5) % 1.0
            p.setPen(pen(C("#FFFFFF", 160 * (1 - ph)), 1.2))
            sx = x - 3 + i * 6
            path = QPainterPath(QPointF(sx, y - 11))
            path.cubicTo(QPointF(sx - 3, y - 15 - ph * 4), QPointF(sx + 3, y - 18 - ph * 6),
                         QPointF(sx, y - 22 - ph * 8))
            p.drawPath(path)
    p.save()
    p.translate(x, y)
    p.rotate(rot)
    color = C(pet["mug"])
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen(color.darker(115), 2.4))
    p.drawEllipse(QRectF(5, -5, 8, 9))
    fill(p, color, color.darker(135), 1.0)
    p.drawRoundedRect(QRectF(-7, -9, 14, 18), 2, 2)
    fill(p, "#4A2A18", color.darker(135), 0.8)
    p.drawEllipse(QRectF(-7, -11, 14, 4))
    kind = pet.get("mug_print")
    if kind == "monkey":
        fill(p, "#7B4024")
        ellipse(p, -3, -1, 1.8)
        ellipse(p, 3, -1, 1.8)
        ellipse(p, 0, 0, 3.4)
        fill(p, "#E9C4A5")
        ellipse(p, 0, 0.8, 2.2, 1.8)
    elif kind == "heart":
        draw_heart(p, 0, 0, 3.0, "#E0567E")
    elif kind == "qgis":
        font = QFont()
        font.setPixelSize(5)
        font.setBold(True)
        p.setFont(font)
        p.setPen(pen("#5A9E3A"))
        p.drawText(QRectF(-7, -4, 14, 7), Qt.AlignmentFlag.AlignCenter, "QGIS")
    elif kind == "pig":
        # кружка-свинка: ушки, глазки, пятачок
        pink = color.darker(112)
        fill(p, pink, pink.darker(130), 0.6)
        p.drawPolygon(poly([(-6.5, -9), (-3, -9), (-5.5, -13.5)]))
        p.drawPolygon(poly([(6.5, -9), (3, -9), (5.5, -13.5)]))
        fill(p, "#3A2A2A")
        ellipse(p, -3, -3, 0.9)
        ellipse(p, 3, -3, 0.9)
        fill(p, pink, pink.darker(130), 0.6)
        ellipse(p, 0, 2, 4.2, 3.0)
        fill(p, pink.darker(150))
        ellipse(p, -1.4, 2, 0.8, 1.1)
        ellipse(p, 1.4, 2, 0.8, 1.1)
    elif kind == "paw":
        fill(p, "#7A4A20")
        ellipse(p, 0, 2, 3.2, 2.6)
        for dx, dy in ((-3.4, -2), (-1.2, -3.8), (1.2, -3.8), (3.4, -2)):
            ellipse(p, dx, dy, 1.2)
    p.restore()


def draw_phone(p, pet, pose):
    x, y = pose["phx"], pose["phy"]
    up = pose["phup"]
    w = 15.0 - 2.0 * up
    h = 6.0 + 16.0 * up
    case = C(pet["phone"])
    p.save()
    p.translate(x, y)
    p.rotate(pose["phrot"])
    fill(p, case, case.darker(150), 0.8)
    p.drawRoundedRect(QRectF(-w / 2, -h / 2, w, h), 2.2, 2.2)
    if up > 0.4 and pose["phback"] > 0.5:
        # задняя крышка с камерой (селфи)
        fill(p, "#15161A", "#000000", 0.4)
        p.drawRoundedRect(QRectF(-w / 2 + 1.5, -h / 2 + 1.5, 6, 6), 1.5, 1.5)
        fill(p, "#3A4A66")
        ellipse(p, -w / 2 + 3.2, -h / 2 + 3.2, 1.1)
        ellipse(p, -w / 2 + 5.8, -h / 2 + 5.8, 1.1)
        fill(p, case.lighter(130))
        ellipse(p, 0, 2, 2.6)
    elif up > 0.4:
        screen = QRectF(-w / 2 + 1.4, -h / 2 + 1.6, w - 2.8, h - 3.2)
        g = QLinearGradient(0, screen.top(), 0, screen.bottom())
        g.setColorAt(0, C("#BFE3FF"))
        g.setColorAt(1, C("#F4D2F0"))
        fill(p, g)
        p.drawRect(screen)
        fill(p, C("#FFFFFF", 210))
        for i in range(3):
            p.drawRect(QRectF(screen.left() + 1, screen.top() + 1.5 + i * 5.5, screen.width() - 2, 4))
    else:
        fill(p, "#15161A")
        p.drawRoundedRect(QRectF(-w / 2 + 1.2, -h / 2 + 1.0, w - 2.4, h - 2.0), 1.5, 1.5)
    p.restore()


# ---------------------------------------------------------------- монитор

def screen_transform():
    src = poly([(0, 0), (SCREEN_W, 0), (SCREEN_W, SCREEN_H), (0, SCREEN_H)])
    dst = poly(SCREEN_QUAD)
    tr = QTransform()
    QTransform.quadToQuad(src, dst, tr)
    return tr


_SCREEN_TRANSFORM = []


def draw_monitor(p, ctx):
    # подставка: ножка от середины низа экрана к основанию на столе
    fill(p, "#26262B", "#151518", 0.8)
    ellipse(p, 262, 170, 19, 4.2)
    p.drawPolygon(poly([(255, 140), (264, 141), (266, 169), (258, 169)]))
    fill(p, "#34343A")
    ellipse(p, 262, 169, 6, 1.6)
    # торец корпуса и рамка
    fill(p, "#2E2E34", "#0D0D10", 0.8)
    p.drawPolygon(poly(MONITOR_SIDE))
    fill(p, "#1D1D21", "#0D0D10", 1.0)
    p.drawPolygon(poly(BEZEL_QUAD))
    if not _SCREEN_TRANSFORM:
        _SCREEN_TRANSFORM.append(screen_transform())
    p.save()
    p.setTransform(_SCREEN_TRANSFORM[0], True)
    p.setClipRect(QRectF(0, 0, SCREEN_W, SCREEN_H))
    draw_screen(p, ctx)
    p.restore()
    # блик
    fill(p, C("#FFFFFF", 22))
    p.drawPolygon(poly([(218, 76), (252, 70.5), (234, 132.5), (218, 135)]))


# Кварталы на карте: неровная сетка, раскрашенная как карта лесоустройства
_MAP_CELLS = []


def map_cells():
    if _MAP_CELLS:
        return _MAP_CELLS
    rnd = random.Random(7)
    cols, rows, step = 14, 12, 11.0
    pts = [[(c * step + rnd.uniform(-3, 3), r * step + rnd.uniform(-3, 3)) for c in range(cols + 1)]
           for r in range(rows + 1)]
    palette = ("#9CCB6B", "#7DB85A", "#B9D77A", "#E3D879", "#6FA85B", "#A7D18A", "#88C3A8",
               "#C9E08F", "#5E9E55")
    for r in range(rows):
        for c in range(cols):
            quad = [pts[r][c], pts[r][c + 1], pts[r + 1][c + 1], pts[r + 1][c]]
            _MAP_CELLS.append((quad, rnd.choice(palette)))
    return _MAP_CELLS


def draw_screen(p, ctx):
    mode = ctx.get("screen", "map")
    t = ctx["t"]
    if mode == "sleep":
        p.fillRect(QRectF(0, 0, SCREEN_W, SCREEN_H), C("#0D1015"))
        font = QFont()
        font.setPixelSize(9)
        font.setBold(True)
        p.setFont(font)
        x = 30 + 28 * math.sin(t * 0.25)
        y = 32 + 16 * math.sin(t * 0.37)
        p.setPen(pen(C("#6FBF4A", 140)))
        p.drawText(QRectF(x, y, 60, 14), Qt.AlignmentFlag.AlignCenter, "QGIS")
        return
    # интерфейс QGIS: панель инструментов, слои, карта
    p.fillRect(QRectF(0, 0, SCREEN_W, SCREEN_H), C("#F1F1F0"))
    p.fillRect(QRectF(0, 0, SCREEN_W, 8), C("#E3E3E1"))
    icons = ("#E8B54A", "#5B9BD5", "#6DBF5B", "#D9584A", "#9B7BC9", "#5BC0C0")
    for i in range(14):
        fill(p, icons[i % len(icons)])
        p.drawRect(QRectF(3 + i * 7.5, 2, 4.5, 4.5))
    p.fillRect(QRectF(0, 8, 30, SCREEN_H - 8), C("#FFFFFF"))
    layers = ("#9CCB6B", "#C9554A", "#5B9BD5", "#E3D879", "#8E8E8E", "#6FA85B", "#B07AC9")
    for i, c in enumerate(layers):
        y = 12 + i * 8
        fill(p, "#FFFFFF", "#8A8A8A", 0.5)
        p.drawRect(QRectF(2, y, 3.5, 3.5))
        p.setPen(pen("#3C8C3C", 0.7))
        p.drawLine(QPointF(2.6, y + 1.8), QPointF(3.6, y + 2.8))
        p.drawLine(QPointF(3.6, y + 2.8), QPointF(5.2, y + 0.6))
        fill(p, c)
        p.drawRect(QRectF(7.5, y, 4, 3.5))
        fill(p, "#A9A9A9")
        p.drawRect(QRectF(13, y + 1, 9 + (i * 5) % 9, 1.6))
    # карта
    p.save()
    p.setClipRect(QRectF(31, 9, SCREEN_W - 31, SCREEN_H - 9))
    pan_x, pan_y = 0.0, 0.0
    if mode == "pan":
        pan_x = 6.0 * math.sin(t * 0.45)
        pan_y = 4.0 * math.sin(t * 0.33)
    if mode == "zoom":
        # колёсико: карта приближается и отдаляется вокруг центра
        zoom = 1.0 + 0.3 * math.sin(t * 1.6)
        p.translate(75, 44)
        p.scale(zoom, zoom)
        p.translate(-75, -44)
    p.translate(24 + pan_x, 2 + pan_y)
    for quad, color in map_cells():
        fill(p, color, "#FFFFFF", 0.35)
        p.drawPolygon(poly(quad))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen("#D04A3E", 0.9))
    p.drawPolyline(poly([(0, 34), (40, 31), (66, 40), (110, 36), (160, 44)]))
    p.drawPolyline(poly([(66, 0), (62, 40), (72, 90), (70, 140)]))
    p.setPen(pen("#4C8FD0", 2.2))
    river = QPainterPath(QPointF(-5, 60))
    river.cubicTo(QPointF(30, 45), QPointF(50, 85), QPointF(90, 62))
    river.cubicTo(QPointF(110, 50), QPointF(130, 70), QPointF(160, 58))
    p.drawPath(river)
    p.restore()
    if mode == "pan":
        cx = 75 + 22 * math.sin(t * 0.9)
        cy = 44 + 15 * math.sin(t * 1.3)
        fill(p, "#FFFFFF", "#000000", 0.6)
        p.drawPolygon(poly([(cx, cy), (cx, cy + 7), (cx + 2, cy + 5.2), (cx + 3.4, cy + 8),
                            (cx + 4.6, cy + 7.4), (cx + 3.2, cy + 4.8), (cx + 5.4, cy + 4.8)]))
    elif mode == "typing":
        draw_attribute_table(p, t)
    elif mode == "saved":
        fill(p, "#3E8E3E", "#2C6B2C", 0.6)
        p.drawRoundedRect(QRectF(64, 60, 52, 12), 3, 3)
        p.setPen(pen("#FFFFFF", 1.4))
        p.drawPolyline(poly([(68, 66), (70, 68.5), (74, 63.5)]))
        font = QFont()
        font.setPixelSize(6)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(76, 60, 40, 12), Qt.AlignmentFlag.AlignVCenter, "Сохранено")
    elif mode == "undo":
        p.fillRect(QRectF(31, 9, SCREEN_W - 31, SCREEN_H - 9), C("#FFFFFF", 90))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen("#E08A2E", 3.2))
        p.drawArc(QRectF(62, 28, 24, 24), 200 * 16, -250 * 16)
        fill(p, "#E08A2E")
        p.drawPolygon(poly([(58, 38), (66, 36), (61, 44)]))
    elif mode == "busy":
        p.fillRect(QRectF(31, 9, SCREEN_W - 31, SCREEN_H - 9), C("#FFFFFF", 120))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen("#5A9E3A", 3.0))
        p.drawArc(QRectF(65, 34, 16, 16), int(-t * 360 * 16) % (360 * 16), 260 * 16)
        fill(p, "#D8D8D6")
        p.drawRect(QRectF(40, 60, 66, 4))
        fill(p, "#5A9E3A")
        p.drawRect(QRectF(40, 60, 66 * ((t * 0.18) % 1.0), 4))
    # строка состояния
    p.fillRect(QRectF(0, SCREEN_H - 4, SCREEN_W, 4), C("#E3E3E1"))


def draw_attribute_table(p, t):
    x0, y0, w, h = 38, 14, 76, 58
    fill(p, "#FFFFFF", "#8A8A8A", 0.6)
    p.drawRect(QRectF(x0, y0, w, h))
    p.fillRect(QRectF(x0, y0, w, 6), C("#DADAD8"))
    cols = (0, 14, 34, 54)
    rows = 8
    progress = (t * 2.2) % (rows * 3 + 4)  # заполняются клетки, потом заново
    for r in range(rows):
        y = y0 + 8 + r * 6.2
        if r % 2:
            p.fillRect(QRectF(x0, y - 1, w, 6.2), C("#F4F6F8"))
        for ci, cx in enumerate(cols[1:]):
            idx = r * 3 + ci
            if idx < progress:
                length = 6 + (idx * 7) % 10
                fill(p, "#7A7A7A")
                p.drawRect(QRectF(x0 + cx + 1.5, y + 1.2, length, 1.8))
        fill(p, "#7A7A7A")
        p.drawRect(QRectF(x0 + 2, y + 1.2, 6, 1.8))
    p.setPen(pen("#C8C8C8", 0.4))
    for cx in cols[1:]:
        p.drawLine(QPointF(x0 + cx, y0), QPointF(x0 + cx, y0 + h))
    # мигающий курсор в текущей клетке
    idx = int(progress)
    if idx < rows * 3 and int(t * 3) % 2 == 0:
        r, ci = divmod(idx, 3)
        y = y0 + 8 + r * 6.2
        p.setPen(pen("#000000", 0.6))
        x = x0 + cols[ci + 1] + 1.5 + 6 + (idx * 7) % 10
        p.drawLine(QPointF(x, y + 0.5), QPointF(x, y + 4))


# ---------------------------------------------------------------- руки

def quad_point(a, c, b, k):
    """Точка квадратичной кривой a→b с контрольной точкой c."""
    m = 1.0 - k
    return (m * m * a[0] + 2 * m * k * c[0] + k * k * b[0],
            m * m * a[1] + 2 * m * k * c[1] + k * k * b[1])


def arm_curve(pose, left):
    """Плечо, контрольная точка дуги и кисть. Дуга проходит через локоть."""
    side = -1 if left else 1
    s = (150.0 + pose["bdx"] + side * SHOULDER_DX, SHOULDER_Y + pose["bdy"])
    prefix = "l" if left else "r"
    h = (pose["h%sx" % prefix], pose["h%sy" % prefix])
    dx, dy = h[0] - s[0], h[1] - s[1]
    dist = math.hypot(dx, dy) or 1e-3
    # Локоть сам отходит от середины руки вниз и наружу (как под тяжестью) — тем дальше,
    # чем сильнее рука согнута. Направление — «тяжесть», спроецированная поперёк руки:
    # так оно меняется плавно, куда бы ни двигалась кисть, и локоть не перескакивает
    sag = 0.8 * math.sqrt(max(0.0, (ARM_LENGTH / 2) ** 2 - (dist / 2) ** 2))
    ux, uy = dx / dist, dy / dist
    gx, gy = ELBOW_PULL[0] * side, ELBOW_PULL[1]
    along = gx * ux + gy * uy
    # у самого плеча направление руки скачет — там локоть просто свисает
    near = min(1.0, dist / 34.0)
    near = near * near * (3.0 - 2.0 * near)
    nx = gx + (gx - along * ux - gx) * near
    ny = gy + (gy - along * uy - gy) * near
    bend = pose[prefix + "b"]
    ex = (s[0] + h[0]) / 2 + nx * bend * sag
    ey = (s[1] + h[1]) / 2 + ny * bend * sag
    # …или стоит там, где его поставила анимация
    w = pose[prefix + "ew"]
    ex += (pose[prefix + "ex"] - ex) * w
    ey += (pose[prefix + "ey"] - ey) * w
    c = (2 * ex - (s[0] + h[0]) / 2, 2 * ey - (s[1] + h[1]) / 2)
    return s, c, h


def draw_arms(p, pet, pose, hands=True):
    draw_arm(p, pet, pose, left=True, hand=hands)
    draw_arm(p, pet, pose, left=False, hand=hands)


def draw_hands(p, pet, pose):
    for left in (True, False):
        s, c, h = arm_curve(pose, left)
        draw_hand(p, pet, pose, h, math.degrees(math.atan2(h[1] - c[1], h[0] - c[0])), left)


def draw_arm(p, pet, pose, left, hand=True):
    s, c, h = arm_curve(pose, left)
    path = QPainterPath(QPointF(*s))
    path.quadTo(QPointF(*c), QPointF(*h))
    fur = C(pet["fur"])
    clothes = pet["clothes"]
    p.setBrush(Qt.BrushStyle.NoBrush)
    if clothes in ("suit", "sweater"):
        sleeve = C(pet["jacket"])
        p.setPen(pen(sleeve.darker(150), 12.5 if clothes == "suit" else 13.5))
        p.drawPath(path)
        p.setPen(pen(sleeve, 10.5 if clothes == "suit" else 11.5))
        p.drawPath(path)
        # манжета рубашки или вязаная резинка
        a, b = quad_point(s, c, h, 0.84), quad_point(s, c, h, 0.93)
        cuff = "#F2F2EE" if clothes == "suit" else sleeve.darker(118)
        p.setPen(pen(cuff, 8.0 if clothes == "suit" else 11.0, Qt.PenCapStyle.FlatCap))
        p.drawLine(QPointF(*a), QPointF(*b))
    else:
        width = {"chimp": 10.0, "lion": 10.5}.get(pet.get("kind"), 8.5)
        p.setPen(pen(fur.darker(150), width + 2))
        p.drawPath(path)
        p.setPen(pen(fur, width))
        p.drawPath(path)
    if clothes == "shirt":
        # короткий рукав рубашки — начало той же дуги
        k = 0.3
        sleeve = QPainterPath(QPointF(*s))
        mid = (s[0] + (c[0] - s[0]) * k, s[1] + (c[1] - s[1]) * k)
        sleeve.quadTo(QPointF(*mid), QPointF(*quad_point(s, c, h, k)))
        p.setPen(pen("#B9B9B2", 14.5))
        p.drawPath(sleeve)
        p.setPen(pen("#F5F5F2", 12.5))
        p.drawPath(sleeve)
    if hand:
        draw_hand(p, pet, pose, h, math.degrees(math.atan2(h[1] - c[1], h[0] - c[0])), left)


def draw_hand(p, pet, pose, at, angle, left):
    hand = C(pet["hand"])
    outline = hand.darker(140)
    x, y = at
    side = -1 if left else 1
    if not left and pose["rthumb"] > 0.5:
        # кулак с большим пальцем вверх
        fill(p, hand, outline, 0.8)
        p.drawRoundedRect(QRectF(x - 5, y - 4, 10, 9), 3.5, 3.5)
        p.drawRoundedRect(QRectF(x - 2.2, y - 12, 4.4, 9), 2.2, 2.2)
        return
    if not left and pose["rpeace"] > 0.5:
        # «мир»: два пальца вверх
        p.setPen(pen(outline, 4.4))
        p.drawLine(QPointF(x - 1.5, y - 2), QPointF(x - 4.5, y - 11))
        p.drawLine(QPointF(x + 1.5, y - 2), QPointF(x + 4.5, y - 11))
        p.setPen(pen(hand, 2.8))
        p.drawLine(QPointF(x - 1.5, y - 2), QPointF(x - 4.5, y - 11))
        p.drawLine(QPointF(x + 1.5, y - 2), QPointF(x + 4.5, y - 11))
        fill(p, hand, outline, 0.8)
        ellipse(p, x, y + 1, 5, 4.6)
        return
    p.save()
    p.translate(x, y)
    p.rotate(angle)
    fill(p, hand, outline, 0.8)
    kind = pet.get("kind")
    if kind == "frog":
        # лягушачья лапка: пальцы с круглыми подушечками
        p.drawEllipse(QRectF(-4.5, -4.2, 9, 8.4))
        for fy in (-3.6, 0.0, 3.6):
            ellipse(p, 5.0, fy, 2.0)
        ellipse(p, 0.5, -side * 4.6, 1.9)
    elif kind == "lion":
        # плюшевая лапа с «бобами»
        p.drawEllipse(QRectF(-5.5, -5.5, 11, 11))
        fill(p, "#C98E54")
        for fy in (-2.8, 0.0, 2.8):
            ellipse(p, 3.6, fy, 1.2)
    else:
        p.drawEllipse(QRectF(-4.5, -4.8, 10, 9.6))
        ellipse(p, 1.0, -side * 4.4, 2.4, 2.0)  # большой палец
    p.restore()
    if not left and pose["pen"] > 0.5:
        p.setPen(pen("#2E4A86", 1.8))
        p.drawLine(QPointF(x - 1, y - 6), QPointF(x - 5, y + 5))
        p.setPen(pen("#1A1A1A", 1.0))
        p.drawLine(QPointF(x - 5, y + 5), QPointF(x - 5.6, y + 6.6))


# ---------------------------------------------------------------- значки

def draw_heart(p, x, y, size, color):
    path = QPainterPath(QPointF(x, y + size))
    path.cubicTo(QPointF(x - size * 2.0, y - size * 0.2), QPointF(x - size * 0.9, y - size * 1.6),
                 QPointF(x, y - size * 0.5))
    path.cubicTo(QPointF(x + size * 0.9, y - size * 1.6), QPointF(x + size * 2.0, y - size * 0.2),
                 QPointF(x, y + size))
    fill(p, color)
    p.drawPath(path)


def draw_overlays(p, pet, pose, t):
    hx, hy = head_center(pose)
    font = QFont()
    font.setBold(True)
    if pose["zzz"] > 0.01:
        for i in range(3):
            ph = (t * 0.45 + i / 3.0) % 1.0
            font.setPixelSize(int(6 + ph * 7))
            p.setFont(font)
            p.setPen(pen(C("#5D6FA8", 255 * pose["zzz"] * (1 - ph) * min(1.0, ph * 5))))
            p.drawText(QPointF(hx + 26 + ph * 20, hy - 18 - ph * 34), "Z")
    if pose["notes"] > 0.01:
        accent = pet.get("accent", "#E0679A")
        for i in range(3):
            ph = (t * 0.38 + i / 3.0) % 1.0
            alpha = 255 * pose["notes"] * (1 - ph) * min(1.0, ph * 5)
            x = hx + 34 + 8 * math.sin(ph * 6 + i) - i * 3
            y = hy - 2 - ph * 40
            fill(p, C(accent, alpha))
            ellipse(p, x, y, 2.6, 2.0)
            p.setPen(pen(C(accent, alpha), 1.0))
            p.drawLine(QPointF(x + 2.3, y), QPointF(x + 2.3, y - 8))
            p.drawLine(QPointF(x + 2.3, y - 8), QPointF(x + 5, y - 6))
    if pose["hearts"] > 0.01:
        for i in range(3):
            ph = (t * 0.5 + i / 3.0) % 1.0
            alpha = 255 * pose["hearts"] * (1 - ph) * min(1.0, ph * 5)
            draw_heart(p, TIGER[0] - 4 + 9 * math.sin(ph * 5 + i * 2), TIGER[1] - 18 - ph * 30,
                       2.4 + ph, C("#F0567E", alpha))
    if pose["quest"] > 0.01:
        font.setPixelSize(16)
        p.setFont(font)
        p.setPen(pen(C("#4A6FB5", 255 * pose["quest"])))
        p.drawText(QPointF(hx + 26, hy - 26 + 1.5 * math.sin(t * 3)), "?")
    if pose["excl"] > 0.01:
        font.setPixelSize(16)
        p.setFont(font)
        p.setPen(pen(C("#E0503A", 255 * pose["excl"])))
        p.drawText(QPointF(hx + 26, hy - 26), "!")
    if pose["bulb"] > 0.01:
        a = pose["bulb"]
        bx, by = hx + 30, hy - 40
        g = QRadialGradient(QPointF(bx, by), 15)
        g.setColorAt(0, C("#FFF3A0", 180 * a))
        g.setColorAt(1, C("#FFF3A0", 0))
        fill(p, g)
        ellipse(p, bx, by, 15)
        fill(p, C("#FFE15A", 255 * a), C("#C9A21E", 255 * a), 0.8)
        ellipse(p, bx, by, 6, 6.5)
        fill(p, C("#9A9A9A", 255 * a))
        p.drawRect(QRectF(bx - 2.6, by + 5.5, 5.2, 3.5))
        p.setPen(pen(C("#F2C230", 255 * a), 1.0))
        for k in range(5):
            ang = math.radians(-160 + k * 35)
            p.drawLine(QPointF(bx + 9 * math.cos(ang), by + 9 * math.sin(ang)),
                       QPointF(bx + 12 * math.cos(ang), by + 12 * math.sin(ang)))
    if pose["sweat"] > 0.01:
        a = pose["sweat"]
        sx, sy = hx - 24, hy - 14 + ((t * 0.8) % 1.0) * 6
        path = QPainterPath(QPointF(sx, sy - 5))
        path.cubicTo(QPointF(sx + 4, sy), QPointF(sx + 3, sy + 3.5), QPointF(sx, sy + 3.5))
        path.cubicTo(QPointF(sx - 3, sy + 3.5), QPointF(sx - 4, sy), QPointF(sx, sy - 5))
        fill(p, C("#8CC8F0", 230 * a), C("#4C8FD0", 230 * a), 0.8)
        p.drawPath(path)
    if pose["check"] > 0.01:
        # значок «сохранено»
        a = pose["check"]
        cx, cy = hx + 32, hy - 30
        fill(p, C("#3E9E4A", 255 * a), C("#FFFFFF", 255 * a), 1.2)
        ellipse(p, cx, cy, 7.5)
        p.setPen(pen(C("#FFFFFF", 255 * a), 2.0))
        p.drawPolyline(poly([(cx - 3.5, cy), (cx - 1, cy + 3), (cx + 4, cy - 3)]))
    if pose["boardcheck"] > 0.01:
        # ставит галочку в списке дел на доске
        a = pose["boardcheck"]
        p.setPen(pen(C("#D84B4B", 255 * a), 1.6))
        p.drawPolyline(poly([(224, 50), (227, 54), (234, 45)]))
        fill(p, C("#FFF3A0", 160 * a))
        for i in range(4):
            ang = t * 3 + i * math.pi / 2
            ellipse(p, 230 + 9 * math.cos(ang), 49 + 7 * math.sin(ang), 1.2)
    if pose["dots"] > 0.01:
        # «…» — вздох, пока QGIS думает
        a = pose["dots"]
        bx, by = hx + 30, hy - 30
        fill(p, C("#FFFFFF", 235 * a), C("#9A9A9A", 235 * a), 0.8)
        p.drawRoundedRect(QRectF(bx - 10, by - 6, 20, 11), 5, 5)
        p.drawPolygon(poly([(bx - 6, by + 4), (bx - 9, by + 9), (bx - 2, by + 5)]))
        fill(p, C("#6A6A6A", 255 * a))
        for i in range(3):
            if (t * 3) % 3 >= i:
                ellipse(p, bx - 5 + i * 5, by - 0.5, 1.4)
    for key, text, color, dx in (("achoo", "Апчхи!", "#4C8FD0", 24), ("roar", "Р-р-р!", "#C9542A", 26)):
        if pose[key] > 0.01:
            font.setPixelSize(13)
            p.setFont(font)
            p.setPen(pen(C(color, 255 * pose[key]), 1.0))
            p.drawText(QPointF(hx + dx, hy - 22 + 2 * math.sin(t * 20)), text)
    if pose["flash"] > 0.01:
        # вспышка селфи
        p.fillRect(QRectF(-2000, -2000, 4000, 4000), C("#FFFFFF", 200 * min(1.0, pose["flash"])))
