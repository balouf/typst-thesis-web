"""Compile the examples and check that nothing is lost on the way to HTML.

    uv run --with pytest pytest -q

Needs `typst` on PATH. HTML export is experimental and its output may change
between Typst versions: these tests are what tells us when it does. The
expected numbers are the census of each example's output (see tools/check.py).
"""

from __future__ import annotations

import json
import subprocess
import sys
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
        {"headings": 6, "statements": 4, "html-figures": 5, "captions": 5, "svg-frames": 10, "block-equations": 4,
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


def test_vendored_copies_are_current():
    done = run([sys.executable, str(TOOLS / "sync.py"), "--check"], ".")
    assert done.returncode == 0, done.stdout
