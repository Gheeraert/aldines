"""Accueil et ressources de l’Augustinus, indépendants du lecteur."""

from html import escape as esc

EDITORIAL_ASSETS = ("editorial.css", "frontispice-1641.webp")


def editorial_page(title, body, *, root="./", on_resources=False):
    resources_current = ' aria-current="page"' if on_resources else ""
    home_current = "" if on_resources else ' aria-current="page"'
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · Augustinus</title>
<link rel="stylesheet" href="{root}assets/editorial.css"></head>
<body class="editorial">
<a class="skip-link" href="#main">Aller au contenu</a>
<div class="editorial-frame">
<header class="editorial-header">
<a class="wordmark" href="{root}"{home_current}>Augustinus</a>
<nav aria-label="Navigation principale">
<a href="{root}contents/">Édition</a>
<a href="{root}ressources/"{resources_current}>Études et ressources</a>
<a href="{root}ressources/#projet">Le projet</a>
</nav>
</header>
<main id="main" tabindex="-1">{body}</main>
<footer class="editorial-footer">
<nav aria-label="Navigation éditoriale">
<a href="{root}ressources/#presentation">Présentation de l’œuvre</a>
<a href="{root}ressources/#projet">Projet et crédits</a>
</nav>
</footer>
</div>
</body></html>'''


def home():
    return editorial_page("Accueil", '''<section class="intro" aria-labelledby="titre">
<div class="intro-copy">
<h1 id="titre" lang="la">Augustinus</h1>
<p class="author">Cornelius Jansenius</p>
<p class="subtitle">Édition numérique</p>
<p class="summary">Le traité majeur de Cornelius Jansenius (1585–1638) sur la nature humaine, la grâce et la controverse pélagienne, dans une édition numérique.</p>
<a class="read-button" href="contents/">Lire l’édition <span aria-hidden="true">→</span></a>
</div>
<figure class="frontispiece">
<img src="assets/frontispice-1641.webp" width="911" height="1416"
alt="Frontispice gravé montrant saint Augustin brandissant un cœur enflammé, entouré de figures ecclésiastiques.">
<figcaption><cite lang="la">Augustinus</cite>, tome I, Paris, 1641.<br>Numérisation Google Books.</figcaption>
</figure>
</section>
<div class="entry-points">
<section aria-labelledby="edition-title">
<h2 id="edition-title">L’édition</h2>
<p>Le texte latin de l’<cite lang="la">Augustinus</cite>, établi et présenté dans une édition numérique.</p>
<a href="contents/">Lire l’édition <span aria-hidden="true">→</span></a>
</section>
<section aria-labelledby="resources-title">
<h2 id="resources-title">Études et ressources</h2>
<p>Présentation de l’œuvre, articles, bibliographie et documents complémentaires.</p>
<a href="ressources/">Accéder aux ressources <span aria-hidden="true">→</span></a>
</section>
</div>''')


def resources(meta):
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
    return editorial_page("Études et ressources", f'''<div class="resource-index">
<h1>Études et ressources</h1>
<p>Cette rubrique est destinée à accueillir des articles scientifiques, des études historiques et théologiques, des bibliographies et des documents complémentaires sur l’<cite lang="la">Augustinus</cite>.</p>
<section aria-labelledby="presentation">
<h2 id="presentation">Présentation de l’œuvre</h2>
<p>Dans l’<cite lang="la">Augustinus</cite>, Cornelius Jansenius aborde la nature humaine et la grâce à travers la controverse pélagienne.</p>
<p><a href="../contents/">Lire l’édition <span aria-hidden="true">→</span></a></p>
</section>
<section aria-labelledby="projet">
<h2 id="projet">Projet et crédits</h2>
{description}
<dl>{details}</dl>
{''.join(extra)}
<p>Édition numérique réalisée avec Studio Aldines.</p>
</section>
</div>''', root="../", on_resources=True)
