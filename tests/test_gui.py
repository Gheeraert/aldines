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
from lxml import html

from aldines.config import load_project
from aldines.__main__ import main
from aldines.gui import Window
from conftest import tei


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


def test_gui_lists_tome_three_preface(project):
    app = QApplication.instance() or QApplication([])
    path = project.directory / "aug-t3-gc-l01-c00.xml"
    path.write_text(tei().replace("t1.l01.s01", "t3.gc.l01.c00"), encoding="utf-8")
    project.data["sources"]["master"] = f"tei/{path.name}"
    project.save()
    window = Window()
    window.open_project(project.path)
    wait_for_worker(window)
    leaf, = window.leaves()
    assert leaf.parent().text(0) == "Tome 3 · De la grâce du Christ Sauveur, livre I"
    assert leaf.text(0) == f"Préface — {path.name}"
    assert leaf.data(0, Qt.UserRole) == "t3.l01.c00"
    assert window.preview_unit.itemText(0).endswith(" · Préface")
    window.close()


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
    assert not window.home_controls.isEnabled()
    assert window.busy_indicator.isHidden()
    assert window.navigation.item(3).text() == "04   Ressources"
    assert window.stack.widget(3) is window.resources_page
    assert window.stack.widget(0).isAncestorOf(window.credits_file)
    window.show()
    errors = []
    window.error = errors.append
    window.open_project(project.path)
    assert not window.busy_indicator.isHidden()
    assert window.statusBar().currentMessage() == "Chargement du corpus…"
    wait_for_worker(window)
    assert window.busy_indicator.isHidden()
    assert not errors
    assert window.save_button.isEnabled()
    assert window.home_controls.isEnabled()
    assert len(window.leaves()) == 2
    author_field = window.fields[("corpus", "author")]
    title_field = window.fields[("corpus", "title")]
    assert author_field.geometry().top() < title_field.geometry().top() < window.home_controls.geometry().top()
    author_field.setText("Cornelius Jansenius")
    title_field.setText("Augustinus")
    window.fields[("appearance", "font_size")].setValue(22)
    window.fields[("appearance", "text_align")].setCurrentIndex(1)
    window.fields[("publication", "origin")].setText("https://example.org")
    scan_url = "https://example.org/edition.pdf?id=1641&view=full#page=12"
    scan_field = window.fields[("corpus", "source_edition_url")]
    scan_field.setText(scan_url)
    home_texts = {"home_intro": "Introduction personnalisée", "home_edition": "Une autre description",
                  "home_resources": ""}
    for key, text in home_texts.items():
        window.fields[("editorial", key)].setPlainText(text)
    window.leaves()[0].setCheckState(0, Qt.Unchecked)
    assert window.dirty
    QTest.mouseClick(window.save_button, Qt.LeftButton)
    assert window.save_feedback.text() == "Projet enregistré."
    assert not window.dirty
    saved = load_project(project.path)
    assert saved.data["corpus"]["author"] == "Cornelius Jansenius"
    assert saved.data["corpus"]["title"] == "Augustinus"
    assert saved.data["sources"]["selection"] == ["t1.l01.s01"]
    assert saved.data["appearance"]["font_size"] == 22
    assert saved.data["appearance"]["text_align"] == "justify"
    assert saved.data["publication"]["origin"] == "https://example.org"
    assert saved.data["corpus"]["source_edition_url"] == scan_url
    assert {key: saved.data["editorial"][key] for key in home_texts} == home_texts
    window.fields[("appearance", "font_size")].setValue(23)
    assert not window.save_feedback.text()
    window.fields[("appearance", "font_size")].setValue(22)
    assert window.save_project()
    opened = []
    window.browse_site = lambda output, route="": opened.append((output, route))
    window.preview_unit.setCurrentIndex(1)
    window.preview()
    assert not window.busy_indicator.isHidden()
    wait_for_worker(window)
    assert window.busy_indicator.isHidden()
    assert not errors and opened[0][1] == "t1/l1/s01/"
    assert (opened[0][0] / "t1/l1/s01/index.html").exists()
    window.publish()
    assert not window.busy_indicator.isHidden()
    wait_for_worker(window)
    assert window.busy_indicator.isHidden()
    assert not errors
    assert (project.output / "t1/l1/s01/index.html").exists()
    assert not (project.output / "t1/l1/s02/index.html").exists()
    contents = html.parse(str(project.output / "contents/index.html"))
    assert contents.xpath('//form[@id="corpus-navigator"]/following-sibling::*[1]/a'
                          '[text()="Consulter l’édition numérisée"]/@href') == [scan_url]
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
    editorial = load_project(project.path).data["editorial"]
    assert editorial["resources"] == ["deux.md"] and editorial["credits"] == "projet.md"
    image = tmp_path / "accueil.webp"
    image.write_bytes((project.output / "assets/frontispice-1641.webp").read_bytes())
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(image), ""))
    choose_image = next(button for button in window.home_controls.findChildren(QPushButton)
                        if button.text() == "Choisir une image…")
    QTest.mouseClick(choose_image, Qt.LeftButton)
    assert not window.home_caption.toPlainText() and not window.home_alt.text()
    window.home_caption.setPlainText("Légende choisie")
    window.home_alt.setText("Description de l’image")
    assert window.dirty and window.save_project()
    window.open_project(project.path)
    wait_for_worker(window)
    assert window.home_image.text() == image.name
    assert window.home_caption.toPlainText() == "Légende choisie"
    assert window.home_alt.text() == "Description de l’image"
    assert scan_field.text() == scan_url
    for key, text in home_texts.items():
        assert window.fields[("editorial", key)].toPlainText() == text
    window.show()
    app.processEvents()
    window.grab().save(str(tmp_path / "qt-project.png"))
    window.close()
