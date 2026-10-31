# -*- coding: utf-8 -*-
"""Плагин из release/q_pets-<версия>.zip в настоящем QGIS (без окна): python -m unittest discover -s tests

Архив распаковывается в пустую папку модулей, и плагин загружается тем же путём, что и в QGIS:
qgis.utils читает metadata.txt, импортирует пакет, вызывает classFactory и initGui, потом unload.
QGIS запускается в отдельном процессе: в этом процессе другие тесты подменяют qgis на PyQt5.
Нужен PyQGIS; без него тест загрузки пропускается.
"""

import configparser
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLUGIN = "q_pets"


def source_version():
    parser = configparser.ConfigParser()
    parser.read(os.path.join(ROOT, PLUGIN, "metadata.txt"), encoding="utf-8")
    return parser["general"]["version"]


def release_zip():
    return os.path.join(ROOT, "release", "{}-{}.zip".format(PLUGIN, source_version()))


def has_pyqgis():
    probe = subprocess.run([sys.executable, "-c", "import qgis.core"], capture_output=True,
                           env=dict(os.environ, QT_QPA_PLATFORM="offscreen"))
    return probe.returncode == 0


LOAD_SCRIPT = textwrap.dedent('''
    import os, sys, tempfile, zipfile
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    plugins = tempfile.mkdtemp()
    zipfile.ZipFile(sys.argv[1]).extractall(plugins)

    from qgis.core import Qgis, QgsApplication
    app = QgsApplication([], True, tempfile.mkdtemp())
    app.initQgis()
    from qgis.PyQt.QtCore import QObject, pyqtSignal
    from qgis.PyQt.QtWidgets import QMainWindow
    from qgis.gui import QgsMapCanvas
    import qgis.utils

    class Iface(QObject):
        initializationCompleted = pyqtSignal()

        def __init__(self):
            super().__init__()
            self.window = QMainWindow()
            self.canvas = QgsMapCanvas(self.window)
            self.window.setCentralWidget(self.canvas)
            self.window.resize(1000, 700)
            self.toolbar, self.menu = [], []

        def mainWindow(self):
            return self.window

        def mapCanvas(self):
            return self.canvas

        def addToolBarIcon(self, action):
            self.toolbar.append(action)

        def removeToolBarIcon(self, action):
            self.toolbar.remove(action)

        def addPluginToMenu(self, menu, action):
            self.menu.append(action)

        def removePluginMenu(self, menu, action):
            self.menu.remove(action)

    iface = Iface()
    qgis.utils.iface = iface
    qgis.utils.plugin_paths = [plugins]
    sys.path.insert(0, plugins)
    qgis.utils.updateAvailablePlugins()
    assert "q_pets" in qgis.utils.available_plugins, qgis.utils.available_plugins
    meta = {key: qgis.utils.pluginMetadata("q_pets", key)
            for key in ("name", "version", "license", "changelog", "qgisMinimumVersion")}
    assert qgis.utils.loadPlugin("q_pets")
    assert qgis.utils.startPlugin("q_pets")
    plugin = qgis.utils.plugins["q_pets"]
    assert plugin.panel.__module__.startswith("q_pets"), "загружен не плагин из архива"
    assert os.path.dirname(sys.modules["q_pets"].__file__).startswith(plugins)

    iface.window.show()
    iface.initializationCompleted.emit()
    app.processEvents()
    assert plugin.dock.isVisible(), "окошко не открылось"
    assert len(iface.toolbar) == 1 and len(iface.menu) == 1
    view = plugin.panel.view
    view.resize(340, 260)
    view.tick()
    assert not view.grab().isNull()
    assert len(plugin.panel.quiz.questions) == 100
    plugin.panel.show_quiz()
    assert plugin.panel.quiz_showing
    plugin.panel.hide_quiz()
    assert qgis.utils.unloadPlugin("q_pets")
    assert iface.toolbar == [] and iface.menu == []
    print("QGIS", Qgis.QGIS_VERSION)
    for key, value in meta.items():
        print("%s=%s" % (key, value.splitlines()[0] if value else value))
    app.exitQgis()
''')


class ReleaseZipTest(unittest.TestCase):

    def test_zip_matches_plugin_folder(self):
        """В архиве — папка q_pets с теми же файлами, что в репозитории, без мусора."""
        path = release_zip()
        self.assertTrue(os.path.isfile(path), "нет %s — соберите: python tools/build_zip.py" % path)
        names = sorted(zipfile.ZipFile(path).namelist())
        expected = []
        for folder, dirs, files in os.walk(os.path.join(ROOT, PLUGIN)):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                if not name.endswith(".pyc"):
                    full = os.path.join(folder, name)
                    expected.append(os.path.relpath(full, ROOT).replace(os.sep, "/"))
        self.assertEqual(names, sorted(expected))
        self.assertFalse([n for n in names if "__pycache__" in n or n.endswith(".pyc")])
        with zipfile.ZipFile(path) as archive:
            meta = archive.read(PLUGIN + "/metadata.txt").decode("utf-8")
        with open(os.path.join(ROOT, PLUGIN, "metadata.txt"), encoding="utf-8") as handle:
            self.assertEqual(meta, handle.read(), "архив собран из старой версии — пересоберите")

    def test_metadata_for_plugin_manager(self):
        parser = configparser.ConfigParser()
        parser.read(os.path.join(ROOT, PLUGIN, "metadata.txt"), encoding="utf-8")
        general = parser["general"]
        self.assertEqual(general["license"], "GPL-2.0-or-later")
        changelog = general["changelog"].splitlines()
        self.assertTrue(changelog[0].startswith(general["version"] + ":"))
        self.assertTrue(changelog[-1].startswith("0.1.0:"))
        with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as handle:
            headings = [line[3:].strip() for line in handle if line.startswith("## ")]
        self.assertEqual([line.split(":")[0].strip() for line in changelog], headings)


@unittest.skipUnless(has_pyqgis(), "нужен PyQGIS")
class LoadInQgisTest(unittest.TestCase):

    def test_plugin_loads_from_zip(self):
        with tempfile.TemporaryDirectory() as folder:
            script = os.path.join(folder, "load.py")
            with open(script, "w", encoding="utf-8") as handle:
                handle.write(LOAD_SCRIPT)
            run = subprocess.run([sys.executable, script, release_zip()], capture_output=True,
                                 text=True, timeout=300, cwd=folder,
                                 env=dict(os.environ, QT_QPA_PLATFORM="offscreen"))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("version=" + source_version(), run.stdout)
        self.assertIn("license=GPL-2.0-or-later", run.stdout)
        print("\n" + run.stdout.strip())


if __name__ == "__main__":
    unittest.main()
