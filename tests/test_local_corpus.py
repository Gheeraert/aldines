"""Tests privés facultatifs : aucun texte inédit n’est inclus dans le dépôt."""
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
    before = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in project.directory.glob("*.xml")}
    corpus = read_corpus(project)
    assert not corpus.issues
    assert len(corpus.units) == 97
    assert sum(u.sentences for u in corpus.units) == 1644
    for u in corpus.units:
        doc = etree.parse(str(u.file))
        la = doc.findall('.//t:div[@type="edition"]//t:s', NS)
        fr = {s.get("corresp").lstrip("#"): s for s in doc.findall('.//t:div[@type="translation"]//t:s', NS)}
        rows = [r for r in u.rows if r.kind == "sentence"]
        assert len(rows) == len(la)
        for sentence, row in zip(la, rows):
            assert row.anchor == sentence.get(XID)
            assert row.latin_text == expected_text(sentence)
            assert row.french_text == expected_text(fr[row.anchor])
            # Contrôler le texte extrait du HTML réellement produit, pas seulement l’index.
            for markup, expected in [(row.latin, row.latin_text), (row.french, row.french_text)]:
                dom = html.fragment_fromstring(markup, create_parent="div")
                for extra in dom.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," note ") or contains(concat(" ",normalize-space(@class)," ")," marginalia ") or contains(@class,"-marker")]'):
                    extra.drop_tree()
                assert " ".join(dom.text_content().split()) == expected
        # Chaque note réelle doit être présente textuellement dans le rendu.
        for note in doc.findall('.//t:text//t:note', NS):
            expected = " ".join("".join(note.itertext()).split())
            # Les développements d’abréviations restent en infobulle dans une note.
            if note.find('.//t:choice', NS) is None and note.find('.//t:gap', NS) is None:
                output_text = " ".join(html.fragment_fromstring("".join(r.latin + r.french for r in u.rows), create_parent="div").text_content().split())
                assert expected in output_text
    assert before == {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in before}


def test_full_local_site():
    result = build(load_project(LOCAL))
    assert result.count == 97
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
