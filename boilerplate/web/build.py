# /// script
# dependencies = ["beautifulsoup4", "pagefind[extended]"]
# ///
"""
Build script for the bilingual HTML thesis website.

Usage:
    uv run web/build.py                 # Build both languages + PDFs
    uv run web/build.py --skip-lang en  # Build French only
    uv run web/build.py --skip-pdf      # Skip PDF compilation
    uv run web/build.py --skip-compile  # Skip Typst compilation (reuse full.html)
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("Error: beautifulsoup4 required. Run with: uv run web/build.py")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration  # TODO: adapt this entire section to your thesis
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
DIST_DIR = WEB_DIR / "dist"
ASSETS_SRC = WEB_DIR / "assets"

LANGS = ["fr", "en"]

# Chapter metadata: (section_id, output_filename, short_title)
# TODO: adapt — add your own chapters here, one entry per section in your Typst source
CHAPTERS = {
    "fr": [
        ("cover", "index.html", "Accueil"),
        ("example", "example.html", "Chapitre d'exemple"),
        ("bibliography", "bibliography.html", "Bibliographie"),
    ],
    "en": [
        ("cover", "index.html", "Home"),
        ("example", "example.html", "Example Chapter"),
        ("bibliography", "bibliography.html", "Bibliography"),
    ],
}

# Sub-level items: rendered indented and smaller in the sidebar
# TODO: adapt — list section_ids that should appear as sub-items (e.g. sub-sections of a chapter)
SUB_CHAPTERS: set[str] = set()

# TODO: adapt — group chapters into parts; use (None, [...]) for a flat list, or ("Part Title", [...]) for named parts
PARTS = {
    "fr": [
        (None, ["cover", "example", "bibliography"]),
    ],
    "en": [
        (None, ["cover", "example", "bibliography"]),
    ],
}

# TODO: adapt — set your thesis title in each language
THESIS_TITLE = {
    "fr": "Titre de la thèse",
    "en": "Thesis Title",
}

LANG_LABELS = {
    "fr": "Français",
    "en": "English",
}

GITHUB_URL = "https://github.com/your-user/your-repo"  # TODO: adapt
BASE_URL = "/"  # Overridden by --base-url CLI arg

# ---------------------------------------------------------------------------
# SVG Icons (inline, no external dependency)
# ---------------------------------------------------------------------------

ICON_HAMBURGER = '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 5h14M3 10h14M3 15h14"/></svg>'
ICON_SEARCH = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>'
ICON_GITHUB = '<svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>'
ICON_TOC = '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 4h14M3 8h10M3 12h12M3 16h8"/></svg>'
ICON_THEME_LIGHT = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'


# ---------------------------------------------------------------------------
# Step 1: Compile Typst -> HTML
# ---------------------------------------------------------------------------

def compile_typst(lang: str) -> Path:
    """Compile the thesis to a single HTML file for one language."""
    full_html = DIST_DIR / f"full-{lang}.html"
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "typst", "compile",
        "--features", "html",
        "--format", "html",
        "--input", f"lang={lang}",
        "--input", "html=true",
        str(ROOT / "main-html.typ"),
        str(full_html),
    ]
    print(f"  Compiling HTML ({lang}): {' '.join(cmd[-3:])}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        for line in result.stderr.splitlines():
            if line.startswith("error:"):
                print(line, file=sys.stderr)
        sys.exit(1)
    warnings = [l for l in result.stderr.splitlines() if l.startswith("warning:")]
    if warnings:
        print(f"    ({len(warnings)} warnings suppressed)")
    print(f"    -> {full_html.name} ({full_html.stat().st_size // 1024} KB)")
    return full_html


# ---------------------------------------------------------------------------
# Step 2: Compile PDFs
# ---------------------------------------------------------------------------

def compile_pdfs(langs: list[str]):
    """Compile thesis PDFs for each language."""
    pdf_dir = DIST_DIR / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    for lang in langs:
        out = pdf_dir / f"thesis-{lang}.pdf"
        cmd = [
            "typst", "compile",
            "--input", f"lang={lang}",
            str(ROOT / "main.typ"),
            str(out),
        ]
        print(f"  Compiling PDF ({lang})...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            for line in result.stderr.splitlines():
                if line.startswith("error:"):
                    print(line, file=sys.stderr)
            print(f"  WARNING: PDF compilation failed for {lang}", file=sys.stderr)
            continue
        warnings = [l for l in result.stderr.splitlines() if l.startswith("warning:")]
        if warnings:
            print(f"    ({len(warnings)} warnings suppressed)")
        print(f"    -> pdf/thesis-{lang}.pdf ({out.stat().st_size // 1024} KB)")


# ---------------------------------------------------------------------------
# Step 3: Parse and split into chapters
# ---------------------------------------------------------------------------

def extract_local_toc(section: Tag) -> list[dict]:
    """Extract h2/h3 headings from a section for the local TOC."""
    toc = []
    for heading in section.find_all(["h2", "h3"]):
        heading_id = heading.get("id", "")
        if not heading_id:
            text = heading.get_text(strip=True)
            heading_id = re.sub(r"[^\w-]", "-", text.lower())[:60]
            heading["id"] = heading_id
        toc.append({
            "level": int(heading.name[1]),
            "id": heading_id,
            "text": heading.get_text(strip=True),
        })
    return toc


def build_global_nav(chapters: list[tuple], parts: list[tuple], current_id: str) -> str:
    """Build the global navigation sidebar HTML."""
    chapter_map = {sid: (fname, title) for sid, fname, title in chapters}
    lines = ['<nav class="global-nav" aria-label="Global navigation">']
    for part_title, section_ids in parts:
        if part_title:
            lines.append(f'  <div class="nav-part">{part_title}</div>')
        lines.append("  <ul>")
        for sid in section_ids:
            fname, title = chapter_map[sid]
            classes = []
            if sid == current_id:
                classes.append("active")
            if sid in SUB_CHAPTERS:
                classes.append("nav-sub")
            cls = f' class="{" ".join(classes)}"' if classes else ""
            lines.append(f'    <li{cls}><a href="{fname}">{title}</a></li>')
        lines.append("  </ul>")
    lines.append("</nav>")
    return "\n".join(lines)


def build_local_toc(toc: list[dict], lang: str) -> str:
    """Build the local TOC sidebar HTML."""
    if not toc:
        return ""
    title = "Sur cette page" if lang == "fr" else "On this page"
    lines = [f'<nav class="local-toc" aria-label="{title}">']
    lines.append(f"  <h3>{title}</h3>")
    lines.append("  <ul>")
    for item in toc:
        indent = "    " if item["level"] == 2 else "      "
        cls = "" if item["level"] == 2 else ' class="toc-l3"'
        lines.append(f'{indent}<li{cls}><a href="#{item["id"]}">{item["text"]}</a></li>')
    lines.append("  </ul>")
    lines.append("</nav>")
    return "\n".join(lines)


def build_page(
    section_html: str,
    global_nav: str,
    local_toc: str,
    title: str,
    thesis_title: str,
    prev_link: tuple | None,
    next_link: tuple | None,
    lang: str,
    current_file: str,
) -> str:
    """Assemble a complete HTML page with topbar."""
    other_lang = "en" if lang == "fr" else "fr"
    other_label = LANG_LABELS[other_lang]

    prev_btn = f'<a href="{prev_link[0]}" class="nav-prev">&larr; {prev_link[1]}</a>' if prev_link else '<span></span>'
    next_btn = f'<a href="{next_link[0]}" class="nav-next">{next_link[1]} &rarr;</a>' if next_link else '<span></span>'

    search_label = "Rechercher" if lang == "fr" else "Search"

    return f"""<!DOCTYPE html>
<html lang="{lang}" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — {thesis_title}</title>
  <meta name="author" content="Fabien Mathieu">
  <meta name="pagefind-base" content="{BASE_URL}">
  <link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="../assets/style.css">
  <script>
    (function(){{
      var t=localStorage.getItem("theme")||"auto";
      if(t==="auto")t=matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light";
      document.documentElement.dataset.theme=t;
    }})();
  </script>
</head>
<body>
  <header class="topbar" data-pagefind-ignore>
    <div class="topbar-left">
      <button class="sidebar-toggle-btn" id="sidebar-toggle-left" aria-label="Menu">{ICON_HAMBURGER}</button>
      <a href="index.html" class="topbar-title">{thesis_title}</a>
    </div>
    <div class="topbar-right">
      <button class="search-trigger" aria-label="{search_label} (Ctrl+K)">{ICON_SEARCH} <kbd>Ctrl+K</kbd></button>
      <button class="theme-toggle" aria-label="Toggle theme" title="Toggle theme">{ICON_THEME_LIGHT}</button>
      <a href="../{other_lang}/{current_file}" class="lang-switch" title="{other_label}">{other_lang.upper()}</a>
      <a href="{GITHUB_URL}" class="github-link" aria-label="GitHub" target="_blank" rel="noopener">{ICON_GITHUB}</a>
      <button class="sidebar-toggle-btn" id="sidebar-toggle-right" aria-label="Table of contents">{ICON_TOC}</button>
    </div>
  </header>
  <div class="layout">
    <aside class="sidebar-left" data-pagefind-ignore>
      {global_nav}
    </aside>
    <main class="content">
      {section_html}
      <footer class="page-nav" data-pagefind-ignore>
        {prev_btn}
        {next_btn}
      </footer>
    </main>
    <aside class="sidebar-right" data-pagefind-ignore>
      {local_toc}
    </aside>
  </div>
  <div class="sidebar-backdrop" id="sidebar-backdrop"></div>
  <div class="search-overlay" id="search-overlay">
    <div class="search-dialog">
      <div class="search-header">
        <input type="text" class="search-input" id="search-input" placeholder="{search_label}..." autocomplete="off">
        <kbd class="search-close">Esc</kbd>
      </div>
      <div class="search-results" id="search-results"></div>
    </div>
  </div>
  <script type="module" src="../assets/nav.js"></script>
</body>
</html>"""


def split_and_generate(full_html: Path, lang: str):
    """Parse the full HTML, split by sections, generate individual pages."""
    chapters = CHAPTERS[lang]
    parts = PARTS[lang]
    thesis_title = THESIS_TITLE[lang]
    out_dir = DIST_DIR / lang
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Parsing HTML ({lang})...")
    soup = BeautifulSoup(full_html.read_text(encoding="utf-8"), "html.parser")

    # Find all chapter sections
    chapter_map = {sid: (fname, title) for sid, fname, title in chapters}
    sections: dict[str, Tag] = {}

    for section in soup.find_all("section", class_="chapter"):
        sid = section.get("id", "")
        if sid in chapter_map:
            sections[sid] = section

    print(f"    Found {len(sections)} chapter sections")

    # Extract endnotes (footnotes)
    endnotes_section = soup.find("section", attrs={"role": "doc-endnotes"})
    footnote_map: dict[str, Tag] = {}
    if endnotes_section:
        for li in endnotes_section.find_all("li", id=True):
            footnote_map[li["id"]] = li
        print(f"    Found {len(footnote_map)} footnotes")

    # Build id -> filename map for cross-chapter link rewriting
    id_to_file: dict[str, str] = {}
    for sid, fname, _title in chapters:
        if sid not in sections:
            continue
        id_to_file[sid] = fname
        for elem in sections[sid].find_all(attrs={"id": True}):
            id_to_file[elem["id"]] = fname

    # Map footnote IDs to chapter files
    if footnote_map:
        for sid, fname, _title in chapters:
            if sid not in sections:
                continue
            for ref_a in sections[sid].find_all("a", attrs={"role": "doc-noteref"}):
                target_id = ref_a.get("href", "").lstrip("#")
                if target_id in footnote_map:
                    id_to_file[target_id] = fname

    cross_links_total = 0

    # Generate each page
    for i, (sid, fname, title) in enumerate(chapters):
        if sid not in sections:
            print(f"    WARNING: section '{sid}' not found, skipping")
            continue

        section = sections[sid]
        local_toc = extract_local_toc(section)
        global_nav = build_global_nav(chapters, parts, sid)
        local_toc_html = build_local_toc(local_toc, lang)

        prev_link = (chapters[i - 1][1], chapters[i - 1][2]) if i > 0 else None
        next_link = (chapters[i + 1][1], chapters[i + 1][2]) if i < len(chapters) - 1 else None

        # Rewrite cross-chapter href="#id" to href="other-file.html#id"
        cross_links = 0
        for a_tag in section.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("#"):
                target_id = href[1:]
                target_file = id_to_file.get(target_id)
                if target_file and target_file != fname:
                    a_tag["href"] = f"{target_file}#{target_id}"
                    cross_links += 1

        # Collect footnotes for this chapter
        footnotes_html = ""
        if footnote_map:
            noterefs = section.find_all("a", attrs={"role": "doc-noteref"})
            chapter_footnotes = []
            for ref_a in noterefs:
                target_id = ref_a.get("href", "").lstrip("#")
                if target_id in footnote_map:
                    chapter_footnotes.append(footnote_map[target_id])
            if chapter_footnotes:
                for fn in chapter_footnotes:
                    for a_tag in fn.find_all("a", href=True):
                        href = a_tag["href"]
                        if href.startswith("#"):
                            tid = href[1:]
                            target_file = id_to_file.get(tid)
                            if target_file and target_file != fname:
                                a_tag["href"] = f"{target_file}#{tid}"
                                cross_links += 1
                items = "\n".join(fn.decode() for fn in chapter_footnotes)
                footnotes_html = (
                    f'\n<section class="footnotes" role="doc-endnotes">'
                    f'\n<hr>\n<ol style="list-style-type: none">\n{items}\n</ol>'
                    f'\n</section>'
                )

        section_html = section.decode_contents() + footnotes_html

        page = build_page(
            section_html=section_html,
            global_nav=global_nav,
            local_toc=local_toc_html,
            title=title,
            thesis_title=thesis_title,
            prev_link=prev_link,
            next_link=next_link,
            lang=lang,
            current_file=fname,
        )

        cross_links_total += cross_links
        out_path = out_dir / fname
        out_path.write_text(page, encoding="utf-8")
        print(f"    -> {lang}/{out_path.name} ({len(local_toc)} TOC, {cross_links} xlinks)")

    print(f"    Total cross-chapter links rewritten: {cross_links_total}")


# ---------------------------------------------------------------------------
# Step 4: Generate redirect index
# ---------------------------------------------------------------------------

def generate_redirect_index():
    """Generate dist/index.html with browser language detection + redirect."""
    html = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Thesis</title>
  <script>
    var lang = (navigator.language || navigator.userLanguage || "fr").toLowerCase();
    var target = lang.startsWith("en") ? "en" : "fr";
    window.location.replace(target + "/index.html");
  </script>
  <meta http-equiv="refresh" content="0;url=fr/index.html">
  <noscript><meta http-equiv="refresh" content="0;url=fr/index.html"></noscript>
</head>
<body>
  <p>Redirecting&hellip; <a href="fr/index.html">Fran&ccedil;ais</a> | <a href="en/index.html">English</a></p>
</body>
</html>"""
    out = DIST_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  -> index.html (redirect)")


# ---------------------------------------------------------------------------
# Step 5: Copy assets
# ---------------------------------------------------------------------------

def copy_assets():
    """Copy CSS/JS assets to dist/assets/."""
    assets_dist = DIST_DIR / "assets"
    assets_dist.mkdir(parents=True, exist_ok=True)
    for src in ASSETS_SRC.glob("*"):
        if src.is_file():
            shutil.copy2(src, assets_dist / src.name)
            print(f"  -> assets/{src.name}")


# ---------------------------------------------------------------------------
# Step 6: Run Pagefind
# ---------------------------------------------------------------------------

def run_pagefind():
    """Index the site with Pagefind for search."""
    pf_args = ["--site", str(DIST_DIR), "--output-subdir", "assets/pagefind"]
    # Try several ways to run Pagefind
    candidates = [
        [sys.executable, "-m", "pagefind"] + pf_args,
        ["pagefind"] + pf_args,
        ["npx", "-y", "pagefind"] + pf_args,
    ]
    for cmd in candidates:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print("  Pagefind indexing complete")
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    print("  WARNING: Pagefind not available, search will be disabled")
    print("  Install with: pip install pagefind, or npm i -g pagefind")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build bilingual HTML thesis")
    parser.add_argument("--skip-lang", choices=["fr", "en"], help="Skip one language")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip PDF compilation")
    parser.add_argument("--skip-compile", action="store_true", help="Skip Typst HTML compilation")
    parser.add_argument("--skip-search", action="store_true", help="Skip Pagefind indexing")
    parser.add_argument("--base-url", default="/", help="Base URL prefix for deployment (e.g. /phd-pagerank/)")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.base_url

    langs = [l for l in LANGS if l != args.skip_lang]

    print("=== Building bilingual HTML thesis ===\n")

    # Clean language output dirs (avoid stale files)
    for lang in langs:
        lang_dir = DIST_DIR / lang
        if lang_dir.exists():
            shutil.rmtree(lang_dir)

    # Step 1: Compile HTML for each language
    full_htmls = {}
    if not args.skip_compile:
        print("[1/5] Compiling Typst -> HTML")
        for lang in langs:
            full_htmls[lang] = compile_typst(lang)
    else:
        print("[1/5] Skipping Typst compilation")
        for lang in langs:
            p = DIST_DIR / f"full-{lang}.html"
            if not p.exists():
                print(f"  Error: {p.name} not found. Run without --skip-compile first.")
                sys.exit(1)
            full_htmls[lang] = p

    # Step 2: Split and generate pages
    print("\n[2/5] Splitting into chapter pages")
    for lang in langs:
        split_and_generate(full_htmls[lang], lang)
        full_htmls[lang].unlink()

    # Step 3: Compile PDFs
    if not args.skip_pdf:
        print("\n[3/5] Compiling PDFs")
        compile_pdfs(langs)
    else:
        print("\n[3/5] Skipping PDF compilation")

    # Step 4: Generate redirect index + copy assets
    print("\n[4/5] Generating assets and index")
    generate_redirect_index()
    copy_assets()

    # Step 5: Pagefind
    if not args.skip_search:
        print("\n[5/5] Running Pagefind search indexer")
        run_pagefind()
    else:
        print("\n[5/5] Skipping search indexing")

    print(f"\nDone! Open {DIST_DIR / 'index.html'} in a browser.")


if __name__ == "__main__":
    main()
