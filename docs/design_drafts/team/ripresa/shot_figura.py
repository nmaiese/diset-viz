"""Screenshot della sola figura di una scheda, a piu' larghezze e nei due temi.

Uso: uv run --with playwright python shot_figura.py <url> <cartella>
"""
import sys
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ANALYTICS_HOSTS = ("googletagmanager.com", "google-analytics.com", "googlesyndication.com", "doubleclick.net")


def _route(route):
    host = urlsplit(route.request.url).hostname or ""
    if any(host == domain or host.endswith("." + domain) for domain in ANALYTICS_HOSTS):
        route.abort()
    else:
        route.continue_()


url, out = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    for tema in ("light", "dark"):
        for w in (375, 768):
            context = browser.new_context(viewport={"width": w, "height": 900}, color_scheme=tema, user_agent="DivarioCheck/1.0")
            context.route("**/*", _route)
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            fig = page.locator("figure.scatter-figure").first
            n = fig.count()
            larghezza = page.evaluate("document.documentElement.scrollWidth")
            tema_html = page.evaluate("document.documentElement.getAttribute('data-theme')")
            if n:
                fig.scroll_into_view_if_needed()
                fig.screenshot(path=f"{out}/figura-{w}-{tema}.png")
                box = fig.bounding_box()
                punti = fig.locator("circle").count()
                cap = fig.locator("figcaption").inner_text()[:160]
            else:
                box, punti, cap = None, 0, ""
            print(f"{w}px {tema}: figure={n} punti={punti} scrollWidth={larghezza} data-theme={tema_html} box={box and (round(box['width']), round(box['height']))}")
            print(f"   {cap}")
            context.close()
    browser.close()
