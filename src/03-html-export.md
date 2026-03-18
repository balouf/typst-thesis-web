# HTML Export

This chapter covers the full pipeline from Typst source to a navigable, multi-page HTML
website. The key idea: Typst compiles your thesis into a single HTML blob, then a Python
script splits it into one page per chapter with sidebar navigation, search, and
cross-chapter links.

## Dual Entry Points

Your project has two Typst entry points:

- **`main.typ`** — PDF output. Includes page setup, headers/footers, table of contents,
  page numbers.
- **`main-html.typ`** — HTML output. Wraps each chapter in a `chapter-section()` call so
  `build.py` knows where to split. Applies HTML-specific show rules.

Both files import the same chapter files (`chapters/*.typ`), so the content is shared.
The difference is in the structural markup around them.

Compiling for HTML:

```bash
typst compile --features html --format html \
  --input lang=fr --input html=true \
  main-html.typ web/dist/full-fr.html
```

The `--features html` flag unlocks the `target()` function, and `--input html=true` sets
the `_is-html` flag that chapter files can read without needing `--features html`
themselves.

## html-overrides.typ

This file (in `templates/`) provides three things:

### `chapter-section(id, body)`

Wraps content in `<section class="chapter" id="id">` for HTML; passes through
transparently for PDF. This is the marker that `build.py` uses to find and split
chapters:

```typ
#chapter-section("distribution")[
  #include "chapters/distribution.typ"
]
```

The `id` must match the `section_id` in build.py's `CHAPTERS` list.

### `part-marker(id, title)`

Optional grouping headers. In HTML, emits a `<section class="part">` with an `<h1>` that
appears in the sidebar as a part heading (e.g., "Part I: Content Distribution"). In PDF,
it does nothing — part pages are handled by the thesis style.

### `html-show-rules`

A set of show rules applied only in HTML mode, using `target()`:

- **Headings** are converted to semantic `<h1>`--`<h4>` with `id` attributes derived from
  their labels. Chapter counters are reset at each `<h1>`.
- **Inline math** is rendered as SVG via `html.frame()` wrapped in a `box` (so it stays
  inline).
- **Block math** is rendered as SVG via `html.frame()`.
- **Grids** (e.g., side-by-side figures) are rendered as SVG with constrained width
  (`42em`) to avoid oversized output.
- **Algorithms** (figures of kind `"algorithm"`) are rendered as SVG at `38em` width to
  force line wrapping within the HTML content area.

**Important caveat about `target()`**: The `target()` function is only available when
compiling with `--features html`. Files included by *both* `main.typ` and `main-html.typ`
(i.e., your chapter files and shared templates) cannot call `target()` directly — it will
error during PDF compilation. Instead, use the `_is-html` flag from `i18n.typ`:

```typ
#import "i18n.typ": _is-html

#let my-function = if _is-html {
  // HTML version
} else {
  // PDF version
}
```

Only `html-overrides.typ` itself (which is imported exclusively by `main-html.typ`) may
use `target()`.

## Theorem Environments

The file `environments.typ` provides dual implementations for every theorem type
(theorem, lemma, proposition, corollary, definition, conjecture, remark, etc.):

- **PDF mode**: uses the `ctheorems` package (`thmbox`) with colored fills and borders.
- **HTML mode**: uses `_html-thm()` to generate `<div class="thm-box thm-theoreme">`
  wrapped in a `figure` (for labeling and numbering).

Each environment type has a CSS class (e.g., `.thm-theoreme`, `.thm-lemme`,
`.thm-proposition`). The `css-class` argument in `_html-thm()` must match a rule in
`style.css`.

**Common gotcha**: if you add a new theorem type and forget the CSS rule, the box will
render with no background and no border — effectively invisible. Always add both the
light and dark theme CSS rules:

```css
.thm-mytype    { background: #f0f0f0; border-color: #999; }

[data-theme="dark"] .thm-mytype { background: #1e1e1e; }
```

## build.py — The Build Script

The Python build script (`web/build.py`) orchestrates the full pipeline. Run it with:

```bash
uv run web/build.py                 # Build both languages
uv run web/build.py --skip-lang en  # French only
uv run web/build.py --skip-pdf      # Skip PDF compilation
uv run web/build.py --skip-compile  # Reuse existing full.html (faster iteration)
```

The script performs these steps:

1. **Compile Typst to HTML** — runs `typst compile --features html --format html` for
   each language, producing a single `full-fr.html` / `full-en.html`.
2. **Parse and split** — loads the HTML with BeautifulSoup, finds all
   `<section class="chapter">` elements, and maps their `id` to the chapter list.
3. **Rewrite cross-chapter links** — any `href="#some-id"` pointing to an element in a
   different chapter is rewritten to `href="other-file.html#some-id"`.
4. **Collect footnotes** — Typst emits all footnotes as endnotes in a single section.
   The script distributes them back to their respective chapter pages.
5. **Generate pages** — each chapter becomes a standalone HTML page with: a sticky
   topbar, a left sidebar (global navigation), a right sidebar (local table of contents
   from h2/h3 headings), and prev/next navigation links.
6. **Generate redirect index** — `dist/index.html` detects the browser language and
   redirects to `fr/` or `en/`.
7. **Copy CSS/JS assets** — copies `style.css`, `nav.js`, and any other files from
   `web/assets/` into `dist/assets/`.
8. **Run Pagefind** — indexes the generated pages for client-side full-text search.

## Configuration in build.py

The top of `build.py` has a configuration section marked with `# TODO: adapt` comments.
Here is what to customize:

### `CHAPTERS`

A dict keyed by language, each value a list of `(section_id, filename, title)` tuples:

```python
CHAPTERS = {
    "fr": [
        ("cover", "index.html", "Accueil"),
        ("distribution", "distribution.html", "Distribution de contenu"),
        ("bibliography", "bibliography.html", "Bibliographie"),
    ],
    "en": [
        ("cover", "index.html", "Home"),
        ("distribution", "distribution.html", "Content Distribution"),
        ("bibliography", "bibliography.html", "Bibliography"),
    ],
}
```

The `section_id` must match the `id` in the corresponding `chapter-section("id")` call in
`main-html.typ`. If they do not match, the script will print a warning and skip the
chapter.

### `PARTS`

Groups chapters in the sidebar. Each entry is `(title_or_none, [list_of_section_ids])`:

```python
PARTS = {
    "fr": [
        (None, ["cover", "introduction"]),
        ("Distribution", ["distribution", "caching"]),
        (None, ["bibliography"]),
    ],
}
```

Use `None` for a flat group (no heading), or a string for a labeled group that renders as
a part header in the sidebar.

### `SUB_CHAPTERS`

A set of `section_id` values that should appear indented and in a smaller font in the
sidebar:

```python
SUB_CHAPTERS = {"acyclique-origine", "acyclique-bases", "acyclique-convergence"}
```

This is useful when decomposing a large chapter into multiple pages (see below).

### Other settings

- `THESIS_TITLE` — the title shown in the topbar, per language.
- `GITHUB_URL` — links to the GitHub icon in the topbar.
- `BASE_URL` — overridden by the `--base-url` CLI argument; critical for GitHub Pages
  deployment.

## CSS Theming

The file `web/assets/style.css` uses CSS variables for light and dark modes. The root
`:root` block defines light theme colors, and `[data-theme="dark"]` overrides them.

Key conventions:

- `.thm-*` classes define theorem box appearance (background + left border).
- SVG frames from `html.frame()` get the class `.typst-frame`. In dark mode, they are
  inverted with `filter: invert(1) hue-rotate(180deg)` to flip black-on-white to
  white-on-dark while preserving colors.
- The layout is a CSS grid with three columns (left sidebar, content, right TOC) that
  collapses responsively at 1200px and 960px breakpoints.

The file `web/assets/nav.js` handles theme toggling (light/dark/auto cycle), sidebar
open/close on mobile, Pagefind search modal (lazy-loaded on first open), keyboard
shortcuts (Ctrl+K for search, Escape to close), and scroll-spy highlighting in the local
table of contents.

## Decomposing a Large Chapter

If a chapter has natural sub-sections that would each make a long page (like the acyclic
preferences chapter in [hdr-p2p](https://github.com/balouf/hdr-p2p)), you can split it
into multiple HTML pages while keeping the single chapter structure in the PDF.

In `main-html.typ`, use separate `chapter-section()` calls for each sub-section:

```typ
#chapter-section("acyclique")[
  #include "chapters/acyclique-html-intro.typ"
]
#chapter-section("acyclique-origine")[
  #include "chapters/acyclique-origine.typ"
]
#chapter-section("acyclique-bases")[
  #include "chapters/acyclique-bases.typ"
]
```

In `main.typ`, include the full chapter as a single unit (the PDF has no splitting).

Then in `build.py`, list the sub-sections in `CHAPTERS` and add their IDs to
`SUB_CHAPTERS` so they render indented in the sidebar. The parent entry
(`"acyclique"`) appears as a top-level item, and the sub-entries appear nested below it.

This gives readers a manageable page length in the browser while the PDF retains its
natural flow.
