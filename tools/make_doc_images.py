# -*- coding: utf-8 -*-
"""Картинки для README, инструкции и презентации: python tools/make_doc_images.py

docs/img/<питомец>.png — каждый питомец за любимым делом, boss.png — начальник застал
питомца отдыхающим, fox.png — лиса за окном, quiz.png — вопрос викторины.
Нужен только PyQt5 (QGIS не нужен).
"""

import os
import random
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qgis_shim  # noqa: E402,F401

from PyQt5.QtGui import QColor, QImage, QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from preview import render  # noqa: E402
from q_pets.brain import PetBrain  # noqa: E402
from q_pets.drawing import H, W, draw_scene  # noqa: E402
from q_pets.pets import PETS_BY_KEY  # noqa: E402
from q_pets.visitors import BOSS_WALK  # noqa: E402

OUT = os.path.join(ROOT, "docs", "img")
WIDTH = 960

FAVOURITES = [("bow", "tiger_play", 3.0), ("cap", "dance", 3.0), ("chimp", "plane", 3.2),
              ("frog", "fly", 6.1), ("lion", "roar", 1.8)]


def scene_with_visitors(pet_key, visitor, seed=4):
    """Сцена с гостем: время идёт по шагам, питомец успевает заскучать и отдыхать."""
    pet = PETS_BY_KEY[pet_key]
    brain = PetBrain(pet, rng=random.Random(seed), now=0.0, boss=False, fox=False)
    now = 0.0
    while now < 40.0:                     # 40 с без нажатий — питомец занят своими делами
        now += 0.2
        brain.update(now)
    if visitor == "boss":
        brain.boss.enabled = True
        brain.boss.call(now)
        end = now + BOSS_WALK + 2.5
    else:
        brain.fox.enabled = True
        brain.fox.call(now)
        end = now + 3.0
    while now < end:
        now += 0.1
        brain.update(now)
    img = QImage(WIDTH, int(WIDTH * H / W), QImage.Format.Format_ARGB32)
    img.fill(QColor(pet["wall"]))
    p = QPainter(img)
    p.scale(WIDTH / W, WIDTH / W)
    ctx = {"t": now, "screen": brain.screen(), "hour": 12}
    ctx.update(brain.visitors(now))
    draw_scene(p, pet, brain.pose(now), ctx)
    p.end()
    return img


def quiz_image():
    from q_pets.quiz_questions import QUESTIONS
    from q_pets.quiz_widget import QuizWidget
    widget = QuizWidget()
    widget.resize(480, 360)
    question = dict(QUESTIONS[0])
    widget.show_question(question, "Счёт: 7 из 9")
    widget.show()
    QApplication.processEvents()
    image = widget.grab().toImage()
    widget.timer.stop()
    return image


if __name__ == "__main__":
    app = QApplication(sys.argv[:1])
    os.makedirs(OUT, exist_ok=True)
    for key, activity, t in FAVOURITES:
        render(PETS_BY_KEY[key], activity, t, WIDTH).save(os.path.join(OUT, key + ".png"))
    scene_with_visitors("chimp", "boss").save(os.path.join(OUT, "boss.png"))
    scene_with_visitors("bow", "fox", seed=2).save(os.path.join(OUT, "fox.png"))
    quiz_image().save(os.path.join(OUT, "quiz.png"))
    print(OUT)
