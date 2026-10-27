# -*- coding: utf-8 -*-
"""Иконка плагина (q_pets/icon.png) — головы всех питомцев: python tools/make_icon.py"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qgis_shim  # noqa: E402,F401

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QImage, QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from q_pets.animation import pose  # noqa: E402
from q_pets.heads import draw_head  # noqa: E402
from q_pets.pets import get_pet  # noqa: E402

SIZE = 128
# (питомец, центр головы на иконке, масштаб): сзади — Аня, Роберт, Маша; спереди — Сема и Денис
LAYOUT = [("bow", 24, 40, 0.64), ("chimp", 64, 34, 0.64), ("cap", 104, 40, 0.64),
          ("frog", 38, 92, 0.74), ("lion", 91, 90, 0.7)]

if __name__ == "__main__":
    app = QApplication(sys.argv[:1])
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    face = pose(turn=0.0, lookx=0.0, looky=0.2, smile=0.8, puff=0.3)
    for key, x, y, scale in LAYOUT:
        p.save()
        p.translate(x, y)
        p.scale(scale, scale)
        p.translate(-150, -82)
        draw_head(p, get_pet(key), face)
        p.restore()
    p.end()
    path = os.path.join(ROOT, "q_pets", "icon.png")
    img.save(path)
    print(path)
