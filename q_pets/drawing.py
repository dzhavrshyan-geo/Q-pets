# -*- coding: utf-8 -*-
"""Рисование сцены: кабинет, стол, компьютер и сам питомец.

Сцена рисуется в логических координатах 320×240 (масштабирует pet_widget.py).
Слева — окно в лес, справа — монитор с QGIS, в центре за столом — питомец.
Руки ставятся по положению кисти (поза), локоть считается сам (draw_arm).
"""

import math
import random

from qgis.PyQt.QtCore import QPointF, QRectF, Qt
from qgis.PyQt.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath,
                             QPen, QPolygonF, QRadialGradient, QTransform)

from .animation import MUG_DESK

W, H = 320.0, 240.0
DESK_Y = 164.0      # задний край столешницы
DESK_FRONT = 204.0  # передний край
NECK = (150.0, 116.0)
SHOULDER_DX, SHOULDER_Y = 23.0, 128.0
UPPER_ARM, FOREARM = 34.0, 34.0

# Экран монитора: прямоугольник содержимого → четырёхугольник в сцене (монитор
# развёрнут к питомцу, поэтому правый край чуть дальше и меньше)
SCREEN_W, SCREEN_H = 120.0, 80.0
SCREEN_QUAD = [(206.0, 67.0), (300.0, 74.0), (300.0, 137.0), (206.0, 146.0)]
BEZEL_QUAD = [(202.0, 62.0), (304.0, 70.0), (304.0, 141.0), (202.0, 151.0)]

INK = QColor("#3A2A22")
NO_PEN = Qt.PenStyle.NoPen
ROUND = Qt.PenCapStyle.RoundCap


def C(color, alpha=None):
    c = QColor(color)
    if alpha is not None:
        c.setAlpha(max(0, min(255, int(alpha))))
    return c


def pen(color, width=1.0, cap=ROUND):
    p = QPen(QColor(color), width)
    p.setCapStyle(cap)
    p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return p


def poly(points):
    return QPolygonF([QPointF(x, y) for x, y in points])


def fill(p, color, outline=None, width=1.0):
    p.setBrush(QBrush(C(color)) if not isinstance(color, (QBrush, QLinearGradient,
                                                         QRadialGradient)) else QBrush(color))
    p.setPen(pen(outline, width) if outline is not None else NO_PEN)


def ellipse(p, x, y, rx, ry=None):
    p.drawEllipse(QPointF(x, y), rx, rx if ry is None else ry)


def head_center(pose):
    return (150.0 + pose["bdx"] + pose["turn"] * 2.0, 86.0 + pose["hdy"] + pose["bdy"])


# ====================================================================== сцена

def draw_scene(p, pet, pose, ctx):
    """ctx: t — время (с), screen — режим монитора, hour — час для неба за окном."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    t = ctx["t"]
    draw_room(p, pet, ctx)
    draw_chair(p, pet)
    if pet.get("tail"):
        draw_tail(p, pet, t)
    draw_body(p, pet, pose)
    draw_head(p, pet, pose)
    if pet["special"] == "tiger":
        draw_tiger(p, pose, t)
    draw_desk(p)
    draw_desk_items(p, pet, pose, ctx)
    if pet["special"] == "tiger":
        draw_tiger_paws(p, pose)
    draw_arm(p, pet, pose, left=True)
    draw_arm(p, pet, pose, left=False)
    if not mug_on_desk(pose):
        draw_mug(p, pet, pose, t)  # кружку в руке держат перед собой
    draw_overlays(p, pet, pose, t)


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
    color = "#EBAFBF" if kind == "fuzzy" else "#F2A9BE"
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


def draw_tail(p, pet, t):
    sway = 3.0 * math.sin(t * 1.3)
    path = QPainterPath(QPointF(176, 158))
    path.cubicTo(QPointF(200, 158 + sway * 0.3), QPointF(206 + sway, 128),
                 QPointF(196 + sway, 116))
    path.quadTo(QPointF(188 + sway, 110), QPointF(186 + sway * 0.8, 118))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen(C(pet["fur"]).darker(150), 7.0))
    p.drawPath(path)
    p.setPen(pen(pet["fur"], 5.0))
    p.drawPath(path)


# ---------------------------------------------------------------- тело

def draw_body(p, pet, pose):
    cx = 150.0 + pose["bdx"]
    top = 117.0 + pose["bdy"]
    fur = C(pet["fur"])
    fill(p, fur)
    ellipse(p, cx, top - 2, 9, 7)  # шея
    path = QPainterPath(QPointF(cx - 25, DESK_Y + 12))
    path.lineTo(QPointF(cx - 26, top + 14))
    path.quadTo(QPointF(cx - 26, top + 2), QPointF(cx - 13, top))
    path.lineTo(QPointF(cx + 13, top))
    path.quadTo(QPointF(cx + 26, top + 2), QPointF(cx + 26, top + 14))
    path.lineTo(QPointF(cx + 25, DESK_Y + 12))
    path.closeSubpath()
    if pet["clothes"] == "suit":
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
        p.drawLine(QPointF(cx + 0.5, top + 36), QPointF(cx + 0.5, DESK_Y))


# ---------------------------------------------------------------- голова

def face_shape(cx, cy, chimp):
    path = QPainterPath()
    if chimp:
        path.addEllipse(QPointF(cx - 10.5, cy - 2), 13.5, 12.5)
        path.addEllipse(QPointF(cx + 10.5, cy - 2), 13.5, 12.5)
        path.addEllipse(QPointF(cx, cy + 13), 19, 14)
    else:
        path.addEllipse(QPointF(cx - 10, cy - 2), 12.5, 12.5)
        path.addEllipse(QPointF(cx + 10, cy - 2), 12.5, 12.5)
        path.addEllipse(QPointF(cx, cy + 12), 16, 12)
    return path.simplified()


def draw_head(p, pet, pose):
    hx, hy = head_center(pose)
    chimp = pet.get("chimp", False)
    fur = C(pet["fur"])
    fur_light = C(pet["fur_light"])
    skin = C(pet["skin"])
    turn = pose["turn"]
    fx = turn * 7.0  # лицо сдвигается в сторону поворота
    p.save()
    p.translate(hx, hy + 26)
    p.rotate(pose["tilt"])
    p.translate(-hx, -(hy + 26))

    # пучок на макушке (под бантом)
    if pet.get("headwear") == "bow":
        fill(p, fur.darker(115))
        ellipse(p, hx - fx * 0.3, hy - 36, 14, 12)
        p.setPen(pen(fur_light, 0.8))
        for a in (-0.8, -0.3, 0.2, 0.7):
            p.drawArc(QRectF(hx - fx * 0.3 - 10, hy - 46, 20, 20), int(math.degrees(a) * 16 + 900),
                      400)

    # уши
    ear_r = 11.5 if chimp else 8.5
    ear_y = hy + (4 if chimp else 1)
    for side in (-1, 1):
        ex = hx + side * (29 if chimp else 29.5) - fx * 0.35
        fill(p, fur)
        ellipse(p, ex, ear_y, ear_r)
        fill(p, skin.darker(108))
        ellipse(p, ex + side * 0.5, ear_y, ear_r * 0.62)

    # голова с пушистым краем
    grad = QRadialGradient(QPointF(hx - 8, hy - 12), 40)
    grad.setColorAt(0, fur_light)
    grad.setColorAt(1, fur)
    fill(p, grad)
    if not chimp:
        for i in range(18):
            a = i / 18.0 * 2 * math.pi
            ellipse(p, hx + 27 * math.cos(a), hy + 27 * math.sin(a), 5.2)
    ellipse(p, hx, hy, 29.5 if not chimp else 30.5)
    if chimp:
        # волосы на макушке
        p.setPen(pen(fur.lighter(130), 1.0))
        for dx in (-6, -2, 2, 6):
            p.drawLine(QPointF(hx + dx, hy - 27), QPointF(hx + dx * 1.3 + 1, hy - 33))

    # лицо
    face = face_shape(hx + fx, hy, chimp)
    fill(p, skin, skin.darker(118), 0.8)
    p.drawPath(face)
    if pose["glow"] > 0.01:  # свет от телефона
        g = QRadialGradient(QPointF(hx + fx, hy + 12), 22)
        g.setColorAt(0, C("#CFE8FF", 110 * pose["glow"]))
        g.setColorAt(1, C("#CFE8FF", 0))
        fill(p, g)
        p.drawPath(face)
    if pet.get("blush"):
        fill(p, C("#F08A9A", 120 * pet["blush"]))
        for side in (-1, 1):
            ellipse(p, hx + fx + side * 15, hy + 9, 4.2, 2.6)
    draw_eyes(p, pet, pose, hx + fx, hy)
    draw_mouth(p, pet, pose, hx + fx, hy)
    draw_headwear(p, pet, pose, hx, hy, fx)
    p.restore()


def draw_eyes(p, pet, pose, cx, cy):
    chimp = pet.get("chimp", False)
    openness = max(0.0, pose["eyes"])
    gap = 10.5 if chimp else 9.8
    rx, ry = (5.0, 5.2) if chimp else (5.6, 6.5)
    if openness > 1.0:
        ry *= 1.0 + 0.2 * (openness - 1.0)
    look_x = pose["lookx"] * 2.3 + pose["turn"] * 0.8
    look_y = pose["looky"] * 2.0
    for side in (-1, 1):
        ex, ey = cx + side * gap, cy - 2
        if openness < 0.12:
            # закрытый глаз — дуга
            p.setPen(pen(INK, 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath(QPointF(ex - rx + 1, ey))
            path.quadTo(QPointF(ex, ey + 3.5), QPointF(ex + rx - 1, ey))
            p.drawPath(path)
        else:
            fill(p, "#FFFFFF", INK, 0.9)
            ellipse(p, ex, ey, rx, ry)
            p.save()
            clip = QPainterPath()
            clip.addEllipse(QPointF(ex, ey), rx, ry)
            p.setClipPath(clip)
            ix, iy = ex + look_x, ey + look_y + 0.5
            fill(p, "#4A2C18" if not chimp else "#3A2414")
            ellipse(p, ix, iy, 3.9 if not chimp else 4.2)
            fill(p, "#120C08")
            ellipse(p, ix, iy, 2.2)
            fill(p, "#FFFFFF")
            ellipse(p, ix - 1.4, iy - 1.6, 1.3)
            if openness < 1.0:
                lid = ey - ry + 2 * ry * (1.0 - openness)
                fill(p, C(pet["skin"]).darker(106))
                p.drawRect(QRectF(ex - rx - 1, ey - ry - 1, 2 * rx + 2, lid - (ey - ry) + 1))
                p.setPen(pen(INK, 1.0))
                p.drawLine(QPointF(ex - rx, lid), QPointF(ex + rx, lid))
            p.restore()
        if pet.get("lashes"):
            p.setPen(pen(INK, 1.0))
            top = ey - ry * min(1.0, openness) if openness >= 0.12 else ey
            ox = ex + side * (rx - 1.0)
            p.drawLine(QPointF(ox, top + 2.0), QPointF(ox + side * 2.6, top - 0.2))
            p.drawLine(QPointF(ox - side * 1.8, top + 0.6), QPointF(ox - side * 0.6 + side * 1.4, top - 1.6))
        # брови
        brow = pose["brow"]
        base = ey - ry - 3.2 - brow * 2.2
        inner_drop = max(0.0, -brow) * 2.4
        outer = (ex + side * 5.2, base + 0.6)
        inner = (ex - side * 4.2, base + inner_drop)
        p.setPen(pen(C(pet["fur"]).darker(120), 1.8 if chimp else 1.5))
        p.drawLine(QPointF(*inner), QPointF(*outer))


def draw_mouth(p, pet, pose, cx, cy):
    chimp = pet.get("chimp", False)
    # нос
    fill(p, INK)
    spread = 3.4 if chimp else 2.6
    ny = cy + (9 if chimp else 8)
    for side in (-1, 1):
        ellipse(p, cx + side * spread, ny, 1.4 if chimp else 1.2, 1.0)
    mx, my = cx, cy + (17.5 if chimp else 15.5)
    width = 8.0 if chimp else 6.5
    opened = pose["mouth"]
    if opened > 0.06:
        h = 1.5 + 8.0 * opened
        w = width * (0.75 + 0.3 * opened)
        fill(p, "#5A1E1E", INK, 1.0)
        p.drawEllipse(QRectF(mx - w, my - 1.5 - pose["smile"] * 0.8, 2 * w, h + 1.5))
        if opened > 0.3:
            fill(p, "#E07A86")
            ellipse(p, mx, my + h - 2.2, w * 0.6, min(2.6, h * 0.3))
    else:
        s = pose["smile"]
        p.setPen(pen(INK, 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath(QPointF(mx - width, my - s * 1.5))
        path.quadTo(QPointF(mx, my + s * 5.0), QPointF(mx + width, my - s * 1.5))
        p.drawPath(path)
    if pose["tongue"] > 0.05:
        fill(p, "#E8798A", "#B4505E", 0.8)
        tl = 3.8 * pose["tongue"]
        p.drawEllipse(QRectF(mx + 0.5, my - 0.5, 4.6, tl + 1.0))


def draw_headwear(p, pet, pose, hx, hy, fx):
    kind = pet.get("headwear")
    phones = pet.get("headphones")
    if kind == "bow":
        bx, by = hx - fx * 0.3, hy - 47
        fill(p, "#18181B", "#000000", 0.6)
        p.drawPolygon(poly([(bx, by), (bx - 13, by - 7), (bx - 12, by + 6)]))
        p.drawPolygon(poly([(bx, by), (bx + 13, by - 7), (bx + 12, by + 6)]))
        p.drawPolygon(poly([(bx - 1, by + 1), (bx - 6, by + 11), (bx - 2, by + 10)]))
        p.drawPolygon(poly([(bx + 1, by + 1), (bx + 6, by + 11), (bx + 2, by + 10)]))
        fill(p, "#2C2C31")
        ellipse(p, bx, by, 3.2, 3.0)
    if kind == "cap":
        cap = C(pet["cap"])
        dome = QPainterPath(QPointF(hx - 29.5, hy - 9))
        dome.cubicTo(QPointF(hx - 30, hy - 44), QPointF(hx + 30, hy - 44), QPointF(hx + 29.5, hy - 9))
        dome.quadTo(QPointF(hx, hy - 15), QPointF(hx - 29.5, hy - 9))
        g = QLinearGradient(hx - 30, 0, hx + 30, 0)
        g.setColorAt(0, cap.lighter(108))
        g.setColorAt(1, cap.darker(112))
        fill(p, g, cap.darker(135), 1.0)
        p.drawPath(dome)
        p.setPen(pen(cap.darker(125), 0.8))
        p.drawLine(QPointF(hx + fx * 0.5, hy - 36), QPointF(hx + fx * 0.7, hy - 14))
        fill(p, cap.darker(108), cap.darker(140), 1.0)
        p.drawEllipse(QRectF(hx + fx * 0.9 - 21, hy - 18, 42, 10))
        fill(p, cap.darker(110))
        ellipse(p, hx + fx * 0.5, hy - 37, 2.2, 1.6)
        # бант сбоку кепки
        bx, by = hx + 22 - fx * 0.2, hy - 27
        fill(p, cap.lighter(105), cap.darker(140), 0.8)
        p.drawPolygon(poly([(bx, by), (bx - 6, by - 9), (bx - 9, by + 2)]))
        p.drawPolygon(poly([(bx, by), (bx + 9, by - 6), (bx + 7, by + 6)]))
        ellipse(p, bx, by, 2.6)
    if phones:
        c = C(phones)
        if kind != "cap":
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen(c.darker(130), 4.2))
            p.drawArc(QRectF(hx - 32, hy - 36, 64, 66), 10 * 16, 160 * 16)
            p.setPen(pen(c, 3.0))
            p.drawArc(QRectF(hx - 32, hy - 36, 64, 66), 10 * 16, 160 * 16)
        for side in (-1, 1):
            ex = hx + side * 30 - fx * 0.35
            fill(p, c, c.darker(150), 1.0)
            p.drawRoundedRect(QRectF(ex - 6.5, hy - 9, 13, 20), 6, 6)
            fill(p, c.lighter(125) if c.lightness() < 128 else c.darker(115))
            ellipse(p, ex, hy + 1, 3.6)
            fill(p, pet["fur"])
            ellipse(p, ex, hy + 1.2, 1.8)


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
            fill(p, "#3C5A2A")
            ellipse(p, ex + 0.3, ey + 0.3, 2.0)
            fill(p, "#000000")
            ellipse(p, ex + 0.3, ey + 0.3, 1.1)
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


def draw_tiger_paws(p, pose):
    x, _ = TIGER
    for dx in (-7, 7):
        fill(p, "#E98A2F", "#7A4314", 0.8)
        p.drawEllipse(QRectF(x + dx - 5, DESK_Y + 1, 10, 7))
        p.setPen(pen("#2B1C12", 1.0))
        p.drawLine(QPointF(x + dx - 1.5, DESK_Y + 2), QPointF(x + dx - 1.5, DESK_Y + 5))
        p.drawLine(QPointF(x + dx + 1.5, DESK_Y + 2), QPointF(x + dx + 1.5, DESK_Y + 5))


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
    draw_plant(p, t)
    extra = pet.get("desk_extra")
    if extra == "folders":
        draw_folders(p)
    elif extra == "books":
        draw_books(p)
    elif extra == "penguin":
        draw_penguin(p, 50, 186)
    draw_monitor(p, ctx)
    draw_keyboard(p, ctx)
    draw_mouse(p, pose)
    draw_phone(p, pet, pose)
    if mug_on_desk(pose):
        draw_mug(p, pet, pose, t)


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


def mug_on_desk(pose):
    return pose["mugy"] > MUG_DESK[1] - 8


def draw_mug(p, pet, pose, t):
    x, y, rot = pose["mugx"], pose["mugy"], pose["mugrot"]
    if abs(x - MUG_DESK[0]) < 1 and abs(y - MUG_DESK[1]) < 1:
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
    if up > 0.4:
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
    fill(p, "#26262B", "#151518", 0.8)
    p.drawRect(QRectF(248, 146, 10, 21))
    ellipse(p, 253, 169, 21, 4.2)
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
    p.drawPolygon(poly([(206, 67), (246, 70), (222, 145), (206, 146)]))


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

def solve_arm(sx, sy, tx, ty, outward):
    """Локоть по плечу и кисти (две кости). outward — в какую сторону от тела локоть."""
    dx, dy = tx - sx, ty - sy
    dist = math.hypot(dx, dy) or 1e-3
    reach = UPPER_ARM + FOREARM - 0.5
    if dist > reach:
        tx, ty = sx + dx / dist * reach, sy + dy / dist * reach
        dist = reach
    dist = max(dist, abs(UPPER_ARM - FOREARM) + 1.0)
    ux, uy = dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)
    cos_a = (UPPER_ARM ** 2 + dist ** 2 - FOREARM ** 2) / (2 * UPPER_ARM * dist)
    a = math.acos(max(-1.0, min(1.0, cos_a)))
    best = None
    for sign in (1, -1):
        ca, sa = math.cos(a * sign), math.sin(a * sign)
        ex = sx + UPPER_ARM * (ux * ca - uy * sa)
        ey = sy + UPPER_ARM * (ux * sa + uy * ca)
        # локоть — наружу и немного вниз
        score = (ex - (sx + tx) / 2) * outward * 0.6 + (ey - (sy + ty) / 2)
        if best is None or score > best[0]:
            best = (score, ex, ey)
    return best[1], best[2], tx, ty


def draw_arm(p, pet, pose, left):
    side = -1 if left else 1
    sx = 150.0 + pose["bdx"] + side * SHOULDER_DX
    sy = SHOULDER_Y + pose["bdy"]
    hx, hy = (pose["hlx"], pose["hly"]) if left else (pose["hrx"], pose["hry"])
    ex, ey, hx, hy = solve_arm(sx, sy, hx, hy, side)
    path = QPainterPath(QPointF(sx, sy))
    path.lineTo(QPointF(ex, ey))
    path.lineTo(QPointF(hx, hy))
    fur = C(pet["fur"])
    p.setBrush(Qt.BrushStyle.NoBrush)
    if pet["clothes"] == "suit":
        jacket = C(pet["jacket"])
        p.setPen(pen(jacket.darker(150), 12.5))
        p.drawPath(path)
        p.setPen(pen(jacket, 10.5))
        p.drawPath(path)
        # манжета
        k = 0.82
        cx, cy = ex + (hx - ex) * k, ey + (hy - ey) * k
        p.setPen(pen("#F2F2EE", 8.0, Qt.PenCapStyle.FlatCap))
        p.drawLine(QPointF(cx, cy), QPointF(ex + (hx - ex) * 0.9, ey + (hy - ey) * 0.9))
    else:
        width = 10.0 if pet.get("chimp") else 8.5
        p.setPen(pen(fur.darker(150), width + 2))
        p.drawPath(path)
        p.setPen(pen(fur, width))
        p.drawPath(path)
        # короткий рукав рубашки
        k = 0.55
        mx, my = sx + (ex - sx) * k, sy + (ey - sy) * k
        p.setPen(pen("#B9B9B2", 14.5))
        p.drawLine(QPointF(sx, sy), QPointF(mx, my))
        p.setPen(pen("#F5F5F2", 12.5))
        p.drawLine(QPointF(sx, sy), QPointF(mx, my))
    # кисть
    hand = C(pet["hand"])
    angle = math.degrees(math.atan2(hy - ey, hx - ex))
    p.save()
    p.translate(hx, hy)
    p.rotate(angle)
    fill(p, hand, hand.darker(140), 0.8)
    p.drawEllipse(QRectF(-4.5, -4.8, 10, 9.6))
    ellipse(p, 1.0, -side * 4.4, 2.4, 2.0)  # большой палец
    p.restore()


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
