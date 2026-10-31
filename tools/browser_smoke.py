"""Vérification facultative du site local : python tools/browser_smoke.py.

Nécessite Playwright et Chromium (outils de développement uniquement).
Les captures scientifiques restent dans .local, exclu de Git.
"""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aldines.preview import start_preview


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default=None, help="Par exemple chrome si Chromium Playwright n’est pas installé")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    site = root / "publication"
    shots = root / ".local" / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    server, url = start_preview(site)
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, timeout=15000, channel=args.channel)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            page.screenshot(path=str(shots / "home-desktop.png"), full_page=True)
            page.get_by_role("link", name="Parcourir l’édition").click()
            assert page.locator(".contents-list li").count() == 97
            page.get_by_role("link", name="Section 1", exact=True).click()
            assert page.locator(".aligned-row.sentence").count() == 74
            page.locator(".note-call").first.click()
            assert page.locator(".note-content").first.is_visible()
            page.screenshot(path=str(shots / "reader-desktop.png"), full_page=False)
            page.locator('[data-anchor="t1.l01.s01.la.s14"]').scroll_into_view_if_needed()
            row = page.locator('[data-anchor="t1.l01.s01.la.s14"]')
            page.screenshot(path=str(shots / "greek-desktop.png"))
            anchor = page.evaluate('''() => {
                const bottom = document.querySelector('.reader-tools').getBoundingClientRect().bottom;
                return [...document.querySelectorAll('.aligned-row.sentence')].find(r => r.getBoundingClientRect().bottom > bottom).dataset.anchor;
            }''')
            visible = page.locator(f'[data-anchor="{anchor}"]')
            before = visible.bounding_box()["y"]
            page.locator("#reading-mode").select_option("latin")
            # Le changement de mode conserve la première phrase visible.
            assert abs(visible.bounding_box()["y"] - before) < 4
            assert not row.locator(".french").is_visible()
            page.locator("#reading-mode").select_option("french")
            assert not row.locator(".latin").is_visible()
            page.locator("#reading-mode").select_option("bilingual")
            page.locator("#theme-toggle").click()
            assert page.locator("html").get_attribute("data-theme") == "dark"
            page.screenshot(path=str(shots / "reader-dark.png"))
            page.goto(url + "search/")
            page.locator("#query").fill("Pélage")
            page.locator("#search-language").select_option("fr")
            page.get_by_role("button", name="Rechercher", exact=True).click()
            assert page.locator("#search-results li").count() > 0
            page.locator("#search-results a").first.click()
            assert "#t1." in page.url
            assert page.locator(":target").count() == 1
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(url + "t1/l1/s01/")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.locator(".aligned-row.sentence").first.locator(".latin").is_visible()
            assert page.locator(".aligned-row.sentence").first.locator(".french").is_visible()
            page.screenshot(path=str(shots / "reader-mobile.png"), full_page=False)
            # Sous-répertoire : le serveur sert ici le projet, donc /publication/.
            parent_server, parent_url = start_preview(root)
            try:
                response = page.goto(parent_url + "publication/t1/l2/c01/")
                assert response.status == 200
                assert page.locator(".aligned-row.sentence").count() == 94
                page.get_by_role("link", name="Sommaire", exact=True).click()
                assert "/publication/contents/" in page.url
                assert page.locator(".contents-list li").count() == 97
            finally:
                parent_server.shutdown()
                parent_server.server_close()
            assert not errors, errors
            browser.close()
        print("Navigateur : ordinateur, mobile, modes, notes, thème, recherche et sous-répertoire OK.")
        print(f"Captures privées : {shots}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
