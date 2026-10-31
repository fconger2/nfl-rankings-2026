"""Build the GitHub Pages site (index.html at the repo root) from the dashboard page.

The dashboard page (dashboard/index.html) is written for the claude.ai dashboard runtime.
site/shell.html supplies a small stand-in for that runtime that reads data/dashboard/*.csv,
so the same page runs as a plain static site.
"""
import json

from .config import DASH, ROOT


def build():
    page = (ROOT / "dashboard" / "index.html").read_text()
    page = page.replace('<meta name="dash-one-writer">', "")
    ids = sorted(p.stem for p in DASH.glob("*.csv"))
    shell = (ROOT / "site" / "shell.html").read_text()
    html = shell.replace("/*IDS*/[]", json.dumps(ids)).replace("<!--PAGE-->", page)
    (ROOT / "index.html").write_text(html)
    (ROOT / ".nojekyll").write_text("")
    print(f"site: index.html ({len(ids)} datasets)")
