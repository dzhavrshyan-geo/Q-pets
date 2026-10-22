# -*- coding: utf-8 -*-
"""Окошко питомца: сцена с анимацией и нижняя панель (выбор питомца, настройки, свернуть)."""

import time

from qgis.PyQt.QtCore import QSize, Qt, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QColor, QPainter
from qgis.PyQt.QtWidgets import (QComboBox, QHBoxLayout, QMenu, QSizePolicy, QToolButton,
                                 QVBoxLayout, QWidget)

try:
    from qgis.PyQt.QtGui import QActionGroup
except ImportError:  # Qt5
    from qgis.PyQt.QtWidgets import QActionGroup

from .brain import PetBrain
from .drawing import H, W, draw_scene
from .pets import PETS, get_pet

KEY_PET = "q_pets/pet"
KEY_IDLE = "q_pets/idle_timeout"
KEY_NAP = "q_pets/nap"
KEY_COLLAPSED = "q_pets/collapsed"
IDLE_CHOICES = (10, 15, 30, 60)
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
            draw_scene(p, pet, self.brain.pose(now), ctx)
        except Exception:
            # Ошибку покажем один раз, а не 25 раз в секунду
            self.failed = True
            self.timer.stop()
            raise
        finally:
            p.end()


class PetPanel(QWidget):
    """Содержимое панели Q-pets."""

    collapsedChanged = pyqtSignal(bool)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        pet = get_pet(settings.value(KEY_PET, PETS[0]["key"]))
        idle = int(settings.value(KEY_IDLE, 15))
        nap = to_bool(settings.value(KEY_NAP, True))
        self.brain = PetBrain(pet, idle_timeout=idle, nap_after=NAP_AFTER if nap else None,
                              now=time.monotonic())
        self.view = PetView(self.brain, self)

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
        layout.addWidget(self.view, 1)
        layout.addLayout(bar)

        self.collapsed = False
        self.set_collapsed(to_bool(settings.value(KEY_COLLAPSED, False)), save=False)

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
        return menu

    # -------------------------------------------------- события QGIS

    def key_pressed(self):
        self.brain.key(time.monotonic())

    def mouse_used(self):
        self.brain.mouse(time.monotonic())

    # -------------------------------------------------- настройки

    def on_pet_changed(self, index):
        key = self.combo.itemData(index)
        self.settings.setValue(KEY_PET, key)
        self.brain.set_pet(get_pet(key), time.monotonic())
        self.view.update()

    def set_idle_timeout(self, seconds):
        self.brain.idle_timeout = float(seconds)
        self.settings.setValue(KEY_IDLE, seconds)

    def set_nap(self, enabled):
        self.brain.nap_after = NAP_AFTER if enabled else None
        self.settings.setValue(KEY_NAP, bool(enabled))

    def set_collapsed(self, collapsed, save=True):
        self.collapsed = collapsed
        self.view.setVisible(not collapsed)
        self.collapse_button.setText("▴" if collapsed else "▾")
        self.collapse_button.setToolTip("Развернуть" if collapsed else "Свернуть")
        if save:
            self.settings.setValue(KEY_COLLAPSED, collapsed)
        self.collapsedChanged.emit(collapsed)

    def stop(self):
        self.view.timer.stop()
