"""Interprétation des conventions observées le 31/10/2026 dans les 97 TEI.

Point de remplacement futur : read_corpus(Project) -> Corpus. Le générateur
ne connaît ni lxml, ni les noms des éléments TEI. Aucun fichier source n’est écrit.
Le parcours des structures et l’alignement @corresp reprennent le principe de
outils/tei2html.py, en préservant aussi titres, paragraphes et repères intercalés.
"""
from collections import defaultdict
from html import escape as esc
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from lxml import etree as ET

from .model import Corpus, Issue, Row, Unit

T = "{http://www.tei-c.org/ns/1.0}"
NS = {"t": T[1:-1]}
XI = "{http://www.w3.org/2001/XInclude}include"
XID = "{http://www.w3.org/XML/1998/namespace}id"
LANG = "{http://www.w3.org/XML/1998/namespace}lang"
KNOWN = set("text body div p s head trailer note quote title foreign hi milestone pb cb fw lb "
            "sic corr unclear gap choice abbr expan lg l ref seg name num date emph supplied del add".split())


def tag(e):
    return ET.QName(e).localname if isinstance(e.tag, str) else ""


def content_text(e):
    """Texte pour la recherche : sans notes ni repères, sans double expansion."""
    if tag(e) in ("note", "pb", "cb", "milestone", "fw"):
        return ""
    if tag(e) == "gap":
        return "[…]"
    if tag(e) == "choice":
        chosen = next((c for c in e if tag(c) in ("abbr", "sic", "orig")), None)
        if chosen is not None:
            return content_text(chosen)
    result = e.text or ""
    for ch in e:
        result += content_text(ch) + (ch.tail or "")
    return result


def clean(e):
    return " ".join(content_text(e).split()) if e is not None else ""


def metadata(root):
    header = root.find(T + "teiHeader")
    if header is None:
        return {}
    def text(path):
        return clean(header.find(path, NS))
    people = header.findall(".//t:respStmt", NS)
    contributors = [f"{clean(p.find(T + 'name'))} — {clean(p.find(T + 'resp'))}" for p in people]
    editor = next((clean(p.find(T + "name")) for p in people
                   if "direction" in clean(p.find(T + "resp")).lower()), "")
    return {"title": text(".//t:titleStmt/t:title"), "author": text(".//t:titleStmt/t:author"),
            "editor": editor, "contributors": contributors,
            "source_edition": text(".//t:sourceDesc"),
            "languages": [e.get("ident") for e in header.findall(".//t:language", NS) if e.get("ident")]}


class Reader:
    def __init__(self, project):
        self.project = project
        self.corpus = Corpus()
        self.ids = {}
        self.references = []
        self.origins = {}

    def issue(self, level, file, message, e=None):
        self.corpus.issues.append(Issue(level, Path(file).name, message, e.sourceline if e is not None else None))

    def parse(self, path, stack=()):
        path = path.resolve()
        if not path.is_relative_to(self.project.directory):
            self.issue("error", path, "Ressource hors du dossier TEI autorisé.")
            return None
        if path in stack:
            self.issue("error", path, "Cycle XInclude.")
            return None
        if not path.exists():
            self.issue("warning", path, "Inclusion absente : unité en cours d’établissement, ignorée.")
            return None
        try:
            parser = ET.XMLParser(resolve_entities=False, load_dtd=False, no_network=True,
                                  collect_ids=False, remove_comments=True, remove_pis=True)
            root = ET.parse(str(path), parser).getroot()
            if root.getroottree().docinfo.doctype:
                self.issue("error", path, "DOCTYPE et entités externes non autorisés.")
                return None
        except (OSError, ET.XMLSyntaxError) as exc:
            self.issue("error", path, f"Lecture XML impossible : {exc}")
            return None
        for e in root.iter():
            self.origins[e] = path
        for inc in list(root.iter(XI)):
            href = inc.get("href", "")
            parts = urlsplit(href)
            if (not href or parts.scheme or parts.netloc or parts.query or parts.fragment
                    or inc.get("parse", "xml") != "xml" or inc.get("xpointer")
                    or "\\" in href or ":" in href or Path(unquote(parts.path)).is_absolute()):
                self.issue("error", path, f"XInclude non pris en charge (XML local relatif requis) : {href}", inc)
                continue
            included = self.parse(path.parent / unquote(parts.path), (*stack, path))
            parent = inc.getparent()
            if included is not None:
                included.tail = (included.tail or "") + (inc.tail or "")
                parent.replace(inc, included)
            else:
                # Ne pas rendre le fallback comme s’il s’agissait d’un texte établi.
                parent.remove(inc)
        return root

    def inspect(self, root):
        for e in root.iter():
            if not isinstance(e.tag, str):
                continue
            path = self.origins.get(e, self.project.master)
            ident = e.get(XID)
            if ident:
                if ident in self.ids:
                    self.issue("error", path, f"xml:id dupliqué : {ident} (déjà dans {self.ids[ident]})", e)
                self.ids[ident] = path.name
            for attr in ("corresp", "target", "resp"):
                for ref in e.get(attr, "").split():
                    if ref.startswith("#"):
                        self.references.append((path, ref[1:], e))
        for path, ref, e in self.references:
            if ref not in self.ids:
                self.issue("warning", path, f"Référence interne inconnue : #{ref}", e)

    def unit(self, root):
        path = self.origins.get(root, self.project.master)
        ed = root.find(".//t:div[@type='edition']", NS)
        fr = root.find(".//t:div[@type='translation']", NS)
        if ed is None:
            self.issue("error", path, 'Aucun div type="edition".', root)
            return None
        # L’identité vient du TEI ; le nom de fichier n’est qu’un dernier recours.
        match = re.search(r"t(\d+)\.l(\d+)\.([sc])(\d+)", ed.get(XID, ""))
        if not match:
            match = re.search(r"t(\d+)-l(\d+)-([sc])(\d+)", path.stem)
        if not match:
            self.issue("error", path, "Identité Augustinus introuvable (tome/livre/section ou chapitre).", ed)
            return None
        tome, book, kind, number = match.groups()
        uid = f"t{int(tome)}.l{int(book):02}.{kind}{int(number):02}"
        label = f"{'Section' if kind == 's' else 'Chapitre'} {int(number)}"
        unit = Unit(uid, path, metadata(root).get("title") or label,
                    f"t{int(tome)}/l{int(book)}/{kind}{int(number):02}/", int(tome), int(book), label,
                    metadata=metadata(root))
        for body in (ed, fr):
            if body is None:
                continue
            unknown = set()
            for e in body.iter():
                if tag(e) and (tag(e) not in KNOWN or not e.tag.startswith(T)) and e.tag != XI:
                    if e.tag not in unknown:
                        self.issue("warning", path, f"Élément non traité : {e.tag} ; contenu conservé.", e)
                        unknown.add(e.tag)
        latin = list(ed.iter(T + "s"))
        unit.sentences = len(latin)
        la_ids = {s.get(XID) for s in latin if s.get(XID)}
        mapping = defaultdict(list)
        orphan = []
        for sentence in fr.iter(T + "s") if fr is not None else []:
            refs = [r[1:] for r in sentence.get("corresp", "").split() if r.startswith("#")]
            valid = [r for r in refs if r in la_ids]
            if not valid:
                orphan.append(sentence)
                self.issue("warning", path, "Phrase française sans correspondance latine ; conservée en fin d’unité.", sentence)
            else:
                mapping[valid[0]].append(sentence)
                if len(valid) > 1:
                    self.issue("warning", path, "Correspondance française multiple : affichée auprès de la première phrase ciblée.", sentence)
        unit.translated = len({r[1:] for s in fr.iter(T + 's') for r in s.get('corresp', '').split()
                               if r.startswith('#') and r[1:] in la_ids}) if fr is not None else 0
        renderer = Inline()
        fheads = list(fr.iter(T + "head")) if fr is not None else []
        head_index = 0
        serial = 0

        def emit(e, paragraph_style=""):
            nonlocal head_index, serial
            name = tag(e)
            ident = e.get(XID)
            serial += 1
            anchor = ident or f"{uid}.block{serial}"
            if name == "s":
                matches = mapping.get(ident, [])
                if not ident:
                    self.issue("warning", path, "Phrase latine sans xml:id : ancre locale de remplacement.", e)
                if not matches:
                    self.issue("warning", path, f"Phrase sans traduction : {anchor}", e)
                row = Row(anchor, renderer.render(e), " ".join(renderer.render(f) for f in matches)
                          or '<em class="missing">Traduction à venir</em>', clean(e),
                          " ".join(clean(f) for f in matches), style=paragraph_style)
                unit.rows.append(row)
            elif name == "head":
                fh = fheads[head_index] if head_index < len(fheads) else None
                head_index += 1
                unit.rows.append(Row(anchor, renderer.render(e), renderer.render(fh) if fh is not None else "", kind="heading"))
            elif name in ("div", "p", "trailer"):
                style = e.get("rend", "") if e.get("rend") in ("epistola", "rubrica") else ""
                if name in ("p", "trailer"):
                    paragraph_style = style
                if name != "div":
                    unit.rows.append(Row(anchor, "", "", kind="paragraph " + style))
                if e.text and e.text.strip():
                    unit.rows.append(Row(f"{anchor}.text", esc(e.text), "", kind="block"))
                for ch in e:
                    emit(ch, paragraph_style)
                    if ch.tail and ch.tail.strip():
                        unit.rows.append(Row(f"{uid}.tail{len(unit.rows)}", esc(ch.tail), "", kind="block"))
            else:
                unit.rows.append(Row(anchor, renderer.render(e), "", kind="block"))
        emit(ed)
        for s in orphan:
            unit.rows.append(Row(s.get(XID) or f"{uid}.orphan{len(unit.rows)}", "", renderer.render(s),
                                 french_text=clean(s)))
        # Conserver aussi le texte français hors phrases et hors titres (rare).
        if fr is not None:
            extras = []
            def outside(e):
                if tag(e) in ("s", "head"):
                    return
                if tag(e) not in ("div", "p", "trailer"):
                    extras.append(renderer.render(e))
                    return
                if e.text and e.text.strip():
                    extras.append(esc(e.text))
                for child in e:
                    outside(child)
                    if child.tail and child.tail.strip():
                        extras.append(esc(child.tail))
            outside(fr)
            if extras:
                unit.rows.append(Row(f"{uid}.fr.extra", "", "".join(extras), kind="block"))
                self.issue("warning", path, "Texte français hors phrases alignées conservé en fin d’unité.", fr)
        # Les conteneurs non rendus (div, paragraphes français) gardent une ancre
        # au plus près de leur première phrase, sans déplacer les xml:id réels.
        rendered_ids = set(re.findall(r'\bid="([^"]+)"', "".join(r.latin + r.french for r in unit.rows)))
        row_ids = {r.anchor for r in unit.rows}
        for body in (ed, fr):
            if body is None:
                continue
            for e in body.iter():
                ident = e.get(XID)
                if ident and ident not in rendered_ids and ident not in row_ids:
                    first = next(e.iter(T + "s"), None)
                    target = first.get(XID) if first is not None else unit.rows[0].anchor
                    if first is not None and not target:
                        refs = first.get("corresp", "").split()
                        target = refs[0].lstrip("#") if refs else None
                    unit.aliases[ident] = target if target in row_ids else unit.rows[0].anchor
        return unit


class Inline:
    """Échappe tout texte ; seules les constructions HTML ci-dessous sont émises."""
    def render(self, e):
        name = tag(e)
        value = esc(e.text or "") + "".join(self.render(c) + esc(c.tail or "") for c in e)
        ident = f' id="{esc(e.get(XID))}"' if e.get(XID) else ""
        lang = f' lang="{esc(e.get(LANG))}"' if e.get(LANG) else ""
        if name in ("pb", "cb", "milestone", "fw"):
            cls = {"pb": "page-marker", "cb": "column-marker", "milestone": "column-marker", "fw": "material-marker"}[name]
            label = {"pb": "p. ", "cb": "col. ", "milestone": "", "fw": ""}[name]
            return f'<span{ident} class="{cls}" aria-label="Repère de l’imprimé">{label}{esc(e.get("n", ""))}{value}</span>'
        if name == "lb":
            return f'<span{ident} class="line-break"></span>' if e.get("break") == "no" else f'<br{ident}>'
        if name == "note":
            marginal = e.get("place", "").startswith("margin")
            cls = "marginalia" if marginal else "note"
            label = "Manchette" if marginal else {"trad": "Traduction", "source": "Source"}.get(e.get("type"), "Note")
            label += " " + e.get("n", "")
            return f'<span{ident} class="{cls}"><button type="button" class="note-call" aria-expanded="false">{esc(label.strip())}</button><span class="note-content" hidden>{value}</span></span>'
        if name == "choice":
            chosen = next((c for c in e if tag(c) in ("abbr", "sic", "orig")), None)
            alternative = next((c for c in e if tag(c) in ("expan", "corr", "reg")), None)
            if chosen is not None:
                title = f' title="{esc(clean(alternative))}"' if alternative is not None else ""
                value = self.render(chosen)
                # L’alternative reste inspectable, sans être ajoutée à la lecture.
                if alternative is not None and alternative.get(XID):
                    value += f'<span id="{esc(alternative.get(XID))}"></span>'
                return f'<abbr{ident}{title}>{value}</abbr>'
        if name == "gap":
            return f'<span{ident} class="uncertainty" title="Lacune : {esc(e.get("reason", "non précisée"))}">[…]</span>'
        if name == "ref":
            target = e.get("target", "")
            if target.startswith("#"):
                return f'<a{ident}{lang} href="{esc(target)}" data-tei-ref="{esc(target[1:])}">{value}</a>'
            if urlsplit(target).scheme in ("http", "https"):
                return f'<a{ident}{lang} href="{esc(target)}" rel="noreferrer">{value}</a>'
        cls = {"quote": "quotation", "title": "italic", "foreign": "italic", "emph": "italic",
               "sic": "uncertainty", "unclear": "uncertainty", "corr": "correction", "lg": "verse",
               "l": "verse-line", "supplied": "uncertainty", "del": "deleted"}.get(name, "")
        if name == "hi":
            cls = {"smallcaps": "smallcaps", "caps": "caps", "sup": "superscript",
                   "italic": "italic", "it": "italic"}.get(e.get("rend"), "")
        if e.get(LANG) == "grc":
            cls += " greek"
        if e.get("rend") == "indent":
            cls += " indent"
        return f'<span{ident}{lang} class="{cls.strip()}">{value}</span>'


def read_corpus(project):
    reader = Reader(project)
    if not project.master.is_file():
        reader.issue("error", project.master, "Fichier maître introuvable.")
        return reader.corpus
    root = reader.parse(project.master)
    if root is None:
        return reader.corpus
    reader.inspect(root)
    reader.corpus.metadata = metadata(root)
    roots = [root] if root.tag == T + "TEI" else list(root.iter(T + "TEI"))
    if root.tag not in (T + "TEI", T + "teiCorpus"):
        reader.issue("error", project.master, "Racine TEI ou teiCorpus attendue.", root)
    routes = set()
    for r in roots:
        unit = reader.unit(r)
        if unit:
            if unit.route in routes:
                reader.issue("error", unit.file, f"URL dupliquée : {unit.route}")
            routes.add(unit.route)
            reader.corpus.units.append(unit)
            for key, value in unit.metadata.items():
                if not reader.corpus.metadata.get(key):
                    reader.corpus.metadata[key] = value
    return reader.corpus
