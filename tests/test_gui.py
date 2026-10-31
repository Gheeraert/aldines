"""Parcours Qt hors écran ; facultatif si l’interface n’est pas installée."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QEventLoop, QTimer, QSettings, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont
from pathlib import Path

from aldines.config import load_project
from aldines.gui import Window


def wait_for_worker(window):
    loop = QEventLoop()
    if window.worker and window.worker.isRunning():
        window.worker.finished.connect(loop.quit)
        QTimer.singleShot(10000, loop.quit)
        loop.exec()
    QApplication.processEvents()
    assert not window.worker.isRunning()


def test_qt_open_select_save_preview_and_publish(project, tmp_path):
    app = QApplication.instance() or QApplication([])
    # Le plugin Qt hors écran ne charge pas toujours les polices Windows.
    # Charger celles-ci explicitement pour rendre la capture de test lisible.
    for filename in ("segoeui.ttf", "georgia.ttf"):
        font = Path("C:/Windows/Fonts") / filename
        if font.exists():
            QFontDatabase.addApplicationFont(str(font))
    app.setFont(QFont("Segoe UI", 10))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    window = Window()
    errors = []
    window.error = errors.append
    window.open_project(project.path)
    wait_for_worker(window)
    assert not errors
    assert len(window.leaves()) == 2
    window.fields[("appearance", "font_size")].setValue(22)
    window.leaves()[0].setCheckState(0, Qt.Unchecked)
    assert window.dirty
    assert window.save_project()
    saved = load_project(project.path)
    assert saved.data["sources"]["selection"] == ["t1.l01.s01"]
    assert saved.data["appearance"]["font_size"] == 22
    opened = []
    window.browse_site = lambda output, route="": opened.append((output, route))
    window.preview_unit.setCurrentIndex(1)
    window.preview()
    wait_for_worker(window)
    assert not errors and opened[0][1] == "t1/l1/s01/"
    assert (opened[0][0] / "t1/l1/s01/index.html").exists()
    window.publish()
    wait_for_worker(window)
    assert not errors
    assert (project.output / "t1/l1/s01/index.html").exists()
    assert not (project.output / "t1/l1/s02/index.html").exists()
    window.show()
    app.processEvents()
    window.grab().save(str(tmp_path / "qt-project.png"))
    window.close()
