# Commandes regroupées, alignement et navigation hiérarchique

Suite de la révision sur la branche locale `css`, depuis `44d2aee`. Modifications non commitées et non poussées. Les modifications préexistantes de `.gitignore` et `aldines.json` sont conservées ; aucune modification des TEI, de `Sources/` ou de la publication existante.

## En-tête commun

Le gabarit `page()` regroupe la navigation principale et les commandes de lecture dans l’en-tête. Sur les pages d’édition, Sommaire, Rechercher, Clair / sombre, Lecture, la sélection de langue et Options d’affichage tiennent sur une ligne à 1280 et 1440 px. La hauteur mesurée est de 76 px, contre 133 px pour l’en-tête et la barre de lecture précédents.

Sur écran étroit, les groupes passent à la ligne et les commandes gardent une hauteur minimale de 44 px. Le bouton « Affichage » est renommé « Options d’affichage ». Il est aussi disponible sur l’accueil et le sommaire, pour y régler l’alignement. Les options concernant les annotations restent propres aux pages d’édition.

L’en-tête des pages d’édition reste fixe pendant le défilement. Sa hauteur est mesurée par un `ResizeObserver` pour réserver l’espace nécessaire aux sauts vers les ancres. Le maintien de la position pendant un changement de langue se réfère désormais au bas de cet en-tête complet.

## Alignement à gauche ou justifié

Nouveau paramètre JSON : `appearance.text_align`, avec les valeurs `left` et `justify`. La valeur par défaut est `left` ; les projets existants restent compatibles. Le projet personnel `aldines.json` n’a pas été réécrit.

Le panneau Présentation de l’atelier Qt propose « Alignement du texte et des présentations ». La valeur est enregistrée dans le JSON et appliquée aux pages générées. Le lecteur peut ensuite modifier ce choix dans Options d’affichage : sa préférence est mémorisée dans le stockage local du navigateur et appliquée aux pages suivantes sur la même origine web. Elle prend le pas sur le choix initial du projet.

L’alignement concerne les phrases latines/françaises, l’introduction et les paragraphes de présentation et de notice scientifique. Les titres, commandes de navigation, notes et manchettes conservent leur présentation. Aucun changement des textes, de leur alignement bilingue ou de leurs identifiants.

## Navigation tome → livre → unité

Le sommaire commence par trois sélecteurs natifs, utilisables au clavier et adaptés aux téléphones. Choisir un tome filtre les livres disponibles ; choisir un livre filtre les sections ou chapitres. Le lien « Ouvrir le texte » suit la sélection sans déclencher de changement de page pendant le choix.

Les tomes et livres indiquent leur nombre d’unités. Chaque section/chapitre conserve son libellé et affiche le nombre de phrases et de phrases traduites. Un résumé reprend ces comptes pour l’unité choisie et pour son livre. Seules les unités effectivement publiées sont proposées ; l’ordre reste celui du maître. Les livres non sélectionnés ou absents ne sont pas ajoutés.

La dernière sélection est mémorisée dans le navigateur. Si une unité n’est plus publiée, le menu choisit une unité disponible. La liste complète reste accessible dans un volet dépliable. Sans JavaScript, ce volet est ouvert et le formulaire est masqué : tous les liens restent utilisables.

Les données des menus proviennent des mêmes entrées HTML que la liste, via des attributs `data-*`. Aucun chargement distant, nouvelle dépendance ou deuxième index du corpus.

## Vérifications

- 27 tests Python/Qt réussis en 12,62 secondes. Vérification supplémentaire d’une valeur d’alignement invalide ; le parcours Qt vérifie la sauvegarde et la relecture de `justify`.
- Génération isolée depuis les sources réelles : 161 unités, zéro diagnostic, dans `.local/css-next/site/`. Le corpus poursuit son évolution ; ce nombre correspond au moment du contrôle.
- Tous les liens et ancres de cette génération contrôlés, sans identifiants HTML dupliqués.
- Chrome à 1440, 1280, 768, 390 et 375 px : en-tête sur une ligne sur ordinateur, absence de débordement horizontal, choix d’alignement sur le lecteur et l’accueil, conservation de la préférence, sélection d’un livre/chapitre et ouverture de la bonne unité.
- Navigation testée sur trois tomes synthétiques, dont plusieurs livres dans le tome II et une unité sans traduction au tome III : filtrage et comptes exacts.
- Recherche, visibilité des ancres sous l’en-tête fixe, modes bilingue/monolingues et maintien de la position à moins de 4 px : vérifiés aux cinq largeurs. Thème sombre contrôlé.
- Parcours navigateur existant adapté au sélecteur et aux corpus de taille variable : notes, recherche, mobile et sous-répertoire réussis via `python tools/browser_smoke.py --directory .local/css-next/site --channel chrome`.
- Captures revues visuellement : `.local/css-next/reader-1440.png`, `reader-375.png`, `navigation-390.png` et variantes aux cinq largeurs. Résultats détaillés : `.local/css-next/browser-results.json`. Ces fichiers scientifiques restent exclus de Git.

Les contrôles sur téléphone et tablette sont simulés dans Chrome. À ces largeurs, une seule ligne pour toutes les commandes réduirait excessivement leur taille : le retour à la ligne est donc conservé. Les menus natifs suivent le comportement du système ; les comptes de l’unité sélectionnée sont aussi repris dans le résumé pour rester lisibles lorsque son libellé dépasse la largeur du sélecteur.

Pour examiner l’aperçu : `python -m aldines serve .local/css-next/site --port 8000`. La publication courante utilisera ces nouveautés à sa prochaine génération depuis la branche `css`.
