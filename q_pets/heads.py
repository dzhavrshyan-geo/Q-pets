# -*- coding: utf-8 -*-
"""Головы питомцев: обезьянки, шимпанзе, лягушонок в очках и плюшевый лев.

Голова рисуется вокруг head_center(pose) и наклоняется вокруг шеи (pose["tilt"]).
Поворот головы (pose["turn"]) сдвигает черты лица в сторону поворота (fx).
"""

import math
import random

from qgis.PyQt.QtCore import QPointF, QRectF, Qt
from qgis.PyQt.QtGui import QLinearGradient, QPainterPath, QRadialGradient

from .paint import C, INK, ellipse, fill, head_center, pen, poly


def draw_head(p, pet, pose, t=0.0):
    hx, hy = head_center(pose)
    fx = pose["turn"] * 7.0  # лицо сдвигается в сторону поворота
    p.save()
    p.translate(hx, hy + 26)
    p.rotate(pose["tilt"])
    p.translate(-hx, -(hy + 26))
    kind = pet.get("kind", "monkey")
    if kind == "frog":
        draw_frog_head(p, pet, pose, hx, hy, fx)
    elif kind == "lion":
        draw_lion_head(p, pet, pose, hx, hy, fx, t)
    else:
        draw_monkey_head(p, pet, pose, hx, hy, fx)
    p.restore()


def mouth_point(pet, pose):
    """Где рот (без учёта наклона головы) — откуда стреляет язык лягушонка и т. п."""
    hx, hy = head_center(pose)
    fx = pose["turn"] * 7.0
    dy = {"frog": 11.0, "lion": 17.0, "chimp": 17.5}.get(pet.get("kind"), 15.5)
    return hx + fx, hy + dy


# ---------------------------------------------------------------- глаза, брови, рот

def draw_eye(p, pose, ex, ey, rx, ry, openness, lid_color, iris_r, iris_color,
             look_scale=(2.3, 2.0), pupil_r=None, white=True):
    """Один глаз: белок, радужка по взгляду, веко при прищуре; закрытый — дуга."""
    if openness < 0.12:
        p.setPen(pen(INK, 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath(QPointF(ex - rx + 1, ey))
        path.quadTo(QPointF(ex, ey + 3.5), QPointF(ex + rx - 1, ey))
        p.drawPath(path)
        return
    if openness > 1.0:
        ry *= 1.0 + 0.2 * (openness - 1.0)
    look_x = pose["lookx"] * look_scale[0] + pose["turn"] * 0.8
    look_y = pose["looky"] * look_scale[1]
    p.save()
    if white:
        fill(p, "#FFFFFF", INK, 0.9)
        ellipse(p, ex, ey, rx, ry)
    clip = QPainterPath()
    clip.addEllipse(QPointF(ex, ey), rx + (0 if white else 0.5), ry + (0 if white else 0.5))
    p.setClipPath(clip)
    ix, iy = ex + look_x, ey + look_y + 0.5
    fill(p, iris_color)
    ellipse(p, ix, iy, iris_r)
    fill(p, "#120C08")
    ellipse(p, ix, iy, pupil_r if pupil_r is not None else iris_r * 0.56)
    fill(p, "#FFFFFF")
    ellipse(p, ix - iris_r * 0.36, iy - iris_r * 0.4, max(0.8, iris_r * 0.33))
    if openness < 1.0:
        lid = ey - ry + 2 * ry * (1.0 - openness)
        fill(p, lid_color)
        p.drawRect(QRectF(ex - rx - 1, ey - ry - 1, 2 * rx + 2, lid - (ey - ry) + 1))
        p.setPen(pen(INK, 1.0))
        p.drawLine(QPointF(ex - rx, lid), QPointF(ex + rx, lid))
    p.restore()


def eye_openness(pose, side):
    eyes = max(0.0, pose["eyes"])
    return eyes * (1.0 - pose["wink"]) if side > 0 else eyes


def draw_brow(p, pose, ex, top, side, color, width):
    brow = pose["brow"]
    base = top - 3.2 - brow * 2.2
    inner_drop = max(0.0, -brow) * 2.4
    p.setPen(pen(color, width))
    p.drawLine(QPointF(ex - side * 4.2, base + inner_drop), QPointF(ex + side * 5.2, base + 0.6))


def draw_open_mouth(p, mx, my, width, pose):
    opened = pose["mouth"]
    h = 1.5 + 8.0 * opened
    w = width * (0.75 + 0.3 * opened)
    fill(p, "#5A1E1E", INK, 1.0)
    p.drawEllipse(QRectF(mx - w, my - 1.5 - pose["smile"] * 0.8, 2 * w, h + 1.5))
    if opened > 0.3:
        fill(p, "#E07A86")
        ellipse(p, mx, my + h - 2.2, w * 0.6, min(2.6, h * 0.3))
    return h


def draw_smile(p, mx, my, width, smile, color=INK, line=1.3):
    p.setPen(pen(color, line))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath(QPointF(mx - width, my - smile * 1.5))
    path.quadTo(QPointF(mx, my + smile * 5.0), QPointF(mx + width, my - smile * 1.5))
    p.drawPath(path)


def draw_tongue(p, mx, my, pose):
    if pose["tongue"] > 0.05:
        fill(p, "#E8798A", "#B4505E", 0.8)
        p.drawEllipse(QRectF(mx + 0.5, my - 0.5, 4.6, 3.8 * pose["tongue"] + 1.0))


def draw_blush(p, pet, cx, cy, spread):
    if pet.get("blush"):
        fill(p, C("#F08A9A", 120 * pet["blush"]))
        for side in (-1, 1):
            ellipse(p, cx + side * spread, cy, 4.2, 2.6)


def draw_glow(p, pose, shape, cx, cy):
    """Свет от экрана телефона на лице."""
    if pose["glow"] > 0.01:
        g = QRadialGradient(QPointF(cx, cy), 22)
        g.setColorAt(0, C("#CFE8FF", 110 * pose["glow"]))
        g.setColorAt(1, C("#CFE8FF", 0))
        fill(p, g)
        p.drawPath(shape)


# ---------------------------------------------------------------- обезьянки

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


def draw_monkey_head(p, pet, pose, hx, hy, fx):
    chimp = pet.get("kind") == "chimp"
    fur = C(pet["fur"])
    fur_light = C(pet["fur_light"])
    skin = C(pet["skin"])

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

    cx = hx + fx
    face = face_shape(cx, hy, chimp)
    fill(p, skin, skin.darker(118), 0.8)
    p.drawPath(face)
    draw_glow(p, pose, face, cx, hy + 12)
    draw_blush(p, pet, cx, hy + 9, 15)

    # глаза и брови
    gap = 10.5 if chimp else 9.8
    rx, ry = (5.0, 5.2) if chimp else (5.6, 6.5)
    for side in (-1, 1):
        ex, ey = cx + side * gap, hy - 2
        openness = eye_openness(pose, side)
        draw_eye(p, pose, ex, ey, rx, ry, openness, skin.darker(106), 4.2 if chimp else 3.9,
                 C("#3A2414" if chimp else "#4A2C18"), pupil_r=2.2)
        if pet.get("lashes"):
            p.setPen(pen(INK, 1.0))
            top = ey - ry * min(1.0, openness) if openness >= 0.12 else ey
            ox = ex + side * (rx - 1.0)
            p.drawLine(QPointF(ox, top + 2.0), QPointF(ox + side * 2.6, top - 0.2))
            p.drawLine(QPointF(ox - side * 1.8, top + 0.6), QPointF(ox + side * 0.8, top - 1.6))
        draw_brow(p, pose, ex, ey - ry, side, fur.darker(120), 1.8 if chimp else 1.5)

    # нос и рот
    fill(p, INK)
    spread = 3.4 if chimp else 2.6
    ny = hy + (9 if chimp else 8)
    for side in (-1, 1):
        ellipse(p, cx + side * spread, ny, 1.4 if chimp else 1.2, 1.0)
    mx, my = cx, hy + (17.5 if chimp else 15.5)
    width = 8.0 if chimp else 6.5
    if pose["mouth"] > 0.06:
        draw_open_mouth(p, mx, my, width, pose)
    else:
        draw_smile(p, mx, my, width, pose["smile"])
    draw_tongue(p, mx, my, pose)
    draw_headwear(p, pet, hx, hy, fx)


def draw_headwear(p, pet, hx, hy, fx):
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


# ---------------------------------------------------------------- лягушонок

def frog_eyes(hx, hy, fx):
    return [(hx + side * 13.0 + fx * 0.6, hy - 13.0) for side in (-1, 1)]


def draw_frog_head(p, pet, pose, hx, hy, fx):
    skin_top = C(pet["fur_light"])
    skin = C(pet["fur"])
    belly = C(pet["skin"])
    eyes = frog_eyes(hx, hy, fx)
    head = QPainterPath()
    head.addEllipse(QPointF(hx, hy + 5), 32, 23)
    for ex, ey in eyes:
        head.addEllipse(QPointF(ex, ey), 13.5, 13.0)
    head = head.simplified()
    g = QLinearGradient(0, hy - 26, 0, hy + 28)
    g.setColorAt(0, skin_top)
    g.setColorAt(1, skin)
    fill(p, g, skin.darker(140), 1.0)
    p.drawPath(head)
    # светлый подбородок
    p.save()
    p.setClipPath(head)
    fill(p, belly)
    ellipse(p, hx + fx * 0.5, hy + 22, 25, 11)
    # пятнышки
    fill(p, C(skin.darker(115), 140))
    for dx, dy, r in ((-22, 0, 2.2), (-25, 7, 1.4), (23, 2, 1.8), (19, -4, 1.2), (-4, -6, 1.3)):
        ellipse(p, hx + dx, hy + dy, r)
    p.restore()
    cx = hx + fx
    draw_glow(p, pose, head, cx, hy + 10)
    draw_blush(p, pet, cx, hy + 8, 21)

    # большие глаза на макушке
    for side, (ex, ey) in zip((-1, 1), eyes):
        draw_eye(p, pose, ex, ey, 9.5, 10.0, eye_openness(pose, side), skin_top, 6.0,
                 C("#2F6DB5"), look_scale=(3.0, 2.6), pupil_r=3.2)
        # веко-бровь показывает настроение
        brow = pose["brow"]
        p.setPen(pen(skin.darker(150), 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        y = ey - 11.5 - brow * 1.5
        inner = max(0.0, -brow) * 2.5
        p.drawLine(QPointF(ex - side * 5, y + inner), QPointF(ex + side * 6, y + 0.8))

    if pet.get("glasses") and pose["glassoff"] < 0.5:
        draw_glasses(p, eyes, hx)

    # ноздри и широкий рот
    fill(p, skin.darker(170))
    for side in (-1, 1):
        ellipse(p, cx + side * 3.2, hy + 3.5, 0.9, 0.7)
    mx, my = cx, hy + 11
    if pose["mouth"] > 0.06:
        draw_open_mouth(p, mx, my, 9.5, pose)
    else:
        draw_smile(p, mx, my, 19.0, pose["smile"] * 0.9, skin.darker(190), 1.5)
    draw_tongue(p, mx, my, pose)


def draw_glasses(p, eyes, hx, scale=1.0):
    """Толстая чёрная оправа (как на картинке)."""
    p.setBrush(Qt.BrushStyle.NoBrush)
    for ex, ey in eyes:
        p.setPen(pen("#111114", 2.8 * scale))
        p.drawRoundedRect(QRectF(ex - 12.5 * scale, ey - 11 * scale, 25 * scale, 21 * scale),
                          6 * scale, 6 * scale)
        p.setPen(pen(C("#FFFFFF", 70), 1.2 * scale))
        p.drawLine(QPointF(ex - 8 * scale, ey - 7 * scale), QPointF(ex - 4 * scale, ey - 8.5 * scale))
    (x1, y1), (x2, y2) = eyes
    p.setPen(pen("#111114", 2.4 * scale))
    path = QPainterPath(QPointF(x1 + 12.5 * scale, y1 - 1 * scale))
    path.quadTo(QPointF((x1 + x2) / 2, y1 - 5 * scale), QPointF(x2 - 12.5 * scale, y2 - 1 * scale))
    p.drawPath(path)


# ---------------------------------------------------------------- плюшевый лев

def _mane_tufts():
    """Неровная, слегка помятая грива: у каждой пряди свой размер и наклон."""
    rnd = random.Random(11)
    outer = []
    for i in range(22):
        a = i / 22.0 * 2 * math.pi + rnd.uniform(-0.12, 0.12)
        outer.append((a, rnd.uniform(29, 36), rnd.uniform(7.5, 11.5), rnd.uniform(0.85, 1.15)))
    inner = []
    for i in range(16):
        a = i / 16.0 * 2 * math.pi + rnd.uniform(-0.15, 0.15)
        inner.append((a, rnd.uniform(22, 26), rnd.uniform(6.5, 9.0), rnd.uniform(0.9, 1.1)))
    strands = []
    for _ in range(14):
        a = rnd.uniform(0, 2 * math.pi)
        strands.append((a, rnd.uniform(34, 40), rnd.uniform(4, 9), rnd.uniform(-0.5, 0.5)))
    fuzz = [(rnd.uniform(-18, 18), rnd.uniform(-16, 20), rnd.uniform(0, math.pi))
            for _ in range(26)]
    return outer, inner, strands, fuzz


MANE = _mane_tufts()


def draw_lion_head(p, pet, pose, hx, hy, fx, t=0.0):
    fur = C(pet["fur"])
    fur_light = C(pet["fur_light"])
    mane = C(pet["mane"])
    mane_light = C(pet["mane_light"])
    muzzle = C(pet["skin"])
    outer, inner, strands, fuzz = MANE
    puff = 1.0 + 0.16 * pose["puff"]
    ruffle = pose["ruffle"]
    my_c = hy + 3

    def wiggle(i):
        return ruffle * 2.5 * math.sin(t * 11.0 + i * 1.7)

    # грива: тёмные пряди снаружи, светлые внутри, торчащие волоски
    for i, (a, r, size, stretch) in enumerate(outer):
        x = hx + math.cos(a) * r * puff + wiggle(i)
        y = my_c + math.sin(a) * r * puff * 0.95 + wiggle(i + 3)
        fill(p, mane.darker(108) if i % 3 else mane)
        p.save()
        p.translate(x, y)
        p.rotate(math.degrees(a))
        p.drawEllipse(QRectF(-size * stretch, -size * 0.8, 2 * size * stretch, 1.6 * size))
        p.restore()
    p.setPen(pen(mane.darker(125), 1.1))
    for i, (a, r, length, bend) in enumerate(strands):
        x0, y0 = hx + math.cos(a) * r * puff, my_c + math.sin(a) * r * puff
        x1 = x0 + math.cos(a + bend) * length + wiggle(i)
        y1 = y0 + math.sin(a + bend) * length
        p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
    for i, (a, r, size, stretch) in enumerate(inner):
        fill(p, mane_light if i % 2 else mane_light.darker(106))
        ellipse(p, hx + math.cos(a) * r * puff + wiggle(i + 7),
                my_c + math.sin(a) * r * puff * 0.95, size * stretch, size)

    # уши — чуть кривые, плюшевые
    for side, (dy, rot) in ((-1, (-16.0, -12)), (1, (-18.5, 18))):
        ex = hx + side * 17.5 - fx * 0.3
        p.save()
        p.translate(ex, hy + dy)
        p.rotate(rot)
        fill(p, fur, fur.darker(130), 0.8)
        p.drawEllipse(QRectF(-6.5, -6, 13, 12))
        fill(p, C("#E7C9A0"))
        p.drawEllipse(QRectF(-3.6, -3.2, 7.2, 6.4))
        p.restore()

    # мордочка
    face = QPainterPath()
    face.addEllipse(QPointF(hx + fx * 0.3, my_c), 23.5, 22.5)
    g = QRadialGradient(QPointF(hx - 6, hy - 6), 30)
    g.setColorAt(0, fur_light)
    g.setColorAt(1, fur)
    fill(p, g, fur.darker(125), 0.8)
    p.drawPath(face)
    # плюшевый ворс
    p.setPen(pen(C(fur.darker(112), 150), 0.7))
    for dx, dy, a in fuzz:
        x, y = hx + fx * 0.3 + dx, my_c + dy
        p.drawLine(QPointF(x, y), QPointF(x + 1.6 * math.cos(a), y + 1.6 * math.sin(a)))
    cx = hx + fx
    draw_glow(p, pose, face, cx, hy + 12)

    # переносица и белая пушистая мордочка
    fill(p, C("#B98146", 150))
    p.drawPolygon(poly([(cx - 3.5, hy - 3), (cx + 3.5, hy - 3), (cx + 6, hy + 7), (cx - 6, hy + 7)]))
    fill(p, muzzle)
    for dx, dy, rx, ry in ((-5.5, 13, 8, 6.8), (5.5, 13, 8, 6.8), (0, 19, 7.5, 5.5)):
        ellipse(p, cx + dx, hy + dy, rx, ry)
    p.setPen(pen(C("#D9CFBF"), 0.6))
    for dx in (-9, -6, 6, 9):
        p.drawLine(QPointF(cx + dx, hy + 11), QPointF(cx + dx * 1.15, hy + 12.5))

    # глаза-бусинки
    for side in (-1, 1):
        ex, ey = cx + side * 9.5, hy + 1.0
        openness = eye_openness(pose, side)
        if openness < 0.12:
            p.setPen(pen("#2A1A10", 1.3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath(QPointF(ex - 3.2, ey))
            path.quadTo(QPointF(ex, ey + 2.6), QPointF(ex + 3.2, ey))
            p.drawPath(path)
        else:
            k = min(1.25, openness)
            lx, ly = pose["lookx"] * 1.0, pose["looky"] * 0.8
            fill(p, "#1A120C")
            p.drawEllipse(QRectF(ex - 3.5 + lx, ey - 3.9 * k + ly, 7.0, 7.8 * k))
            fill(p, C("#FFFFFF", 220))
            ellipse(p, ex - 1.2 + lx, ey - 1.5 * k + ly, 1.2)
        brow = pose["brow"]
        base = ey - 7.5 - brow * 1.8
        inner_drop = max(0.0, -brow) * 2.0
        p.setPen(pen(C("#A9763D"), 1.4))
        p.drawLine(QPointF(ex - side * 3.5, base + inner_drop), QPointF(ex + side * 4.5, base + 0.8))

    # нос-треугольник и рот «галочкой», как у игрушки
    fill(p, "#3E2A1E", "#2A1A10", 0.6)
    p.drawPolygon(poly([(cx - 5, hy + 6), (cx + 5, hy + 6), (cx + 1, hy + 10.5), (cx - 1, hy + 10.5)]))
    fill(p, C("#FFFFFF", 120))
    ellipse(p, cx - 1.5, hy + 7, 1.4, 0.8)
    smile = pose["smile"] + pet.get("smile_bias", -0.35)
    if pose["mouth"] > 0.06:
        h = draw_open_mouth(p, cx, hy + 17, 7.0, pose)
        if pose["mouth"] > 0.5:  # клыки, когда рычит
            fill(p, "#FFFFFF")
            for side in (-1, 1):
                p.drawPolygon(poly([(cx + side * 3.5, hy + 16), (cx + side * 1.8, hy + 16),
                                    (cx + side * 2.8, hy + 16 + min(4.0, h * 0.4))]))
    else:
        p.setPen(pen("#2A1A10", 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(cx, hy + 10.5), QPointF(cx, hy + 14))
        path = QPainterPath(QPointF(cx - 5.5, hy + 17.5 - smile * 3.5))
        path.quadTo(QPointF(cx - 2.5, hy + 13.5 + smile * 1.5), QPointF(cx, hy + 14))
        path.quadTo(QPointF(cx + 2.5, hy + 13.5 + smile * 1.5), QPointF(cx + 5.5, hy + 17.5 - smile * 3.5))
        p.drawPath(path)
    draw_tongue(p, cx, hy + 16, pose)
