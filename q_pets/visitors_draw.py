# -*- coding: utf-8 -*-
"""Рисование гостей: начальник-горилла с кружкой BOSS, лиса за окном, облачка с речью."""

import math

from qgis.PyQt.QtCore import QPointF, QRectF, Qt
from qgis.PyQt.QtGui import QFont, QLinearGradient, QPainterPath

from .paint import C, ellipse, fill, pen, poly

SCENE_W = 320.0


def flag(value):
    """Флаги Qt как число (в Qt6 перечисления — не int)."""
    return value.value if hasattr(value, "value") else int(value)


TEXT_FLAGS = flag(Qt.TextFlag.TextWordWrap) | flag(Qt.AlignmentFlag.AlignHCenter)


# ---------------------------------------------------------------- облачка

def draw_bubble(p, text, anchor, alpha, thought=False, side="right", max_w=112.0, px=8):
    """Облачко с текстом; хвостик (или цепочка кружков у мыслей) — к точке anchor."""
    if alpha < 0.02 or not text:
        return
    font = QFont()
    font.setPixelSize(px)
    p.save()
    p.setFont(font)
    text_rect = p.boundingRect(QRectF(0, 0, max_w, 200), TEXT_FLAGS, text)
    w, h = text_rect.width() + 12, text_rect.height() + 8
    ax, ay = anchor
    x = ax + 4 if side == "right" else ax - w - 4
    x = max(3.0, min(SCENE_W - 3.0 - w, x))
    y = max(3.0, ay - h - (14 if thought else 9))
    p.setOpacity(alpha)
    border = C("#5A5A66")
    if thought:
        for i, r in enumerate((1.6, 2.4, 3.2)):
            k = (i + 1) / 4.0
            fill(p, "#FFFFFF", border, 0.8)
            ellipse(p, ax + (x + 14 - ax) * k, ay + (y + h - ay) * k, r)
        fill(p, "#FFFFFF", border, 0.9)
        for bx in range(int(x + 8), int(x + w - 4), 9):  # «облачные» бугорки
            ellipse(p, bx, y + 1, 5.2)
            ellipse(p, bx + 4, y + h - 1, 5.2)
        p.drawRoundedRect(QRectF(x, y, w, h), 8, 8)
        fill(p, "#FFFFFF")
        p.drawRoundedRect(QRectF(x + 1, y + 1, w - 2, h - 2), 7, 7)
        for bx in range(int(x + 8), int(x + w - 4), 9):
            ellipse(p, bx, y + 1.5, 4.4)
            ellipse(p, bx + 4, y + h - 1.5, 4.4)
    else:
        tip_x = max(x + 8, min(x + w - 8, ax))
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), 6, 6)
        tail = QPainterPath(QPointF(tip_x - 4, y + h - 1))
        tail.lineTo(QPointF(ax, ay))
        tail.lineTo(QPointF(tip_x + 4, y + h - 1))
        tail.closeSubpath()
        fill(p, "#FFFFFF", border, 0.9)
        p.drawPath(path.united(tail))
    p.setPen(pen("#26262E"))
    p.drawText(QRectF(x + 6, y + 4, w - 12, h - 8), TEXT_FLAGS, text)
    p.restore()


# ---------------------------------------------------------------- начальник

def draw_boss(p, boss):
    """Большая горилла в костюме; в правой руке — кружка BOSS."""
    t = boss["t"]
    bx = boss["x"]
    bob = -2.5 * abs(math.sin(t * 7.0)) * boss["walk"]
    p.save()
    p.translate(0, bob)

    # туловище: пиджак, рубашка, красный галстук
    jacket = C("#3B3F4A")
    body = QPainterPath(QPointF(bx - 50, 300))
    body.lineTo(QPointF(bx - 52, 104))
    body.quadTo(QPointF(bx - 50, 82), QPointF(bx - 26, 80))
    body.lineTo(QPointF(bx + 26, 80))
    body.quadTo(QPointF(bx + 50, 82), QPointF(bx + 52, 104))
    body.lineTo(QPointF(bx + 50, 300))
    body.closeSubpath()
    g = QLinearGradient(bx - 50, 0, bx + 50, 0)
    g.setColorAt(0, jacket.darker(115))
    g.setColorAt(0.5, jacket.lighter(110))
    g.setColorAt(1, jacket.darker(120))
    fill(p, g, jacket.darker(150), 1.0)
    p.drawPath(body)
    fill(p, "#F4F4F0")
    p.drawPolygon(poly([(bx - 13, 80), (bx + 13, 80), (bx, 122)]))
    fill(p, "#C0392B", "#8E2A20", 0.6)
    p.drawPolygon(poly([(bx - 3, 84), (bx + 3, 84), (bx + 4.5, 114), (bx, 120), (bx - 4.5, 114)]))
    p.setPen(pen(jacket.lighter(140), 1.0))
    p.drawLine(QPointF(bx - 13, 81), QPointF(bx - 3, 128))
    p.drawLine(QPointF(bx + 13, 81), QPointF(bx + 3, 128))
    # левая рука висит вдоль тела
    p.setBrush(Qt.BrushStyle.NoBrush)
    arm = QPainterPath(QPointF(bx - 44, 92))
    arm.quadTo(QPointF(bx - 60, 130), QPointF(bx - 52, 176))
    p.setPen(pen(jacket.darker(150), 17))
    p.drawPath(arm)
    p.setPen(pen(jacket, 15))
    p.drawPath(arm)

    draw_boss_head(p, boss, bx)

    # правая рука с кружкой BOSS (иногда отхлёбывает)
    sip = boss["sip"]
    mug_x = bx + 40 + (bx + 14 - (bx + 40)) * sip
    mug_y = 112 + (70 - 112) * sip
    hand = (mug_x - 11, mug_y + 1)  # держит за ручку — надпись видна
    arm = QPainterPath(QPointF(bx + 44, 92))
    arm.quadTo(QPointF(bx + 62 - 10 * sip, 120 - 6 * sip), QPointF(*hand))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen(jacket.darker(150), 17))
    p.drawPath(arm)
    p.setPen(pen(jacket, 15))
    p.drawPath(arm)
    p.save()
    p.translate(mug_x, mug_y)
    p.rotate(-28 * sip)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen("#D9D9D4", 2.6))
    p.drawEllipse(QRectF(-14, -5, 8, 9))
    fill(p, "#FAFAF7", "#9A9A94", 1.0)
    p.drawRoundedRect(QRectF(-8, -10, 17, 20), 2, 2)
    fill(p, "#3A2414", "#9A9A94", 0.6)
    p.drawEllipse(QRectF(-8, -12, 17, 4))
    font = QFont()
    font.setPixelSize(5)
    font.setBold(True)
    p.setFont(font)
    p.setPen(pen("#111111"))
    p.drawText(QRectF(-8, -5, 17, 9), flag(Qt.AlignmentFlag.AlignCenter), "BOSS")
    p.restore()
    fill(p, "#4A4148", "#2A242A", 0.8)
    ellipse(p, hand[0], hand[1], 6.5, 6)
    p.restore()


def draw_boss_head(p, boss, bx):
    t = boss["t"]
    shake = boss["shake"] * 7.0 * math.sin(t * 12.0)
    p.save()
    p.translate(bx, 76)
    p.rotate(shake)
    p.translate(-bx, -76)
    fur = C("#2A2A2E")
    skin = C("#5A5058")
    fill(p, fur, "#151517", 1.0)
    ellipse(p, bx, 72, 20, 9)          # загривок
    ellipse(p, bx, 30, 15, 12)         # «гребень» на макушке
    ellipse(p, bx, 50, 27, 26)
    for side in (-1, 1):
        fill(p, skin.darker(115))
        ellipse(p, bx + side * 26, 53, 5)
    face = QPainterPath()
    face.addEllipse(QPointF(bx, 45), 21, 7.5)
    face.addEllipse(QPointF(bx, 54), 15, 9)
    face.addEllipse(QPointF(bx, 63), 17, 12.5)
    face = face.simplified()
    fill(p, skin, skin.darker(130), 0.8)
    p.drawPath(face)
    # глаза под тяжёлыми бровями; смотрят на питомца
    mood = boss["mood"]
    for side in (-1, 1):
        ex, ey = bx + side * 8, 51
        fill(p, "#F2EDE4")
        ellipse(p, ex, ey, 2.9, 2.3)
        fill(p, "#2A1A12")
        ellipse(p, ex + 1.0, ey + 0.2, 1.6)
        stern = 2.2 if mood == "stern" else 0.6
        p.setPen(pen("#1E1B20", 2.4))
        p.drawLine(QPointF(ex - side * 1.5, ey - 3.5 + stern * 0.4),
                   QPointF(ex + side * 5.5, ey - 4.5 - stern * 0.6))
    # широкий нос
    fill(p, skin.darker(125))
    ellipse(p, bx, 59, 7.5, 4.5)
    fill(p, "#1A1618")
    ellipse(p, bx - 3.2, 60, 1.9, 1.5)
    ellipse(p, bx + 3.2, 60, 1.9, 1.5)
    # рот: ворчит, говорит или молчит
    if boss.get("talking"):
        open_k = 0.5 + 0.5 * abs(math.sin(t * 11.0))
        fill(p, "#2A1216", "#1A1618", 0.8)
        p.drawEllipse(QRectF(bx - 6, 67, 12, 2.5 + 4.5 * open_k))
    else:
        curve = -2.5 if mood == "stern" else 1.0
        p.setPen(pen("#1A1618", 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath(QPointF(bx - 8, 69))
        path.quadTo(QPointF(bx, 69 + curve), QPointF(bx + 8, 69))
        p.drawPath(path)
    p.restore()


def boss_speech_anchor(boss):
    return boss["x"] + 20, 60.0


# ---------------------------------------------------------------- лиса за окном

def draw_fox(p, fox):
    """Лиса выглядывает из-за ёлок за окном (рисуется внутри рамки окна)."""
    rise = fox["rise"]
    if rise < 0.01:
        return
    x = fox["x"]
    y = 116.0 - 30.0 * rise
    orange = C("#E2742B")
    fill(p, orange, orange.darker(140), 0.8)
    p.drawRoundedRect(QRectF(x - 11, y + 6, 22, 20), 8, 8)      # плечи
    fill(p, "#FFF4E8")
    ellipse(p, x, y + 12, 6, 6)
    for side in (-1, 1):                                        # уши
        fill(p, orange, orange.darker(140), 0.8)
        p.drawPolygon(poly([(x + side * 8.5, y - 3), (x + side * 5.5, y - 14), (x + side * 1.5, y - 6)]))
        fill(p, "#2A1A12")
        p.drawPolygon(poly([(x + side * 6.6, y - 10), (x + side * 5.5, y - 14), (x + side * 4.4, y - 10.5)]))
    fill(p, orange, orange.darker(140), 0.8)
    ellipse(p, x, y, 10, 8.5)
    fill(p, "#FFF4E8")
    p.drawPolygon(poly([(x - 9.5, y + 1), (x, y + 8.5), (x + 9.5, y + 1), (x + 4, y + 3), (x - 4, y + 3)]))
    fill(p, "#1A1210")
    ellipse(p, x, y + 4.5, 1.6, 1.2)
    if fox["bino"]:
        # бинокль
        fill(p, "#2B2E35", "#111316", 0.6)
        for side in (-1, 1):
            p.drawRoundedRect(QRectF(x + side * 4 - 3.2, y - 4.5, 6.4, 6), 2, 2)
        fill(p, "#7FB3E0")
        for side in (-1, 1):
            ellipse(p, x + side * 4, y - 1.6, 2.0)
        fill(p, C("#FFFFFF", 200))
        ellipse(p, x - 4.6, y - 2.4, 0.7)
        fill(p, orange.lighter(110), orange.darker(140), 0.6)
        ellipse(p, x - 8.5, y + 3, 2.6, 2.2)
        ellipse(p, x + 8.5, y + 3, 2.6, 2.2)
    else:
        # хитрые прищуренные глаза косятся на питомца
        for side in (-1, 1):
            ex, ey = x + side * 4, y - 1.2
            fill(p, "#1A1210")
            ellipse(p, ex + 0.8, ey + 0.2, 1.5, 1.1)
            p.setPen(pen("#1A1210", 0.9))
            p.drawLine(QPointF(ex - 2.4, ey - 1.2 + side * 0.4), QPointF(ex + 2.4, ey - 1.4 - side * 0.4))


def fox_thought_anchor(fox):
    return fox["x"] + 8, 116.0 - 30.0 * fox["rise"] - 12
