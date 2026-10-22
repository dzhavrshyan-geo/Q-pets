# -*- coding: utf-8 -*-
"""Плагин Q-pets: панель с питомцем, который работает вместе с вами в QGIS."""

import os
import time

from qgis.core import QgsApplication, QgsSettings
from qgis.PyQt.QtCore import QEvent, QObject, Qt, QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDockWidget, QWidget

from .pet_widget import PetPanel

MENU = "Q-pets"
KEY_PLACED = "q_pets/placed"
KEY_HEIGHT = "q_pets/expanded_height"
DEFAULT_SIZE = (340, 290)


class ActivityWatcher(QObject):
    """Ловит нажатия клавиш и мыши во всех окнах QGIS (кроме самого питомца)."""

    # Сочетания вроде Ctrl+S до виджета доходят только как ShortcutOverride
    KEY_EVENTS = (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride)
    MOUSE_EVENTS = (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick)
    WHEEL_EVENT = QEvent.Type.Wheel
    MOVE_EVENT = QEvent.Type.MouseMove

    def __init__(self, panel, dock):
        super().__init__()
        self.panel = panel
        self.dock = dock
        self.last_move = 0.0
        self.last_combo = (None, 0.0)

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype in self.KEY_EVENTS:
            kind = "key"
        elif etype in self.MOUSE_EVENTS:
            kind = "mouse"
        elif etype == self.WHEEL_EVENT:
            kind = "wheel"
        elif etype == self.MOVE_EVENT:
            now = time.monotonic()
            if now - self.last_move < 0.15:
                return False
            self.last_move = now
            kind = "mouse"
        else:
            return False
        # Событие приходит и окну, и виджету — считаем только виджеты
        if not isinstance(obj, QWidget) or obj is self.dock or self.dock.isAncestorOf(obj):
            return False
        if kind == "key":
            self.panel.key_pressed(self.combo(event))
        else:
            self.panel.mouse_used(wheel=kind == "wheel")
        return False

    def combo(self, event):
        """Ctrl+S — «save», Ctrl+Z — «undo» (одно нажатие приходит дважды — считаем раз)."""
        modifiers = event.modifiers()
        if not modifiers & Qt.KeyboardModifier.ControlModifier:
            return None
        key = event.key()
        if key == Qt.Key.Key_S:
            name = "save"
        elif key == Qt.Key.Key_Z and not modifiers & Qt.KeyboardModifier.ShiftModifier:
            name = "undo"
        else:
            return None
        now = time.monotonic()
        previous, when = self.last_combo
        self.last_combo = (name, now)
        if previous == name and now - when < 0.4:
            return None
        return name


class QPetsPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.dock = None
        self.panel = None
        self.watcher = None
        self.restored = False
        self.shown = False

    def initGui(self):
        main_window = self.iface.mainWindow()
        self.panel = PetPanel(QgsSettings())
        self.panel.view.busy_probe = self.qgis_busy
        self.panel.collapsedChanged.connect(self.on_collapsed)

        self.dock = QDockWidget("Q-pets", main_window)
        self.dock.setObjectName("QPetsDock")
        self.dock.setWidget(self.panel)
        # Место и размер панели QGIS запоминает сам; если панель создана после
        # восстановления окна, достаём её прошлое положение вручную
        self.restored = main_window.restoreDockWidget(self.dock)
        if not self.restored:
            main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()

        action = self.dock.toggleViewAction()
        action.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "icon.png")))
        action.setText("Q-pets: показать питомца")
        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(MENU, action)

        self.watcher = ActivityWatcher(self.panel, self.dock)
        QgsApplication.instance().installEventFilter(self.watcher)

        # При запуске QGIS показываем, когда главное окно уже на экране,
        # при включении в менеджере модулей — сразу
        self.iface.initializationCompleted.connect(self.show_pet)
        QTimer.singleShot(0, self.show_pet)

    def unload(self):
        if self.watcher is not None:
            QgsApplication.instance().removeEventFilter(self.watcher)
            self.watcher = None
        try:
            self.iface.initializationCompleted.disconnect(self.show_pet)
        except (TypeError, RuntimeError):
            pass
        if self.dock is not None:
            action = self.dock.toggleViewAction()
            self.iface.removeToolBarIcon(action)
            self.iface.removePluginMenu(MENU, action)
            self.panel.stop()
            self.iface.mainWindow().removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
            self.panel = None

    # -------------------------------------------------- окно

    def show_pet(self):
        if self.dock is None or self.shown or not self.iface.mainWindow().isVisible():
            return
        self.shown = True
        settings = QgsSettings()
        if not self.restored and not settings.value(KEY_PLACED, False, type=bool):
            self.place_in_corner()
            settings.setValue(KEY_PLACED, True)
        self.dock.show()
        self.dock.raise_()
        if self.panel.collapsed:
            self.on_collapsed(True)

    def place_in_corner(self):
        """Первый запуск: маленькое окошко в правом нижнем углу QGIS."""
        geo = self.iface.mainWindow().geometry()
        width, height = DEFAULT_SIZE
        self.dock.setFloating(True)
        self.dock.resize(width, height)
        self.dock.move(geo.x() + geo.width() - width - 24, geo.y() + geo.height() - height - 48)

    def on_collapsed(self, collapsed):
        """Свёрнутое плавающее окошко уменьшается до нижней панели, нижний край остаётся на месте."""
        if self.dock is None or not self.dock.isFloating():
            return
        settings = QgsSettings()
        geo = self.dock.geometry()
        if collapsed:
            if geo.height() > 160:
                settings.setValue(KEY_HEIGHT, geo.height())
            height = self.dock.minimumSizeHint().height()
        else:
            height = max(int(settings.value(KEY_HEIGHT, DEFAULT_SIZE[1])), 160)
        self.dock.setGeometry(geo.x(), geo.y() + geo.height() - height, geo.width(), height)

    # -------------------------------------------------- QGIS занят

    def qgis_busy(self):
        canvas = self.iface.mapCanvas()
        if canvas is not None and canvas.isDrawing():
            return True
        return QgsApplication.taskManager().countActiveTasks() > 0
