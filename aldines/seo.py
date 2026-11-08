"""Métadonnées des pages et découverte des URL du site statique."""

from html import escape
from textwrap import shorten
from xml.etree.ElementTree import Element, ElementTree, SubElement


def page_tags(*, description="", canonical="", indexable=True):
    tags = []
    if description := shorten(description, width=200, placeholder="…"):
        tags.append(f'<meta name="description" content="{escape(description)}">')
    if not indexable:
        tags.append('<meta name="robots" content="noindex">')
    elif canonical:
        tags.append(f'<link rel="canonical" href="{escape(canonical)}">')
    return "\n".join(tags)


def write_sitemap(path, urls):
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for address in urls:
        SubElement(SubElement(root, "url"), "loc").text = address
    ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
