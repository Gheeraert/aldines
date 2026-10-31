# Journal de développement et état de la version 0.1

## 31 octobre 2026 — périmètre réalisé

Travail dans `C:/aldines`, sur la branche `dev`, à partir du commit initial du dépôt fourni `Gheeraert/aldines`. Ce dépôt était **déjà public** lors de l’examen ; sa visibilité n’a pas été modifiée. Le nom du paquet et de l’application est Studio Aldines ; le dépôt distant conserve le nom choisi par son propriétaire. Aucun déploiement, workflow Pages ou publication du corpus.

### Examen de l’existant

- Lecture du maître, inventaire XML des 97 unités, examen de plusieurs passages de chacun des deux livres, du plan JSON et des trois scripts Python.
- Proposition courte communiquée avant l’implémentation : configuration, traitement Augustinus, publication statique, interface Qt ; un seul contrat entre traitement et publication.
- Copie locale privée de 102 fichiers de référence : 98 XML, le plan et les trois scripts. Empreintes SHA-256 enregistrées dans `.local/source-hashes.json`. `a-verifier.md` n’a pas été incorporé à cette copie ni lu comme donnée de publication.
- Inventaire et décisions consignés dans `architecture.md`. Le plan est informatif et n’impose pas des unités absentes.

### Générateur

- Chargement et sauvegarde du JSON, priorités des métadonnées, valeurs par défaut et erreurs compréhensibles.
- Résolution récursive des XInclude locaux dans l’ordre du maître, détection des cycles, ressources confinées, XML sans DTD ni entités externes.
- Alignement latin/français par `corresp`, titres, paragraphes, clôture du livre I, citations, petits caractères typographiques, grec, vers, abréviations et incertitudes.
- Manchettes et notes de source/traduction distinguées, repères de pages/colonnes/sections, signatures et réclames. Les annotations ouvertes sont placées après la phrase par le JavaScript, pour garder le fil du texte.
- Conservation du texte inconnu avec avertissement ; diagnostics d’alignement, identifiants dupliqués et références internes.
- Accueil scientifique, sommaire suivant le maître, lecteur, précédent/suivant, fil d’Ariane, ancres TEI et notices issues des en-têtes.
- Recherche entièrement statique, sans requête distante. Liens relatifs pour les hébergements en sous-répertoire.
- Options typographiques, thèmes clair/sombre, trois modes de lecture, commandes accessibles pendant le défilement, présentation mobile sans défilement horizontal.
- Génération dans un dossier temporaire puis remplacement d’une sortie dédiée, préservation du site précédent en cas d’échec. Rapport JSON et journal simple.

### Atelier Qt

- Cinq espaces : Projet, Corpus, Présentation, Prévisualisation, Publication.
- Ouverture et création du projet JSON, tous les champs scientifiques, projets récents, indication des modifications non enregistrées.
- Arbre par tome/livre, état de traduction, sélection par unité, affichage des diagnostics.
- Réglages de lecture, police, corps, largeur, interlignage et proportion des colonnes.
- Aperçu séparé d’une unité ; ouverture du navigateur, de la publication ou du dossier de sortie.
- Chargement et génération dans un `QThread`. Les formulaires sont désactivés pendant l’opération afin de ne pas modifier le projet en cours de traitement ; l’application continue de traiter ses événements et le journal progresse. La fermeture attend la fin de l’opération en cours. Pas d’annulation forcée.
- Serveur d’aperçu limité à `127.0.0.1`, arrêté à la fermeture de l’application.

## Vérifications effectuées

### Tests Python et Qt

Suite exécutée avec Python 3.14 et les dépendances déjà installées. La commande de référence de la session utilise un dossier temporaire réservé sous `.local`, car le dossier temporaire Windows du bac à sable n’était pas accessible à pytest :

```powershell
python -m pytest -q --basetemp=C:/aldines/.local/pytest-run-04
```

**26 tests réussis**, incluant les paramètres de validation JSON et les tests privés du corpus réel. Dernière exécution après les retouches : `pytest-final-06`, 26 réussites en 11,89 secondes. Versions présentes : lxml 6.1.3, PySide6 6.11.1, pytest 9.0.3, Playwright 1.61.0. Le moteur et l’interface représentent environ 1 400 lignes Python, hors tests et ressources.

Tests publics : projet/JSON, priorités de métadonnées, ordre maître différent de l’ordre des noms, inclusions imbriquées/absentes/cycliques, XML mal formé, refus des entités et ressources externes, identifiants dupliqués, références invalides, alignement, conservation du texte inconnu, échappement HTML, notes/manchettes, repères au milieu d’un mot, grec et ligatures, référence HTML attendue, navigation, liens entre unités et ancres, sous-répertoire, sélection, préservation des sources et de la publication antérieure.

Test Qt hors écran : ouverture, chargement du corpus, modification de présentation, sélection, sauvegarde/relecture JSON, aperçu d’une unité et génération complète de la sélection via les vrais workers. Capture contrôlée visuellement. Les polices Windows ont été chargées explicitement dans le test, car le plugin Qt hors écran ne les chargeait pas par défaut ; le lancement normal utilise Segoe UI.

Tests privés, hors Git : les **1 644 phrases latines et les 1 644 phrases françaises** sont comparées à une extraction XML indépendante, puis au texte extrait du HTML réellement généré. Les notes sont vérifiées, les 97 pages contrôlées, tous les liens et ancres résolus et les identifiants HTML vérifiés uniques. Quelques passages réels ont aussi une référence textuelle figée dans `.local/reference-golden.json`. Les empreintes de la copie scientifique restent identiques.

Construction du paquet Python également vérifiée avec le setuptools 80.9.0 déjà disponible dans Python 3.13 : `.local/wheels/studio_aldines-0.1.0-py3-none-any.whl`. Archive inspectée : 16 fichiers, CSS et JavaScript inclus, aucun TEI, HTML scientifique ou document privé. Aucun paquet n’a dû être téléchargé. La première tentative avec Python 3.14 ne disposait pas de setuptools et son dossier temporaire pip était restreint ; l’outil de construction existant sous Python 3.13 a permis de terminer cette vérification sans installer de dépendance supplémentaire. Le fonctionnement de l’application et les tests sont vérifiés avec Python 3.14 ; le paquet produit n’est pas un installateur autonome.

Génération finale exécutée directement depuis `aldines.json`, donc depuis les **originaux G:** : 97 unités, 1 644 paires de phrases, zéro diagnostic. Comparaison finale des **102 empreintes d’origine : aucun fichier modifié**. Les ressources et les scripts originaux restent en lecture seule tout au long du développement.

### Navigateur et revue visuelle

```powershell
python tools/browser_smoke.py --channel chrome
```

Script facultatif nécessitant Playwright, utilisé ici avec Chrome déjà installé. Aucun navigateur n’a été téléchargé. Vérifications : 97 entrées du sommaire, 74 phrases dans la section 1, 94 dans le chapitre II.1, ouverture des notes, modes latin/français/bilingue, maintien de la première phrase visible pendant le changement de mode (écart inférieur à 4 px), thème sombre, recherche française et accès à son ancre, largeur mobile de 390 px sans débordement, accès au site sous un sous-répertoire. Aucune erreur JavaScript relevée. Il s’agit d’un écran mobile simulé dans Chrome, pas d’un essai matériel sur téléphone.

Captures dans `.local/screenshots` : accueil, lecteur de bureau, grec, thème sombre et lecteur mobile. Revue visuelle effectuée. Les captures et le site contiennent du texte inédit et restent exclus de Git.

### Défauts trouvés et corrigés pendant les essais

- lxml enveloppe certaines absences de fichiers en erreur générique : contrôle explicite d’existence avant analyse pour conserver le statut d’avertissement.
- Accès refusé ponctuel lors d’un renommage de dossier sous Windows : remplacement réessayé brièvement en cas de verrou de partage, sans toucher aux sources.
- Panneau de lecture initialement placé hors de portée après défilement : commandes désormais fixes au sommet pendant la lecture et position conservée sur la première phrase visible.
- Une note ouverte à l’intérieur d’une phrase interrompait sa lecture : détail déplacé après le texte de la phrase.
- Capture Qt hors écran initialement sans glyphes : chargement des polices de test, puis nouvelle capture lisible.

## Livrables locaux

- `aldines.json` : projet configuré pour les originaux du lecteur G:.
- `publication/` : démonstration locale complète, 97 unités, non suivie par Git.
- `.local/reference/` : copie privée des références ; `.local/aldines.json` : projet de test de cette copie.
- `.local/source-hashes.json` : empreintes des originaux avant le développement.
- `.local/reference-golden.json` : attentes textuelles figées de passages réels.
- Code moteur, atelier Qt, lanceur Windows, tests synthétiques et documentation : seuls fichiers destinés à la branche distante.

## Limites connues et travail restant

À reprendre après usage réel de cette première version, sans refonte préalable :

1. **Relecture scientifique par l’éditeur** : aucune vérification informatique ne certifie les leçons, les sources ni la traduction. Renseigner licence, date et formule de citation avant toute diffusion ; elles restent volontairement non décidées par le logiciel.
2. **Essais d’usage Qt** sur le poste de travail, y compris les réglages d’échelle Windows, le parcours de création d’un nouveau projet et les fenêtres de dialogue système. Le parcours principal Qt est testé automatiquement ; l’ensemble des gestes et des plateformes ne l’est pas.
3. **Téléphones réels et autres navigateurs** : tests exécutés dans Chrome avec écran étroit simulé. À compléter lors de la préparation d’une diffusion.
4. **Polices** : EB Garamond et les polices grecques sont recherchées localement avec replis ; aucune fonte n’est embarquée. Un lot de fontes redistribuables et ses licences pourra être ajouté si un rendu identique sur tous les appareils devient nécessaire.
5. **Correspondances complexes** : toutes les unités observées ont une correspondance phrase à phrase. Plusieurs phrases françaises visant la même phrase latine sont conservées ; une phrase française visant plusieurs phrases latines est conservée près de la première, avec avertissement. Les phrases françaises sans cible restent accessibles en fin d’unité. Ne pas considérer ces cas comme un alignement scientifique validé. Les titres français sont appariés aux titres latins dans leur ordre local.
6. **Manchettes** : consultables après la phrase, sur ordinateur et mobile. Leur placement dans une véritable marge extérieure n’est pas développé ; cette présentation évite les chevauchements en mode bilingue.
7. **Périmètre XInclude/TEI** : inclusions XML entières uniquement, sans XPointer, fallback de remplacement, réseau ou profils arbitraires. Les rendus supplémentaires (`corr`, `ref`, etc.) sont prudents mais ne constituent pas une prise en charge générale de la TEI. Une unité doit posséder une division latine et une identité Augustinus.
8. **Recherche** : expression simple, sans index des notes, surbrillance des termes, lemmatisation ni classement de pertinence. Les résultats montrent les phrases entières ; les 100 premiers sont affichés.
9. **Distribution** : application lancée avec Python ou le script Windows ; aucun installateur autonome, signature ou paquet exécutable fourni. L’aperçu cesse avec l’application. Pas de serveur de production.
10. **Informations du plan et fac-similés** : `plan-t1.json` reste disponible comme référence privée ; pas d’enrichissement automatique des titres de livres ni de visualiseur PDF. Aucun export EPUB/PDF ou apparat critique complexe.

Évolutions documentées seulement : Gassendi et autres conventions TEI, éditions multilingues ou sans traduction, apparats complexes, grandes collections, fac-similés enrichis et exports. Aucun code fictif correspondant n’a été ajouté.
