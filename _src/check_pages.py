"""Screenshot every page at phone and desktop widths, and report sideways overflow and script errors.

Usage: python3 _src/check_pages.py OUTPUT_DIR
Needs Playwright with Chromium. YouTube thumbnails may not load in a sandbox; the pages then show their
built-in placeholder tiles, which is expected.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
pages = sorted(p for p in REPO.glob("*.html") if p.name != "404.html")
bad = 0
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for name, width in (("phone", 390), ("desktop", 1280)):
        page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme="dark")
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        for p in pages:
            page.goto(p.as_uri())
            page.wait_for_timeout(300)
            if page.evaluate("document.documentElement.scrollWidth > window.innerWidth"):
                print(f"{name}: {p.name} scrolls sideways")
                bad += 1
            page.screenshot(path=str(OUT / f"{name}-{p.stem}.png"), full_page=True)
        for err in errors:
            print(f"{name}: script error: {err}")
            bad += 1
        page.close()
    browser.close()
print(f"{len(pages)} pages checked at phone and desktop widths; problems: {bad}; screenshots in {OUT}")
sys.exit(1 if bad else 0)
