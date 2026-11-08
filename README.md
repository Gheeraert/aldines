# Studio Aldines

Atelier de bureau Python/Qt pour l’édition numérique bilingue de l’*Augustinus* de Cornelius Jansenius. Première version utilisable, développée à partir des 97 fichiers TEI réellement disponibles le 31 octobre 2026.

Le moteur fonctionne sans Qt. Il génère un site statique autonome, avec sommaire, trois modes de lecture, notes consultables, ancres TEI, navigation et recherche latine/française. L’application ne modifie jamais les TEI et ne met rien en ligne.

## Installation et lancement sous Windows

Depuis PowerShell, dans le dépôt :

```powershell
cd C:\aldines
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[gui,test]"
.\.venv\Scripts\python.exe -m aldines gui
```

Python 3.11 ou supérieur. Dépendances : `lxml` ; `PySide6` pour l’interface ; `pytest` pour les tests. Aucun navigateur intégré, framework web, base de données ni service distant. Une fois les dépendances installées, on peut aussi double-cliquer sur `Lancer-Studio-Aldines.cmd`.

Sur l’ordinateur de développement, les dépendances sont déjà présentes dans Python 3.14. `python -m aldines gui` ouvre l’atelier sans projet, comme le lanceur Windows. Pour ouvrir un projet précis au démarrage, passez son chemin à la commande, par exemple `python -m aldines gui aldines.json`.

## Premier projet Augustinus

Le fichier `aldines.json` est prêt pour les sources originales dans `G:/Mon Drive/Augustinus/tei/t1`. Il écrit uniquement dans `C:/aldines/publication`. Adapter ces chemins sur un autre ordinateur.

1. **Projet** : ouvrir ce JSON, ou créer un projet depuis un dossier TEI en désignant son fichier maître. Enregistrer le JSON hors du dossier TEI. Les métadonnées laissées vides sont complétées par les en-têtes ; leurs valeurs apparaissent en indication dans les champs.
2. **Corpus** : recharger et contrôler ; cocher les unités à publier. L’ordre suit exclusivement les inclusions du maître. Une inclusion absente produit un avertissement ; les livres encore absents du maître ne sont pas des erreurs.
3. **Présentation** : choisir langues, typographie, thème, alignement à gauche ou justifié et repères ; enregistrer les réglages. L’alignement concerne aussi les textes de présentation.
4. **Prévisualisation** : sélectionner une unité et générer l’aperçu. Il s’ouvre dans le navigateur via un petit serveur limité à `127.0.0.1` ; il reste actif tant que l’application est ouverte.
5. **Publication** : choisir un dossier dédié, générer toutes les unités sélectionnées et consulter le journal. « Ouvrir le site » lance l’aperçu local, sans déploiement.

Un astérisque dans le titre indique les réglages non enregistrés. Le message « Projet enregistré. » apparaît à côté du bouton après la sauvegarde. Une génération utilise les réglages actuellement affichés, même avant sauvegarde. Enregistrez le projet pour pouvoir reproduire ce rendu en ligne de commande. Choisissez un dossier de sortie vide ou déjà généré par Aldines, qui remplacera son contenu lors des générations suivantes.

Dans **Projet**, utilisez **Image d’accueil → Choisir une image…** pour sélectionner un fichier JPEG, PNG ou WebP. Renseignez la légende et le texte alternatif, enregistrez, puis régénérez le site. L’image source doit rester hors du dossier de sortie. Studio Aldines en publie une copie dans `assets/`. Le bouton **Rétablir le frontispice** rétablit également sa légende et sa description d’origine.

## Publier des ressources et des crédits

Dans **Ressources**, juste après **Présentation**, ajoutez les fichiers `.md` ou `.markdown` à publier. Dans **Projet**, utilisez **Projet et crédits → Choisir le Markdown…** pour sélectionner le fichier unique de cette page. Sans ce fichier, la page reprend les métadonnées du projet. Enregistrez les réglages dans **Projet**, puis générez le site.

Les fichiers doivent être en UTF-8 et rester hors du dossier de sortie. Installez Pandoc et vérifiez que la commande `pandoc --version` fonctionne avant de générer un site avec des fichiers Markdown. Chaque document est publié en HTML avec un lien de téléchargement du XML-TEI. Pour donner un titre à une ressource, utilisez `title: Mon titre` dans un en-tête YAML entre deux lignes `---`. Sans titre, le nom du fichier sert de titre.

Le dossier de publication contient aussi une copie de chaque Markdown à côté de sa page et du XML-TEI, ainsi qu’un fichier `aldines.json` avec les réglages utilisés et une notice `LISEZ-MOI.txt`. Le JSON conserve les chemins configurés dans le projet. Ces fichiers sont accessibles si le dossier complet est mis en ligne.

Le Markdown accepte notamment `*italique*`, `**gras**`, `[souligné]{.underline}`, `[lien](https://example.org)`, les listes à puces et numérotées, ainsi que les notes avec un appel `[^1]` et une définition `[^1]: Texte de la note.`.

Dans le site, toutes les pages présentent le bandeau complet : Sommaire, Rechercher, Clair / sombre, Lecture et son menu latin/français/bilingue, Options d’affichage. Ce dernier contient les six réglages de notes, manchettes, pages, colonnes, incertitudes et identifiants. Les préférences de lecture sont conservées dans le navigateur. L’alignement à gauche ou justifié est exclusivement décidé dans Studio Aldines, puis appliqué par la génération. Le sommaire propose trois sélections liées : tome, livre et section/chapitre, avec les nombres de phrases et de traductions, puis « Ouvrir le texte ». La dernière sélection est mémorisée. Une liste complète dépliable reste disponible, y compris sans JavaScript.

## Ligne de commande

```powershell
python -m aldines check aldines.json
python -m aldines build aldines.json
python -m aldines build aldines.json --unit t1.l01.s01 --output preview
python -m aldines serve publication --port 8000
```

Consulter ensuite `http://127.0.0.1:8000/`. L’aperçu HTTP est recommandé plutôt que le double-clic sur un fichier HTML : les liens utilisent les URL de répertoires (`t1/l1/s01/`). La commande `serve` ne sert que le dossier explicitement indiqué et écoute sur la boucle locale.

`check` ne produit aucun fichier ; son code de sortie vaut 1 en présence d’erreurs bloquantes, 0 sinon. `build` conserve le site précédent en cas d’échec de lecture ou de transformation. Les avertissements n’interdisent pas la publication. Le rapport est écrit dans `publication/build-report.json` ; ce rapport porte sur tout le corpus chargé, y compris les unités non sélectionnées.

## Ajouter du texte et publier

Ajouter un fichier TEI conforme aux conventions de l’Augustinus, puis son `xi:include` à la place voulue dans le maître, avec votre outil de travail habituel. Recharger le corpus et régénérer. Aldines n’ajoute pas lui-même d’inclusions et ne corrige pas les sources.

Le site contient les pages HTML, CSS, JavaScript et une copie exacte du fichier TEI original de chaque unité publiée, placée à côté de sa page HTML. Le bouton discret « Télécharger le TEI », en haut de chaque page d’édition, télécharge ce fichier sous son nom d’origine. Seules les unités sélectionnées sont copiées, y compris lors d’un aperçu ; les sources restent intactes. Après validation scientifique et autorisation de diffusion, copier **le contenu du dossier de publication** sur un hébergement statique. Les liens relatifs fonctionnent à la racine et sous `/augustinus/` ou un autre répertoire ; renseigner `publication.base_path` pour consigner ce montage. `.nojekyll` est fourni pour un éventuel hébergement GitHub Pages. Aucun workflow de déploiement n’est installé.

EB Garamond est employée lorsqu’elle est installée sur l’appareil de lecture ; sinon Garamond ou Georgia prend le relais. Le grec dispose de polices de repli spécifiques. Aucune police n’est téléchargée à l’ouverture du site. Les notes, modes de lecture et recherche utilisent JavaScript.

## Tests et documentation

```powershell
python -m pytest -q
# Dans un environnement restreignant le dossier temporaire Windows :
python -m pytest -q --basetemp=C:/aldines/.local/pytest-manuel
```

Le dernier chemin doit être réservé aux tests : pytest le nettoie. Les tests publics utilisent des textes synthétiques. Les tests du corpus réel sont facultatifs et nécessitent la copie privée `.local/reference` et son projet `.local/aldines.json` ; ils sont ignorés sur une installation sans corpus privé. Les essais navigateur supplémentaires sont décrits dans le journal de développement.

- [Examen initial, architecture et JSON](docs/architecture.md)
- [Journal, résultats et limites de cette version](docs/developpement.md)

Le code est sous la licence MIT déjà présente dans le dépôt. Cette licence n’attribue aucun droit sur le corpus, ses traductions ou ses annotations. Les TEI, les copies de référence, les captures et le site généré sont exclus de Git. `a-verifier.md` n’est jamais lu par le programme, publié ou utilisé pour corriger les textes.
