# Correction du bandeau et du titre d’accueil

Correction locale sur `css`, à partir de `2bd29e9`. Le dernier état a été corrigé sans annulation globale : le sélecteur hiérarchique et le réglage Qt d’alignement sont conservés. Aucun nouveau commit ni push.

## Cause et correction

Le gabarit conditionnait le libellé Lecture et son sélecteur à `reader=True`. Sur l’accueil et le sommaire, il ne présentait donc que le bouton d’options et le choix d’alignement. Les six options éditoriales étaient également absentes de ces pages. La précédente vérification avait contrôlé ces fonctions dans le lecteur sans exiger leur présence sur toutes les pages.

Le même bandeau complet est maintenant généré partout : Sommaire, Rechercher, Clair / sombre, Lecture, Latin · Français / Latin / Français, Options d’affichage. Le panneau contient systématiquement Notes, Manchettes, Pages, Colonnes et sections imprimées, Signalement des incertitudes, Identifiants des phrases. Les choix de lecture sont mémorisés et suivent le lecteur entre les pages. Sur ordinateur, les commandes tiennent sur une ligne ; sur téléphone, elles se répartissent sur plusieurs lignes pour rester accessibles.

L’alignement est désormais exclusivement décidé dans Studio Aldines via `appearance.text_align`. Le sélecteur d’alignement a été retiré du site ainsi que le code permettant au navigateur de remplacer le réglage de l’éditeur. Une ancienne préférence enregistrée est ignorée. Les notes et les titres gardent leurs styles propres.

Le titre d’accueil passe de 40–60 px à `clamp(30px, 2.3vw, 32px)`, contre 27–28 px dans l’en-tête. Son corps ne dépasse donc celui de l’en-tête que de 11 à 14 % aux largeurs vérifiées.

## Vérifications

- 28 tests réussis en 11,89 secondes. Un test de régression vérifie chaque page générée : présence de Lecture, des trois modes, des six options et absence de sélecteur d’alignement dans le site ; l’alignement publié doit être celui du projet.
- Génération réelle dans `.local/css-fix/site/` : 162 unités, zéro diagnostic. La publication existante et les sources n’ont pas été remplacées.
- Chrome à 1440, 1280, 768, 390 et 375 px : contrôles visibles sur accueil, sommaire et lecteur ; six cases consultables ; modes monolingues et bilingue fonctionnels ; notes consultables ; aucun débordement horizontal.
- Un ancien choix navigateur `left` est injecté dans l’essai : le texte reste justifié conformément au projet actuel. La présentation de l’accueil utilise aussi cet alignement.
- Rapport entre taille du titre d’accueil et de la marque vérifié inférieur à 1,2 ; captures revues visuellement. Le titre et la présentation personnels sont ceux du JSON actuel, conservé intact.
- Parcours navigateur existant réussi sur l’aperçu corrigé : recherche, modes, notes, mobile et sous-répertoire.

Captures : `.local/css-fix/home-1440.png`, `reader-options-1440.png`, `home-options-375.png` et variantes aux cinq largeurs. Résultats : `.local/css-fix/results.json`. Ces artefacts restent exclus de Git.

La première tentative pytest a échoué avant l’exécution des tests concernés parce que le dossier parent temporaire n’existait pas encore. L’exécution a été reprise avec ce dossier disponible et les 28 tests sont passés. Un sélecteur du script navigateur a également été ajusté au libellé Lecture contenant un sélecteur imbriqué ; la vérification finale est réussie.

Pour examiner le site corrigé : `python -m aldines serve .local/css-fix/site --port 8000`. Pour utiliser les corrections dans la publication courante, la régénérer depuis Studio Aldines lancé sur la branche `css`.
