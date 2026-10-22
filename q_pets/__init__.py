# -*- coding: utf-8 -*-


def classFactory(iface):  # noqa: N802 - имя задаёт QGIS
    from .plugin import QPetsPlugin
    return QPetsPlugin(iface)
