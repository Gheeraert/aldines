"""Parcours Qt hors écran ; facultatif si l’interface n’est pas installée."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QEventLoop, QTimer, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton
from PySide6.QtGui import QFontDatabase, QFont
from pathlib import Path

from aldines.config import load_project
from aldines.__main__ import main
from aldines.gui import Window


def wait_for_worker(window):
    loop = QEventLoop()
    if window.worker and window.worker.isRunning():
        window.worker.finished.connect(loop.quit)
        QTimer.singleShot(10000, loop.quit)
        loop.exec()
    QApplication.processEvents()
    assert not window.worker.isRunning()


def test_gui_loads_a_project_only_when_requested(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "aldines.json"
    project.touch()
    launched = []
    monkeypatch.setattr("aldines.gui.run", launched.append)
    main(["gui"])
    main(["gui", str(project)])
    assert launched == [None, str(project)]


def test_qt_open_select_save_preview_and_publish(project, tmp_path, monkeypatch):
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
    assert window.project is window.corpus is window.worker is None
    assert not window.save_button.isEnabled()
    assert not window.credits_controls.isEnabled()
    assert window.navigation.item(3).text() == "04   Ressources"
    assert window.stack.widget(3) is window.resources_page
    assert window.stack.widget(0).isAncestorOf(window.credits_file)
    window.show()
    errors = []
    window.error = errors.append
    window.open_project(project.path)
    wait_for_worker(window)
    assert not errors
    assert window.save_button.isEnabled()
    assert len(window.leaves()) == 2
    window.fields[("appearance", "font_size")].setValue(22)
    window.fields[("appearance", "text_align")].setCurrentIndex(1)
    window.leaves()[0].setCheckState(0, Qt.Unchecked)
    assert window.dirty
    QTest.mouseClick(window.save_button, Qt.LeftButton)
    assert window.save_feedback.text() == "Projet enregistré."
    assert not window.dirty
    saved = load_project(project.path)
    assert saved.data["sources"]["selection"] == ["t1.l01.s01"]
    assert saved.data["appearance"]["font_size"] == 22
    assert saved.data["appearance"]["text_align"] == "justify"
    window.fields[("appearance", "font_size")].setValue(23)
    assert not window.save_feedback.text()
    window.fields[("appearance", "font_size")].setValue(22)
    assert window.save_project()
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
    files = [str(tmp_path / name) for name in ("un.md", "deux.md")]
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: (files, ""))
    window.add_resources()
    window.add_resources()
    assert window.resource_files.count() == 2
    window.resource_files.item(0).setSelected(True)
    window.remove_resources()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(tmp_path / "projet.md"), ""))
    choose = next(button for button in window.credits_controls.findChildren(QPushButton)
                  if button.text() == "Choisir le Markdown…")
    QTest.mouseClick(choose, Qt.LeftButton)
    assert window.dirty and window.save_project()
    assert load_project(project.path).data["editorial"] == {"resources": ["deux.md"], "credits": "projet.md"}
    window.show()
    app.processEvents()
    window.grab().save(str(tmp_path / "qt-project.png"))
    window.close()
