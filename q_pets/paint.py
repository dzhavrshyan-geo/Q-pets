# -*- coding: utf-8 -*-
"""Общие мелочи для рисования: цвета, перья, заливки."""

from qgis.PyQt.QtCore import QPointF, Qt
from qgis.PyQt.QtGui import QBrush, QColor, QLinearGradient, QPen, QPolygonF, QRadialGradient

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
