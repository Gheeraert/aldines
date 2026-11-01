from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lxml import html
import pytest

from aldines.augustinus import read_corpus
from aldines.build import build, publication_metadata
from aldines.config import load_project, ProjectError
from conftest import tei


def source_hashes(project):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in project.directory.glob("*.xml")}


def test_complete_reading_controls_on_every_page_and_editor_alignment(project):
    project.data['appearance']['text_align'] = 'justify'
    result = build(project)
    for path in result.output.rglob('index.html'):
        doc = html.parse(str(path))
        assert doc.xpath('//label[select[@id="reading-mode"]]')
        assert doc.xpath('//select[@id="reading-mode"]/option/@value') == ['bilingual', 'latin', 'french']
        assert len(doc.xpath('//fieldset[@id="display-options"]//input[@data-option]')) == 6
        assert doc.xpath('//button[@id="reader-options"]/text()') == ['Options d’affichage']
        assert not doc.xpath('//select[@id="text-alignment"]')
        assert doc.xpath('//body/@data-alignment') == ['justify']


def test_project_roundtrip_and_metadata_priority(project):
    loaded = load_project(project.path)
    assert loaded.master == project.directory / "master.xml"
    corpus = read_corpus(loaded)
    assert publication_metadata(loaded, corpus)["author"] == "Auteur TEI"
    loaded.data["corpus"]["author"] = "Auteur JSON"
    loaded.save()
    assert publication_metadata(load_project(loaded.path), corpus)["author"] == "Auteur JSON"


@pytest.mark.parametrize("group,key,value", [("appearance", "font_size", "grand"),
    ("appearance", "font_size", True), ("reading", "show_notes", "false"),
    ("reading", "default_mode", "invalid"), ("publication", "base_path", "/../"),
    ("corpus", "languages", "la"), ("sources", "selection", "tout"),
    ("appearance", "text_align", "invalid")])
def test_clear_json_errors(project, group, key, value):
    data = deepcopy(project.data)
    data[group][key] = value
    project.path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProjectError, match=key):
        load_project(project.path)


def test_invalid_json(project):
    project.path.write_text("{bad", encoding="utf-8")
    with pytest.raises(ProjectError, match="Impossible de lire"):
        load_project(project.path)


def test_master_order_alignment_notes_and_reference_output(project):
    corpus = read_corpus(project)
    assert not corpus.issues
    assert [u.id for u in corpus.units] == ["t1.l01.s02", "t1.l01.s01"]
    u = corpus.units[1]
    assert u.sentences == u.translated == 3
    rows = [r for r in u.rows if r.kind == "sentence"]
    assert rows[0].latin_text == "Pater & λόγος æterna."
    assert rows[0].french_text == "Père et parole éternelle."
    assert rows[1].latin_text == "q; ui[…]"
    # Référence de transformation indépendante, sur un passage synthétique public.
    expected = ('<span id="t1.l01.s01.la.s2" class=""><abbr title="que"><span class="">q;</span></abbr> '
                '<span class="uncertainty">u</span><span class="uncertainty">i</span>'
                '<span class="uncertainty" title="Lacune : illegible">[…]</span></span>')
    assert rows[1].latin == expected
    assert "Manchette ancienne." in rows[0].latin and 'class="marginalia"' in rows[0].latin
    assert "Sens de la traduction." in rows[0].french and "Source citée." in rows[0].french
    assert any(r.kind == "heading" and "TITRE FRANÇAIS" in r.french for r in u.rows)
    assert rows[-1].french_text == "Fin."


def test_missing_and_nested_includes(project):
    master = project.master.read_text(encoding="utf-8")
    project.master.write_text(master.replace('href="a.xml"', 'href="missing.xml"'), encoding="utf-8")
    c = read_corpus(project)
    assert len(c.units) == 1 and not c.errors
    assert "Inclusion absente" in str(c.issues[0])
    wrapper = project.directory / "nested.xml"
    wrapper.write_text(master, encoding="utf-8")
    project.master.write_text(master.replace('href="b.xml"', 'href="nested.xml"').replace('<xi:include href="a.xml"/>', ''), encoding="utf-8")
    assert len(read_corpus(project).units) == 2
    wrapper.write_text(wrapper.read_text(encoding="utf-8").replace('href="b.xml"', 'href="master.xml"'), encoding="utf-8")
    assert any("Cycle" in str(i) for i in read_corpus(project).errors)


@pytest.mark.parametrize("href", ["../outside.xml", "https://example.org/file.xml", "file:///etc/passwd"])
def test_resources_confined_to_sources(project, href):
    project.master.write_text(project.master.read_text(encoding="utf-8").replace('href="a.xml"', f'href="{href}"'), encoding="utf-8")
    assert read_corpus(project).errors


def test_no_entities_or_malformed_xml(project):
    f = project.directory / "a.xml"
    f.write_text('<!DOCTYPE TEI [<!ENTITY x SYSTEM "file:///etc/passwd">]>' + tei().replace("Finis.", "&x;"), encoding="utf-8")
    assert any("DOCTYPE" in str(i) for i in read_corpus(project).errors)
    f.write_text("<TEI><broken>", encoding="utf-8")
    assert any("XML" in str(i) for i in read_corpus(project).errors)


def test_duplicates_alignment_and_invalid_references(project):
    f = project.directory / "a.xml"
    f.write_text(tei().replace('xml:id="t1.l01.s01.la.s2"', 'xml:id="t1.l01.s01.la.s1"'), encoding="utf-8")
    assert any("dupliqué" in str(i) for i in read_corpus(project).errors)
    f.write_text(tei().replace('corresp="#t1.l01.s01.la.s2"', 'corresp="#inconnu"'), encoding="utf-8")
    corpus = read_corpus(project)
    assert not corpus.errors
    assert any("Référence interne inconnue" in str(i) for i in corpus.issues)
    assert any("sans traduction" in str(i) for i in corpus.issues)
    assert any("sans correspondance" in str(i) for i in corpus.issues)
    assert any("Abréviation et incertitude" in r.french for r in corpus.units[1].rows)


def test_unknown_markup_preserves_safe_content(project):
    f = project.directory / "a.xml"
    f.write_text(tei(extra='<nouveau>&lt;script&gt; &amp; texte</nouveau><ref target="javascript:alert(1)">lien</ref>'), encoding="utf-8")
    c = read_corpus(project)
    assert not c.errors and any("nouveau" in str(i) for i in c.issues)
    result = build(project)
    page = (result.output / "t1/l1/s01/index.html").read_text(encoding="utf-8")
    assert "&lt;script&gt; &amp; texte" in page and "javascript:" not in page


def assert_site_links(output):
    docs = {f.resolve(): html.parse(str(f)) for f in output.rglob("*.html")}
    for f, doc in docs.items():
        ids = doc.xpath("//@id")
        assert not [k for k, v in Counter(ids).items() if v > 1], f
        for url in doc.xpath("//a/@href | //script/@src | //link/@href"):
            parts = urlsplit(url)
            if parts.scheme or parts.netloc:
                continue
            target = (f.parent / unquote(parts.path)).resolve() if parts.path else f
            if target.is_dir():
                target /= "index.html"
            assert target.exists(), (f, url)
            if parts.fragment:
                assert unquote(parts.fragment) in docs[target].xpath("//@id"), (f, url)


def test_static_build_navigation_subdirectory_and_no_source_writes(project):
    before = source_hashes(project)
    project.data["publication"]["base_path"] = "/augustinus/"
    result = build(project)
    assert result.count == 2
    assert_site_links(result.output)
    page = html.parse(str(result.output / "t1/l1/s01/index.html"))
    assert page.xpath('//a[@rel="prev"]/@href') == ["../s02/", "../s02/"]
    assert not page.xpath('//a[@rel="next"]')
    assert before == source_hashes(project)
    assert len(list(result.output.rglob("*.xml"))) == 2
    for route, filename in [("t1/l1/s01", "a.xml"), ("t1/l1/s02", "b.xml")]:
        copied = result.output / route / filename
        assert copied.read_bytes() == (project.directory / filename).read_bytes()
        unit_page = html.parse(str(result.output / route / "index.html"))
        assert unit_page.xpath('//a[@class="tei-download"]/@href') == [filename]
        assert unit_page.xpath('//a[@class="tei-download"]/@download') == [filename]
    assert not list(result.output.rglob("a-verifier.md"))
    assert (result.output / ".nojekyll").exists()
    # Une nouvelle sélection élimine les anciennes pages, sans toucher aux sources.
    project.data["sources"]["selection"] = ["t1.l01.s01"]
    assert build(project).count == 1
    assert not (result.output / "t1/l1/s02").exists()
    assert len(list(result.output.rglob("*.xml"))) == 1


def test_cross_unit_refs_and_unpublished_refs(project):
    f = project.directory / "a.xml"
    f.write_text(tei(extra='<ref target="#t1.l01.s02.la.s1">autre unité</ref><ref target="#absent">absent</ref>'), encoding="utf-8")
    result = build(project)
    assert_site_links(result.output)
    doc = html.parse(str(result.output / "t1/l1/s01/index.html"))
    assert doc.xpath('//a[text()="autre unité"]/@href') == ["../s02/#t1.l01.s02.la.s1"]
    assert doc.xpath('//a[text()="absent"]/@aria-disabled') == ["true"]


def test_failures_preserve_previous_site_and_protect_other_directories(project):
    build(project)
    previous = (project.output / "index.html").read_bytes()
    (project.directory / "a.xml").write_text("<broken>", encoding="utf-8")
    with pytest.raises(ProjectError):
        build(project)
    assert (project.output / "index.html").read_bytes() == previous
    for output in [project.directory, project.directory.parent, project.path.parent / "foreign"]:
        output.mkdir(exist_ok=True)
        if output.name == "foreign":
            (output / "precieux.txt").write_text("conserver", encoding="utf-8")
        with pytest.raises(ProjectError):
            build(project, output=output)


def test_empty_or_unknown_selection_is_explicit(project):
    project.data["sources"]["selection"] = []
    with pytest.raises(ProjectError, match="Aucune unité"):
        build(project)
    project.data["sources"]["selection"] = ["absent"]
    with pytest.raises(ProjectError, match="introuvables"):
        build(project)


def test_cannot_save_project_into_source_directory(project):
    project.data["sources"]["directory"] = str(project.directory)
    project.path = project.directory / "aldines.json"
    with pytest.raises(ProjectError, match="hors du dossier TEI"):
        project.save()
