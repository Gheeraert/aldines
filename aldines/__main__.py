import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

from .augustinus import read_corpus
from .build import build
from .config import load_project, ProjectError


def main(argv=None):
    parser = argparse.ArgumentParser(prog="aldines", description="Studio Aldines — atelier de publication de l’Augustinus")
    subs = parser.add_subparsers(dest="command", required=True)
    for command, help_text in [("build", "Générer le site statique"), ("check", "Contrôler le corpus en lecture seule"),
                               ("gui", "Ouvrir l’atelier Qt")]:
        p = subs.add_parser(command, help=help_text)
        p.add_argument("project", nargs="?" if command == "gui" else None)
        if command == "build":
            p.add_argument("--unit", help="Identifiant d’une unité pour un aperçu isolé")
            p.add_argument("--output", help="Dossier de sortie différent de celui du projet")
    serve = subs.add_parser("serve", help="Prévisualiser un site sur la boucle locale")
    serve.add_argument("directory", nargs="?", default="publication")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    try:
        if args.command == "gui":
            try:
                from .gui import run
            except ImportError as exc:
                raise ProjectError('Installer l’interface : python -m pip install -e ".[gui]"') from exc
            return run(args.project if args.project and Path(args.project).is_file() else None)
        if args.command == "serve":
            directory = Path(args.directory).resolve()
            if not (directory / "index.html").is_file():
                raise ProjectError("Le dossier ne contient pas de site généré (index.html absent).")
            handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
            with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
                print(f"Aperçu : http://127.0.0.1:{server.server_port}/ — Ctrl+C pour arrêter", flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
            return 0
        project = load_project(args.project)
        if args.command == "check":
            corpus = read_corpus(project)
            print(f"{len(corpus.units)} unités, {sum(u.sentences for u in corpus.units)} phrases latines.")
            for issue in corpus.issues:
                print(issue)
            return 1 if corpus.errors else 0
        result = build(project, only=args.unit, output=args.output, progress=lambda s: print(s, flush=True))
        for issue in result.corpus.issues:
            print(issue)
        print(f"Site : {result.output}\nRapport : {result.output / 'build-report.json'}")
        return 0
    except (ProjectError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
