# -*- coding: utf-8 -*-
"""Окошко питомца: сцена с анимацией (или вопрос викторины) и нижняя панель."""

import time

from qgis.PyQt.QtCore import QSize, Qt, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QColor, QPainter
from qgis.PyQt.QtWidgets import (QComboBox, QHBoxLayout, QMenu, QSizePolicy, QStackedWidget,
                                 QToolButton, QVBoxLayout, QWidget)

try:
    from qgis.PyQt.QtGui import QActionGroup
except ImportError:  # Qt5
    from qgis.PyQt.QtWidgets import QActionGroup

from .brain import PetBrain
from .drawing import H, W, draw_scene
from .pets import PETS, get_pet
from .quiz import Quiz, format_ids, parse_ids
from .quiz_widget import QuizWidget

KEY_PET = "q_pets/pet"
KEY_IDLE = "q_pets/idle_timeout"
KEY_NAP = "q_pets/nap"
KEY_COLLAPSED = "q_pets/collapsed"
KEY_BOSS = "q_pets/boss"
KEY_FOX = "q_pets/fox"
KEY_AWAY = "q_pets/away"
KEY_QUIZ = "q_pets/quiz"
KEY_QUIZ_EVERY = "q_pets/quiz_every"
KEY_QUIZ_SEEN = "q_pets/quiz_seen"
KEY_QUIZ_RIGHT = "q_pets/quiz_right"
KEY_QUIZ_TOTAL = "q_pets/quiz_total"
IDLE_CHOICES = (10, 15, 30, 60)
QUIZ_CHOICES = (5, 10, 15, 30)  # минут между вопросами
NAP_AFTER = 180.0
FPS = 25


def to_bool(value):
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


class PetView(QWidget):
    """Сцена с питомцем. Анимация идёт, только пока окно видно."""

    def __init__(self, brain, parent=None):
        super().__init__(parent)
        self.brain = brain
        self.busy_probe = None  # функция: занят ли QGIS
        self.t0 = time.monotonic()
        self.setMinimumSize(120, 90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Щёлкните по питомцу — он помашет")
        self.timer = QTimer(self)
        self.timer.setInterval(1000 // FPS)
        self.timer.timeout.connect(self.tick)
        self.failed = False

    def sizeHint(self):
        return QSize(320, 240)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.failed:
            self.timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.timer.stop()

    def tick(self):
        if self.window().isMinimized():
            return
        now = time.monotonic()
        if self.busy_probe is not None:
            self.brain.set_busy(self.busy_probe(), now)
        self.brain.update(now)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.brain.poke(time.monotonic())
        super().mousePressEvent(event)

    def paintEvent(self, event):
        now = time.monotonic()
        pet = self.brain.pet
        p = QPainter(self)
        try:
            w, h = float(self.width()), float(self.height())
            # Заполняем окно сценой; если пропорции сильно другие — не обрезаем больше 20 %
            fit = min(w / W, h / H)
            scale = min(max(w / W, h / H), fit * 1.25)
            p.fillRect(self.rect(), QColor(pet["wall"]))
            p.translate((w - W * scale) / 2.0, (h - H * scale) / 2.0)
            p.scale(scale, scale)
            local = time.localtime()
            ctx = {"t": now - self.t0, "screen": self.brain.screen(),
                   "hour": local.tm_hour + local.tm_min / 60.0}
            ctx.update(self.brain.visitors(now))
            draw_scene(p, pet, self.brain.pose(now), ctx)
        except Exception:
            # Ошибку покажем один раз, а не 25 раз в секунду
            self.failed = True
            self.timer.stop()
            raise
        finally:
            p.end()


class PetPanel(QWidget):
    """Содержимое панели Q-pets: сцена (или вопрос викторины) и нижняя панель."""

    collapsedChanged = pyqtSignal(bool)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        pet = get_pet(settings.value(KEY_PET, PETS[0]["key"]))
        idle = int(settings.value(KEY_IDLE, 15))
        nap = to_bool(settings.value(KEY_NAP, True))
        now = time.monotonic()
        self.brain = PetBrain(pet, idle_timeout=idle, nap_after=NAP_AFTER if nap else None,
                              now=now, boss=to_bool(settings.value(KEY_BOSS, True)),
                              fox=to_bool(settings.value(KEY_FOX, True)),
                              can_leave=to_bool(settings.value(KEY_AWAY, True)))
        self.view = PetView(self.brain, self)

        # викторина
        self.quiz = Quiz(seen=parse_ids(settings.value(KEY_QUIZ_SEEN, "")))
        self.quiz_enabled = to_bool(settings.value(KEY_QUIZ, True))
        self.quiz_every = int(settings.value(KEY_QUIZ_EVERY, 5))
        self.quiz_right = int(settings.value(KEY_QUIZ_RIGHT, 0))
        self.quiz_total = int(settings.value(KEY_QUIZ_TOTAL, 0))
        self.next_quiz = now + self.quiz_every * 60.0
        self.quiz_widget = QuizWidget(self)
        self.quiz_widget.answered.connect(self.on_quiz_answered)
        self.quiz_widget.finished.connect(self.hide_quiz)
        self.quiz_reaction = None
        self.quiz_timer = QTimer(self)
        self.quiz_timer.setInterval(15000)
        self.quiz_timer.timeout.connect(self.check_quiz)
        self.quiz_timer.start()

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.view)
        self.stack.addWidget(self.quiz_widget)

        self.combo = QComboBox(self)
        for item in PETS:
            self.combo.addItem(item["name"], item["key"])
        self.combo.setCurrentIndex(max(0, self.combo.findData(pet["key"])))
        self.combo.setToolTip("Питомец")
        self.combo.currentIndexChanged.connect(self.on_pet_changed)

        self.settings_button = QToolButton(self)
        self.settings_button.setText("⚙")
        self.settings_button.setToolTip("Настройки")
        self.settings_button.setAutoRaise(True)
        self.settings_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.settings_button.setMenu(self.build_menu(idle, nap))

        self.collapse_button = QToolButton(self)
        self.collapse_button.setAutoRaise(True)
        self.collapse_button.clicked.connect(lambda: self.set_collapsed(not self.collapsed))

        bar = QHBoxLayout()
        bar.setContentsMargins(4, 2, 4, 2)
        bar.setSpacing(2)
        bar.addWidget(self.combo, 1)
        bar.addWidget(self.settings_button)
        bar.addWidget(self.collapse_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack, 1)
        layout.addLayout(bar)

        self.collapsed = False
        self.set_collapsed(to_bool(settings.value(KEY_COLLAPSED, False)), save=False)

    def save(self, key, value):
        """Сохранить настройку сразу на диск — чтобы она пережила и перезапуск QGIS."""
        self.settings.setValue(key, value)
        self.settings.sync()

    def build_menu(self, idle, nap):
        menu = QMenu(self)
        idle_menu = menu.addMenu("Отдыхать после простоя")
        group = QActionGroup(self)
        for seconds in IDLE_CHOICES:
            action = idle_menu.addAction("%d с" % seconds)
            action.setCheckable(True)
            action.setChecked(seconds == idle)
            action.triggered.connect(lambda checked=False, s=seconds: self.set_idle_timeout(s))
            group.addAction(action)
        nap_action = menu.addAction("Дремать после %d мин простоя" % int(NAP_AFTER // 60))
        nap_action.setCheckable(True)
        nap_action.setChecked(nap)
        nap_action.toggled.connect(self.set_nap)
        away = menu.addAction("Иногда выходит из кабинета")
        away.setCheckable(True)
        away.setChecked(self.brain.can_leave)
        away.toggled.connect(self.set_can_leave)

        menu.addSeparator()
        boss = menu.addAction("Начальник заглядывает в кабинет")
        boss.setCheckable(True)
        boss.setChecked(self.brain.boss.enabled)
        boss.toggled.connect(lambda on: self.set_visitor(self.brain.boss, KEY_BOSS, on))
        menu.addAction("Позвать начальника").triggered.connect(
            lambda: self.brain.boss.call(time.monotonic()))
        fox = menu.addAction("Лиса-шпион за окном")
        fox.setCheckable(True)
        fox.setChecked(self.brain.fox.enabled)
        fox.toggled.connect(lambda on: self.set_visitor(self.brain.fox, KEY_FOX, on))
        menu.addAction("Позвать лису").triggered.connect(
            lambda: self.brain.fox.call(time.monotonic()))

        menu.addSeparator()
        quiz = menu.addAction("Викторина по Лесоустроительной инструкции")
        quiz.setCheckable(True)
        quiz.setChecked(self.quiz_enabled)
        quiz.toggled.connect(self.set_quiz_enabled)
        every_menu = menu.addMenu("Вопрос каждые")
        group = QActionGroup(self)
        for minutes in QUIZ_CHOICES:
            action = every_menu.addAction("%d мин" % minutes)
            action.setCheckable(True)
            action.setChecked(minutes == self.quiz_every)
            action.triggered.connect(lambda checked=False, m=minutes: self.set_quiz_every(m))
            group.addAction(action)
        self.quiz_now_action = menu.addAction("Задать вопрос сейчас")
        self.quiz_now_action.triggered.connect(self.show_quiz)
        self.score_action = menu.addAction("")
        self.score_action.setEnabled(False)
        menu.aboutToShow.connect(self.update_quiz_menu)
        return menu

    # -------------------------------------------------- события QGIS

    def key_pressed(self, combo=None):
        self.brain.key(time.monotonic(), combo)

    def mouse_used(self, wheel=False):
        self.brain.mouse(time.monotonic(), wheel)

    # -------------------------------------------------- настройки

    def on_pet_changed(self, index):
        key = self.combo.itemData(index)
        self.save(KEY_PET, key)
        self.brain.set_pet(get_pet(key), time.monotonic())
        self.view.update()

    def set_idle_timeout(self, seconds):
        self.brain.idle_timeout = float(seconds)
        self.save(KEY_IDLE, seconds)

    def set_nap(self, enabled):
        self.brain.nap_after = NAP_AFTER if enabled else None
        self.save(KEY_NAP, bool(enabled))

    def set_can_leave(self, enabled):
        self.brain.can_leave = bool(enabled)
        self.save(KEY_AWAY, bool(enabled))

    def set_visitor(self, visitor, key, enabled):
        visitor.enabled = bool(enabled)
        self.save(key, bool(enabled))

    def set_collapsed(self, collapsed, save=True):
        self.collapsed = collapsed
        self.stack.setVisible(not collapsed)
        self.collapse_button.setText("▴" if collapsed else "▾")
        self.collapse_button.setToolTip("Развернуть" if collapsed else "Свернуть")
        if save:
            self.save(KEY_COLLAPSED, collapsed)
        self.collapsedChanged.emit(collapsed)

    # -------------------------------------------------- викторина

    def set_quiz_enabled(self, enabled):
        self.quiz_enabled = bool(enabled)
        self.save(KEY_QUIZ, self.quiz_enabled)
        if not enabled and self.quiz_showing:
            self.hide_quiz()

    def set_quiz_every(self, minutes):
        self.quiz_every = int(minutes)
        self.next_quiz = time.monotonic() + minutes * 60.0
        self.save(KEY_QUIZ_EVERY, self.quiz_every)

    def score_text(self):
        return "Верно: %d из %d" % (self.quiz_right, self.quiz_total) if self.quiz_total else ""

    def update_quiz_menu(self):
        available = self.quiz.available
        self.quiz_now_action.setEnabled(available and not self.quiz_showing)
        self.quiz_now_action.setText("Задать вопрос сейчас" if available
                                     else "Задать вопрос сейчас (вопросы ещё не добавлены)")
        self.score_action.setText(self.score_text() or "Ответов пока нет")

    @property
    def quiz_showing(self):
        return self.stack.currentWidget() is self.quiz_widget

    def check_quiz(self):
        """Пора ли задать вопрос: включено, есть вопросы, окошко видно и не свёрнуто."""
        if not (self.quiz_enabled and self.quiz.available) or self.quiz_showing:
            return
        if time.monotonic() < self.next_quiz or self.collapsed or not self.isVisible():
            return
        self.show_quiz()

    def show_quiz(self):
        question = self.quiz.next()
        if question is None:
            return
        self.save(KEY_QUIZ_SEEN, format_ids(self.quiz.seen))
        self.quiz_widget.show_question(question, self.score_text())
        self.stack.setCurrentWidget(self.quiz_widget)
        if self.collapsed:
            self.set_collapsed(False)

    def on_quiz_answered(self, ok):
        self.quiz_total += 1
        self.quiz_right += 1 if ok else 0
        self.save(KEY_QUIZ_TOTAL, self.quiz_total)
        self.save(KEY_QUIZ_RIGHT, self.quiz_right)
        self.quiz_reaction = "saved" if ok else "oops"

    def hide_quiz(self):
        self.stack.setCurrentWidget(self.view)
        self.next_quiz = time.monotonic() + self.quiz_every * 60.0
        if self.quiz_reaction:
            # питомец радуется правильному ответу или хватается за голову
            self.brain.pending_reaction = self.quiz_reaction
            self.quiz_reaction = None

    def stop(self):
        self.view.timer.stop()
        self.quiz_timer.stop()
        self.quiz_widget.timer.stop()
