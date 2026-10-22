# -*- coding: utf-8 -*-
"""Иконка плагина (q_pets/icon.png) — голова первого питомца: python tools/make_icon.py"""

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
from q_pets.drawing import draw_head  # noqa: E402
from q_pets.pets import PETS  # noqa: E402

SIZE = 64

if __name__ == "__main__":
    app = QApplication(sys.argv[:1])
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    scale = SIZE / 96.0
    p.scale(scale, scale)
    p.translate(48 - 150, 48 - 72)
    draw_head(p, PETS[0], pose(turn=0.0, lookx=0.0, looky=0.2, smile=0.8))
    p.end()
    path = os.path.join(ROOT, "q_pets", "icon.png")
    img.save(path)
    print(path)
