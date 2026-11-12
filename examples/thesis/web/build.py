# /// script
# requires-python = ">=3.11"
# dependencies = ["pagefind[extended]"]
# ///
"""Build the thesis site into web/dist/.

    uv run web/build.py                       # everything
    uv run web/build.py --lang fr --skip-pdf  # quick loop on one language

For each language: one Typst bundle (web/dist/<lang>/, one HTML page per
chapter, written by Typst from main-html.typ), one PDF (web/dist/pdf/) and one
Pagefind search index. Plus a redirect page at the root. This script only runs
commands and cleans up: it never rewrites the HTML.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "web" / "dist"

# TODO: adapt — languages (the first one is where the root page redirects by
# default) and the name of the PDF, which chapters/cover.typ links to.
LANGS = ["fr", "en"]
PDF_NAME = "thesis-{lang}.pdf"

# Typst says this on every web compilation.
NOISE = ("html export is under active development", "bundle export is experimental")


def typst(*args: str) -> None:
    """Run `typst compile`, show what it reports, stop on failure."""
    done = subprocess.run(["typst", "compile", *args], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    report, skip = [], False
    for line in done.stderr.splitlines():
        if line.startswith(("warning:", "error:")):
            skip = any(n in line for n in NOISE)
        if not skip:
            report.append(line)
    if "".join(report).strip():
        print("\n".join("    " + line for line in report), file=sys.stderr)
    if done.returncode != 0:
        sys.exit(f"typst compile failed ({' '.join(args)})")


def build_site(lang: str) -> None:
    out = DIST / lang
    # Typst never removes files from a bundle directory: a renamed chapter
    # would leave its old page behind.
    shutil.rmtree(out, ignore_errors=True)
    typst("--features", "html,bundle", "--format", "bundle", "--input", f"lang={lang}", "main-html.typ", str(out))
    pages = list(out.rglob("*.html"))
    print(f"  {lang}: {len(pages)} pages, {sum(p.stat().st_size for p in pages) // 1024} KiB")


def build_pdf(lang: str) -> None:
    out = DIST / "pdf" / PDF_NAME.format(lang=lang)
    out.parent.mkdir(parents=True, exist_ok=True)
    typst("--input", f"lang={lang}", "main.typ", str(out))
    print(f"  {lang}: pdf/{out.name}, {out.stat().st_size // 1024} KiB")


def build_search(lang: str) -> None:
    """One index per language, next to web.js, which loads it on first use."""
    args = ["--site", str(DIST / lang), "--output-subdir", "assets/pagefind"]
    for cmd in ([sys.executable, "-m", "pagefind"], ["pagefind"], ["npx", "-y", "pagefind"]):
        try:
            if subprocess.run(cmd + args, capture_output=True, text=True).returncode == 0:
                print(f"  {lang}: search index")
                return
        except FileNotFoundError:
            continue
    print(f"  {lang}: Pagefind not found, the search box will say so (run through `uv run`, or install pagefind)")


def write_redirect(langs: list[str]) -> None:
    """Root page: send the visitor to their language, the first one by default."""
    default = langs[0]
    links = " | ".join(f'<a href="{lang}/index.html">{lang}</a>' for lang in langs)
    (DIST / "index.html").write_text(
        f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Redirecting…</title>
  <script>
    var langs = {langs!r};
    var mine = (navigator.language || "").toLowerCase().slice(0, 2);
    location.replace((langs.indexOf(mine) >= 0 ? mine : {default!r}) + "/index.html");
  </script>
  <noscript><meta http-equiv="refresh" content="0;url={default}/index.html"></noscript>
</head>
<body><p>{links}</p></body>
</html>
""",
        encoding="utf-8",
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--lang", action="append", choices=LANGS, help="build only this language (repeatable)")
    p.add_argument("--skip-pdf", action="store_true")
    p.add_argument("--skip-search", action="store_true")
    args = p.parse_args()
    langs = args.lang or LANGS

    print("Site")
    for lang in langs:
        build_site(lang)
    if not args.skip_pdf:
        print("PDF")
        for lang in langs:
            build_pdf(lang)
    if not args.skip_search:
        print("Search")
        for lang in langs:
            build_search(lang)
    write_redirect(LANGS)
    print(f"Done: open {DIST / 'index.html'}")


if __name__ == "__main__":
    main()
