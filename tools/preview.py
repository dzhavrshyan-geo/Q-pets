# -*- coding: utf-8 -*-
"""Картинки сцены без QGIS: python tools/preview.py папка [ширина]

Для каждого питомца рисует лист с кадрами всех анимаций (sheet_<питомец>.png).
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qgis_shim  # noqa: E402,F401

from PyQt5.QtCore import QRectF, Qt  # noqa: E402
from PyQt5.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from q_pets.animation import ACTIVITIES, Animator  # noqa: E402
from q_pets.drawing import H, W, draw_scene  # noqa: E402
from q_pets.pets import PETS  # noqa: E402

SHOTS = [
    ("typing", 0.3), ("mouse", 1.0), ("focus", 6.0), ("thinking", 5.0),
    ("window", 4.0), ("phone", 4.0), ("coffee", 3.0), ("coffee", 5.5),
    ("stretch", 2.0), ("nap", 2.0), ("wake", 0.3), ("wave", 0.5),
]
SPECIAL_TIMES = (4.0, 8.0)


def render(pet, name, t, width, hour=12):
    img = QImage(width, int(width * H / W), QImage.Format.Format_ARGB32)
    img.fill(QColor("#FFFFFF"))
    p = QPainter(img)
    p.scale(width / W, width / W)
    anim = Animator(pet)
    anim.play(name, 0.0)
    pose = anim.pose(t)
    draw_scene(p, pet, pose, {"t": 100 + t, "screen": ACTIVITIES[name].screen, "hour": hour})
    p.end()
    return img


def sheet(pet, width, out):
    shots = SHOTS + [(pet["special"], s) for s in SPECIAL_TIMES]
    cols = 4
    rows = (len(shots) + cols - 1) // cols
    cell_h = int(width * H / W) + 14
    img = QImage(cols * width, rows * cell_h, QImage.Format.Format_ARGB32)
    img.fill(QColor("#FFFFFF"))
    p = QPainter(img)
    font = QFont()
    font.setPixelSize(11)
    p.setFont(font)
    for i, (name, t) in enumerate(shots):
        x, y = (i % cols) * width, (i // cols) * cell_h
        hour = 21 if name in ("nap", "wake") else 18 if name == "window" else 12
        p.drawImage(x, y + 14, render(pet, name, t, width, hour))
        p.setPen(QColor("#000000"))
        p.drawText(QRectF(x + 4, y, width, 14), Qt.AlignmentFlag.AlignLeft, "%s t=%.1f" % (name, t))
    p.end()
    img.save(os.path.join(out, "sheet_%s.png" % pet["key"]))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    os.makedirs(out, exist_ok=True)
    app = QApplication(sys.argv[:1])
    for pet in PETS:
        sheet(pet, width, out)
        render(pet, "focus", 0.5, 960).save(os.path.join(out, "big_%s.png" % pet["key"]))
    print("готово:", out)
