"""Publication statique ; ce module ne connaît pas le vocabulaire TEI."""
from dataclasses import dataclass
from html import escape as esc
import json
from pathlib import Path
import posixpath
import re
import shutil
import tempfile
import time
import unicodedata
from urllib.parse import quote

from . import __version__
from .augustinus import read_corpus
from .config import ProjectError, validate
from .editorial import FRONTISPICE, editorial_document, home, project_credits, publication_footer, resources
from .markdown import read_markdown

MARKER = ".aldines-generated"


@dataclass
class BuildResult:
    output: Path
    corpus: object
    count: int


def chosen_units(project, corpus, only=None):
    selection = [only] if only else project.data["sources"]["selection"]
    if selection is None:
        return corpus.units
    unknown = set(selection) - {u.id for u in corpus.units}
    if unknown:
        raise ProjectError("Unités sélectionnées introuvables : " + ", ".join(sorted(unknown)))
    return [u for u in corpus.units if u.id in selection]


def publication_metadata(project, corpus):
    result = dict(corpus.metadata)
    for key, value in project.data["corpus"].items():
        if value is not None and value != "" and value != []:
            result[key] = value
    result.setdefault("title", "Augustinus")
    return result


def link(current, target=""):
    """Liens relatifs : même site à la racine, en sous-dossier ou en aperçu."""
    rel = posixpath.relpath(target or ".", current or ".")
    return "./" if rel == "." else rel.rstrip("/") + "/"


def page(project, meta, title, body, current="", reader=False):
    root = link(current)
    page_class = "edition-page" if reader else {"": "home-page", "contents/": "contents-page"}.get(current, "")
    a = project.data["appearance"]
    reading = project.data["reading"]
    classes = " ".join("hide-" + key[5:].replace("_", "-") for key, value in reading.items()
                       if key.startswith("show_") and not value)
    css = (f":root{{--reading-font:'{a['font']}',Garamond,Georgia,serif;--text-size:{a['font_size']}px;"
           f"--leading:{a['line_height']};--measure:{a['content_width']}px;--ratio:{a['column_ratio']}%;}}")
    options = "".join(f'<option value="{value}"{" selected" if reading["default_mode"] == value else ""}>{label}</option>'
                      for value, label in [("bilingual", "Latin · Français"), ("latin", "Latin"), ("french", "Français")])
    toolbar = f'<div class="reader-tools"><label>Lecture <select id="reading-mode">{options}</select></label>'
    toolbar += '<button id="reader-options" aria-expanded="false" aria-controls="display-options">Options d’affichage</button></div>'
    panel = f'''<fieldset id="display-options" hidden><legend>Options d’affichage</legend>
{''.join(
        f'<label><input type="checkbox" data-option="{key[5:].replace("_", "-")}" {"checked" if reading[key] else ""}> {label}</label>'
        for key, label in [("show_notes", "Notes"), ("show_marginalia", "Manchettes"),
                           ("show_page_numbers", "Pages"), ("show_column_markers", "Colonnes et sections imprimées"),
                           ("show_uncertainties", "Signalement des incertitudes"), ("show_sentence_ids", "Identifiants des phrases")])}</fieldset>'''
    return f'''<!doctype html>
<html lang="fr" data-theme="{a['theme']}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="generator" content="Studio Aldines 0.1">
<title>{esc(title)} · {esc(meta['title'])}</title>
<link rel="stylesheet" href="{root}assets/site.css">
<link rel="stylesheet" href="{root}assets/footer.css"><style>{css}</style>
<script src="{root}assets/site.js" defer></script></head>
<body class="{classes}" data-mode="{reading['default_mode']}" data-root="{root}" data-alignment="{a['text_align']}">
<a class="skip" href="#main">Aller au contenu</a>
<header class="site-header{' reading-header' if reader else ''}"><a class="brand" href="{root}">
<span>{esc(meta['title'])}<small>{esc(meta.get('subtitle', ''))}</small></span></a>
<div class="header-controls"><nav aria-label="Navigation principale"><a href="{root}contents/">Sommaire</a><a href="{root}search/">Rechercher</a>
<button id="theme-toggle" aria-label="Changer le thème">Clair / sombre</button></nav>{toolbar}</div></header>
{panel}<main id="main" class="{page_class}">{body}</main>
{publication_footer(meta)}
</body></html>'''


def contents(units):
    result = ['<p class="eyebrow">EXPLORER LE CORPUS</p><h1>Table des matières</h1>',
              '<p>Choisissez un tome, un livre, puis une section ou un chapitre disponible.</p>',
              '''<form id="corpus-navigator" hidden><div class="corpus-selectors">
<label>Tome<select id="nav-tome"></select></label>
<label>Livre<select id="nav-book"></select></label>
<label>Section / chapitre<select id="nav-unit"></select></label></div>
<p id="nav-summary" role="status"></p><a id="nav-open" class="primary">Ouvrir le texte →</a></form>
<details class="contents-fallback" open><summary>Liste complète des unités disponibles</summary>''']
    last_tome = last_book = None
    opened = False
    for u in units:
        if (u.tome, u.book) != (last_tome, last_book):
            if opened:
                result.append("</ol>")
            if u.tome != last_tome:
                result.append(f"<h2>Tome {u.tome}</h2>")
            result.append(f'<h3>Livre {u.book}</h3><ol class="contents-list">')
            last_tome, last_book, opened = u.tome, u.book, True
        result.append(f'<li data-tome="{u.tome}" data-book="{u.book}" data-sentences="{u.sentences}" data-translated="{u.translated}"><a href="{link("contents/", u.route)}">{esc(u.label)}</a>'
                      f'<span>{u.sentences} phrases · {u.translated} traduites</span></li>')
    if opened:
        result.append("</ol>")
    result.append("</details>")
    return "".join(result)


def reader_page(unit, units, index, global_anchors):
    nav = f'<a href="{link(unit.route, "contents/")}">Table des matières</a>'
    if index:
        nav = f'<a rel="prev" href="{link(unit.route, units[index - 1].route)}">← {esc(units[index - 1].label)}</a>' + nav
    if index + 1 < len(units):
        nav += f'<a rel="next" href="{link(unit.route, units[index + 1].route)}">{esc(units[index + 1].label)} →</a>'
    rows = []
    alias_map = {}
    for alias, target in unit.aliases.items():
        alias_map.setdefault(target, []).append(alias)
    for row in unit.rows:
        fragment = row.latin + row.french
        own_id = "" if f'id="{esc(row.anchor)}"' in fragment else f' id="{esc(row.anchor)}"'
        aliases = "".join(f'<span class="tei-anchor" id="{esc(a)}"></span>' for a in alias_map.get(row.anchor, []))
        sid = f'<span class="sentence-id">{esc(row.anchor)}</span>' if row.kind == "sentence" else ""
        rows.append(f'<div{own_id} class="aligned-row {esc(row.kind)} {esc(row.style)}" data-anchor="{esc(row.anchor)}">{aliases}'
                    f'<div class="latin" lang="la">{sid}{row.latin}</div><div class="french" lang="fr">{row.french}</div></div>')
    rendered = "".join(rows)
    def resolve_ref(match):
        target = match.group(2)
        route = global_anchors.get(target)
        if route is None:
            return f'<a{match.group(1)} aria-disabled="true" class="unavailable-ref" title="Référence non publiée : {esc(target)}"'
        return f'<a{match.group(1)} href="{link(unit.route, route)}#{quote(target, safe=".")}"'
    # Seuls les liens créés par l’interpréteur portent data-tei-ref.
    rendered = re.sub(r'<a([^>]*?) href="[^"]*" data-tei-ref="([^"]+)"', resolve_ref, rendered)
    return f'''<nav class="breadcrumb" aria-label="Fil d’Ariane"><a href="{link(unit.route)}">Accueil</a> / <a href="{link(unit.route, 'contents/')}">Tome {unit.tome} · Livre {unit.book}</a> / {esc(unit.label)}
<a class="tei-download" href="{quote(unit.file.name, safe='')}" download="{esc(unit.file.name)}" type="application/tei+xml">Télécharger le TEI</a></nav>
<p class="eyebrow">AUGUSTINUS · TOME {unit.tome} · LIVRE {unit.book}</p><h1>{esc(unit.label)}</h1>
<nav class="unit-nav" aria-label="Unités">{nav}</nav>
<div class="language-headings"><span>Texte latin</span><span>Traduction française</span></div>
<article class="reader" aria-label="Texte et traduction">{rendered}</article>
<nav class="unit-nav" aria-label="Suite de la lecture">{nav}</nav>
<details class="source-metadata"><summary>Notice scientifique du fichier TEI</summary><p>{esc(unit.title)}</p>
<p>{esc(unit.metadata.get('source_edition', ''))}</p><ul>{''.join('<li>' + esc(c) + '</li>' for c in unit.metadata.get('contributors', []))}</ul></details>'''


def check_output(project, output):
    output = output.resolve()
    source = project.directory
    if (output == project.path.parent or project.path.parent.is_relative_to(output)
            or output.is_relative_to(source) or source.is_relative_to(output)):
        raise ProjectError("Le dossier de sortie doit être distinct du projet et des sources TEI.")
    editorial = project.data["editorial"]
    for path in [*editorial["resources"], editorial["credits"]]:
        if path and project.resolve(path).is_relative_to(output):
            raise ProjectError("Placez les fichiers Markdown hors du dossier de sortie.")
    image = editorial["home_image"]
    if image and project.resolve(image).is_relative_to(output):
        raise ProjectError("Placez l’image d’accueil hors du dossier de sortie.")
    if output.exists() and (not output.is_dir() or output.is_symlink()):
        raise ProjectError("La sortie doit être un dossier ordinaire dédié à la publication.")
    if output.exists() and any(output.iterdir()) and not (output / MARKER).is_file():
        raise ProjectError("Le dossier de sortie contient des fichiers étrangers à Aldines. Choisir un dossier vide.")


def remove_owned_tree(path, parent):
    """Suppression limitée à un dossier temporaire possédé et à son parent vérifié."""
    path, parent = path.resolve(), parent.resolve()
    if path.parent != parent or not (path / MARKER).is_file():
        raise ProjectError(f"Nettoyage refusé : dossier non identifié {path}")
    shutil.rmtree(path)


def replace_directory(source, destination):
    # Sous Windows, un antivirus peut retenir brièvement un fichier récemment
    # écrit. Réessayer uniquement l’erreur de partage, pendant moins d’une seconde.
    source, destination = source.resolve(), destination.resolve()
    if source.parent != destination.parent:
        raise ProjectError("Le remplacement doit rester dans le dossier parent de publication.")
    for attempt in range(5):
        try:
            source.replace(destination)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.05 * (attempt + 1))


def build(project, *, only=None, output=None, progress=lambda message: None):
    validate(project.data)
    output = Path(output).resolve() if output else project.output
    check_output(project, output)
    progress("Lecture et contrôles du corpus…")
    corpus = read_corpus(project)
    if corpus.errors:
        raise ProjectError("Génération interrompue :\n" + "\n".join(map(str, corpus.issues)))
    units = chosen_units(project, corpus, only)
    if not units:
        raise ProjectError("Aucune unité sélectionnée et disponible.")
    meta = publication_metadata(project, corpus)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".aldines-stage-", dir=output.parent)).resolve()
    (stage / MARKER).write_text("Studio Aldines — dossier généré, remplaçable\n", encoding="utf-8")
    try:
        def write(route, value):
            destination = stage / route / "index.html"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(value, encoding="utf-8")

        def write_document(route, filename, *, credits=False):
            name = Path(filename).name
            progress(f"Conversion Markdown : {name}")
            document = read_markdown(project.resolve(filename))
            write(route, editorial_document(meta, document, credits=credits))
            (stage / route / "document.xml").write_bytes(document.tei)
            (stage / route / name).write_bytes(document.source)
            return document.title, document.excerpt

        editorial = project.data["editorial"]
        assets = stage / "assets"
        assets.mkdir()
        bundled_assets = Path(__file__).parent / "assets"
        image = FRONTISPICE
        filename = editorial["home_image"]
        if filename:
            image = "accueil" + Path(filename).suffix.lower()
            try:
                shutil.copyfile(project.resolve(filename), assets / image)
            except OSError as exc:
                raise ProjectError(f"Impossible de copier l’image d’accueil {Path(filename).name} : {exc}") from exc
        else:
            shutil.copyfile(bundled_assets / image, assets / image)
        write("", home(meta, image, editorial["home_caption"], editorial["home_alt"]))

        documents = {}
        for filename in editorial["resources"]:
            path = project.resolve(filename)
            ascii_stem = unicodedata.normalize("NFKD", path.stem).encode("ascii", "ignore").decode().lower()
            base = "document-" + (re.sub(r"[^a-z0-9]+", "-", ascii_stem)[:60].strip("-") or "ressource")
            slug, suffix = base, 2
            while slug in documents:
                slug = f"{base}-{suffix}"
                suffix += 1
            documents[slug] = write_document(f"ressources/{slug}", filename)
        write("ressources", resources(meta, documents.items()))
        if editorial["credits"]:
            write_document("projet", editorial["credits"], credits=True)
        else:
            write("projet", project_credits(meta))
        write("contents", page(project, meta, "Table des matières", contents(units), "contents/"))
        anchors = {}
        for u in units:
            for ident in list(u.aliases) + [r.anchor for r in u.rows]:
                anchors[ident] = u.route
            for ident in re.findall(r'\bid="([^"]+)"', "".join(r.latin + r.french for r in u.rows)):
                anchors[ident] = u.route
        for i, u in enumerate(units):
            progress(f"{i + 1}/{len(units)} · {u.label} · Livre {u.book}")
            write(u.route, page(project, meta, u.label, reader_page(u, units, i, anchors), u.route, reader=True))
            # Publier le fichier original, sans sérialisation ni modification.
            shutil.copyfile(u.file, stage / u.route / u.file.name)
        search_body = '''<p class="eyebrow">LATIN & FRANÇAIS</p><h1>Rechercher dans l’édition</h1>
<form id="search-form" role="search"><label for="query">Un mot ou une expression</label>
<div class="search-box"><input id="query" type="search" required minlength="2" placeholder="Pélage, gratia…"><select id="search-language" aria-label="Langue"><option value="all">Les deux langues</option><option value="la">Latin</option><option value="fr">Français</option></select><button type="submit">Rechercher</button></div></form>
<p id="search-status" role="status"></p><ol id="search-results"></ol>
<script src="../assets/search-data.js" defer></script>'''
        write("search", page(project, meta, "Recherche", search_body, "search/"))
        for name in ("site.css", "site.js", "footer.css", "editorial.css"):
            shutil.copyfile(bundled_assets / name, assets / name)
        records = [{"unit": u.label, "book": u.book, "route": u.route, "anchor": r.anchor,
                    "la": r.latin_text, "fr": r.french_text} for u in units for r in u.rows
                   if r.latin_text or r.french_text]
        search_json = json.dumps(records, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        (assets / "search-data.js").write_text("window.ALDINES_SEARCH = " + search_json + ";\n", encoding="utf-8")
        report = corpus.report()
        report["published_units"] = len(units)
        report["base_path"] = project.data["publication"]["base_path"]
        (stage / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (stage / "aldines.json").write_text(json.dumps(project.data, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
        notice = f"""Publication générée avec Studio Aldines {__version__}.
Code et documentation : https://github.com/Gheeraert/aldines

Ouvrir index.html via un serveur web statique. Pour un aperçu local,
exécuter python -m aldines serve depuis le projet en indiquant ce dossier.

aldines.json contient les réglages utilisés lors de la génération.
Les chemins relatifs sont ceux du projet d’origine. Pour régénérer le site
depuis cette copie, adapter les chemins vers le corpus et les fichiers Markdown.
build-report.json consigne les diagnostics et le nombre d’unités publiées.
"""
        if documents or editorial["credits"]:
            notice += ("\nLes fichiers Markdown ont été convertis avec Pandoc. Une copie de chaque\n"
                       "source Markdown accompagne sa page HTML et son fichier document.xml.\n")
        if only:
            notice += f"\nAperçu limité à l’unité {only}.\n"
        (stage / "LISEZ-MOI.txt").write_text(notice, encoding="utf-8")
        (stage / ".nojekyll").touch()
        # Le site précédent n’est remplacé qu’après la réussite de toute la génération.
        backup = None
        if output.exists():
            backup = Path(tempfile.mkdtemp(prefix=".aldines-backup-", dir=output.parent)).resolve()
            backup.rmdir()  # répertoire vide créé par nous
            replace_directory(output, backup)
            if not (backup / MARKER).exists():  # ancien dossier vide
                (backup / MARKER).touch()
        try:
            replace_directory(stage, output)
        except OSError:
            if backup is not None:
                replace_directory(backup, output)
            raise
        if backup is not None:
            remove_owned_tree(backup, output.parent)
    finally:
        if stage.exists():
            remove_owned_tree(stage, output.parent)
    progress(f"Terminé : {len(units)} unités, {len(corpus.issues)} diagnostic(s).")
    return BuildResult(output, corpus, len(units))
