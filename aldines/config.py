"""Un JSON lisible, des chemins relatifs au projet, aucune écriture dans les TEI."""
from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re


class ProjectError(ValueError):
    pass


DEFAULTS = {
    "schema_version": 1,
    "corpus": {"id": "augustinus", "title": "", "subtitle": "Édition numérique bilingue",
               "author": "", "editor": "", "contributors": [],
               "institution": "Université de Rouen Normandie", "laboratory": "CEREdI",
               "description": "", "source_edition": "", "languages": ["la", "fr"],
               "status": "Édition en cours", "license": None, "citation": None,
               "identifiers": [], "publication_date": None, "version": "0.1"},
    "sources": {"directory": "tei/t1", "master": "tei/t1/aug-t1.xml", "selection": None},
    "reading": {"default_mode": "bilingual", "show_marginalia": True, "show_notes": True,
                "show_page_numbers": True, "show_column_markers": True,
                "show_uncertainties": True, "show_sentence_ids": False},
    "appearance": {"theme": "light", "font": "EB Garamond", "font_size": 20,
                   "line_height": 1.65, "content_width": 1200, "column_ratio": 50,
                   "text_align": "left"},
    "publication": {"output": "publication", "base_path": "/"},
}


@dataclass
class Project:
    path: Path
    data: dict

    def resolve(self, value):
        return (self.path.parent / value).resolve()

    @property
    def directory(self):
        return self.resolve(self.data["sources"]["directory"])

    @property
    def master(self):
        return self.resolve(self.data["sources"]["master"])

    @property
    def output(self):
        return self.resolve(self.data["publication"]["output"])

    def save(self):
        validate(self.data)
        # Une sauvegarde de projet ne peut pas écraser un fichier scientifique.
        if self.path.suffix.lower() != ".json" or self.path.is_relative_to(self.directory):
            raise ProjectError("Enregistrer le projet JSON hors du dossier TEI.")
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.path)


def validate(data):
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ProjectError("schema_version doit valoir 1.")
    for group in ("corpus", "sources", "reading", "appearance", "publication"):
        if not isinstance(data.get(group), dict):
            raise ProjectError(f"{group} doit être un objet JSON.")
    for group, keys in {"sources": ["directory", "master"], "publication": ["output"]}.items():
        for key in keys:
            if not isinstance(data[group].get(key), str) or not data[group][key].strip():
                raise ProjectError(f"{group}.{key} : chemin requis.")
    for key, value in data["corpus"].items():
        if key in ("contributors", "identifiers", "languages"):
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                raise ProjectError(f"corpus.{key} doit être une liste de textes.")
        elif value is not None and not isinstance(value, str):
            raise ProjectError(f"corpus.{key} doit être un texte ou null.")
    selection = data["sources"].get("selection")
    if selection is not None and (not isinstance(selection, list) or any(not isinstance(v, str) for v in selection)):
        raise ProjectError("sources.selection doit être null (tout) ou une liste d’identifiants.")
    for key in DEFAULTS["reading"]:
        if key != "default_mode" and type(data["reading"].get(key)) is not bool:
            raise ProjectError(f"reading.{key} doit être true ou false.")
    if data["reading"].get("default_mode") not in ("bilingual", "latin", "french"):
        raise ProjectError("reading.default_mode : bilingual, latin ou french attendu.")
    a = data["appearance"]
    if a.get("text_align") not in ("left", "justify"):
        raise ProjectError("appearance.text_align : left ou justify attendu.")
    if a.get("theme") not in ("light", "dark"):
        raise ProjectError("appearance.theme : light ou dark attendu.")
    if not isinstance(a.get("font"), str) or not re.fullmatch(r"[\w .-]{1,80}", a["font"]):
        raise ProjectError("appearance.font : nom de police simple attendu.")
    for key, low, high in [("font_size", 12, 36), ("line_height", 1.2, 2.5),
                           ("content_width", 600, 1800), ("column_ratio", 30, 70)]:
        v = a.get(key)
        if type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high:
            raise ProjectError(f"appearance.{key} doit être compris entre {low} et {high}.")
    base = data["publication"].get("base_path")
    if not isinstance(base, str) or not re.fullmatch(r"/(?:[A-Za-z0-9_-]+/)*", base):
        raise ProjectError("publication.base_path : / ou /sous-dossier/ attendu.")


def load_project(path):
    path = Path(path).resolve()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ProjectError(f"Impossible de lire {path.name} : {exc}") from exc
    if not isinstance(raw, dict):
        raise ProjectError("Le projet doit être un objet JSON.")
    data = deepcopy(DEFAULTS)
    for key, value in raw.items():
        if isinstance(data.get(key), dict) and isinstance(value, dict):
            data[key].update(value)
        else:
            data[key] = value
    validate(data)
    return Project(path, data)
