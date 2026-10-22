# -*- coding: utf-8 -*-
"""Подмена модуля qgis.PyQt на PyQt5, чтобы рисовать и тестировать без QGIS."""

import sys
import types

from PyQt5 import QtCore, QtGui, QtWidgets

qgis = types.ModuleType("qgis")
qgis_pyqt = types.ModuleType("qgis.PyQt")
qgis.PyQt = qgis_pyqt
sys.modules.setdefault("qgis", qgis)
sys.modules.setdefault("qgis.PyQt", qgis_pyqt)
for name, module in (("QtCore", QtCore), ("QtGui", QtGui), ("QtWidgets", QtWidgets)):
    setattr(qgis_pyqt, name, module)
    sys.modules.setdefault("qgis.PyQt." + name, module)
