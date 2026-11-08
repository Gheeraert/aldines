"""Pages éditoriales de l’Augustinus et pied de page commun."""

from html import escape as esc

FRONTISPICE = "frontispice-1641.webp"


def publication_footer(meta):
    license_text = meta.get("license") or "Licence des contenus non renseignée."
    return f'''<footer class="site-footer">
<span>{esc(meta.get('institution', ''))} · {esc(meta.get('laboratory', ''))}</span>
<span>{esc(meta.get('status', 'Édition en cours'))} · {esc(meta.get('version', ''))}</span>
<p>{esc(license_text)} · Réalisé avec <a href="https://github.com/gheeraert/aldines">Studio Aldines</a></p>
</footer>'''


def editorial_page(meta, title, body, *, root="./", current="accueil"):
    def active(page):
        return ' aria-current="page"' if current == page else ""

    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · Augustinus</title>
<link rel="stylesheet" href="{root}assets/editorial.css">
<link rel="stylesheet" href="{root}assets/footer.css"></head>
<body class="editorial">
<a class="skip-link" href="#main">Aller au contenu</a>
<header class="editorial-header">
<a class="brand" href="{root}"{active('accueil')}>
<span>{esc(meta['title'])}<small>{esc(meta.get('subtitle', ''))}</small></span></a>
<nav aria-label="Navigation principale">
<a href="{root}contents/">Édition</a>
<a href="{root}ressources/"{active('ressources')}>Études et ressources</a>
<a href="{root}projet/"{active('projet')}>Le projet</a>
</nav>
</header>
<div class="editorial-frame">
<main id="main" tabindex="-1">{body}</main>
{publication_footer(meta)}
</div>
</body></html>'''


def home(meta, image, editorial):
    def paragraph(key, attributes=""):
        text = esc(editorial[key].strip()).replace("\n", "<br>")
        return f"<p{attributes}>{text}</p>" if text else ""

    caption = esc(editorial["home_caption"]).replace("\n", "<br>")
    alt = esc(editorial["home_alt"])
    figcaption = f"<figcaption>{caption}</figcaption>" if caption else ""
    engraving = ' class="engraving" width="911" height="1416"' if image == FRONTISPICE else ""
    return editorial_page(meta, "Accueil", f'''<section class="intro" aria-labelledby="titre">
<div class="intro-copy">
<h1 id="titre" lang="la">Augustinus</h1>
<p class="author">Cornelius Jansenius</p>
{paragraph('home_intro', ' class="summary"')}
<a class="read-button" href="contents/">Lire l’édition <span aria-hidden="true">→</span></a>
</div>
<figure class="frontispiece">
<img src="assets/{esc(image)}"{engraving} alt="{alt}">
{figcaption}
</figure>
</section>
<div class="entry-points">
<section aria-labelledby="edition-title">
<h2 id="edition-title">L’édition</h2>
{paragraph('home_edition')}
<a href="contents/">Lire l’édition <span aria-hidden="true">→</span></a>
</section>
<section aria-labelledby="resources-title">
<h2 id="resources-title">Études et ressources</h2>
{paragraph('home_resources')}
<a href="ressources/">Accéder aux ressources <span aria-hidden="true">→</span></a>
</section>
</div>''')


def resources(meta, documents):
    previews = []
    for slug, (title, excerpt) in documents:
        title = esc(title)
        paragraph = f'<p>{esc(excerpt)}</p>' if excerpt else ''
        previews.append(f'''<article class="resource-preview">
<h3>{title}</h3>
{paragraph}
<a href="{slug}/" aria-label="Lire la suite – {title}">Lire la suite <span aria-hidden="true">→</span></a>
</article>''')
    listing = "\n".join(previews) or '<p>Aucun document publié pour le moment.</p>'
    return editorial_page(meta, "Études et ressources", f'''<section class="resource-index" aria-labelledby="resources-title">
<h2 id="resources-title">Études et ressources</h2>
{listing}
</section>''', root="../", current="ressources")


def editorial_document(meta, document, *, credits=False):
    title = "Projet et crédits" if credits else document.title
    back = "" if credits else '<p><a href="../">← Études et ressources</a></p>'
    return editorial_page(meta, title, f'''<article class="resource-index">
{back}
<div class="markdown-body">{document.body}</div>
<p><a href="document.xml" download>Télécharger le XML-TEI</a></p>
</article>''', root="../" if credits else "../../", current="projet" if credits else "document")


def project_credits(meta):
    fields = [
        ("Auteur", meta.get("author")),
        ("Responsable scientifique", meta.get("editor")),
        ("Édition de référence", meta.get("source_edition")),
        ("Publication", " · ".join(filter(None, [meta.get("publication_date"), meta.get("version")]))),
        ("État de l’édition", meta.get("status")),
        ("Institution", meta.get("institution")),
        ("Laboratoire", meta.get("laboratory")),
        ("Citation", meta.get("citation")),
        ("Licence", meta.get("license") or "Licence des contenus non renseignée."),
    ]
    details = "".join(f"<dt>{esc(label)}</dt><dd>{esc(value)}</dd>" for label, value in fields if value)
    description = "".join(f"<p>{esc(paragraph)}</p>" for paragraph in (meta.get("description") or "").split("\n\n")
                          if paragraph.strip())
    extra = []
    for heading, key in (("Contributions", "contributors"), ("Identifiants pérennes", "identifiers")):
        if meta.get(key):
            items = "".join(f"<li>{esc(value)}</li>" for value in meta[key])
            extra.append(f"<h3>{heading}</h3><ul>{items}</ul>")
    return editorial_page(meta, "Projet et crédits", f'''<article class="resource-index">
{description}
<dl>{details}</dl>
{''.join(extra)}
</article>''', root="../", current="projet")
