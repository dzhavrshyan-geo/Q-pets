# -*- coding: utf-8 -*-
"""Плагин и рисование без QGIS: qgis.PyQt подменяется на PyQt5, qgis.core и iface — заглушки.

Запуск:  python -m unittest discover tests   (нужен PyQt5: pip install PyQt5)
"""

import os
import sys
import tempfile
import time
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    import qgis_shim  # noqa: F401
    from PyQt5.QtCore import QEvent, QObject, QPoint, QPointF, QSettings, Qt, pyqtSignal
    from PyQt5.QtGui import QImage, QKeyEvent, QPainter, QWheelEvent
    from PyQt5.QtWidgets import QApplication, QLineEdit, QMainWindow
except ImportError:  # pragma: no cover
    QApplication = None

SETTINGS_FILE = os.path.join(tempfile.mkdtemp(), "settings.ini")

if QApplication is not None:
    class FakeTaskManager:
        active = 0

        def countActiveTasks(self):  # noqa: N802
            return self.active

    class QgsApplication:
        task_manager = FakeTaskManager()

        @staticmethod
        def instance():
            return QApplication.instance()

        @staticmethod
        def taskManager():  # noqa: N802
            return QgsApplication.task_manager

    class QgsSettings(QSettings):
        def __init__(self):
            super().__init__(SETTINGS_FILE, QSettings.Format.IniFormat)

    core = types.ModuleType("qgis.core")
    core.QgsApplication = QgsApplication
    core.QgsSettings = QgsSettings
    sys.modules["qgis.core"] = core

    class FakeCanvas:
        drawing = False

        def isDrawing(self):  # noqa: N802
            return self.drawing

    class FakeIface(QObject):
        initializationCompleted = pyqtSignal()

        def __init__(self):
            super().__init__()
            self.window = QMainWindow()
            self.window.resize(1200, 800)
            self.editor = QLineEdit(self.window)
            self.window.setCentralWidget(self.editor)
            self.canvas = FakeCanvas()
            self.toolbar, self.menu = [], []

        def mainWindow(self):  # noqa: N802
            return self.window

        def mapCanvas(self):  # noqa: N802
            return self.canvas

        def addToolBarIcon(self, action):  # noqa: N802
            self.toolbar.append(action)

        def removeToolBarIcon(self, action):  # noqa: N802
            self.toolbar.remove(action)

        def addPluginToMenu(self, menu, action):  # noqa: N802
            self.menu.append((menu, action))

        def removePluginMenu(self, menu, action):  # noqa: N802
            self.menu.remove((menu, action))


@unittest.skipIf(QApplication is None, "нужен PyQt5")
class DrawingTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_every_activity_draws(self):
        from q_pets.animation import ACTIVITIES, Animator
        from q_pets.drawing import draw_scene
        from q_pets.pets import PETS
        img = QImage(320, 240, QImage.Format.Format_ARGB32)
        for pet in PETS:
            for name, activity in ACTIVITIES.items():
                anim = Animator(pet)
                anim.play(name, 0.0)
                for t in (0.0, 0.2, 1.5, 4.0, 8.0, 12.0):
                    for hour in (3, 7, 12):
                        p = QPainter(img)
                        draw_scene(p, pet, anim.pose(t),
                                   {"t": t, "screen": activity.screen, "hour": hour})
                        p.end()


    def test_arms_move_smoothly(self):
        """Локти и кисти не перескакивают: ни внутри анимаций, ни при прерывании их работой."""
        import math
        import random
        from q_pets.animation import ACTIVITIES, Animator
        from q_pets.drawing import arm_curve
        from q_pets.pets import PETS

        def joints(pose):
            points = []
            for left in (True, False):
                s, c, h = arm_curve(pose, left)
                points += [((c[0] + (s[0] + h[0]) / 2) / 2, (c[1] + (s[1] + h[1]) / 2) / 2), h]
            return points

        def worst_step(poses):
            frames = [joints(p) for p in poses]
            return max(math.hypot(a[0] - b[0], a[1] - b[1])
                       for f0, f1 in zip(frames, frames[1:]) for a, b in zip(f0, f1))

        dt = 1 / 25.0
        rnd = random.Random(3)
        pet = PETS[0]
        for name, activity in ACTIVITIES.items():
            duration = activity.duration or 12.0
            anim = Animator(pet)
            anim.play(name, 0.0)
            poses = [anim.pose(i * dt) for i in range(int(duration / dt) + 1)]
            self.assertLess(worst_step(poses), 25.0, name)
            for target in ("typing", "mouse"):
                cut = rnd.uniform(0.3, duration)
                anim = Animator(pet)
                anim.play(name, 0.0)
                poses = [anim.pose(cut - dt)]
                anim.play(target, cut)
                poses += [anim.pose(cut + i * dt) for i in range(30)]
                self.assertLess(worst_step(poses), 25.0, (name, target, cut))


@unittest.skipIf(QApplication is None, "нужен PyQt5")
class PluginTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        QSettings(SETTINGS_FILE, QSettings.Format.IniFormat).clear()
        from q_pets import classFactory
        self.iface = FakeIface()
        self.plugin = classFactory(self.iface)
        self.plugin.initGui()

    def tearDown(self):
        if self.plugin.dock is not None:
            self.plugin.unload()
        self.iface.window.close()
        self.app.processEvents()

    def start_qgis(self):
        self.iface.window.show()
        self.iface.initializationCompleted.emit()
        self.app.processEvents()

    def test_shows_in_corner_after_start(self):
        dock = self.plugin.dock
        self.assertFalse(dock.isVisible())  # главное окно ещё не показано
        self.start_qgis()
        self.assertTrue(dock.isVisible())
        self.assertTrue(dock.isFloating())
        win, geo = self.iface.window.geometry(), dock.geometry()
        self.assertGreater(geo.x(), win.x() + win.width() / 2)
        self.assertGreater(geo.y(), win.y() + win.height() / 2)
        self.assertEqual(len(self.iface.toolbar), 1)
        self.assertTrue(self.iface.toolbar[0].isChecked())

    def test_second_start_keeps_user_place(self):
        self.start_qgis()
        self.plugin.unload()
        self.plugin = type(self.plugin)(self.iface)
        self.plugin.initGui()
        self.plugin.dock.setFloating(False)
        self.plugin.shown = False
        self.plugin.show_pet()
        self.assertTrue(self.plugin.dock.isVisible())
        self.assertFalse(self.plugin.dock.isFloating())  # не переносим в угол снова

    def test_counts_keys_and_mouse_outside_pet(self):
        self.start_qgis()
        brain = self.plugin.panel.brain
        before = time.monotonic()
        QApplication.sendEvent(self.iface.editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A,
                                                            Qt.KeyboardModifier.NoModifier, "a"))
        self.assertGreaterEqual(brain.last_key, before)
        self.assertEqual(brain.update(time.monotonic()), "typing")
        # нажатия внутри окошка питомца — не работа
        brain.last_key = -1e9
        QApplication.sendEvent(self.plugin.panel.combo, QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "a"))
        self.assertEqual(brain.last_key, -1e9)

    def test_wheel_and_shortcuts(self):
        self.start_qgis()
        brain = self.plugin.panel.brain
        editor = self.iface.editor
        wheel = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, 120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(editor, wheel)
        self.assertEqual(brain.update(time.monotonic()), "scroll")
        ctrl = Qt.KeyboardModifier.ControlModifier
        # Ctrl+S приходит и как ShortcutOverride, и как KeyPress — реакция одна
        for etype in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
            QApplication.sendEvent(editor, QKeyEvent(etype, Qt.Key.Key_S, ctrl, ""))
        self.assertEqual(brain.pending_reaction, "saved")
        self.assertEqual(brain.update(time.monotonic()), "saved")
        QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_S, ctrl, ""))
        self.assertIsNone(brain.pending_reaction)
        QApplication.sendEvent(editor, QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Z, ctrl | Qt.KeyboardModifier.ShiftModifier, ""))
        self.assertIsNone(brain.pending_reaction)  # Ctrl+Shift+Z — это «вернуть»
        QApplication.sendEvent(editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Z, ctrl, ""))
        self.assertEqual(brain.pending_reaction, "oops")

    def test_busy_qgis(self):
        self.start_qgis()
        view = self.plugin.panel.view
        self.iface.canvas.drawing = True
        view.tick()
        view.brain.busy_since -= 1.0
        view.tick()
        self.assertEqual(view.brain.animator.name, "thinking")
        self.iface.canvas.drawing = False
        QgsApplication.task_manager.active = 1
        view.tick()
        self.assertEqual(view.brain.animator.name, "thinking")
        QgsApplication.task_manager.active = 0
        view.tick()
        self.assertEqual(view.brain.animator.name, "read")

    def test_paints_and_pokes(self):
        self.start_qgis()
        view = self.plugin.panel.view
        view.resize(500, 200)
        self.assertFalse(view.grab().isNull())
        view.resize(200, 400)
        self.assertFalse(view.grab().isNull())
        view.brain.poke(time.monotonic())
        view.tick()
        self.assertEqual(view.brain.animator.name, "wave")

    def test_collapse_keeps_bottom_edge(self):
        self.start_qgis()
        dock, panel = self.plugin.dock, self.plugin.panel
        bottom = dock.geometry().bottom()
        tall = dock.height()
        panel.set_collapsed(True)
        self.assertFalse(panel.view.isVisible())
        self.assertLess(dock.height(), tall)
        self.assertEqual(dock.geometry().bottom(), bottom)
        panel.set_collapsed(False)
        self.assertEqual(dock.height(), tall)
        self.assertTrue(panel.view.isVisible())

    def test_settings_are_saved(self):
        panel = self.plugin.panel
        panel.combo.setCurrentIndex(2)
        panel.set_idle_timeout(30)
        panel.set_nap(False)
        self.assertEqual(panel.brain.pet["key"], "chimp")
        settings = QgsSettings()
        self.assertEqual(settings.value("q_pets/pet"), "chimp")
        self.assertEqual(int(settings.value("q_pets/idle_timeout")), 30)
        self.plugin.unload()
        self.plugin = type(self.plugin)(self.iface)
        self.plugin.initGui()
        brain = self.plugin.panel.brain
        self.assertEqual(brain.pet["key"], "chimp")
        self.assertEqual(brain.idle_timeout, 30)
        self.assertIsNone(brain.nap_after)

    def test_unload_cleans_up(self):
        self.start_qgis()
        watcher = self.plugin.watcher
        self.plugin.unload()
        self.assertEqual(self.iface.toolbar, [])
        self.assertEqual(self.iface.menu, [])
        self.assertIsNone(self.plugin.dock)
        # фильтр снят: события больше не доходят до питомца
        calls = []
        watcher.panel = types.SimpleNamespace(key_pressed=lambda: calls.append(1))
        QApplication.sendEvent(self.iface.editor, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A,
                                                            Qt.KeyboardModifier.NoModifier, "a"))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
