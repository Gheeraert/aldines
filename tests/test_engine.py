from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit

from lxml import etree, html
import pytest

from aldines.augustinus import read_corpus
from aldines.build import build, publication_metadata, page
from aldines.config import load_project, ProjectError
from conftest import tei


def source_hashes(project):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in project.directory.glob("*.xml")}


@pytest.mark.parametrize('subtitle', ['Édition bilingue <latin & français>', ''])
def test_header_uses_project_subtitle_without_added_laboratory(project, subtitle):
    project.data['corpus']['subtitle'] = subtitle
    project.data['corpus']['laboratory'] = ''
    meta = publication_metadata(project, read_corpus(project))
    doc = html.fromstring(page(project, meta, 'Accueil', ''))
    assert doc.xpath('string(//header//small)') == subtitle
    assert 'CEREdI' not in doc.xpath('string(//header)')


@pytest.mark.parametrize("author", ["Cornelius <Jansenius>", ""])
def test_current_title_in_editorial_and_reading_headers(project, author):
    project.data["corpus"].update(title="Augustinus & alii", author=author)
    if not author:
        for path in project.directory.glob("[ab].xml"):
            source = path.read_text(encoding="utf-8")
            path.write_text(source.replace("<author>Auteur TEI</author>", ""), encoding="utf-8")
    output = build(project).output
    for route in ("", "ressources", "projet", "contents", "search", "t1/l1/s01"):
        document = html.parse(str(output / route / "index.html"))
        brand = document.xpath('//header/a[@class="brand"]/span')[0]
        assert brand.xpath('./cite/text()') == ["Augustinus & alii"]
        assert brand.xpath('./text()') == ([f"{author}, "] if author else [])


def test_complete_reading_controls_and_editor_alignment_on_edition_pages(project):
    project.data['appearance']['text_align'] = 'justify'
    result = build(project)
    editorial_pages = [result.output / route / 'index.html' for route in ('', 'ressources', 'projet')]
    for path in set(result.output.rglob('index.html')) - set(editorial_pages):
        doc = html.parse(str(path))
        assert doc.xpath('//label[select[@id="reading-mode"]]')
        assert doc.xpath('//select[@id="reading-mode"]/option/@value') == ['bilingual', 'latin', 'french']
        assert len(doc.xpath('//fieldset[@id="display-options"]//input[@data-option]')) == 6
        assert doc.xpath('//button[@id="reader-options"]/text()') == ['Options d’affichage']
        assert not doc.xpath('//select[@id="text-alignment"]')
        assert doc.xpath('//body/@data-alignment') == ['justify']
    for path in editorial_pages:
        doc = html.parse(str(path))
        assert not doc.xpath('//*[@id="reading-mode"] | //script')
        assert doc.xpath('//link[contains(@href, "editorial.css")]')
    home = html.parse(str(editorial_pages[0]))
    assert home.xpath('//a[@class="read-button"]/@href') == ['contents/']
    assert not html.parse(str(editorial_pages[2])).xpath('//main//h1')
    intro = home.xpath('//section[@class="intro"]//div[@class="intro-copy"]')[0]
    assert intro.xpath('./p[@class="author"]/following-sibling::*[1][self::h1[@id="titre"]]')


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
    ("publication", "origin", "https://example.org/augustinus/"),
    ("publication", "origin", "https://example.org:99999"),
    ("publication", "origin", "https://example.org#fragment"),
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
        for url in doc.xpath("//a/@href | //script/@src | //link/@href | //img/@src"):
            parts = urlsplit(url)
            if parts.scheme or parts.netloc:
                continue
            target = (f.parent / unquote(parts.path)).resolve() if parts.path else f
            if target.is_dir():
                target /= "index.html"
            assert target.exists(), (f, url)
            if parts.fragment:
                assert unquote(parts.fragment) in docs[target].xpath("//@id"), (f, url)


@pytest.mark.skipif(not shutil.which("pandoc"), reason="Pandoc est facultatif")
def test_publish_markdown_resources_and_separate_credits(project):
    resource = project.path.parent / "Étude.md"
    resource.write_text("""---
title: Étude sur la grâce
---

# Grâce et liberté

## Introduction

*italique*, **gras**, [souligné]{.underline}, [site](https://example.org) et note[^a].

[^a]: Note éditoriale.

1. Premier
2. Second

- Une puce

[Lien dangereux](javascript:alert%281%29)
""", encoding="utf-8")
    second = resource.parent / "autre" / resource.name
    second.parent.mkdir()
    second.write_text("Autre document. " * 30, encoding="utf-8")
    credits = resource.parent / "credits.markdown"
    credits.write_bytes("\ufeff# Équipe\r\n\r\n## Contributions\r\n\r\nCrédits propres au **projet**.\r\n".encode("utf-8"))
    project.data["editorial"].update(resources=[resource.name, str(second)], credits=credits.name)
    project.data["corpus"]["license"] = "A. Exemple · CC-BY"
    project.data["publication"]["origin"] = "https://example.org"
    project.save()
    result = build(load_project(project.path))
    assert_site_links(result.output)
    for page_path in result.output.rglob("index.html"):
        published = html.parse(str(page_path))
        assert not published.xpath('//header//span[@class="printer-mark"]'), page_path
        assert not published.xpath('//footer//nav'), page_path
        assert published.xpath("string(//footer/p)") == "A. Exemple · CC-BY · Réalisé avec Studio Aldines", page_path
        assert published.xpath('//footer//a[text()="Studio Aldines"]/@href') == [
            "https://github.com/gheeraert/aldines"
        ], page_path
    index = html.parse(str(result.output / "ressources/index.html"))
    section = index.xpath('//main/section[@aria-labelledby="resources-title"]')[0]
    assert section.xpath('./h2/text()') == ["Études et ressources"]
    assert not section.xpath('.//h1 | ./section')
    assert section.xpath('./article/h3/text()') == ["Étude sur la grâce", "Étude"]
    assert section.xpath('./article/a/@href') == ["document-etude/", "document-etude-2/"]
    assert [label.strip() for label in section.xpath('./article/a/text()')] == ["Lire la suite"] * 2
    first_excerpt, second_excerpt = section.xpath('./article/p/text()')
    assert first_excerpt == "italique, gras, souligné, site et note."
    assert second_excerpt.startswith("Autre document.") and second_excerpt.endswith("…")
    assert len(second_excerpt) <= 281
    route = result.output / "ressources/document-etude"
    doc = html.parse(str(route / "index.html"))
    resource_url = "https://example.org/ressources/document-etude/"
    assert doc.xpath('//head/link[@rel="canonical"]/@href') == [resource_url]
    assert doc.xpath('//head/meta[@name="description"]/@content') == [first_excerpt]
    assert resource_url in sitemap_locations(result.output)
    assert doc.xpath("//h1/text()") == ["Grâce et liberté"]
    assert doc.xpath("//h2[@id='md-introduction']/text()") == ["Introduction"]
    assert len(doc.xpath("//em[text()='italique'] | //strong[text()='gras'] | //u[text()='souligné']")) == 3
    assert doc.xpath("//ol/li[contains(., 'Premier')]") and doc.xpath("//ul/li[contains(., 'Une puce')]")
    assert doc.xpath('//a[@role="doc-noteref"]') and doc.xpath('//a[@role="doc-backlink"]')
    assert doc.xpath('//a[@href="https://example.org"]')
    assert not doc.xpath('//a[starts-with(@href, "javascript:")]')
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    xml = etree.parse(str(route / "document.xml"))
    assert xml.xpath("string(//tei:titleStmt/tei:title)", namespaces=ns) == "Étude sur la grâce"
    fallback_route = result.output / "ressources/document-etude-2"
    assert not html.parse(str(fallback_route / "index.html")).xpath("//h1")
    fallback = etree.parse(str(fallback_route / "document.xml"))
    assert fallback.xpath("string(//tei:titleStmt/tei:title)", namespaces=ns) == "Étude"
    assert xml.xpath("//tei:note", namespaces=ns)
    assert xml.xpath("//tei:hi[@rendition='simple:underline']", namespaces=ns)
    assert xml.xpath("//tei:publicationStmt/tei:p", namespaces=ns)
    credits_page = html.parse(str(result.output / "projet/index.html"))
    assert credits_page.xpath("//h1/text()") == ["Équipe"]
    assert credits_page.xpath("//h2[@id='md-contributions']/text()") == ["Contributions"]
    assert "Crédits propres" in credits_page.xpath("string(//main)")
    assert (result.output / "projet/document.xml").is_file()
    assert (result.output / "projet" / credits.name).read_bytes() == credits.read_bytes()
    assert (route / resource.name).read_bytes() == resource.read_bytes()
    assert (result.output / "ressources/document-etude-2" / second.name).read_bytes() == second.read_bytes()
    assert json.loads((result.output / "aldines.json").read_text(encoding="utf-8")) == project.data
    notice = (result.output / "LISEZ-MOI.txt").read_text(encoding="utf-8")
    assert "Studio Aldines" in notice and "Pandoc" in notice
    assert "Crédits propres" not in (result.output / "ressources/index.html").read_text(encoding="utf-8")
    project.data["editorial"]["resources"] = ["absent.md"]
    with pytest.raises(ProjectError, match="absent.md"):
        build(project)
    assert (route / "document.xml").is_file()


def sitemap_locations(output):
    sitemap = etree.parse(str(output / "sitemap.xml"))
    assert sitemap.getroot().tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset"
    return sitemap.xpath("/s:urlset/s:url/s:loc/text()", namespaces={"s": "http://www.sitemaps.org/schemas/sitemap/0.9"})


@pytest.mark.parametrize("base_path", ["/", "/augustinus/"])
def test_sitemap_and_canonicals_follow_the_published_selection(project, base_path):
    project.data["publication"].update(origin="https://example.org/", base_path=base_path)
    project.data["sources"]["selection"] = ["t1.l01.s01"]
    project.data["editorial"]["home_intro"] = 'Le texte latin & sa traduction "française".'
    result = build(project)
    public_base = "https://example.org" + base_path
    routes = ["", "ressources/", "projet/", "contents/", "t1/l1/s01/"]
    assert sitemap_locations(result.output) == [public_base + route for route in routes]
    for route in routes:
        page = html.parse(str(result.output / route / "index.html"))
        assert page.xpath('//head/link[@rel="canonical"]/@href') == [public_base + route]
        assert not page.xpath('//head/meta[@name="robots"]')
    home = html.parse(str(result.output / "index.html"))
    assert home.xpath('//head/meta[@name="description"]/@content') == [project.data["editorial"]["home_intro"]]
    unit = html.parse(str(result.output / "t1/l1/s01/index.html"))
    assert "Section 1 · Livre 1 · Tome 1" in unit.xpath("string(//head/title)")
    search = html.parse(str(result.output / "search/index.html"))
    assert search.xpath('//head/meta[@name="robots"]/@content') == ["noindex"]
    assert not search.xpath('//head/link[@rel="canonical"]')
    robots = result.output / "robots.txt"
    if base_path == "/":
        assert f"Sitemap: {public_base}sitemap.xml" in robots.read_text(encoding="utf-8")
    else:
        assert not robots.exists()

    preview = build(project, only="t1.l01.s01", output=project.path.parent / "preview").output
    assert not (preview / "sitemap.xml").exists()
    assert not (preview / "robots.txt").exists()
    for path in preview.rglob("index.html"):
        page = html.parse(str(path))
        assert page.xpath('//head/meta[@name="robots"]/@content') == ["noindex"]
        assert not page.xpath('//head/link[@rel="canonical"]')


def test_static_build_navigation_subdirectory_and_no_source_writes(project):
    before = source_hashes(project)
    project.data["publication"]["base_path"] = "/augustinus/"
    result = build(project)
    assert result.count == 2
    assert_site_links(result.output)
    assert not (result.output / "sitemap.xml").exists()
    home = html.parse(str(result.output / "index.html"))
    assert not home.xpath('//head/link[@rel="canonical"] | //head/meta[@name="robots"]')
    contents = html.parse(str(result.output / "contents/index.html"))
    assert not contents.xpath('//a[text()="Consulter l’édition numérisée"]')
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


def test_scan_link_rejects_non_web_urls(project):
    project.data["corpus"]["source_edition_url"] = "javascript:alert(1)"
    with pytest.raises(ProjectError, match="Lien vers la numérisation"):
        build(project)


def test_scientific_notice_renders_tei_web_references(project):
    source = project.directory / "a.xml"
    source.write_text(tei().replace("Imprimé de test", '''Édition &lt;ancienne&gt; (
        <ref target="https://example.org/scan.pdf?id=12&amp;view=full#page=35">Voir la numérisation</ref> ;
        fichier <ref>scan.pdf</ref> ; <ref target="javascript:alert(1)">référence écartée</ref>).'''),
        encoding="utf-8")
    result = build(project)
    page = html.parse(str(result.output / "t1/l1/s01/index.html"))
    notice = page.xpath('//details[@class="source-metadata"]/p[2]')[0]
    assert notice.xpath('./a/@href') == ["https://example.org/scan.pdf?id=12&view=full#page=35"]
    assert notice.xpath('./a/text()') == ["Voir la numérisation"]
    assert notice.text_content() == "Édition <ancienne> ( Voir la numérisation ; fichier scan.pdf ; référence écartée)."


def test_cross_unit_refs_and_unpublished_refs(project):
    f = project.directory / "a.xml"
    f.write_text(tei(extra='<ref target="#t1.l01.s02.la.s1">autre unité</ref><ref target="#absent">absent</ref>'), encoding="utf-8")
    result = build(project)
    assert_site_links(result.output)
    doc = html.parse(str(result.output / "t1/l1/s01/index.html"))
    assert doc.xpath('//a[text()="autre unité"]/@href') == ["../s02/#t1.l01.s02.la.s1"]
    assert doc.xpath('//a[text()="absent"]/@aria-disabled') == ["true"]


def test_publish_nested_masters_for_three_volumes(project):
    def master(path, names):
        includes = "".join(f'<xi:include href="{name}"/>' for name in names)
        path.write_text(f'''<teiCorpus xmlns="http://www.tei-c.org/ns/1.0"
                         xmlns:xi="http://www.w3.org/2001/XInclude">{includes}</teiCorpus>''', encoding="utf-8")

    t2 = project.directory / "t2"
    t2.mkdir()
    parts = ["lp", "ni", "nl.l01", "nl.l02", "nl.l03", "nl.l04", "np.l01", "np.l02", "np.l03"]
    files = []
    for part in parts:
        uid = f"t2.{part}.c01"
        filename = f"aug-{uid.replace('.', '-')}.xml"
        content = tei().replace("t1.l01.s01", uid)
        if part == "lp":
            filename = "aug-t2-l09-c99.xml"  # L’identifiant TEI prime sur le nom.
        elif part == "np.l03":
            content = content.replace(f'xml:id="{uid}.la"', 'xml:id="edition-locale"')
        (t2 / filename).write_text(content, encoding="utf-8")
        files.append(filename)
    master(t2 / "aug-t2.xml", files)
    t3 = project.directory / "t3"
    t3.mkdir()
    romans = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
    chapters = ["gc.l01.c00", "gc.l01.c01", *(f"gc.l{book:02}.c01" for book in range(2, 10)),
                "gc.l10.c19", "pa.c00"]
    files = []
    for chapter in chapters:
        uid = f"t3.{chapter}"
        filename = f"aug-{uid.replace('.', '-')}.xml"
        content = tei(french=chapter != "gc.l01.c01").replace("t1.l01.s01", uid)
        if chapter == "gc.l01.c00":
            content = content.replace("Finis.", "medicinalis")
        elif chapter == "pa.c00":
            content = content.replace(f'xml:id="{uid}.la"', 'xml:id="edition-locale-t3"')
        (t3 / filename).write_text(content, encoding="utf-8")
        files.append(filename)
    master(t3 / "aug-t3.xml", [*files, "a-venir.xml"])
    master(project.directory / "aug.xml", ["master.xml", "t2/aug-t2.xml", "t3/aug-t3.xml"])
    project.data["sources"]["master"] = "tei/aug.xml"

    result = build(project)
    assert_site_links(result.output)
    units = result.corpus.units
    t3_routes = ["t3/l1/c00/", *(f"t3/l{book}/c01/" for book in range(1, 10)),
                 "t3/l10/c19/", "t3/l11/c00/"]
    assert [unit.route for unit in units] == ["t1/l1/s02/", "t1/l1/s01/",
                                               *(f"t2/l{book}/c01/" for book in range(1, 10)),
                                               *t3_routes]
    assert [unit.id for unit in units if unit.tome == 2] == [f"t2.l{book:02}.c01" for book in range(1, 10)]
    assert [unit.id for unit in units if unit.tome == 3] == [
        "t3.l01.c00", *(f"t3.l{book:02}.c01" for book in range(1, 10)), "t3.l10.c19", "t3.l11.c00",
    ]
    assert any(issue.file == "a-venir.xml" and issue.level == "warning" for issue in result.corpus.issues)
    contents = html.parse(str(result.output / "contents/index.html"))
    assert contents.xpath('//h2/text()') == ["Tome 1", "Tome 2", "Tome 3"]
    assert contents.xpath('//h3/text()') == [
        "Livre 1", "Livre introductif", "De l'état de nature innocente",
        *(f"De l'état de nature déchue, livre {n}" for n in ("I", "II", "III", "IV")),
        *(f"De l'état de pure nature, livre {n}" for n in ("I", "II", "III")),
        *(f"De la grâce du Christ Sauveur, livre {n}" for n in romans),
        "Parallèle et balance de l’erreur des Marseillais",
    ]
    assert contents.xpath('//li[@data-tome="2" and @data-book="1"]/@data-book-label') == ["Livre introductif"]
    assert contents.xpath('//li[@data-tome="3" and @data-book="1"]/a/text()') == ["Préface", "Chapitre 1"]
    assert contents.xpath('//li[@data-tome="3" and @data-book="11"]/a/text()') == ["Préface"]
    t2_page = html.parse(str(result.output / "t2/l1/c01/index.html"))
    assert t2_page.xpath('//*[@id="t2.lp.c01.la.s1"]')
    assert "Livre introductif" in t2_page.xpath('string(//nav[@class="breadcrumb"])')
    assert "LIVRE INTRODUCTIF" in t2_page.xpath('string(//p[@class="eyebrow"])')
    assert "Livre introductif" in t2_page.xpath('string(//title)')
    last_t2 = html.parse(str(result.output / "t2/l9/c01/index.html"))
    assert last_t2.xpath('//a[@rel="next"]/@href') == ["../../../t3/l1/c00/"] * 2
    assert last_t2.xpath('//a[@rel="next"]/text()') == ["Préface →"] * 2
    search = (result.output / "assets/search-data.js").read_text(encoding="utf-8")
    assert '"book": 1, "book_label": "Livre introductif", "route": "t2/l1/c01/"' in search
    search_records = json.loads(search.removeprefix("window.ALDINES_SEARCH = ").removesuffix(";\n"))
    match, = (r for r in search_records if "medicinalis" in r["la"])
    assert (match["unit"], match["book_label"], match["route"]) == (
        "Préface", "De la grâce du Christ Sauveur, livre I", "t3/l1/c00/")
    preface = html.parse(str(result.output / "t3/l1/c00/index.html"))
    assert preface.xpath('string(//h1)') == "Préface"
    assert "Préface" in preface.xpath('string(//nav[@class="breadcrumb"])')
    assert preface.xpath('string(//title)').startswith("Préface · De la grâce du Christ Sauveur, livre I")
    t3_page = html.parse(str(result.output / "t3/l1/c01/index.html"))
    assert t3_page.xpath('//em[@class="missing"]/text()') == ["Traduction à venir"] * 3
    assert t3_page.xpath('//a[@rel="prev"]/text()') == ["← Préface"] * 2
    assert all((result.output / route / "index.html").is_file() for route in t3_routes)

    project.data["books"] = {"t2.lp": "Livre proémial", "t2.nl-l1": "Nature déchue — Livre 1",
                             **{f"t3.gc-l{book}": f"Grâce — Livre {n}" for book, n in enumerate(romans, 1)},
                             "t3.pa": "Parallèle et balance"}
    project.save()
    updated = build(load_project(project.path))
    relabelled = updated.corpus.units
    assert relabelled[2].book_label == "Livre proémial"
    assert relabelled[4].book_label == "Nature déchue — Livre 1"
    assert relabelled[-2].book_label == "Grâce — Livre X"
    assert relabelled[-1].book_label == "Parallèle et balance"
    assert [unit.route for unit in relabelled] == [unit.route for unit in units]
    assert html.parse(str(updated.output / "contents/index.html")).xpath('//h3/text()')[-1] == "Parallèle et balance"


@pytest.mark.parametrize("uid,reason", [
    ("t3.gc.c01", "exige un numéro de livre"),
    ("t3.pa.l01.c01", "ne comporte pas de livres"),
    ("t3.zz.c01", "code de partie inconnu"),
    ("t3.gc.l11.c01", "livre 11 hors table"),
])
@pytest.mark.parametrize("from_filename", [False, True])
def test_invalid_named_identity(project, uid, reason, from_filename):
    filename = f"aug-{uid.replace('.', '-')}.xml" if from_filename else "aug-t3-gc-l01-c01.xml"
    edition_id = "edition-locale" if from_filename else f"{uid}.la"
    (project.directory / filename).write_text(
        tei().replace('xml:id="t1.l01.s01.la"', f'xml:id="{edition_id}"'), encoding="utf-8")
    project.data["sources"]["master"] = f"tei/{filename}"
    error, = read_corpus(project).errors
    assert uid in error.message and reason in error.message
    with pytest.raises(ProjectError, match=reason):
        build(project)


def test_generated_anchor_yields_to_real_tei_id(project):
    preface = tei().replace("t1.l01.s01", "t3.gc.l01.c00").replace(
        "<head>TITRE ", '<head xml:id="t3.l01.c00.block2">TITRE ', 1)
    (project.directory / "a.xml").write_text(preface, encoding="utf-8")
    result = build(project)
    assert_site_links(result.output)
    page = html.parse(str(result.output / "t3/l1/c00/index.html"))
    assert page.xpath('//div[@data-anchor="t3.l01.c00.block2"]//*[@id="t3.l01.c00.block2"]')
    assert page.xpath('//*[@id="t3.l01.c00.block2.1"]/@class') == ["aligned-row block "]


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


def test_home_visual_is_configurable_and_source_is_protected(project):
    legacy = json.loads(project.path.read_text(encoding="utf-8"))
    legacy["editorial"] = {"resources": [], "credits": None}
    project.path.write_text(json.dumps(legacy), encoding="utf-8")
    project = load_project(project.path)
    build(project)
    default = html.parse(str(project.output / "index.html"))
    assert default.xpath('//figure/img/@src') == ["assets/frontispice-1641.webp"]
    assert "Paris, 1641" in default.xpath('string(//figcaption)')
    assert default.xpath('string(//p[@class="summary"])').startswith("Le traité majeur")
    assert default.xpath('string(//section[@aria-labelledby="edition-title"]/p)').startswith("Le texte latin")
    assert default.xpath('string(//section[@aria-labelledby="resources-title"]/p)').startswith("Présentation de l’œuvre")

    source = project.path.parent / "Image & accueil.WEBP"
    shutil.copyfile(project.output / "assets/frontispice-1641.webp", source)
    project.data["editorial"].update(home_image=source.name, home_caption="Source <BnF>\nDomaine public",
                                     home_alt='Reproduction "ancienne"', home_intro="Un texte <latin>\nEt sa traduction",
                                     home_edition=" ", home_resources="Articles & bibliographie")
    project.save()
    build(load_project(project.path))
    assert_site_links(project.output)
    home_path = project.output / "index.html"
    doc = html.parse(str(home_path))
    assert doc.xpath('//figure/img/@src') == ["assets/accueil.webp"]
    assert doc.xpath('//figure/img/@alt') == ['Reproduction "ancienne"']
    assert doc.xpath('//figcaption/text()') == ["Source <BnF>", "Domaine public"]
    assert doc.xpath('//p[@class="summary"]/text()') == ["Un texte <latin>", "Et sa traduction"]
    assert doc.xpath('//p[@class="summary"]/br')
    assert not doc.xpath('//section[@aria-labelledby="edition-title"]/p')
    assert doc.xpath('//section[@aria-labelledby="edition-title"]/a/@href') == ["contents/"]
    assert doc.xpath('//section[@aria-labelledby="resources-title"]/p/text()') == ["Articles & bibliographie"]
    copy = project.output / "assets/accueil.webp"
    assert copy.read_bytes() == source.read_bytes()

    previous = home_path.read_bytes()
    for image, message in [(str(copy), "hors du dossier de sortie"), ("absente.webp", "Impossible de copier")]:
        project.data["editorial"]["home_image"] = image
        with pytest.raises(ProjectError, match=message):
            build(project)
        assert home_path.read_bytes() == previous
        assert copy.read_bytes() == source.read_bytes()


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
