# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Move to <head> what belongs there: Typst can only write into <body>.

    uv run tools/head.py page.html          # one page
    uv run tools/head.py web/dist/fr        # every page of a site

HTML export gives a document no access to <head>. web.typ therefore writes its
stylesheet at the top of <body>, and so does a document that emits metadata:

    #html.elem("meta", attrs: (name: "citation_title", content: "..."))

Browsers apply a stylesheet wherever it is. Programs that look for metadata
(Google Scholar, link previews) only read <head>. This script moves every
<style>, <meta> and <link> of the body to the end of <head>, in their order,
and changes nothing else in the file. Microdata (`itemprop`) stays in place.

It is a finishing step: a page is correct without it, and running it twice
changes nothing. Only the standard library is used.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MOVED = re.compile(r"<style\b[^>]*>.*?</style>|<(?:meta|link)\b[^>]*>", re.S)
SCRIPT = re.compile(r"(<script\b[^>]*>.*?</script>)", re.S)
BODY = re.compile(r"<body\b[^>]*>")


def hoist(html: str) -> str:
    """The page with the head-only elements of its body moved to its head."""
    end = html.find("</head>")
    # Searched after the head: a stylesheet may name <body> in a comment.
    body = BODY.search(html, end) if end >= 0 else None
    if body is None:
        return html
    moved: list[str] = []

    def take(m: re.Match) -> str:
        if "itemprop=" in m[0]:
            return m[0]
        moved.append(m[0])
        return ""

    # A script may hold markup in a string: its text is skipped.
    parts = SCRIPT.split(html[body.end():])
    rest = "".join(part if i % 2 else MOVED.sub(take, part) for i, part in enumerate(parts))
    return html[:end] + "".join(moved) + html[end:body.end()] + rest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("path", nargs="+", type=Path, help="HTML files, or folders searched for *.html")
    args = p.parse_args()
    changed = total = 0
    for path in args.path:
        if not path.exists():
            print(f"{path} not found", file=sys.stderr)
            return 2
        for file in sorted(path.rglob("*.html")) if path.is_dir() else [path]:
            before = file.read_bytes().decode("utf-8")
            after = hoist(before)
            total += 1
            if after != before:
                file.write_bytes(after.encode("utf-8"))
                changed += 1
    print(f"{changed} of {total} page(s) changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
