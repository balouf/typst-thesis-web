# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""epub.py — package a web edition made with web.typ as an EPUB 3 book.

Source: https://github.com/balouf/typst-thesis-web (MIT)
Version 0.5.0 (2026-11-13), checked with Typst 0.15.1 and EPUBCheck 5.4.0.
Vendored copy: keep it unmodified, next to web-content.css.

    uv run web/epub.py paper.html -o paper.epub    # a page (typst compile --features html)
    uv run web/epub.py site/ -o thesis.epub        # a site (typst compile --format bundle)

The input is what Typst wrote, the files a website serves. Each HTML page
becomes one chapter of the book:

- the content is kept (article header, <main>, endnotes) and the page furniture
  is left out: scripts, styles, whatever carries `data-pagefind-ignore` (the
  navigation of a site), the table of contents of an article, and anything of
  class `web-only`;
- the markup is rewritten as XHTML. Glyph ids, which Typst repeats in every
  drawing, are made unique; images inlined as data URIs become files;
- links between pages follow the pages; a link to a file that is not in the book
  loses its target, or becomes absolute with --base-url;
- the order of the chapters and the table of contents come from the navigation
  of the site and from the headings;
- the stylesheet is web-content.css plus a few rules that follow the theme of
  the reading app: text keeps the reader's colors, drawings drawn in black
  only follow the text color, the others sit on white.

Title, authors and language are read from the pages; options override them.
With SOURCE_DATE_EPOCH set, the same input gives the same file, byte for byte.
Only the standard library is used.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import posixpath
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin
from xml.sax.saxutils import escape, quoteattr

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
# Never content: Typst cannot write into <head>, so web.typ puts these in <body>.
FURNITURE = {"script", "style", "link", "meta", "noscript", "base", "title"}
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml"}
EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg"}
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
BLACK = {"#000000", "#000", "black"}

# What a reading app needs around web-content.css. The app owns the colors of
# the page (day, sepia, night): nothing here sets a text or page color.
EPUB_CSS = """
/* Added by epub.py. Lines and tints are translucent greys, legible on any
   page color; the text color is the one of the reading app. */
:root {
  --color-text: currentColor;
  --color-text-muted: currentColor;
  --color-bg: transparent;
  --color-sidebar-bg: rgba(128, 128, 128, 0.12);
  --color-border: rgba(128, 128, 128, 0.4);
  --color-border-strong: rgba(128, 128, 128, 0.7);
  --color-link: currentColor;
  --font-math: "New Computer Modern Math", "Latin Modern Math", "STIX Two Math", "Cambria Math", math;
  --font-heading: inherit;
  --box-fill-share: 0%;
  --frame-filter: none;
}
h1, h2, h3, h4, h5, h6 { line-height: 1.25; text-align: left; hyphens: manual; break-after: avoid; page-break-after: avoid; }
h1 .num, h2 .num, h3 .num, h4 .num { opacity: 0.7; }
figure, table, .eq, svg { break-inside: avoid; page-break-inside: avoid; }
figcaption, .eq-num, .article-header .affil, .article-header .date, .article-header .keywords, .article-header .meta,
section[role="doc-endnotes"] { opacity: 0.85; }
table { border-collapse: collapse; margin: 1em auto; font-size: 0.9em; }
th, td { padding: 0.4em 0.6em; border: 1px solid var(--color-border); text-align: left; }
sup, sub { font-size: 0.75em; line-height: 0; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 0.9em; }
blockquote { margin: 1em 0; padding: 0 1em; border-left: 3px solid var(--color-border); font-style: italic; }
math { font-family: var(--font-math); }
/* A drawing in colors keeps them, on white; one drawn in black only has been
   switched to the text color (class added by epub.py). */
svg.in-colors, .typst img { background: #fff; }
svg.in-colors { box-shadow: 0 0 0 0.3em #fff; }
/* A box is outlined: its tint alone may not show on the reader's page. */
.typst .box { border-color: var(--box-stroke, var(--color-border)); }
.article-header .title { font-size: 1.8em; margin: 0 0 0.6em; }
.thesis-header, .thesis-header .thesis-title { text-align: center; }
.thesis-header .abstract { text-align: justify; margin-top: 2em; }
"""


# ---------------------------------------------------------------------------
# Reading the HTML that Typst wrote
# ---------------------------------------------------------------------------

class Node:
    """An element. `raw` holds the source text of an <svg>, copied as is."""

    __slots__ = ("tag", "attrs", "kids", "raw")

    def __init__(self, tag: str, attrs: dict[str, str] | None = None):
        self.tag = tag
        self.attrs = attrs or {}
        self.kids: list[Node | str] = []
        self.raw: str | None = None

    def nodes(self):
        """This element and its descendants, in document order."""
        yield self
        for kid in self.kids:
            if isinstance(kid, Node):
                yield from kid.nodes()

    def first(self, tag: str, **attrs: str) -> Node | None:
        for n in self.nodes():
            if n.tag == tag and all(n.attrs.get(k) == v for k, v in attrs.items()):
                return n
        return None

    def text(self) -> str:
        return "".join(k if isinstance(k, str) else k.text() for k in self.kids)

    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()


class Reader(HTMLParser):
    """Builds the tree of a page. An <svg> is not parsed: Typst writes it as
    XML, which html.parser would lowercase (viewBox), so its text is kept."""

    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.source = text
        self.lines = [0]
        for line in text.split("\n"):
            self.lines.append(self.lines[-1] + len(line) + 1)
        self.root = Node("#document")
        self.stack = [self.root]
        self.svg: tuple[Node, int] | None = None
        self.depth = 0
        self.feed(text)
        self.close()

    def here(self) -> int:
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if self.svg:
            self.depth += tag == "svg"
            return
        node = Node(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].kids.append(node)
        if tag == "svg":
            self.svg, self.depth = (node, self.here()), 1
        elif tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        if not self.svg:
            self.stack[-1].kids.append(Node(tag, {k: v or "" for k, v in attrs}))

    def handle_endtag(self, tag):
        if self.svg:
            self.depth -= tag == "svg"
            if self.depth == 0:
                node, start = self.svg
                node.raw = self.source[start:self.source.index(">", self.here()) + 1]
                self.svg = None
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if not self.svg:
            self.stack[-1].kids.append(data)


# ---------------------------------------------------------------------------
# The book
# ---------------------------------------------------------------------------

class Page:
    def __init__(self, name: str, tree: Node):
        self.name = name  # path in the site, e.g. "ch1.html"
        self.href = "text/" + re.sub(r"\.html?$", "", name) + ".xhtml"  # path in the book
        self.tree = tree
        self.body: list[Node | str] = []
        self.title = ""
        self.headings: list[tuple[int, str, str]] = []  # (level, id, text)
        self.frames = 0


class Book:
    def __init__(self, source: Path, base_url: str | None = None):
        self.dir = source if source.is_dir() else source.parent
        files = sorted(source.rglob("*.html")) if source.is_dir() else [source]
        if not files:
            sys.exit(f"no HTML page in {source}")
        self.pages = {}
        for f in files:
            name = f.relative_to(self.dir).as_posix()
            self.pages[name] = Page(name, Reader(f.read_text(encoding="utf-8")).root)
        self.base_url = base_url
        self.files: dict[str, bytes] = {}  # path in the book -> content
        self.notes: list[str] = []
        self.outline = self.site_outline()
        first = next(self.pages[e["page"]] for e in self.outline if "page" in e)
        self.meta = self.read_meta(first.tree, single=not source.is_dir())
        for page in self.pages.values():
            self.convert(page)

    # -- order of the pages ---------------------------------------------------

    def site_outline(self) -> list[dict]:
        """Pages and parts in reading order: the navigation web.typ writes in
        every page of a site. Entries: {"page": name, "title", "sub"} or
        {"part": title or None}."""
        names = list(self.pages)
        if len(names) == 1:
            return [{"page": names[0], "title": "", "sub": False}]
        entries: list[dict] = []
        for name, page in self.pages.items():
            nav = page.tree.first("nav", **{"class": "global-nav"})
            if nav is None:
                continue
            for li in (n for n in nav.nodes() if n.tag == "li"):
                link = li.first("a")
                if link is None:
                    entries.append({"part": li.text().strip() if "nav-part" in li.classes() else None})
                    continue
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(link.attrs.get("href", ""))))
                if target in self.pages:
                    entries.append({"page": target, "title": " ".join(link.text().split()), "sub": "nav-sub" in li.classes()})
            break
        listed = {e["page"] for e in entries if "page" in e}
        rest = [n for n in names if n not in listed]
        if rest and entries:
            self.notes.append(f"not in the navigation, put at the end: {', '.join(rest)}")
        elif rest:
            self.notes.append("no navigation found: pages are in alphabetical order, index.html first")
            rest.sort(key=lambda n: (n != "index.html", n))
        if rest and entries:
            entries.append({"part": None})
        return entries + [{"page": n, "title": "", "sub": False} for n in rest]

    def read_meta(self, tree: Node, single: bool) -> dict:
        html = tree.first("html")
        head = tree.first("head") or Node("head")
        title = head.first("title")
        site = tree.first("a", **{"class": "topbar-title"})
        named = {n.attrs.get("name"): n.attrs.get("content", "") for n in head.nodes() if n.tag == "meta"}
        style = head.first("style")
        return {
            "title": (site.text() if site is not None else title.text() if title is not None else "").strip(),
            "authors": [a.strip() for a in named.get("authors", "").split(",") if a.strip()],
            "subjects": [k.strip() for k in named.get("keywords", "").split(",") if k.strip()],
            "lang": (html.attrs.get("lang") if html is not None else None) or "en",
            # The MathML rules Typst writes in <head>. EPUBCheck does not know the
            # case-insensitivity flag of `[accent="true" i]`, of no use in XHTML.
            "typst-css": re.sub(r'(\[[\w-]+="[^"]*")\s+i\]', r"\1]", style.text() if style is not None else ""),
            "single": single,
        }

    # -- one page ---------------------------------------------------------------

    def convert(self, page: Page) -> None:
        body = page.tree.first("body")
        if body is None:
            sys.exit(f"{page.name}: no <body>")
        page.body = self.keep(body.kids)
        title = page.tree.first("title")
        page.title = title.text().strip() if title is not None else page.name
        here = posixpath.dirname(page.href)
        for kid in page.body:
            if not isinstance(kid, Node):
                continue
            in_main = kid.tag == "main"
            for n in kid.nodes():
                if n.raw is not None:
                    page.frames += 1
                    n.raw = self.frame(n.raw, f"f{page.frames}-", page, here)
                elif n.tag == "math":
                    n.attrs["xmlns"] = "http://www.w3.org/1998/Math/MathML"
                elif n.tag == "a" and "href" in n.attrs:
                    target = self.link(n.attrs["href"], page)
                    if target is None:
                        n.tag = "span"
                        for name in ("href", "target", "rel", "download", "hreflang", "type"):
                            n.attrs.pop(name, None)
                    else:
                        n.attrs["href"] = target
                elif n.tag == "img" and "src" in n.attrs:
                    n.attrs["src"] = self.image(n.attrs["src"], page, here)
                    n.attrs.setdefault("alt", "")
                elif n.tag in HEADINGS and in_main and n.attrs.get("id"):
                    page.headings.append((int(n.tag[1]), n.attrs["id"], " ".join(n.text().split())))
                self.notes_markup(n)

    def keep(self, kids: list) -> list:
        """The content of a page, without its furniture."""
        out = []
        for kid in kids:
            if isinstance(kid, Node):
                if (kid.tag in FURNITURE or "data-pagefind-ignore" in kid.attrs or "web-only" in kid.classes()
                        or kid.attrs.get("role") == "doc-toc"):
                    continue
                kid.kids = self.keep(kid.kids)
            out.append(kid)
        return out

    @staticmethod
    def notes_markup(n: Node) -> None:
        """Reading apps open a note in place when it is marked with epub:type."""
        role = n.attrs.get("role")
        if role == "doc-noteref":
            link = n.first("a")
            if link is not None and link is not n:
                link.attrs["epub:type"] = "noteref"
        elif role == "doc-endnotes":
            n.attrs["epub:type"] = "footnotes"
            for item in (k for k in n.nodes() if k.tag == "li" and k.attrs.get("id")):
                item.attrs["epub:type"] = "footnote"

    def link(self, href: str, page: Page) -> str | None:
        """Where a link goes in the book; None when its target is not in it."""
        if href.startswith("#") or SCHEME.match(href):
            return href
        path, fragment = urldefrag(href)
        target = posixpath.normpath(posixpath.join(posixpath.dirname(page.name), unquote(path)))
        if target in self.pages:
            there = posixpath.relpath(self.pages[target].href, posixpath.dirname(page.href))
            return there + ("#" + fragment if fragment else "")
        if self.base_url:
            return urljoin(urljoin(self.base_url, page.name), href)
        self.notes.append(f"{page.name}: link to {href} left without a target (not in the book; see --base-url)")
        return None

    def image(self, src: str, page: Page, here: str) -> str:
        """Moves an image into the book and returns its address from `here`."""
        if src.startswith("data:"):
            header, _, payload = src.partition(",")
            media = header[5:].split(";")[0]
            if media not in EXTENSIONS:
                self.notes.append(f"{page.name}: image of type {media or '?'} kept inline")
                return src
            data = base64.b64decode(payload) if ";base64" in header else unquote(payload).encode("utf-8")
            path = "images/" + hashlib.sha256(data).hexdigest()[:16] + EXTENSIONS[media]
        elif SCHEME.match(src):
            self.notes.append(f"{page.name}: remote image {src[:80]} (not allowed in an EPUB)")
            return src
        else:
            local = posixpath.normpath(posixpath.join(posixpath.dirname(page.name), unquote(src)))
            file = self.dir / local
            if local.startswith("..") or not file.is_file() or file.suffix.lower() not in IMAGE_TYPES:
                self.notes.append(f"{page.name}: image {src} not found, or not of a type an EPUB accepts")
                return src
            data, path = file.read_bytes(), "text/" + local
        self.files[path] = data
        return posixpath.relpath(path, here)

    def frame(self, svg: str, prefix: str, page: Page, here: str) -> str:
        """An SVG frame, ready for a document that holds several of them."""
        # Typst names a glyph after its outline, so two frames of a page define
        # the same ids. Those that the frame itself points to get a prefix; the
        # ids that links from the text point to (labels) are left alone.
        used = {m[2] for m in re.finditer(r'<([\w:-]+)\b[^>]*?\s(?:xlink:)?href="#([^"]+)"', svg) if m[1] != "a"}
        used |= set(re.findall(r"url\(#([^)\"]+)\)", svg))
        if used:
            def rename(m: re.Match) -> str:
                return m[1] + (prefix if m[2] in used else "") + m[2] + m[3]
            svg = re.sub(r'(\sid=")([^"]+)(")', rename, svg)
            svg = re.sub(r'(href="#)([^"]+)(")', rename, svg)
            svg = re.sub(r"(url\(#)([^)\"]+)(\))", rename, svg)

        # Images and links of the frame (Typst writes both href and xlink:href).
        def addresses(tag: str, move) -> str:
            def one(m: re.Match) -> str:
                return m[1] + escape(move(m[2].replace("&amp;", "&"))) + m[3]
            return re.sub(rf"<{tag}\b[^>]*>", lambda t: re.sub(r'(href=")([^"]*)(")', one, t[0]), svg)
        svg = addresses("image", lambda src: self.image(src, page, here))
        svg = addresses("a", lambda href: self.link(href, page) or "#")

        # A drawing made of black only follows the text color of the reading
        # app; any other one keeps its colors and is set on white.
        paints = {p.lower() for p in re.findall(r'\b(?:fill|stroke|stop-color)="([^"]+)"', svg)} - {"none", "transparent"}
        if paints <= BLACK and "<image" not in svg and "url(#" not in svg:
            svg = re.sub(r'\b(fill|stroke)="(?:#000000|#000|black)"', r'\1="currentColor"', svg)
            return svg.replace("<svg", '<svg fill="currentColor"', 1)  # for shapes that rely on the default fill
        return svg.replace("<svg", '<svg class="in-colors"', 1)

    # -- writing ------------------------------------------------------------------

    def xhtml(self, page: Page) -> str:
        out: list[str] = []

        def write(node: Node | str) -> None:
            if isinstance(node, str):
                out.append(escape(clean(node)))
            elif node.raw is not None:
                out.append(node.raw)
            else:
                attrs = "".join(f" {k}={quoteattr(clean(v))}" for k, v in node.attrs.items() if re.fullmatch(r"[A-Za-z_][\w.:-]*", k))
                if node.tag in VOID:
                    out.append(f"<{node.tag}{attrs}/>")
                else:
                    out.append(f"<{node.tag}{attrs}>")
                    for kid in node.kids:
                        write(kid)
                    out.append(f"</{node.tag}>")

        for kid in page.body:
            write(kid)
        lang = quoteattr(self.meta["lang"])
        style = posixpath.relpath("style.css", posixpath.dirname(page.href))
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang={lang} xml:lang={lang}>\n'
            f'<head><meta charset="utf-8"/><title>{escape(page.title)}</title>'
            f'<link rel="stylesheet" href={quoteattr(style)}/></head>\n'
            f'<body>{"".join(out)}</body>\n</html>\n'
        )

    def toc(self, depth: int) -> list[dict]:
        """Table of contents: [{"title", "href" or None, "kids": [...]}]."""
        top: list[dict] = []
        level = top  # where pages go: the top, or the current part
        last = None  # the last page that is not a sub-page
        for entry in self.outline:
            if "part" in entry:
                level = top
                if entry["part"]:
                    top.append({"title": entry["part"], "href": None, "kids": []})
                    level = top[-1]["kids"]
                last = None
                continue
            page = self.pages[entry["page"]]
            heads = page.headings
            if self.meta["single"]:
                top.append({"title": self.meta["title"] or page.title, "href": page.href, "kids": []})
                top += nest(heads, page.href, depth)
                continue
            # The first heading of a page is its title: the page stands for it.
            if heads and [h[0] for h in heads].count(heads[0][0]) == 1 and heads[0][0] == min(h[0] for h in heads):
                heads = heads[1:]
            item = {"title": entry["title"] or page.title, "href": page.href, "kids": nest(heads, page.href, depth)}
            if entry["sub"] and last is not None:
                last["kids"].append(item)
            else:
                level.append(item)
                last = item
        return [t for t in top if t["href"] or t["kids"]]

    def nav(self, depth: int) -> str:
        def listing(items: list[dict]) -> str:
            rows = []
            for item in items:
                label = escape(item["title"] or "—")
                head = f'<a href={quoteattr(item["href"])}>{label}</a>' if item["href"] else f"<span>{label}</span>"
                rows.append(f'<li>{head}{listing(item["kids"]) if item["kids"] else ""}</li>')
            return "<ol>" + "".join(rows) + "</ol>"

        lang = quoteattr(self.meta["lang"])
        title = escape(self.meta["title"])
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang={lang} xml:lang={lang}>\n'
            f'<head><meta charset="utf-8"/><title>{title}</title></head>\n'
            f'<body><nav epub:type="toc" role="doc-toc"><h1>{title}</h1>{listing(self.toc(depth))}</nav></body>\n</html>\n'
        )

    def opf(self, modified: datetime, cover: str | None) -> str:
        m = self.meta
        lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang={quoteattr(m["lang"])}>',
            '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">',
            f'    <dc:identifier id="book-id">{escape(m["identifier"])}</dc:identifier>',
            f'    <dc:title>{escape(m["title"])}</dc:title>',
            f'    <dc:language>{escape(m["lang"])}</dc:language>',
        ]
        lines += [f"    <dc:creator>{escape(a)}</dc:creator>" for a in m["authors"]]
        lines += [f"    <dc:subject>{escape(s)}</dc:subject>" for s in m["subjects"]]
        if m.get("date"):
            lines.append(f'    <dc:date>{escape(m["date"])}</dc:date>')
        lines.append(f'    <meta property="dcterms:modified">{modified.strftime("%Y-%m-%dT%H:%M:%SZ")}</meta>')
        lines += ["  </metadata>", "  <manifest>", '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                  '    <item id="style" href="style.css" media-type="text/css"/>']
        order = [self.pages[e["page"]] for e in self.outline if "page" in e]
        for i, page in enumerate(order):
            text = self.files[page.href].decode("utf-8")
            properties = [p for p, mark in (("mathml", "<math"), ("svg", "<svg")) if mark in text]
            if re.search(r'<(?:img|image)\b[^>]*?(?:src|href)="https?:', text):
                properties.append("remote-resources")
            extra = f' properties="{" ".join(properties)}"' if properties else ""
            lines.append(f'    <item id="page-{i + 1}" href={quoteattr(page.href)} media-type="application/xhtml+xml"{extra}/>')
        images = sorted(p for p in self.files if Path(p).suffix.lower() in IMAGE_TYPES)
        for i, path in enumerate(images):
            extra = ' properties="cover-image"' if path == cover else ""
            lines.append(f'    <item id="image-{i + 1}" href={quoteattr(path)} media-type="{IMAGE_TYPES[Path(path).suffix.lower()]}"{extra}/>')
        lines += ["  </manifest>", "  <spine>"]
        lines += [f'    <itemref idref="page-{i + 1}"/>' for i in range(len(order))]
        lines += ["  </spine>", "</package>", ""]
        return "\n".join(lines)

    def write(self, out: Path, css: str, depth: int, cover: Path | None) -> None:
        epoch = os.environ.get("SOURCE_DATE_EPOCH")
        modified = datetime.fromtimestamp(int(epoch), timezone.utc) if epoch else datetime.now(timezone.utc)
        for page in self.pages.values():
            self.files[page.href] = self.xhtml(page).encode("utf-8")
        cover_path = None
        if cover is not None:
            cover_path = "images/cover" + cover.suffix.lower()
            self.files[cover_path] = cover.read_bytes()
        self.files["style.css"] = css.encode("utf-8")
        self.files["nav.xhtml"] = self.nav(depth).encode("utf-8")
        self.files["package.opf"] = self.opf(modified, cover_path).encode("utf-8")
        container = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            '  <rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>\n'
            "</container>\n"
        )
        stamp = max(modified, datetime(1980, 1, 1, tzinfo=timezone.utc)).timetuple()[:6]

        def entry(name: str) -> zipfile.ZipInfo:
            info = zipfile.ZipInfo(name, stamp)
            info.create_system, info.external_attr = 3, 0o644 << 16  # the same bytes on every platform
            return info

        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w") as z:
            # The media type comes first and is not compressed: this is how an EPUB is recognized.
            z.writestr(entry("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
            z.writestr(entry("META-INF/container.xml"), container, zipfile.ZIP_DEFLATED)
            for path in sorted(self.files):
                z.writestr(entry("EPUB/" + path), self.files[path], zipfile.ZIP_DEFLATED)


def clean(text: str) -> str:
    """Without the control characters XML does not allow."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]", "", text)


def nest(headings: list[tuple[int, str, str]], href: str, depth: int) -> list[dict]:
    """Headings as a tree, `depth` levels deep from the highest level present."""
    if not headings or depth <= 0:
        return []
    top = min(h[0] for h in headings)
    root: list[dict] = []
    path: list[tuple[int, list[dict]]] = [(top - 1, root)]
    for level, anchor, title in headings:
        if level - top >= depth:
            continue
        while path[-1][0] >= level:
            path.pop()
        item = {"title": title, "href": f"{href}#{anchor}", "kids": []}
        path[-1][1].append(item)
        path.append((level, item["kids"]))
    return root


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("source", type=Path, help="an HTML page, or the folder of a bundle")
    p.add_argument("-o", "--output", type=Path, required=True, help="the EPUB file to write")
    p.add_argument("--title", help="title of the book (default: read from the pages)")
    p.add_argument("--author", action="append", help="author, repeatable (default: read from the pages)")
    p.add_argument("--lang", help="language tag (default: the lang attribute of the pages)")
    p.add_argument("--identifier", help="unique identifier: a DOI, a URL, ... (default: derived from title and authors)")
    p.add_argument("--date", help="publication date, as YYYY or YYYY-MM-DD")
    p.add_argument("--cover", type=Path, help="cover image (PNG or JPEG) shown in the library of the reading app")
    p.add_argument("--css", type=Path, action="append", default=[], help="extra stylesheet, repeatable")
    p.add_argument("--base-url", help="address of the web edition: links to files that are not in the book point there")
    p.add_argument("--toc-depth", type=int, default=2, help="levels of headings listed under each chapter (default: 2)")
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")

    content_css = Path(__file__).with_name("web-content.css")
    if not content_css.is_file():
        sys.exit(f"{content_css} not found: epub.py is kept next to the stylesheets of the layer")
    if not args.source.exists():
        sys.exit(f"{args.source} not found")
    if args.cover is not None and args.cover.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        sys.exit("the cover must be a PNG or JPEG image")

    book = Book(args.source, args.base_url)
    m = book.meta
    m["title"] = args.title or m["title"] or args.source.stem
    m["authors"] = args.author or m["authors"]
    m["lang"] = args.lang or m["lang"]
    m["date"] = args.date
    seed = args.base_url or "|".join([m["title"], *m["authors"], m["lang"]])
    m["identifier"] = args.identifier or "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
    css = [m["typst-css"], content_css.read_text(encoding="utf-8"), EPUB_CSS] + [f.read_text(encoding="utf-8") for f in args.css]
    book.write(args.output, "\n".join(css), args.toc_depth, args.cover)

    for note in dict.fromkeys(book.notes):
        print(f"note: {note}")
    pages = [e for e in book.outline if "page" in e]
    print(f"{args.output}: {len(pages)} chapter(s), {len(book.files) - len(pages) - 3} image(s), {args.output.stat().st_size / 1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
