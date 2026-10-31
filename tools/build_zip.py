# -*- coding: utf-8 -*-
"""Архив для установки в QGIS: python tools/build_zip.py  →  release/<плагин>-<версия>.zip"""

import os
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PLUGIN = "q_pets"


def version():
    with open(os.path.join(ROOT, PLUGIN, "metadata.txt"), encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("version="):
                return line.split("=", 1)[1].strip()
    return "0"


if __name__ == "__main__":
    folder = os.path.join(ROOT, "release")
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, "{}-{}.zip".format(PLUGIN, version()))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, dirs, files in os.walk(os.path.join(ROOT, PLUGIN)):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(files):
                if name.endswith(".pyc"):
                    continue
                full = os.path.join(path, name)
                archive.write(full, os.path.relpath(full, ROOT))
    print(target)
