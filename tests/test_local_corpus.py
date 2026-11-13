"""Tests privés facultatifs : aucun texte inédit n’est inclus dans le dépôt."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from lxml import etree, html
import pytest

from aldines.augustinus import read_corpus, T, NS, XID
from aldines.build import build
from aldines.config import load_project
from test_engine import assert_site_links

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "aldines.local.json"
if not LOCAL.is_file():
    LOCAL = ROOT / ".local" / "aldines.json"
pytestmark = pytest.mark.skipif(not LOCAL.exists(), reason="Copie scientifique privée absente")


def expected_text(element):
    """Extraction de contrôle indépendante du rendu : copie, retrait des notes/repères."""
    from copy import deepcopy
    element = deepcopy(element)
    for choice in element.findall(".//t:choice", NS):
        for alternative in list(choice):
            if alternative.tag in (T + "expan", T + "corr", T + "reg"):
                choice.remove(alternative)
    for e in element.xpath('.//t:note | .//t:pb | .//t:cb | .//t:milestone | .//t:fw', namespaces=NS):
        if e.getparent() is None:
            continue
        tail = e.tail or ""
        previous = e.getprevious()
        if previous is not None:
            previous.tail = (previous.tail or "") + tail
        else:
            e.getparent().text = (e.getparent().text or "") + tail
        e.getparent().remove(e)
    for gap in element.findall(".//t:gap", NS):
        gap.text = "[…]"
    return " ".join("".join(element.itertext()).split())


def test_all_real_units_and_sentence_alignment():
    project = load_project(LOCAL)
    before = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in project.directory.rglob("*.xml")}
    corpus = read_corpus(project)
    assert not corpus.errors
    assert corpus.units
    if project.master.name == "aug.xml":
        assert {1, 2, 3} <= {u.tome for u in corpus.units}
    for u in corpus.units:
        doc = etree.parse(str(u.file))
        la = doc.findall('.//t:div[@type="edition"]//t:s', NS)
        latin_ids = {s.get(XID) for s in la}
        fr = defaultdict(list)
        orphans = []
        for sentence in doc.findall('.//t:div[@type="translation"]//t:s', NS):
            targets = [ref[1:] for ref in sentence.get("corresp", "").split()
                       if ref.startswith("#") and ref[1:] in latin_ids]
            if targets:
                fr[targets[0]].append(sentence)
            else:
                orphans.append(sentence)
        rows = [r for r in u.rows if r.kind == "sentence"]
        assert len(rows) == len(la) + len(orphans)
        for sentence, row in zip(la, rows):
            if sentence.get(XID):
                assert row.anchor == sentence.get(XID)
            assert row.latin_text == expected_text(sentence)
            assert row.french_text == " ".join(map(expected_text, fr[row.anchor]))
            # Contrôler le texte extrait du HTML réellement produit, pas seulement l’index.
            if not fr[row.anchor]:
                assert row.french == '<em class="missing">Traduction à venir</em>'
            for markup, expected in [(row.latin, row.latin_text), (row.french, row.french_text)]:
                dom = html.fragment_fromstring(markup, create_parent="div")
                for extra in dom.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," note ") or contains(concat(" ",normalize-space(@class)," ")," marginalia ") or contains(@class,"-marker") or @class="missing"]'):
                    extra.drop_tree()
                assert " ".join(dom.text_content().split()) == expected
        assert [r.french_text for r in rows[len(la):]] == list(map(expected_text, orphans))
        # Chaque note réelle doit être présente textuellement dans le rendu.
        output_text = " ".join(html.fragment_fromstring(
            "".join(r.latin + r.french for r in u.rows), create_parent="div").text_content().split())
        for note in doc.findall('.//t:text//t:note', NS):
            expected = " ".join("".join(note.itertext()).split())
            # Les développements d’abréviations restent en infobulle dans une note.
            if note.find('.//t:choice', NS) is None and note.find('.//t:gap', NS) is None:
                assert expected in output_text
    assert before == {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in before}


def test_full_local_site(tmp_path):
    project = load_project(LOCAL)
    result = build(project, output=tmp_path / "publication")
    selection = project.data["sources"]["selection"]
    assert result.count == sum(selection is None or u.id in selection for u in result.corpus.units)
    assert_site_links(result.output)


def test_private_frozen_reference():
    reference = ROOT / ".local" / "reference-golden.json"
    if not reference.exists():
        pytest.skip("Référence privée non installée")
    corpus = read_corpus(load_project(LOCAL))
    rows = {r.anchor: r for u in corpus.units for r in u.rows}
    for passage in json.loads(reference.read_text(encoding="utf-8")):
        row = rows[passage["anchor"]]
        for key in ("latin_text", "french_text", "latin", "french"):
            if key in passage:
                assert getattr(row, key) == passage[key]
