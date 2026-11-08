"""Interface Qt légère ; lecture et génération exécutées dans un QThread."""
from copy import deepcopy
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QThread, Signal, QSettings, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFormLayout, QStackedWidget, QListWidget, QLabel, QPushButton, QLineEdit,
    QPlainTextEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QFileDialog,
    QMessageBox, QTreeWidget, QTreeWidgetItem, QScrollArea, QProgressBar, QGroupBox)

from .augustinus import read_corpus
from .build import build
from .config import DEFAULTS, IMAGE_SUFFIXES, Project, ProjectError, load_project, validate
from .preview import start_preview


class Worker(QThread):
    progress = Signal(str)
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action

    def run(self):
        try:
            self.result.emit(self.action(self.progress.emit))
        except Exception as exc:
            self.failed.emit(str(exc))


class Window(QMainWindow):
    def __init__(self, project_path=None):
        super().__init__()
        self.project = None
        self.corpus = None
        self.worker = None
        self.servers = []
        self.dirty = False
        self.loading = False
        self.settings = QSettings("CEREdI", "Studio Aldines")
        self.fields = {}
        self.setWindowTitle("Studio Aldines")
        self.resize(1180, 820)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(24, 30, 20, 24)
        brand = QLabel("A  /  ALDINES")
        brand.setObjectName("brand")
        side.addWidget(brand)
        caption = QLabel("ATELIER DE PUBLICATION\nAugustinus · CEREdI")
        caption.setObjectName("side-caption")
        side.addWidget(caption)
        self.navigation = QListWidget()
        self.navigation.addItems(["01   Projet", "02   Corpus", "03   Présentation", "04   Ressources",
                                  "05   Prévisualisation", "06   Publication"])
        self.navigation.setObjectName("navigation")
        side.addWidget(self.navigation)
        side.addWidget(QLabel("Studio Aldines  0.1\nÉdition numérique savante"))
        layout.addWidget(sidebar)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.make_project()
        self.make_corpus()
        self.make_appearance()
        self.make_resources()
        self.make_preview()
        self.make_publication()
        self.navigation.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.navigation.setCurrentRow(0)
        self.busy_indicator = QProgressBar()
        self.busy_indicator.setRange(0, 0)
        self.busy_indicator.setTextVisible(False)
        self.busy_indicator.setAccessibleName("Opération en cours")
        self.busy_indicator.setFixedSize(100, 12)
        self.statusBar().addPermanentWidget(self.busy_indicator)
        self.busy_indicator.hide()
        self.statusBar().showMessage("Ouvrez un projet pour commencer.")
        self.setStyleSheet('''
QMainWindow,QWidget{background:#f7f6f0;color:#29352d;font-size:13px}
QWidget#sidebar,QWidget#sidebar QLabel{background:#243c32;color:#d8e0d6}
QLabel#brand{font:23px Georgia;color:#f1ead5;padding-bottom:14px}
QLabel#side-caption{font-size:10px;line-height:1.8;padding-bottom:30px;color:#adbdb1}
QListWidget#navigation{background:#243c32;border:0;color:#d8e0d6;outline:0}
QListWidget#navigation::item{padding:15px 8px;border-radius:4px}
QListWidget#navigation::item:selected{background:#3d5748;color:white}
QLabel#page-title{font:32px Georgia;margin-bottom:8px}
QLabel#intro{color:#69756a;margin-bottom:20px}
QPushButton{background:#fdfcf7;border:1px solid #cbd1c4;border-radius:4px;padding:9px 15px}
QPushButton:hover{border-color:#6b3029;background:#efece1}
QPushButton:disabled{color:#92988e}
QPushButton#primary{background:#304f3c;color:#fffdf4;border:1px solid #304f3c;padding:11px 19px}
QPushButton#primary:hover{background:#3d6049}
QPushButton#primary:focus{border-color:#b2cbb8}
QPushButton#primary:pressed{background:#c9d9cc;color:#20372a;border-color:#304f3c}
QPushButton#primary:disabled{background:#e2e6dd;color:#657267;border-color:#cbd1c4}
QLabel#save-feedback{color:#304f3c;font-weight:bold}
QLineEdit,QPlainTextEdit,QComboBox,QSpinBox,QDoubleSpinBox{background:#fffef9;border:1px solid #cbd1c4;border-radius:3px;padding:6px;selection-background-color:#d8e2d2}
QTreeWidget{background:#fffef9;alternate-background-color:#efefe5;border:1px solid #d4d9cd}
QHeaderView::section{background:#e8ecdf;border:0;padding:9px;color:#3e5142}
QScrollArea{border:0}QCheckBox{padding:6px 0}QStatusBar{background:#e8ecdf}
''')
        if project_path:
            self.open_project(project_path)

    def space(self, title, intro):
        widget = QWidget()
        v = QVBoxLayout(widget)
        v.setContentsMargins(34, 30, 34, 24)
        heading = QLabel(title)
        heading.setObjectName("page-title")
        v.addWidget(heading)
        sub = QLabel(intro)
        sub.setWordWrap(True)
        sub.setObjectName("intro")
        v.addWidget(sub)
        self.stack.addWidget(widget)
        return v

    def button(self, text, slot, primary=False):
        b = QPushButton(text)
        b.clicked.connect(slot)
        if primary:
            b.setObjectName("primary")
        return b

    def track(self, widget):
        if isinstance(widget, QPlainTextEdit):
            widget.textChanged.connect(self.changed)
        elif isinstance(widget, QLineEdit):
            widget.textChanged.connect(self.changed)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self.changed)
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(self.changed)
        else:
            widget.valueChanged.connect(self.changed)
        return widget

    def field(self, group, key, widget):
        self.fields[(group, key)] = self.track(widget)
        return widget

    def changed(self, *_):
        if not self.loading and self.project:
            self.dirty = True
            if self.save_feedback.text():
                self.save_feedback.clear()
                self.statusBar().clearMessage()
            self.setWindowTitle(f"Studio Aldines — {self.project.path.name} *")

    def make_project(self):
        v = self.space("Votre projet éditorial", "Sources, métadonnées scientifiques et réglages de publication sont conservés séparément.")
        actions = QHBoxLayout()
        actions.addWidget(self.button("Ouvrir un projet…", self.choose_project))
        actions.addWidget(self.button("Créer depuis un dossier TEI…", self.create_project))
        self.save_button = self.button("Enregistrer", self.save_project, True)
        self.save_button.setEnabled(False)
        actions.addWidget(self.save_button)
        self.save_feedback = QLabel()
        self.save_feedback.setObjectName("save-feedback")
        self.save_feedback.setWordWrap(True)
        actions.addWidget(self.save_feedback, 1)
        v.addLayout(actions)
        self.recent = QComboBox()
        self.refresh_recent()
        recent_row = QHBoxLayout()
        recent_row.addWidget(QLabel("Projets récents"))
        recent_row.addWidget(self.recent, 1)
        recent_row.addWidget(self.button("Ouvrir", self.open_recent))
        v.addLayout(recent_row)
        self.project_label = QLabel("Aucun projet ouvert")
        self.project_label.setWordWrap(True)
        v.addWidget(self.project_label)
        self.credits_controls = QWidget()
        credits = QHBoxLayout(self.credits_controls)
        credits.setContentsMargins(0, 0, 0, 0)
        credits.addWidget(QLabel("Projet et crédits"))
        self.credits_file = self.track(QLineEdit())
        self.credits_file.setReadOnly(True)
        self.credits_file.setPlaceholderText("Les informations du projet seront utilisées par défaut.")
        credits.addWidget(self.credits_file, 1)
        credits.addWidget(self.button("Choisir le Markdown…", self.choose_credits))
        credits.addWidget(self.button("Retirer le fichier", self.credits_file.clear))
        self.credits_controls.setEnabled(False)
        v.addWidget(self.credits_controls)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        self.home_controls = QGroupBox("Page d’accueil")
        home_form = QFormLayout(self.home_controls)
        image_row = QHBoxLayout()
        self.home_image = self.field("editorial", "home_image", QLineEdit())
        self.home_image.setReadOnly(True)
        self.home_image.setPlaceholderText("Frontispice fourni avec Studio Aldines")
        image_row.addWidget(self.home_image, 1)
        image_row.addWidget(self.button("Choisir une image…", self.choose_home_image))
        image_row.addWidget(self.button("Rétablir le frontispice", self.reset_home_image))
        home_form.addRow("Image d’accueil", image_row)
        self.home_caption = self.field("editorial", "home_caption", QPlainTextEdit())
        self.home_caption.setMaximumHeight(65)
        home_form.addRow("Légende de l’image", self.home_caption)
        self.home_alt = self.field("editorial", "home_alt", QLineEdit())
        self.home_alt.setPlaceholderText("Décrivez brièvement l’image pour les lecteurs d’écran.")
        home_form.addRow("Texte alternatif", self.home_alt)
        for key, label in (("home_intro", "Texte d’introduction"),
                           ("home_edition", "Texte sous « L’édition »"),
                           ("home_resources", "Texte sous « Études et ressources »")):
            text = self.field("editorial", key, QPlainTextEdit())
            text.setMaximumHeight(65)
            home_form.addRow(label, text)
        self.home_controls.setEnabled(False)
        form.addRow(self.home_controls)
        labels = {"id": "Identifiant", "title": "Titre", "subtitle": "Sous-titre", "author": "Auteur",
                  "editor": "Responsable scientifique", "contributors": "Contributions (une par ligne)",
                  "institution": "Institution", "laboratory": "Laboratoire", "description": "Présentation",
                  "source_edition": "Édition de référence", "languages": "Langues (une par ligne)",
                  "status": "État d’avancement", "publication_date": "Date de publication", "version": "Version",
                  "license": "Licence des contenus", "citation": "Formule de citation", "identifiers": "Identifiants pérennes (un par ligne)"}
        for key in DEFAULTS["corpus"]:
            widget = QPlainTextEdit() if key in ("contributors", "description", "languages", "identifiers", "citation", "source_edition") else QLineEdit()
            if isinstance(widget, QPlainTextEdit):
                widget.setMaximumHeight(80)
            form.addRow(labels[key], self.field("corpus", key, widget))
        for key, label in [("directory", "Dossier TEI"), ("master", "Fichier maître")]:
            row = QHBoxLayout()
            field = self.field("sources", key, QLineEdit())
            row.addWidget(field)
            row.addWidget(self.button("Parcourir…", lambda checked=False, k=key: self.browse_source(k)))
            form.addRow(label, row)
        scroll.setWidget(container)
        v.addWidget(scroll)

    def make_corpus(self):
        v = self.space("Le corpus", "L’ordre des unités suit le fichier maître. Les cases à cocher définissent la sélection à publier.")
        row = QHBoxLayout()
        row.addWidget(self.button("Recharger et contrôler", self.scan))
        row.addWidget(self.button("Tout sélectionner", lambda: self.select_all(True)))
        row.addWidget(self.button("Tout désélectionner", lambda: self.select_all(False)))
        row.addStretch()
        v.addLayout(row)
        self.summary = QLabel("Aucun corpus chargé")
        v.addWidget(self.summary)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Unité / fichier", "Latin", "Français", "État"])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemChanged.connect(self.changed)
        v.addWidget(self.tree, 3)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setPlaceholderText("Les diagnostics structurels apparaîtront ici.")
        v.addWidget(self.diagnostics, 1)

    def make_appearance(self):
        v = self.space("Une lecture à votre mesure", "Ces options règlent la présentation initiale du site. Le lecteur peut ensuite changer de mode et de thème.")
        form = QFormLayout()
        mode = QComboBox()
        for label, value in [("Latin et français", "bilingual"), ("Latin seul", "latin"), ("Français seul", "french")]:
            mode.addItem(label, value)
        form.addRow("Mode initial", self.field("reading", "default_mode", mode))
        theme = QComboBox()
        theme.addItem("Clair", "light")
        theme.addItem("Sombre", "dark")
        form.addRow("Thème", self.field("appearance", "theme", theme))
        alignment = QComboBox()
        alignment.addItem("Aligné à gauche", "left")
        alignment.addItem("Justifié", "justify")
        form.addRow("Alignement du texte et des présentations", self.field("appearance", "text_align", alignment))
        form.addRow("Police de lecture", self.field("appearance", "font", QLineEdit()))
        for key, label, low, high, step in [("font_size", "Taille du texte (px)", 12, 36, 1),
                 ("line_height", "Interlignage", 1.2, 2.5, .05), ("content_width", "Largeur (px)", 600, 1800, 50),
                 ("column_ratio", "Part de la colonne latine (%)", 30, 70, 5)]:
            widget = QDoubleSpinBox() if key == "line_height" else QSpinBox()
            widget.setRange(low, high)
            widget.setSingleStep(step)
            form.addRow(label, self.field("appearance", key, widget))
        for key, label in [("show_marginalia", "Afficher les manchettes"), ("show_notes", "Afficher les notes"),
                           ("show_page_numbers", "Repères de pages"), ("show_column_markers", "Repères de colonnes et sections imprimées"),
                           ("show_uncertainties", "Signaler les incertitudes"), ("show_sentence_ids", "Identifiants des phrases")]:
            form.addRow(self.field("reading", key, QCheckBox(label)))
        v.addLayout(form)
        hint = QLabel("EB Garamond est utilisée si elle est installée ; sinon, une police de repli prend le relais.\nLe signalement des incertitudes peut être masqué ; le texte et les lacunes restent conservés.")
        hint.setWordWrap(True)
        v.addWidget(hint)
        v.addStretch()

    def make_preview(self):
        v = self.space("Relire avant de publier", "Générez une unité avec les réglages courants, puis ouvrez-la dans votre navigateur.")
        self.preview_unit = QComboBox()
        v.addWidget(self.preview_unit)
        self.preview_button = self.button("Générer et ouvrir l’aperçu", self.preview, True)
        v.addWidget(self.preview_button)
        label = QLabel("L’aperçu est distinct de la publication complète. Il est servi uniquement sur cet ordinateur.\nAprès une modification des réglages, régénérez pour voir le résultat.")
        label.setWordWrap(True)
        v.addWidget(label)
        v.addStretch()

    def make_publication(self):
        v = self.space("Préparer la publication", "La génération produit un site statique local. Aucune mise en ligne n’est effectuée par l’application.")
        form = QFormLayout()
        row = QHBoxLayout()
        row.addWidget(self.field("publication", "output", QLineEdit()))
        row.addWidget(self.button("Choisir…", self.browse_output))
        form.addRow("Dossier de destination", row)
        origin = self.field("publication", "origin", QLineEdit())
        origin.setPlaceholderText("https://exemple.fr (facultatif, pour le sitemap)")
        form.addRow("Adresse publique du domaine", origin)
        form.addRow("Sous-répertoire web", self.field("publication", "base_path", QLineEdit()))
        v.addLayout(form)
        actions = QHBoxLayout()
        self.build_button = self.button("Générer le site complet", self.publish, True)
        actions.addWidget(self.build_button)
        actions.addWidget(self.button("Ouvrir le site", self.open_site))
        actions.addWidget(self.button("Ouvrir le dossier", self.open_output))
        v.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        v.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        v.addWidget(self.log)

    def make_resources(self):
        v = self.space("Études et ressources",
                       "Ajoutez les fichiers Markdown à publier, puis enregistrez les réglages dans l’onglet Projet.")
        self.resource_files = QListWidget()
        self.resource_files.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        v.addWidget(self.resource_files, 1)
        actions = QHBoxLayout()
        actions.addWidget(self.button("Ajouter des fichiers…", self.add_resources))
        actions.addWidget(self.button("Retirer de la liste", self.remove_resources))
        actions.addStretch()
        v.addLayout(actions)
        self.resources_page = v.parentWidget()
        self.resources_page.setEnabled(False)

    def project_relative_path(self, filename):
        path = Path(filename).resolve()
        directory = self.project.path.parent
        return str(path.relative_to(directory) if path.is_relative_to(directory) else path)

    def add_resources(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Ajouter des ressources", str(self.project.path.parent),
                                               "Fichiers Markdown (*.md *.markdown)")
        known = {self.project.resolve(self.resource_files.item(i).text()) for i in range(self.resource_files.count())}
        for filename in files:
            path = Path(filename).resolve()
            if path not in known:
                self.resource_files.addItem(self.project_relative_path(filename))
                known.add(path)
                self.changed()

    def remove_resources(self):
        selected = self.resource_files.selectedItems()
        for item in selected:
            self.resource_files.takeItem(self.resource_files.row(item))
        if selected:
            self.changed()

    def choose_credits(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir le fichier Projet et crédits", str(self.project.path.parent),
                                              "Fichiers Markdown (*.md *.markdown)")
        if path:
            self.credits_file.setText(self.project_relative_path(path))

    def choose_home_image(self):
        formats = " ".join(f"*{suffix}" for suffix in IMAGE_SUFFIXES)
        path, _ = QFileDialog.getOpenFileName(self, "Choisir l’image d’accueil", str(self.project.path.parent),
                                              f"Images ({formats})")
        if not path:
            return
        if not self.home_image.text():
            defaults = DEFAULTS["editorial"]
            if self.home_caption.toPlainText() == defaults["home_caption"]:
                self.home_caption.clear()
            if self.home_alt.text() == defaults["home_alt"]:
                self.home_alt.clear()
        self.home_image.setText(self.project_relative_path(path))

    def reset_home_image(self):
        self.home_image.clear()
        self.home_caption.setPlainText(DEFAULTS["editorial"]["home_caption"])
        self.home_alt.setText(DEFAULTS["editorial"]["home_alt"])

    def refresh_recent(self):
        self.recent.clear()
        for path in self.settings.value("recent", [], type=list):
            self.recent.addItem(str(path))

    def remember(self):
        paths = [str(self.project.path)] + [self.recent.itemText(i) for i in range(self.recent.count())
                                          if self.recent.itemText(i) != str(self.project.path)]
        self.settings.setValue("recent", paths[:8])
        self.refresh_recent()

    def error(self, message):
        self.statusBar().showMessage("Opération interrompue")
        QMessageBox.warning(self, "Studio Aldines", str(message))

    def can_replace(self):
        if self.worker and self.worker.isRunning():
            self.error("Attendez la fin de l’opération en cours.")
            return False
        if not self.dirty:
            return True
        choice = QMessageBox.question(self, "Réglages non enregistrés", "Enregistrer les réglages avant de continuer ?",
                                      QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        return self.save_project() if choice == QMessageBox.Save else choice == QMessageBox.Discard

    def choose_project(self):
        if self.can_replace():
            path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un projet", str(Path.cwd()), "Projet Aldines (*.json)")
            if path:
                self.open_project(path)

    def open_recent(self):
        if self.recent.currentText() and self.can_replace():
            self.open_project(self.recent.currentText())

    def open_project(self, path):
        try:
            project = load_project(path)
        except ProjectError as exc:
            self.error(exc)
            return
        self.project = project
        self.corpus = None
        self.loading = True
        for (group, key), widget in self.fields.items():
            value = project.data[group][key]
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(widget.findData(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.setValue(value)
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText("\n".join(value) if isinstance(value, list) else value or "")
            else:
                widget.setText(value or "")
        self.resource_files.clear()
        self.resource_files.addItems(project.data["editorial"]["resources"])
        self.credits_file.setText(project.data["editorial"]["credits"] or "")
        self.credits_controls.setEnabled(True)
        self.home_controls.setEnabled(True)
        self.resources_page.setEnabled(True)
        self.loading = False
        self.dirty = False
        self.setWindowTitle(f"Studio Aldines — {project.path.name}")
        self.project_label.setText(str(project.path))
        self.save_feedback.clear()
        self.save_button.setEnabled(True)
        self.remember()
        self.scan()

    def collect(self):
        if not self.project:
            raise ProjectError("Ouvrez ou créez d’abord un projet.")
        data = deepcopy(self.project.data)
        for (group, key), widget in self.fields.items():
            if isinstance(widget, QComboBox):
                value = widget.currentData()
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                value = widget.value()
            else:
                value = widget.toPlainText() if isinstance(widget, QPlainTextEdit) else widget.text()
                if group == "corpus" and key in ("contributors", "languages", "identifiers"):
                    value = [line.strip() for line in value.splitlines() if line.strip()]
                elif group == "corpus" and key in ("license", "citation", "publication_date") and not value.strip():
                    value = None
                elif group == "editorial" and key == "home_image":
                    value = value or None
            data[group][key] = value
        data["editorial"]["resources"] = [self.resource_files.item(i).text() for i in range(self.resource_files.count())]
        data["editorial"]["credits"] = self.credits_file.text() or None
        if self.corpus is not None:
            leaves = self.leaves()
            checked = [leaf.data(0, Qt.UserRole) for leaf in leaves if leaf.checkState(0) == Qt.Checked]
            data["sources"]["selection"] = None if len(checked) == len(leaves) else checked
        validate(data)
        return Project(self.project.path, data)

    def save_project(self):
        self.save_feedback.clear()
        try:
            project = self.collect()
            project.save()
        except (ProjectError, OSError) as exc:
            self.error(exc)
            return False
        self.project = project
        self.dirty = False
        self.setWindowTitle(f"Studio Aldines — {self.project.path.name}")
        message = "Projet enregistré."
        self.save_feedback.setText(message)
        self.statusBar().showMessage(message)
        return True

    def create_project(self):
        if not self.can_replace():
            return
        directory = QFileDialog.getExistingDirectory(self, "Dossier contenant les TEI")
        if not directory:
            return
        master, _ = QFileDialog.getOpenFileName(self, "Sélectionner le fichier maître", str(Path(directory) / "aug-t1.xml"), "XML TEI (*.xml)")
        if not master:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le projet hors du dossier TEI", str(Path.cwd() / "aldines.local.json"), "Projet (*.json)")
        if not path:
            return
        data = deepcopy(DEFAULTS)
        data["sources"].update(directory=directory, master=master)
        project = Project(Path(path).resolve(), data)
        try:
            project.save()
        except (ProjectError, OSError) as exc:
            self.error(exc)
            return
        self.open_project(path)

    def browse_source(self, key):
        if key == "directory":
            path = QFileDialog.getExistingDirectory(self, "Dossier TEI")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Fichier maître", "", "TEI (*.xml)")
        if path:
            self.fields[("sources", key)].setText(path)

    def browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de publication dédié (vide ou déjà généré par Aldines)")
        if path:
            self.fields[("publication", "output")].setText(path)

    def launch(self, action, done, *, message):
        if self.worker and self.worker.isRunning():
            return
        self.stack.setEnabled(False)
        self.progress.setRange(0, 0)
        self.statusBar().showMessage(message)
        self.busy_indicator.show()
        self.worker = Worker(action, self)
        self.worker.progress.connect(self.update_progress)
        self.worker.result.connect(done)
        self.worker.failed.connect(self.error)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def update_progress(self, message):
        self.statusBar().showMessage(message)
        self.log.appendPlainText(message)

    def finished(self):
        self.busy_indicator.hide()
        self.stack.setEnabled(True)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)

    def scan(self):
        try:
            project = self.collect()
        except ProjectError as exc:
            self.error(exc)
            return
        self.launch(lambda progress: read_corpus(project), lambda corpus: self.show_corpus(corpus, project),
                    message="Chargement du corpus…")

    def show_corpus(self, corpus, project):
        self.corpus = corpus
        self.loading = True
        self.tree.clear()
        self.preview_unit.clear()
        groups = {}
        selected = project.data["sources"]["selection"]
        for u in corpus.units:
            key = (u.tome, u.book)
            if key not in groups:
                group = QTreeWidgetItem(self.tree, [f"Tome {u.tome} · Livre {u.book}"])
                group.setFlags(group.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
                groups[key] = group
            leaf = QTreeWidgetItem(groups[key], [f"{u.label} — {u.file.name}", str(u.sentences), str(u.translated),
                                  "Traduction complète" if u.translated == u.sentences else "Traduction en cours"])
            leaf.setData(0, Qt.UserRole, u.id)
            leaf.setFlags(leaf.flags() | Qt.ItemIsUserCheckable)
            leaf.setCheckState(0, Qt.Checked if selected is None or u.id in selected else Qt.Unchecked)
            leaf.setToolTip(0, u.title)
            self.preview_unit.addItem(f"Tome {u.tome} · Livre {u.book} · {u.label}", u.id)
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        self.summary.setText(f"{len(corpus.units)} unités · {sum(u.sentences for u in corpus.units)} phrases latines · {len(corpus.issues)} diagnostic(s)")
        self.diagnostics.setPlainText("\n".join(map(str, corpus.issues)) or "Aucun problème structurel détecté.")
        for key, value in corpus.metadata.items():
            widget = self.fields.get(("corpus", key))
            if widget is not None and hasattr(widget, "setPlaceholderText"):
                widget.setPlaceholderText("\n".join(value) if isinstance(value, list) else value or "")
        self.loading = False
        self.statusBar().showMessage(self.summary.text())

    def leaves(self):
        return [self.tree.topLevelItem(i).child(j) for i in range(self.tree.topLevelItemCount())
                for j in range(self.tree.topLevelItem(i).childCount())]

    def select_all(self, checked):
        for leaf in self.leaves():
            leaf.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)

    def preview(self):
        uid = self.preview_unit.currentData()
        if not uid:
            self.error("Chargez le corpus et sélectionnez une unité.")
            return
        try:
            project = self.collect()
        except ProjectError as exc:
            self.error(exc)
            return
        destination = project.path.parent / ".local" / "preview"
        self.launch(lambda progress: build(project, only=uid, output=destination, progress=progress),
                    lambda result: self.show_result(result, uid), message="Génération de l’aperçu…")

    def publish(self):
        try:
            project = self.collect()
        except ProjectError as exc:
            self.error(exc)
            return
        self.log.clear()
        self.launch(lambda progress: build(project, progress=progress), self.show_result,
                    message="Génération des pages du site…")

    def show_result(self, result, uid=None):
        for issue in result.corpus.issues:
            self.log.appendPlainText(str(issue))
        self.update_progress(f"Site généré : {result.count} unité(s) dans {result.output}")
        if uid:
            unit = next(u for u in result.corpus.units if u.id == uid)
            self.browse_site(result.output, unit.route)

    def browse_site(self, output, route=""):
        if not (output / "index.html").is_file():
            self.error("Générez d’abord le site.")
            return
        server, url = start_preview(output)
        self.servers.append(server)
        QDesktopServices.openUrl(QUrl(url + route))

    def open_site(self):
        try:
            self.browse_site(self.collect().output)
        except ProjectError as exc:
            self.error(exc)

    def open_output(self):
        try:
            output = self.collect().output
            if not output.is_dir():
                raise ProjectError("Le dossier de sortie n’existe pas encore.")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output)))
        except ProjectError as exc:
            self.error(exc)

    def closeEvent(self, event):
        if not self.can_replace():
            event.ignore()
            return
        for server in self.servers:
            server.shutdown()
            server.server_close()
        event.accept()


def run(path=None):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Studio Aldines")
    app.setFont(QFont("Segoe UI", 10))
    window = Window(path)
    window.show()
    return app.exec()
