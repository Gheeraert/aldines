"""Petit serveur HTTP lié exclusivement à la boucle locale."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def start_preview(directory, port=0):
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(QuietHandler, directory=str(Path(directory).resolve())))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}/"
