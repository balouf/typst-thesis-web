# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check a Typst web edition: did anything get lost on the way to HTML?

    uv run tools/check.py web.typ [--root DIR] [--font-path DIR] [--input k=v]
    uv run tools/check.py site.typ --format bundle

The script compiles the entry (HTML or bundle) and reports, in order of trust:

1. compiler diagnostics: Typst warns, with file and line, about every element
   it ignores. Elements that carry content are errors, pure spacing is benign;
2. integrity of the HTML: internal links without a target, duplicate ids,
   empty anchored blocks (a dropped figure leaves `<div id=...></div>`), block
   elements nested in inline ones, HTML elements inside an equation,
   collapsed SVG frames;
3. a census: headings, figures, equations, notes counted in the Typst document
   (`typst eval`) and in the HTML. What sits inside an SVG frame or is repeated
   in a table of contents is counted on the Typst side only, so the HTML may be
   lower; it should never be higher.

Exit status is 1 when an error is found (and on warnings with --strict), so the
script can gate a CI job. `--json` prints the full report for another program.
Only the standard library is used.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag

# Elements whose loss costs nothing: they hold no content.
BENIGN = {"h", "v", "pagebreak", "colbreak", "page", "parbreak", "linebreak"}

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
INLINE = {"a", "abbr", "b", "cite", "code", "em", "i", "kbd", "mark", "q", "s", "small", "span", "strong", "sub", "sup", "u"}
BLOCK = {
    "address", "article", "aside", "blockquote", "details", "div", "dl", "fieldset", "figcaption", "figure",
    "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre",
    "section", "table", "ul",
}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# Page furniture, where the census would count things twice (tables of contents).
CHROME = {"nav", "aside", "footer"}

CENSUS_EXPR = """(
  headings: query(heading).len(),
  figures: query(figure).map(f => if type(f.kind) == str { f.kind } else { repr(f.kind) }),
  captions: query(figure).filter(f => f.caption != none).len(),
  block-equations: query(math.equation.where(block: true)).len(),
  numbered-equations: query(math.equation.where(block: true)).filter(e => e.numbering != none).len(),
  inline-equations: query(math.equation.where(block: false)).len(),
  footnotes: query(footnote).len(),
  citations: query(cite).len(),
)"""

DIAGNOSTIC = re.compile(r"^(?P<where>.*?):(?P<line>\d+):(?P<col>\d+): (?P<level>warning|error): (?P<message>.*)$")
IGNORED = re.compile(r"^(?P<what>.+?) (?:set rule )?was ignored during (?P<stage>HTML|MathML) export")


# ---------------------------------------------------------------------------
# Typst
# ---------------------------------------------------------------------------

def typst_args(args: argparse.Namespace) -> list[str]:
    out: list[str] = []
    if args.root:
        out += ["--root", args.root]
    for path in args.font_path:
        out += ["--font-path", path]
    for pair in args.input:
        out += ["--input", pair]
    return out


def compile_entry(args: argparse.Namespace, out: Path) -> tuple[int, list[dict]]:
    features = "html,bundle" if args.format == "bundle" else "html"
    cmd = ["typst", "compile", "--features", features, "--format", args.format, "--diagnostic-format", "short"]
    cmd += typst_args(args) + [args.entry, str(out)]
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return done.returncode, parse_diagnostics(done.stderr)


def parse_diagnostics(stderr: str) -> list[dict]:
    """Classify each diagnostic as error / dropped / benign / other."""
    found = []
    for line in stderr.splitlines():
        m = DIAGNOSTIC.match(line.strip())
        if not m:
            # Diagnostics without a position ("error: file not found ...").
            m2 = re.match(r"^(warning|error): (.*)$", line.strip())
            if m2 and "under active development" not in m2[2] and "export is experimental" not in m2[2]:
                found.append({"class": "error" if m2[1] == "error" else "other", "where": "", "line": 0, "message": m2[2]})
            continue
        where = re.sub(r"^\\\\\?\\", "", m["where"])
        item = {"where": where, "line": int(m["line"]), "message": m["message"]}
        ignored = IGNORED.match(m["message"])
        if m["level"] == "error":
            item["class"] = "error"
        elif ignored:
            what = ignored["what"].split()[-1]
            item["what"] = what
            item["class"] = "benign" if ignored["stage"] == "HTML" and what in BENIGN else "dropped"
        else:
            item["class"] = "other"
        found.append(item)
    return found


def census_of_source(args: argparse.Namespace, target: str) -> dict | None:
    features = "html,bundle" if target == "bundle" else "html"
    cmd = ["typst", "eval", "--features", features, "--target", target, "--in", args.entry]
    cmd += typst_args(args) + [CENSUS_EXPR]
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        return None
    raw = json.loads(done.stdout)
    kinds = Counter(raw.pop("figures"))
    raw["figures"] = sum(kinds.values())
    raw["figure-kinds"] = dict(sorted(kinds.items()))
    return raw


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

class Page(HTMLParser):
    """One HTML file: ids, links, census, structural problems."""

    def __init__(self, name: str):
        super().__init__(convert_charrefs=True)
        self.name = name
        self.stack: list[dict] = []
        self.ids: list[tuple[str, bool]] = []  # (id, inside svg)
        self.links: list[str] = []
        self.count: Counter = Counter()
        self.nesting: Counter = Counter()
        self.empty: list[str] = []
        self.tiny: list[str] = []

    def _inside(self, tags: set[str]) -> bool:
        return any(e["tag"] in tags for e in self.stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        a = {k: (v or "") for k, v in attrs}
        in_svg = self._inside({"svg"})
        in_math = self._inside({"math"})
        if self.stack:
            self.stack[-1]["content"] = True
        if in_math and (tag in INLINE or tag in BLOCK):
            self.nesting[f"<{tag}> inside <math>"] += 1  # not valid MathML: an EPUB is refused for it

        if "id" in a:
            self.ids.append((a["id"], in_svg or tag == "svg"))
        href = a.get("href", "")
        if tag == "a" and href and not re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I):
            self.links.append(href)

        if not in_svg and not in_math:
            classes = a.get("class", "").split()
            role = a.get("role", "")
            chrome = self._inside(CHROME)
            if tag in BLOCK:
                for e in reversed(self.stack):
                    if e["tag"] in INLINE or e["tag"] == "p":
                        self.nesting[f"<{tag}> inside <{e['tag']}>"] += 1
                        break
            if tag == "svg":
                self.count["svg-frames"] += 1
                width = re.match(r"([\d.]+)pt", a.get("width", ""))
                if width and float(width[1]) < 20:
                    self.tiny.append(f"{a.get('width')} x {a.get('height')}")
            if not chrome:
                # A cover page may have a hand-written <h1> in a <header>.
                if tag in HEADINGS and self._inside({"main"}) and not self._inside({"header"}):
                    self.count["headings"] += 1
                if "env" in classes:
                    self.count["statements"] += 1
                if tag == "figure":
                    self.count["html-figures"] += 1
                if tag == "figcaption":
                    self.count["captions"] += 1
                if tag == "math":
                    self.count["block-equations" if a.get("display") == "block" else "inline-equations"] += 1
                if "eq-num" in classes:
                    self.count["numbered-equations"] += 1
                if role == "doc-noteref":
                    self.count["footnotes"] += 1
                if role == "doc-biblioref":
                    self.count["citations"] += 1

        if tag not in VOID:
            self.stack.append({"tag": tag, "id": a.get("id"), "content": False})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                e = self.stack[i]
                del self.stack[i:]
                if e["id"] and not e["content"] and tag in BLOCK and not self._inside({"svg"}):
                    self.empty.append(f"<{tag} id=\"{e['id']}\">")
                return

    def handle_data(self, data: str):
        if self.stack and data.strip():
            self.stack[-1]["content"] = True


def read_pages(out: Path) -> dict[str, Page]:
    files = [out] if out.is_file() else sorted(out.rglob("*.html"))
    base = out.parent if out.is_file() else out
    pages = {}
    for f in files:
        page = Page(f.relative_to(base).as_posix())
        page.feed(f.read_text(encoding="utf-8"))
        pages[page.name] = page
    return pages


def check_pages(pages: dict[str, Page]) -> dict:
    report: dict = {"dangling-links": [], "duplicate-ids": [], "colon-ids": 0, "empty-anchored": [], "nesting": {}, "tiny-frames": []}
    targets = {name: {i for i, _ in p.ids} for name, p in pages.items()}
    nesting: Counter = Counter()
    for name, page in pages.items():
        here = Path(name).parent
        for href in page.links:
            path, fragment = urldefrag(href)
            dest = name if not path else (here / unquote(path)).as_posix()
            # Normalise "a/../b".
            parts: list[str] = []
            for part in dest.split("/"):
                if part == "..":
                    if parts:
                        parts.pop()
                    else:
                        parts = [".."]
                        break
                elif part not in ("", "."):
                    parts.append(part)
            dest = "/".join(parts)
            if dest not in pages:
                if dest.endswith(".html") and not dest.startswith(".."):
                    report["dangling-links"].append(f"{name}: {href} (no such page)")
                continue
            if fragment and unquote(fragment) not in targets[dest]:
                report["dangling-links"].append(f"{name}: {href}")
        seen = Counter(i for i, in_svg in page.ids if not in_svg)
        report["duplicate-ids"] += [f"{name}: #{i} (x{n})" for i, n in seen.items() if n > 1]
        report["colon-ids"] += sum(1 for i, in_svg in page.ids if ":" in i and not in_svg)
        report["empty-anchored"] += [f"{name}: {e}" for e in page.empty]
        report["tiny-frames"] += [f"{name}: {t}" for t in page.tiny]
        nesting.update(page.nesting)
    report["nesting"] = dict(nesting.most_common())
    return report


def census_of_html(pages: dict[str, Page]) -> dict:
    total: Counter = Counter()
    for page in pages.values():
        total.update(page.count)
    total["figures"] = total["statements"] + total["html-figures"]
    return dict(total)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

COMPARED = ["headings", "figures", "block-equations", "numbered-equations", "inline-equations", "footnotes", "citations"]


def build_report(args: argparse.Namespace, out: Path) -> dict:
    code, diagnostics = compile_entry(args, out)
    report: dict = {"entry": args.entry, "format": args.format, "compiled": code == 0, "diagnostics": diagnostics}
    errors: list[str] = []
    warnings: list[str] = []

    by_class: dict[str, list[dict]] = {}
    for d in diagnostics:
        by_class.setdefault(d["class"], []).append(d)
    for d in by_class.get("error", []):
        errors.append(f"compile error at {d['where']}:{d['line']}: {d['message']}")
    for d in by_class.get("dropped", []):
        errors.append(f"content dropped at {d['where']}:{d['line']}: {d['message']}")
    for d in by_class.get("other", []):
        warnings.append(f"{d['where']}:{d['line']}: {d['message']}")
    if code != 0:
        if not errors:
            errors.append("typst compile failed")
        report.update(errors=errors, warnings=warnings)
        return report

    pages = read_pages(out)
    html = check_pages(pages)
    report["pages"] = len(pages)
    report["size"] = sum(f.stat().st_size for f in ([out] if out.is_file() else out.rglob("*") if out.is_dir() else []) if f.is_file())
    report["html"] = html
    errors += [f"link without target: {x}" for x in html["dangling-links"]]
    errors += [f"duplicate id: {x}" for x in html["duplicate-ids"]]
    errors += [f"empty anchored block (dropped content?): {x}" for x in html["empty-anchored"]]
    errors += [f"invalid nesting: {k} (x{n})" for k, n in html["nesting"].items()]
    warnings += [f"collapsed SVG frame: {x}" for x in html["tiny-frames"]]
    if html["colon-ids"]:
        warnings.append(f"{html['colon-ids']} ids contain ':' (invalid in EPUB, awkward in CSS)")

    found = census_of_html(pages)
    source = census_of_source(args, args.format)
    report["census"] = {"document": source, "output": found}
    if source is None:
        warnings.append("census unavailable: typst eval failed on the entry")
    else:
        for key in COMPARED:
            want, got = source[key], found.get(key, 0)
            if got > want:
                warnings.append(f"census: {key}: {got} in the output, {want} in the document")
            elif got < want:
                report.setdefault("not-in-html", {})[key] = want - got
    report.update(errors=errors, warnings=warnings)
    return report


def print_report(r: dict) -> None:
    print(f"{r['entry']} -> {r['format']}" + (f", {r['pages']} page(s), {r['size'] / 1024:.0f} KiB" if r.get("pages") else ""))
    counts = Counter(d["class"] for d in r["diagnostics"])
    benign = Counter(d.get("what", "?") for d in r["diagnostics"] if d["class"] == "benign")
    line = f"  diagnostics: {counts['error']} error(s), {counts['dropped']} content drop(s), {counts['benign']} benign"
    if benign:
        line += " (" + ", ".join(f"{k} x{n}" for k, n in sorted(benign.items())) + ")"
    print(line)
    if "census" in r:
        c = r["census"]
        truth = c["document"] or {}
        print("  census                document   output")
        for key in COMPARED:
            want, got = truth.get(key, "?"), c["output"].get(key, 0)
            note = ""
            if isinstance(want, int) and got < want:
                note = f"   ({want - got} inside SVG frames, or not rendered)"
            print(f"    {key:<20}{want!s:>8} {got:>8}{note}")
        out = c["output"]
        print(f"    of which: {out.get('statements', 0)} statements, {out.get('html-figures', 0)} <figure>, "
              f"{out.get('captions', 0)} captions, {out.get('svg-frames', 0)} SVG frames")
        if truth.get("figure-kinds"):
            print("    figure kinds: " + ", ".join(f"{k} x{n}" for k, n in truth["figure-kinds"].items()))
    for w in r["warnings"]:
        print(f"  warning: {w}")
    for e in r["errors"]:
        print(f"  ERROR: {e}")
    print("  => " + ("FAILED" if r["errors"] else "ok" + (f", {len(r['warnings'])} warning(s)" if r["warnings"] else "")))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("entry", help="web entry file (.typ)")
    p.add_argument("--format", choices=["html", "bundle"], default="html")
    p.add_argument("--root", help="project root, passed to typst")
    p.add_argument("--font-path", action="append", default=[], help="extra font directory, passed to typst")
    p.add_argument("--input", action="append", default=[], metavar="KEY=VALUE", help="sys.inputs entry, passed to typst")
    p.add_argument("--out", help="keep the compiled output here (a file for html, a directory for bundle)")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    p.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    args = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    if shutil.which("typst") is None:
        print("typst not found on PATH", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
        else:
            out = Path(tmp) / ("site" if args.format == "bundle" else "out.html")
        report = build_report(args, out)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)
    return 1 if report["errors"] or (args.strict and report["warnings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
