"""Conversion des documents éditoriaux, indépendante du corpus de lecture."""

from dataclasses import dataclass
import subprocess
from urllib.parse import urlsplit

from lxml import etree, html

from .config import ProjectError

TEI = "{http://www.tei-c.org/ns/1.0}"
MARKDOWN = "markdown-raw_html-raw_attribute-raw_tex"


@dataclass
class Document:
    title: str
    body: str
    tei: bytes
    source: bytes
    excerpt: str


def document_excerpt(content):
    blocks = content.xpath(".//*[self::p or self::li][not(ancestor::*[@role='doc-endnotes'])]")
    for block in blocks:
        parts = block.xpath(".//text()[not(ancestor::a[@role='doc-noteref'])]")
        excerpt = " ".join("".join(parts).split())
        if excerpt:
            if len(excerpt) > 280:
                excerpt = excerpt[:281].rsplit(" ", 1)[0][:280].rstrip() + "…"
            return excerpt
    return ""


def read_markdown(path):
    try:
        source = path.read_bytes()
        pandoc_input = source.decode("utf-8-sig").encode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProjectError(f"Impossible de lire le fichier Markdown {path.name} : {exc}") from exc

    def convert(target, *options):
        try:
            return subprocess.run(
                ["pandoc", "--sandbox", "--from", MARKDOWN, "--to", target, *options],
                input=pandoc_input, capture_output=True, check=True, timeout=60,
            ).stdout
        except FileNotFoundError as exc:
            raise ProjectError("Installez Pandoc et rendez-le accessible pour publier les fichiers Markdown.") from exc
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.decode("utf-8", errors="replace").strip()
            raise ProjectError(f"Échec de Pandoc pour {path.name} : {message}") from exc
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProjectError(f"Impossible de convertir {path.name} avec Pandoc : {exc}") from exc

    xml = convert("tei", "--standalone")
    try:
        tei = etree.fromstring(xml, parser=etree.XMLParser(resolve_entities=False))
        header = tei.find(f"{TEI}teiHeader/{TEI}fileDesc")
        title = header.find(f"{TEI}titleStmt/{TEI}title")
        publication = header.find(f"{TEI}publicationStmt")
    except (etree.XMLSyntaxError, AttributeError) as exc:
        raise ProjectError(f"Pandoc a produit un document TEI illisible pour {path.name}.") from exc
    if title is None or publication is None:
        raise ProjectError(f"Pandoc a produit un en-tête TEI incomplet pour {path.name}.")
    name = " ".join("".join(title.itertext()).split())
    if not name:
        title.text = name = path.stem
    if not len(publication):
        etree.SubElement(publication, f"{TEI}p").text = "Édition numérique de l’Augustinus."

    fragment = convert("html5", "--id-prefix=md-").decode("utf-8")
    # Les seuls liens publiés sont des ancres internes et des liens HTTP(S).
    content = html.fragment_fromstring(fragment, create_parent="div")
    for element in content.iter():
        if element.tag == "img":
            element.tag = "span"
            element.text = element.attrib.pop("alt", "")
        for key in list(element.attrib):
            if key.startswith("on") or key in ("style", "src", "srcset", "poster"):
                del element.attrib[key]
        href = element.get("href")
        if href and not href.startswith("#"):
            try:
                url = urlsplit(href)
                allowed = url.scheme in ("http", "https") and bool(url.netloc)
            except ValueError:
                allowed = False
            if not allowed:
                del element.attrib["href"]
    return Document(name, html.tostring(content, encoding="unicode"),
                    etree.tostring(tei, encoding="utf-8", xml_declaration=True), source,
                    document_excerpt(content))
