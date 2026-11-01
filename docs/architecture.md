# Examen initial et décisions techniques

## Sources réellement examinées — 31 octobre 2026

Lecture du maître, des 97 unités de `G:/Mon Drive/Augustinus/tei/t1`, du `plan-t1.json` et des scripts `tei2html.py`, `verifier.py`, `assemble.py`. Le dossier `html/t1` contient les expériences antérieures ; le prototype Python fournit leur principe de présentation. Aucun fichier original n’a été écrit. Les fichiers scientifiques ont été copiés exclusivement dans `.local/reference`, ignoré par Git, avec empreintes SHA-256.

Le maître est un `teiCorpus` contenant 97 inclusions locales, d’abord les 85 sections du livre I puis les 12 chapitres disponibles du livre II. Les prévisions du plan (autres chapitres et livres) ne déterminent ni les erreurs ni l’ordre. Le plan n’est pas nécessaire au premier générateur et n’est pas chargé automatiquement.

Inventaire dans le corps du texte :

| Structure | Nombre | Traitement |
|---|---:|---|
| `s` | 3 288 | 1 644 paires latin/français, `xml:id` et `corresp` |
| `note` | 1 572 | 565 manchettes, 581 sources, 426 notes de traduction |
| `quote` | 1 437 | Citations, grec conservé sans normalisation |
| `choice` | 346 | Forme abrégée conservée, développement en infobulle |
| `pb` / `cb` / `milestone` | 148 / 198 / 494 | Repères discrets, sans ajout d’espace dans le mot |
| `fw` / `lb` | 24 / 9 | Signatures/réclames et ruptures explicites |
| `head` / `p` / `trailer` | 52 / 368 / 2 | Titres, limites de paragraphes et clôtures |
| `sic` / `unclear` / `gap` | 58 / 43 / 4 | Graphies conservées, signalement et lacunes |
| `lg` / `l` | 20 / 142 | Vers et retours de vers |

Autres balises présentes : `title`, `foreign`, `hi`, `div`, `text`, `body`, `abbr`, `expan`. `hi/@rend` utilise `smallcaps`, `caps`, `sup`, `italic`, `it`. Certaines lettres ont `p/@rend="epistola"` et certaines rubriques `rubrica`. Les titres de chapitres peuvent être répartis sur plusieurs `head`.

Le prototype donnait déjà le bon principe d’alignement par phrase, mais son dictionnaire français pouvait écraser des correspondances répétées ; son parcours omettait les titres et ignorait plusieurs repères. Le nouveau traitement reprend ce principe sans recopier les scripts d’assemblage ni leur fonction d’écriture scientifique. Les contrôles de `verifier.py` sont intégrés au chargement, avec diagnostics plus précis, sans second framework.

## Organisation retenue

| Fichier | Responsabilité |
|---|---|
| `aldines/config.py` | JSON, valeurs par défaut, contrôles simples, chemins et sauvegarde |
| `aldines/augustinus.py` | XML sûr, XInclude local, diagnostics, métadonnées et rendu des conventions Augustinus |
| `aldines/model.py` | Quelques structures Python : unité, ligne alignée, diagnostic |
| `aldines/build.py` | Pages, liens, index, ressources et remplacement du site généré |
| `aldines/preview.py` | Serveur local d’aperçu |
| `aldines/gui.py` | Cinq espaces Qt, projet courant et travail en arrière-plan |
| `aldines/__main__.py` | Commandes `check`, `build`, `gui`, `serve` |
| `aldines/assets/` | CSS lisible et JavaScript sans dépendance |

Le moteur n’importe jamais Qt. Le travail scientifique reste dans les TEI ; le JSON contient les décisions de publication ; le dépôt contient le programme. Une génération réussie ne signifie pas validation philologique.

## Contrat JSON version 1

L’exemple complet est `aldines.json` à la racine. Tous les chemins relatifs sont interprétés par rapport au dossier **du JSON**, et non au dossier courant du terminal. Les chemins absolus restent possibles. `sources.master` est relatif au projet, pas à `sources.directory` ; chaque `href` XInclude est relatif au fichier qui le contient.

- `corpus` : identifiant, titre, sous-titre, auteur, responsable, contributions, institution, laboratoire, présentation, référence imprimée, langues, avancement, date, version, licence, citation, identifiants pérennes. Contributions, langues et identifiants sont de simples listes de textes.
- `sources` : dossier autorisé, maître, sélection. `selection: null` signifie toutes les unités disponibles ; `[]` signifie aucune ; sinon liste d’identifiants, par exemple `["t1.l01.s01", "t1.l02.c01"]`. L’ordre de cette liste ne réordonne jamais le maître. Une sélection inconnue provoque une erreur claire au lieu de publier autre chose.
- `reading` : mode `bilingual`, `latin`, `french` et six options d’affichage booléennes. Les incertitudes restent dans le texte quand leur soulignement est désactivé ; les lacunes ne disparaissent pas.
- `appearance` : thème `light`/`dark`, nom de police, corps 12–36 px, interlignage 1,2–2,5, largeur 600–1 800 px, proportion latine 30–70 %, `text_align` (`left` par défaut ou `justify`) pour le texte et les présentations. Les anciens JSON reçoivent automatiquement la valeur `left` au chargement.
- `publication` : sortie dédiée et `base_path` (`/` ou `/sous-dossier/`). Le montage prévu est enregistré dans le rapport ; les liens sont relatifs, donc valables dans les deux cas sans réécriture.

Les blocs omis reçoivent des valeurs par défaut. Les champs supplémentaires sont conservés à la sauvegarde ; il n’existe ni moteur de migrations ni schéma externe.

### Priorité des métadonnées

1. Métadonnées du `teiHeader` maître.
2. Pour un champ encore vide, première valeur disponible dans les en-têtes des unités, selon l’ordre du maître.
3. Valeur non vide explicitement renseignée dans `corpus` du JSON.

Une liste vide ou `null` dans le JSON ne supprime pas une information TEI. Le titre courant d’une unité et sa notice bibliographique restent ceux de son propre en-tête. Les responsabilités sont extraites des `respStmt` ; une responsabilité contenant « direction » fournit le responsable scientifique si le JSON ne le renseigne pas. Aucune modification ou synchronisation inverse des en-têtes.

## Fidélité, ressources et génération

Le texte est échappé ; le HTML est construit uniquement à partir d’une liste explicite de rendus. Un élément inconnu conserve son contenu et génère un avertissement. Les graphies, ligatures et caractères ne sont jamais modernisés ; `choice` affiche `abbr` ou `sic` avant `expan` ou `corr`. Les développements restent accessibles en infobulle. Aucune ressource liée par `facs` n’est téléchargée.

Les DTD et entités externes sont refusées. Les instructions de schéma `xml-model` ne déclenchent aucun téléchargement. Les inclusions doivent être XML, locales, relatives et confinées dans `sources.directory`, après résolution des chemins. Les cycles, URL externes et `xpointer` sont signalés comme erreurs. Une inclusion absente est un avertissement ; une unité absente du maître n’est pas attendue. XML mal formé, identifiants ou URL dupliqués et absence de division latine bloquent la génération. Références invalides, texte sans traduction et vocabulaire inconnu produisent des avertissements. Le rapport conserve fichier et numéro de ligne lorsque disponibles.

Les identifiants TEI du corps ont des ancres dans le lecteur ; les conteneurs non matérialisés sont ancrés auprès de leur première phrase. Les identifiants d’en-tête ne sont pas des ancres de lecture. Les références vers une unité non publiée sont rendues inactives avec une indication. Une forme de route découle de l’identité TEI (`t1.l01.s01` → `t1/l1/s01/`) ; le nom de fichier n’est utilisé qu’en dernier recours pour cette identité, jamais pour l’ordre.

Le site est d’abord entièrement écrit dans un dossier temporaire voisin de la sortie. L’ancien site n’est remplacé qu’en cas de succès ; l’opération peut réessayer brièvement un verrou de partage Windows. Un marqueur identifie les dossiers générés. La sortie ne peut être ni le projet, ni le dossier TEI, ni leur ancêtre ; elle ne peut pas recouvrir des sources. Ne placer aucun document personnel dans une sortie déjà marquée comme générée. Un aperçu d’unité utilise un dossier distinct et ne modifie pas la sélection enregistrée.

La recherche embarque les phrases sans les notes ni les repères. Elle ignore casse et accents et rapproche `æ/ae`, `œ/oe`, sans modifier le texte affiché. Elle recherche une expression continue, dans une langue ou les deux, avec un maximum de 100 passages affichés. Elle ne lemmatise pas et n’effectue aucune analyse sémantique.

## Point d’extension futur

`build.py` appelle explicitement `augustinus.read_corpus(project)`, qui retourne un `Corpus` : métadonnées, diagnostics et liste ordonnée de `Unit`. Chaque unité fournit route, libellé, lignes de HTML déjà échappé et textes de recherche. Les conventions TEI, les correspondances et les particularités éditoriales restent dans `augustinus.py`.

Lorsqu’un corpus différent sera disponible, écrire son traitement réel et remplacer ce seul appel/import, ou ajouter alors un choix explicite. L’interface Qt et la publication pourront conserver le petit contrat si celui-ci reste adapté. Il n’y a ni découverte dynamique, ni profil de balises, ni adaptateur fictif, ni modèle d’édition universel. Ne pas étendre ce contrat avant de disposer d’un besoin vérifiable.

Références techniques consultées : [paramètres du parseur lxml](https://lxml.de/parsing.html), [QThread dans Qt for Python](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html).
