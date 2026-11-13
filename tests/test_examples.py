"""Compile the examples and check that nothing is lost on the way to HTML.

    uv run --with pytest pytest -q

Needs `typst` on PATH. HTML export is experimental and its output may change
between Typst versions: these tests are what tells us when it does. The
expected numbers are the census of each example's output (see tools/check.py).

The EPUB editions are also run through EPUBCheck when the environment variable
EPUBCHECK holds the path of epubcheck.jar (and `java` is on PATH).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"

# name: (working directory, arguments of check.py, expected census of the output)
EXAMPLES = {
    "article": (
        "examples/article",
        ["web.typ"],
        {"headings": 3, "statements": 2, "html-figures": 1, "captions": 1, "svg-frames": 1, "block-equations": 1,
         "numbered-equations": 1, "inline-equations": 11, "footnotes": 1, "citations": 2},
    ),
    # A PDF template written with no thought for HTML: every rule of the layer.
    "torture": (
        ".",
        ["examples/torture/web.typ", "--root", "."],
        {"headings": 10, "statements": 4, "html-figures": 5, "captions": 5, "svg-frames": 10, "block-equations": 4,
         "numbered-equations": 3, "inline-equations": 6, "footnotes": 1, "citations": 2},
    ),
    "thesis-fr": (
        "examples/thesis",
        ["main-html.typ", "--format", "bundle", "--input", "lang=fr"],
        {"headings": 5, "statements": 3, "html-figures": 1, "captions": 1, "svg-frames": 1, "block-equations": 2,
         "numbered-equations": 2, "inline-equations": 4, "footnotes": 2, "citations": 2},
    ),
    "thesis-en": (
        "examples/thesis",
        ["main-html.typ", "--format", "bundle", "--input", "lang=en"],
        {"headings": 5, "statements": 3, "html-figures": 1, "captions": 1, "svg-frames": 1, "block-equations": 2,
         "numbered-equations": 2, "inline-equations": 4, "footnotes": 2, "citations": 2},
    ),
}

# PDF editions: (working directory, arguments of `typst compile`)
PDFS = {
    "article": ("examples/article", ["main.typ"]),
    "torture": (".", ["--root", ".", "examples/torture/main.typ"]),
    "thesis-fr": ("examples/thesis", ["--input", "lang=fr", "main.typ"]),
    "thesis-en": ("examples/thesis", ["--input", "lang=en", "main.typ"]),
}


def run(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO / cwd, capture_output=True, text=True, encoding="utf-8")


@pytest.mark.parametrize("name", EXAMPLES)
def test_web_edition_loses_nothing(name: str, tmp_path: Path):
    cwd, args, expected = EXAMPLES[name]
    out = tmp_path / ("site" if "bundle" in args else "out.html")
    done = run([sys.executable, str(TOOLS / "check.py"), *args, "--json", "--out", str(out)], cwd)
    report = json.loads(done.stdout)
    assert report["errors"] == []
    assert report["warnings"] == []
    assert done.returncode == 0
    found = {key: report["census"]["output"].get(key, 0) for key in expected}
    assert found == expected


@pytest.mark.parametrize("name", PDFS)
def test_pdf_edition_compiles(name: str, tmp_path: Path):
    cwd, args = PDFS[name]
    done = run(["typst", "compile", *args, str(tmp_path / "out.pdf")], cwd)
    assert done.returncode == 0, done.stderr
    assert "warning" not in done.stderr, done.stderr


def test_thesis_site_pages(tmp_path: Path):
    """The bundle has one page per `chapter(...)`, cross-linked by relative paths."""
    out = tmp_path / "fr"
    done = run(["typst", "compile", "--features", "html,bundle", "--format", "bundle", "--input", "lang=fr", "main-html.typ", str(out)], "examples/thesis")
    assert done.returncode == 0, done.stderr
    assert sorted(p.name for p in out.glob("*.html")) == ["bibliography.html", "example.html", "index.html", "second.html"]
    assert (out / "assets" / "web.js").is_file()
    second = (out / "second.html").read_text(encoding="utf-8")
    assert 'href="example.html#thm-example"' in second  # a label becomes a stable anchor
    assert 'href="../en/second.html"' in second  # language switch
    assert '<li class="active"><a href="second.html">' in second


def test_heading_ids_and_emails(tmp_path: Path):
    """Headings get stable ids; `emails: false` keeps the addresses off the page."""
    cmd = ["typst", "compile", "--root", ".", "--features", "html", "examples/torture/web.typ"]
    out = tmp_path / "torture.html"
    done = run([*cmd, str(out)], ".")
    assert done.returncode == 0, done.stderr
    page = out.read_text(encoding="utf-8")
    assert 'id="sec-math"' in page  # from the label
    assert 'id="headings-without-a-label"' in page  # from the text
    assert 'id="further-reading"' in page and 'id="further-reading-2"' in page  # same text twice
    assert 'id="erdos-renyi-graphs"' in page  # any accented letter keeps its base
    assert "mailto:ada@example.org" in page
    done = run([*cmd, "--input", "emails=false", str(out)], ".")
    assert done.returncode == 0, done.stderr
    assert "ada@example.org" not in out.read_text(encoding="utf-8")


def test_content_stylesheet_is_embeddable():
    """web-content.css must work inside another site: every rule is scoped to
    .typst, or names something only Typst or web.typ emits."""
    css = re.sub(r"/\*.*?\*/", "", (REPO / "lib" / "web-content.css").read_text(encoding="utf-8"), flags=re.S)
    css = re.sub(r"@media[^{]*\{", "", css)
    allowed = (":where(.typst) ", ".article-header ", 'section[role="doc-endnotes"]', '[role="doc-backlink"]')
    selectors = []
    for group in re.findall(r"([^{}]+)\{[^{}]*\}", css):
        depth, start = 0, 0
        for i, char in enumerate(group + ","):  # split on the commas outside (...) and [...]
            depth += (char in "([") - (char in ")]")
            if char == "," and depth == 0:
                selectors.append(group[start:i].strip())
                start = i + 1
    assert len(selectors) > 50
    assert [s for s in selectors if not s.startswith(allowed)] == []


# EPUB editions: (working directory, typst arguments, output name)
BOOKS = {
    "torture": (".", ["--root", ".", "--features", "html", "examples/torture/web.typ"], "torture.html"),
    "torture-svg": (".", ["--root", ".", "--features", "html", "--input", "math=svg", "examples/torture/web.typ"], "torture.html"),
    "thesis-fr": ("examples/thesis", ["--features", "html,bundle", "--format", "bundle", "--input", "lang=fr", "main-html.typ"], "site"),
}
XHTML = "{http://www.w3.org/1999/xhtml}"
OPF = "{http://www.idpf.org/2007/opf}"


def make_book(name: str, tmp_path: Path) -> Path:
    cwd, args, out = BOOKS[name]
    done = run(["typst", "compile", *args, str(tmp_path / out)], cwd)
    assert done.returncode == 0, done.stderr
    book = tmp_path / f"{name}.epub"
    done = subprocess.run(
        [sys.executable, str(REPO / "lib" / "epub.py"), str(tmp_path / out), "-o", str(book)],
        capture_output=True, text=True, encoding="utf-8", env={**os.environ, "SOURCE_DATE_EPOCH": "0"},
    )
    assert done.returncode == 0, done.stderr
    return book


@pytest.mark.parametrize("name", BOOKS)
def test_epub_edition(name: str, tmp_path: Path):
    """The book is a well-formed EPUB: container, manifest, unique ids, links."""
    book = make_book(name, tmp_path)
    with zipfile.ZipFile(book) as z:
        first = z.infolist()[0]
        assert (first.filename, first.compress_type, z.read(first)) == ("mimetype", zipfile.ZIP_STORED, b"application/epub+zip")
        files = {n.removeprefix("EPUB/"): z.read(n) for n in z.namelist() if n.startswith("EPUB/")}
    package = ET.fromstring(files["package.opf"])
    items = {i.get("id"): i for i in package.iter(OPF + "item")}
    assert {i.get("href") for i in items.values()} == set(files) - {"package.opf"}
    spine = [items[r.get("idref")].get("href") for r in package.iter(OPF + "itemref")]

    ids, links = {}, []
    for path in spine + ["nav.xhtml"]:
        page = ET.fromstring(files[path])  # raises on anything that is not XML
        found = [e.get("id") for e in page.iter() if e.get("id")]
        assert len(found) == len(set(found)), f"duplicate ids in {path}"
        ids[path] = set(found)
        assert not {e.tag for e in page.iter()} & {XHTML + "script", XHTML + "style", XHTML + "aside"}
        folder = Path(path).parent
        links += [(path, (folder / a.get("href")).as_posix() if not a.get("href").startswith("#") else path + a.get("href"))
                  for a in page.iter(XHTML + "a") if a.get("href") and not re.match(r"[a-z][a-z0-9+.-]*:", a.get("href"))]
    for source, target in links:
        path, _, fragment = target.partition("#")
        assert path in ids, f"{source}: link to {target}"
        assert not fragment or fragment in ids[path], f"{source}: link to {target}"

    text = files[spine[-1 if name == "thesis-fr" else 0]].decode("utf-8")
    if name == "thesis-fr":
        assert spine == ["text/index.xhtml", "text/example.xhtml", "text/second.xhtml", "text/bibliography.xhtml"]
        nav = files["nav.xhtml"].decode("utf-8")
        assert "<span>Partie I — Exemples</span>" in nav and 'href="text/second.xhtml#sec-second-section"' in nav
        assert "EPUB" not in files["text/index.xhtml"].decode("utf-8")  # the download links are `web-only`
    else:
        math = "mathml" in (items["page-1"].get("properties") or "")
        assert math == (name == "torture") and ("<math" in text) == math
        assert 'epub:type="noteref"' in text and "data:image" not in text

    again = tmp_path / "again"
    again.mkdir()
    shutil.copy(book, again / "first.epub")
    assert make_book(name, tmp_path).read_bytes() == (again / "first.epub").read_bytes()  # reproducible


@pytest.mark.skipif(not os.environ.get("EPUBCHECK"), reason="EPUBCHECK (path of epubcheck.jar) is not set")
@pytest.mark.parametrize("name", BOOKS)
def test_epub_edition_passes_epubcheck(name: str, tmp_path: Path):
    book = make_book(name, tmp_path)
    # EPUBCheck writes in the language and the encoding of the system.
    done = subprocess.run(["java", "-jar", os.environ["EPUBCHECK"], "--failonwarnings", str(book)], capture_output=True, text=True, errors="replace")
    assert done.returncode == 0, done.stdout + done.stderr


def test_head_tool(tmp_path: Path):
    """tools/head.py moves the stylesheet to <head> and nothing else."""
    spec = importlib.util.spec_from_file_location("head", TOOLS / "head.py")
    head = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(head)
    out = tmp_path / "torture.html"
    done = run(["typst", "compile", "--root", ".", "--features", "html", "examples/torture/web.typ", str(out)], ".")
    assert done.returncode == 0, done.stderr
    before = out.read_text(encoding="utf-8")
    after = head.hoist(before)

    def body(page: str) -> str:
        return page[page.index("<body", page.index("</head>")):]

    assert "<style" in body(before) and "<style" not in body(after)
    assert re.sub(r"<style>.*?</style>", "", body(before), flags=re.S) == body(after)
    assert len(after) == len(before) and head.hoist(after) == after


def test_layer_files_share_a_version():
    version = re.search(r"// Version (\S+)", (REPO / "lib" / "web.typ").read_text(encoding="utf-8"))[1]
    assert f"Version {version} " in (REPO / "lib" / "epub.py").read_text(encoding="utf-8")


def test_vendored_copies_are_current():
    done = run([sys.executable, str(TOOLS / "sync.py"), "--check"], ".")
    assert done.returncode == 0, done.stdout
