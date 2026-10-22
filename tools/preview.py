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

# Самые выразительные моменты каждой анимации (секунды от начала)
MOMENTS = {
    "typing": (0.3, 3.15), "mouse": (1.0,), "scroll": (1.0,), "thinking": (3.0, 12.5),
    "read": (2.0,), "chin": (3.0,), "scratch": (2.0,), "lean": (2.5,), "notes": (2.5,),
    "neck": (1.5,), "window": (4.0,), "phone": (1.6, 4.0), "coffee": (1.7, 2.6, 4.2, 6.2),
    "stretch": (0.9, 2.0), "banana": (1.8, 2.8, 5.0, 8.2), "read_doc": (1.6, 4.0),
    "selfie": (3.2, 6.5), "relax": (3.0,), "board": (3.2,), "nap": (2.0,), "wake": (0.3,),
    "wave": (0.5,), "saved": (0.8,), "oops": (0.8,),
    "tiger": (4.0,), "tiger_play": (3.0,), "daydream": (4.0,), "dance": (3.0,),
    "ponder": (8.0,), "plane": (1.5, 3.2, 4.8),
}
SPECIALS = {"tiger", "tiger_play", "daydream", "dance", "ponder", "plane"}


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
    shots = [(name, t) for name, times in MOMENTS.items()
             if name not in SPECIALS or name in pet["specials"] for t in times]
    cols = 6
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
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 320
    os.makedirs(out, exist_ok=True)
    app = QApplication(sys.argv[:1])
    for pet in PETS:
        sheet(pet, width, out)
    print("готово:", out)
