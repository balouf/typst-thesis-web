# HTML Export

Typst can export HTML, with the mathematics as native MathML. This chapter explains how
to get a web edition of a paper (one self-contained page) or of a thesis (one page per
chapter) **without touching the sections or chapters**, and how to check that nothing
was lost on the way.

Everything rests on a few files that you copy into your project, and on two scripts:

| File | Role |
|------|------|
| `web.typ` | The web layer: Typst show rules and page-building functions. |
| `web-content.css` | Styles of what a document contains: equations, drawings, figures, statements, notes. |
| `web.css` | The page around it, light and dark: typography, layouts, navigation. |
| `web.js` | Multi-page sites only: theme toggle, search, navigation on small screens. |
| `epub.py` | Optional: packages a web edition as an EPUB book. |
| `tools/check.py` | Compiles a web edition and reports what did not make it to HTML. |
| `tools/head.py` | Optional: moves styles and metadata from `<body>` to `<head>`. |

They live in [`lib/`](https://github.com/balouf/typst-thesis-web/tree/main/lib) and
[`tools/`](https://github.com/balouf/typst-thesis-web/tree/main/tools) of this
repository. The layer is written for **Typst 0.15.1**.

> HTML export is still experimental in Typst: it sits behind `--features html`, and its
> output may change from one version to the next. Pin the Typst version you build with,
> and run `check.py` after every upgrade.

## What Typst does, and what it drops

Out of the box, `typst compile --features html` handles paragraphs, headings, lists,
tables, figures with captions, footnotes, citations and bibliography, cross-references,
and equations (as MathML).

It has no HTML equivalent for layout, and what it cannot translate it **drops together
with its content**, with a warning: `pad`, `align`, `stack`, `grid`, `place`, `columns`,
`layout`, shapes (`rect`, `circle`, `line`...), transforms. It also does not print
equation numbers, and it ignores text color, size and font.

A document written for PDF is full of these. A template that typesets headings with a
`stack`, a title block with a `grid`, figures inside an `align(center)`, or theorem
boxes with a `pad` loses all of them: the page compiles without error, and the headings,
the authors, the figures and the theorems are simply not there.

The layer fixes this from the outside, with show rules that only act in web export.

## The principle: one more entry file

A project has one entry file per edition. They include the same sections.

| | PDF edition | Web edition |
|---|---|---|
| Entry file | `main.typ` | `web.typ` (paper) or `main-html.typ` (thesis) |
| Content rules (numbering, references) | yes | yes |
| Layout template (page, fonts, title block) | yes | **no** |
| Web layer | no | yes |
| Sections | `#include` | the same `#include` |

A web entry applies its rules in a fixed order:

```typ
#import "web/web.typ": article, web-rules
#import "template.typ": content-rules

#show: content-rules           // 1. project rules that REPLACE elements
#show: web-rules               // 2. the web layer
// #show: chapter-counters     // 3. project rules that RETURN the element
#show: article.with(title: [...], authors: (...))   // 4. the page

#include "sections/1-intro.typ"                     // 5. the untouched sections
```

The order matters because Typst applies the most recent show rule first:

1. Rules that replace an element (a custom `show ref`, a `show figure` that wraps the
   figure in a block) go **before** `web-rules`, so that the layer has the last word on
   how the element reaches HTML.
2. Rules that return the element they receive, with something added
   (`show heading: it => it + counter(...).update(0)`), go **after**: placed before, they
   would never see the element, because the layer replaces it.

**Never apply a layout template in a web entry.** What a template typesets itself (its
title block, a bibliography passed as an argument) stays under its own rules, where the
layer cannot reach it.

### Splitting a template

For this to work, the template must keep what the document *means* apart from how the
PDF *looks*:

```typ
// What the document means: both editions.
#let content-rules(doc) = {
  set heading(numbering: "1.1")
  set math.equation(numbering: "(1)")
  doc
}

// How the PDF looks: PDF edition only.
#let layout(title: none, authors: (), doc) = {
  set page(paper: "a4", margin: 2.5cm)
  set text(font: "New Computer Modern", size: 11pt)
  // title block, heading typography, running heads...
  doc
}
```

If your template is one function, split it: it is a mechanical change, and the PDF does
not move (both reference theses were split this way and their PDFs are byte-identical
before and after). To compare PDFs byte for byte, set `SOURCE_DATE_EPOCH=0` for both
builds: a PDF carries its creation date, so two plain builds of the same source already
differ. A vendored template you do not own is simply left out of the web entry:
`article` builds the title block.

## What `web-rules` does

Every rule tests the export target, so it does nothing in a PDF build, and nothing
inside an SVG frame either (frames are laid out as paged content).

| Element | In web export |
|---------|---------------|
| `pad`, `align`, `place`, `move`, `columns` | transparent: the content stays |
| `stack` | its children, in order |
| `h` | a space (left alone inside equations) |
| `v`, `pagebreak`, `colbreak`, `hide` | nothing |
| `grid`, shapes, transforms, `layout` callbacks, fixed-size boxes and blocks | an inline SVG (this covers cetz, fletcher, droplet) |
| a `box` that holds a `place` (one drawing set on another) | one SVG, sized to cover what sticks out of the box |
| `heading` | a real `<h1>`–`<h6>` with its number, whatever the template did, and a stable id (see below) |
| `figure` with a string `kind` and no caption | a statement: `<div class="env env-KIND">` |
| `figure` whose kind is in `frame-kinds` (`"algorithm"`) | an SVG with its caption (or text: see [Algorithms](#algorithms)) |
| other figures | `<figure>` and `<figcaption>`; a drawing that contains no image is framed |
| numbered block equation | the equation and its number |
| `math.overline`, `math.underline` | an accent (MathML export drops them) |
| equation using `math.cancel` | an SVG (MathML cannot draw it) |
| delimiters around short content | fixed size (browsers oversize them otherwise) |
| `ref(form: "page")` | nothing (it is an error in HTML) |
| `enum` with a numbering pattern | a list that shows `(i)`, `(ii)`... |
| emphasis around paragraphs or lists | a `<div class="em">` (valid HTML) |
| `strong` or `emph` inside an equation | bold or italic math (an HTML element is not valid in MathML) |
| `strong` with a zero delta | plain text |
| block with a fill or a stroke | `<div class="box">`, colors passed to the stylesheet |

Labels become **stable anchors**: `<thm:main>` gives `id="thm-main"` (the colon is not
valid in EPUB and awkward in CSS), so a link to a theorem survives a revision of the
document.

Parameters, all optional:

```typ
#show: web-rules.with(
  heading-offset: 1,              // level 1 is <h2>; use 0 when a chapter is a page
  heading-number: (it, n) => ..., // how the number is printed before the title
  frame-width: 45em,              // width given to SVG frames of flowing content
  frame-kinds: ("algorithm",),    // figure kinds rendered as SVG
  env-kinds: ("thmenv",),         // figure kinds that are statements even with a caption
  number-equations: true,
  svg-math: (math.cancel,),       // math functions that send an equation to SVG; `true`: all equations
  tame-delimiters: true,
)
```

The rules are also exported by family (`transparent-rules`, `frame-rules`,
`heading-rules`, `figure-rules`, `math-rules`, `text-rules`, `spacing-rules`) if you
need only some of them.

## A paper: one self-contained page

```typ
#show: article.with(
  title: title,
  authors: (
    (name: "Ada Lovelace", orcid: "0000-0000-0000-0000", affiliations: [Analytical Engine Works]),
    "Alan Turing",
  ),
  abstract: abstract,
  keywords: ("typst", "html"),
  links: (("PDF", "paper.pdf"), ("Code", "https://...")),
  meta: (([Funding], [Supported by ...]),),
)
```

```bash
typst compile --features html web.typ paper.html
```

The result is a single file: the stylesheet is inlined, images are embedded, and the
dark theme follows the reader's system. No script, no post-processing. See
[`examples/article`](https://github.com/balouf/typst-thesis-web/tree/main/examples/article).

`article` prints the title block, a table of contents (`toc: false` to remove it, or a
depth) and wraps the body. In a PDF build it returns the body unchanged. With
`emails: false` the e-mail addresses stay out of the page: a `mailto:` link on a public
page is harvested more readily than an address in a PDF.

Keep what both editions print (title, abstract, keywords) in a data file that each
entry imports, as `meta.typ` does in the example, rather than importing one entry file
from another. For a double-blind submission, put the authors in a file of their own,
imported by the non-anonymous editions only: the anonymous build then never loads a
name.

### Anchors

Every element with a label gets an id made from it (`<thm:main>` gives `#thm-main`). A
heading without a label gets an id made from its text (`Related work` gives
`#related-work`, a second one on the same page `#related-work-2`), so a link to a
section keeps working when the document changes elsewhere. Accented letters keep their
base letter (`Erdős–Rényi graphs` gives `#erdos-renyi-graphs`). Label a heading to
choose its anchor; pass `heading-id: it => none` to `web-rules` to leave the ids to
Typst.

## A thesis: one page per chapter

A site is declared in Typst, one `page(...)` per HTML page:

```typ
#import "templates/web/web.typ": page, part, site-assets, web-rules

#show: thesis-content
#show: web-rules.with(heading-offset: 0)
#show: chapter-counters

#let site = (
  title: "Thesis Title",
  repo: "https://github.com/you/your-thesis",   // optional
  other-lang: "en",                             // optional: language switch
)
#let chapter = page.with(site: site)

#site-assets()

#chapter("index.html", title: [Home])[#include "chapters/cover.typ"]

#part[Part I — Foundations]
#chapter("models.html", title: [Ch. 1 — Models])[#include "chapters/models.typ"]
#chapter("proofs.html", title: [Ch. 2 — Proofs])[#include "chapters/proofs.typ"]

#chapter("bibliography.html", title: [Bibliography])[#bibliography("refs.bib")]
```

```bash
typst compile --features html,bundle --format bundle main-html.typ web/dist/en
```

With the `bundle` format, Typst writes one HTML document per `page`, and resolves
everything across them itself: a reference to a theorem in another chapter becomes a
relative link, each page gets its own footnotes, counters run through the whole thesis,
and citations point to the bibliography page. Nothing is split or rewritten afterwards.

- The **path** (`"models.html"`) is the name of the file on the site, hence its URL:
  keep it stable.
- The **title** is the entry in the navigation. `part[...]` names a group of pages,
  `part(none)` ends a group, and `page.with(sub: true)` indents an entry.
- The navigation, the table of contents of each page and the previous/next links are
  built from the pages themselves: there is no list to maintain elsewhere.
- `site-assets()` emits `web.js`; pass `extra: ("assets/favicon.svg": read("..."))` for
  your own files, and `site.favicon` to use one as the icon.

A large chapter can be several pages (give each section its own `page`, the sub-pages
with `sub: true`) while the PDF keeps it as one chapter.

The site needs a few more steps around the Typst compilation: one bundle per language,
the PDFs, the EPUBs, a search index. [`web/build.py`](https://github.com/balouf/typst-thesis-web/tree/main/examples/thesis/web/build.py)
runs them; it only runs commands and never touches the HTML. See
[GitHub Deployment](04-github-deploy.md).

## Theorems and proofs

Two ways of writing statements work in both editions without any HTML-specific code.

**ctheorems.** `thmbox`, `thmplain` and `thmproof` work as they are: numbering,
references, names. The box colors you gave for the PDF (`fill:`, `stroke:`) reach the
web page, which tones them down by itself in the dark theme.

**A figure with a string kind**, the usual home-made environment:

```typ
#let theorem(body) = figure(kind: "theorem", supplement: [Theorem], numbering: "1",
  block(width: 100%)[*Theorem #context counter(figure.where(kind: "theorem")).display().* #emph(body)])
```

Both become `<div class="env env-KIND env-SUPPLEMENT">`, for instance
`env env-thmenv env-theorem`; unnumbered ones (proofs) also get `env-plain`. Style a
given kind in your own CSS if the default does not suit you.

A proof written as a plain `block` is a bare `<div>`. To style it, tag it in the
template: `tag("proof", body)` is the same block in PDF and a `<div class="proof">` on
the web.

If a function of your template really needs two renderings (a drop cap, a reference
with a page number), test the target inside it:

```typ
#let fref(lab) = context if target() == "paged" { [#ref(lab), #ref(lab, form: "page")] } else { ref(lab) }
```

This works for anything that is not referenced by a label. A function whose result
receives a label (`#theorem[...] <thm:x>`) must return the labelled element itself, not
a `context` block.

## Algorithms

An algorithm is a drawing by default: packages lay it out with grids, boxes and drawn
guides, which have no HTML equivalent. With the [`algo`](https://typst.app/universe/package/algo)
package it can be text instead (equations in MathML, working links and notes, text that
a search finds): wrap the call in `algo-lines`, and take the kind out of `frame-kinds`.

```typ
#import "@preview/algo:0.3.6": algo, i, d, comment
#import "web/web.typ": algo-lines

#let alg(..args, body) = figure(
  algo-lines(indent: 15pt, algo(indent-size: 15pt, indent-guides: 1pt + gray, line-numbers: false)[#body]),
  kind: "algorithm", supplement: [Algorithm], ..args,
)
```

```typ
#show: web-rules.with(frame-kinds: ())   // in the web entry
```

`algo-lines` does nothing in the PDF. On the web it turns each line into an indented
block and lets the stylesheet draw the indent guides; `indent` is the indent size given
to the package. It relies on how `algo` builds a line (a box holding a padded line), so
pin the version of the package; another package needs its own adapter, or stays a
drawing. `examples/thesis` is set up this way.

## Drawings

Whatever has no HTML equivalent is laid out by Typst exactly as in the PDF and inlined
as an SVG: cetz and fletcher drawings, grids of sub-figures, shapes. Inside
these frames, references still link, and the text uses the font and size set in the
entry file (which is all `set text(font: ...)` is used for in a web entry).

`frame(body, width: ...)` forces any content into a frame. Content that flows (a
paragraph, a grid with `1fr` columns) needs a width: the layer measures the content and
caps it at `frame-width`.

Frames are black on transparent, so the dark theme inverts them; the photographs they
contain (PNG, JPEG) are inverted back and keep their colors.

## Checking that nothing was lost

A dropped figure does not stop the compilation. `check.py` looks for what a silent loss
leaves behind:

```bash
uv run tools/check.py web.typ
uv run tools/check.py main-html.typ --format bundle --input lang=en
```

```
web.typ -> html, 1 page(s), 863 KiB
  diagnostics: 0 error(s), 0 content drop(s), 0 benign
  census                document   output
    headings                  26       26
    figures                   40       40
    block-equations           55       55
    numbered-equations        53       53
    inline-equations        1629     1516   (113 inside SVG frames, or not rendered)
    footnotes                  1        1
    citations                106      106
  => ok
```

It reports, in decreasing order of trust:

1. **Compiler diagnostics.** Typst names every element it ignores, with file and line.
   An element that carries content is an error; pure spacing is benign.
2. **The HTML itself.** Internal links without a target, duplicate ids, empty anchored
   blocks (what a dropped figure leaves), block elements nested in inline ones,
   collapsed frames.
3. **A census.** Headings, figures, equations, notes and citations, counted in the
   Typst document and in the HTML. What sits in an SVG frame is counted on the Typst
   side only, so the HTML may be lower; it should never be higher.

The exit status is 1 on error, so it can gate a CI job; `--json` gives the full report
to another program; `--out` keeps the compiled page.

## Styling

The two stylesheets are driven by CSS variables (colors, widths, fonts) declared at the
top of `web.css`. To adjust a site, pass extra CSS rather than editing the vendored
files:

```typ
#let site = (title: "...", css: read("web/thesis.css"))   // a site
#show: article.with(css: read("web/web-content.css") + read("web/web.css") + read("paper.css"))   // a page
```

Mathematics is rendered by the browser with a math font of the reader's system; the
stylesheet asks for New Computer Modern Math, Latin Modern Math, STIX Two Math and
Cambria Math, in that order.

## Inside another site

A paper can also be a page of an existing documentation site (Sphinx, mdBook, Jupyter
Book), with the navigation, search and theme of that site. The layer is split for this:

- `web-content.css` styles what the document contains and nothing else. Its rules are
  scoped to a container of class `typst` (with `:where()`, so they weigh no more than
  unscoped rules) and take their colors from CSS variables listed at the top of the
  file.
- Anchors are stable (see above), so the host can keep the ids on its own headings.

The integration itself belongs to the host: compile the web entry, take the article
header (keep its class `article-header`), the content of `<main>` and the endnotes,
wrap them in `<div class="typst">`, and load `web-content.css` unchanged after the
theme, preceded by a few lines that map the theme to the variables:

```css
.typst {
  --color-text: var(--pst-color-text-base);          /* pydata-sphinx-theme, as an example */
  --color-text-muted: var(--pst-color-text-muted);
  --color-bg: var(--pst-color-background);
  --color-sidebar-bg: var(--pst-color-surface);
  --color-border: var(--pst-color-border);
  --color-border-strong: var(--pst-color-border);
  --color-link: var(--pst-color-link);
  --font-math: "New Computer Modern Math", "Latin Modern Math", "STIX Two Math", "Cambria Math", math;
  --font-heading: var(--pst-font-family-heading);
  --box-fill-share: 100%;
  --frame-filter: none;
}
html[data-theme="dark"] .typst {
  --box-fill-share: 0%;
  --frame-filter: invert(1) hue-rotate(180deg);
}
```

Headings, links, tables and code keep the style of the host. No converter ships with the
layer: how a host wants its headings and its table of contents is its own business.

## An EPUB edition

The same output makes a book for reading apps and e-readers. `epub.py`, kept next to
the stylesheets, packages what Typst wrote, a page or the folder of a bundle:

```bash
uv run web/epub.py paper.html -o paper.epub
uv run templates/web/epub.py web/dist/en -o thesis.epub --cover cover.png
```

Each HTML page becomes a chapter. The script works on the files a website serves: there
is no third entry file, and nothing to change in the document.

- **Content only.** Scripts, styles, the navigation of a site and the table of contents
  of an article are left out: a reading app has its own. Give the class `web-only` to
  whatever else belongs to the website alone, such as the download buttons of a cover
  page (`tag("web-only", ...)`).
- **Order and table of contents** come from the navigation of the site (parts, pages,
  sub-pages) and from the headings. `--toc-depth` sets how many levels of headings are
  listed under each chapter.
- **Valid XHTML.** Typst names a glyph after its outline, so the drawings of a page
  define the same ids several times, which an EPUB forbids: they are made unique.
  Images inlined as data URIs become files of the book, which shrinks it: the 19 MB of
  pages of a thesis with many figures give a 3.8 MB book.
- **Links** between chapters follow them. A relative link to a file that is not in the
  book (a PDF next to the site) loses its target, or becomes absolute with
  `--base-url https://.../en/`.
- **Colors belong to the reading app**, in its day, sepia or night theme: the book sets
  no text or page color. A drawing in black only takes the color of the text; a drawing
  in colors keeps them, on a white ground; a colored block keeps a tint of its color
  and gets a border.
- **Metadata.** Title, authors (`set document(author: ...)`), keywords and language are
  read from the pages; `--title`, `--author`, `--lang`, `--date` and `--identifier` (a
  DOI, a URL) override them. `--cover` takes a PNG or JPEG image for the library of the
  reading app. The first page of the PDF edition does well:

  ```bash
  typst compile --pages 1 --ppi 100 main.typ cover.png
  ```

With `SOURCE_DATE_EPOCH` set, the same input gives the same file, byte for byte.
Validate a book with [EPUBCheck](https://www.w3.org/publishing/epubcheck/)
(`java -jar epubcheck.jar thesis.epub`): the examples of this repository and both
reference theses pass version 5.4.0 without a message.

Equations stay MathML, which is part of EPUB 3, so the book needs a reading app built
on a browser engine. calibre displays both reference theses as intended; Apple Books
and Thorium are built the same way, but were not tried. SumatraPDF is not such an app:
its engine (MuPDF) has no MathML, discards the whole stylesheet at the first selector
it does not know, and leaves out the images set inside a drawing. Moon+ Reader, tried
briefly, is acceptable except for the drawings: it does not draw inline SVG, and only
shows the bitmap images set inside one.

Where MathML is missing but inline SVG is drawn well, a second build can draw every
equation, at the cost of a larger file and of formulas that are no longer text (this
does not rescue SumatraPDF, which blurs and clips such drawings):

```typ
#show: web-rules.with(svg-math: true)
```

## Limits

- **Experimental export.** Both `html` and `bundle` are feature flags of Typst. Pin the
  version, and expect to adjust on upgrades.
- **MathML is rendered by the browser.** Spacing and stretching differ slightly between
  browsers and from the PDF. Readers without a math font get a poorer rendering.
- **Text styling is not carried over.** Color, size, weight and font set with `text()`
  are dropped silently by Typst. Use semantic markup (`emph`, `strong`, headings) or
  tag the content.
- **Frames are images.** Text inside an SVG frame is not searchable, a heading inside
  a frame is not a heading, and a footnote call inside a frame is not a link (the note
  itself is still listed).
- **No access to `<head>`.** Typst writes it. The layer therefore puts its stylesheet
  at the top of `<body>`, and a `<meta>` element emitted by a document
  (`html.elem("meta", attrs: (name: "citation_title", content: "..."))`, for Google
  Scholar or link previews) lands in `<body>` too, where no crawler looks.
  `uv run tools/head.py web/dist` moves the styles, `<meta>` and `<link>` elements of
  built pages to `<head>` and changes nothing else. It is a finishing step: pages are
  correct without it.
- **Equation numbers** are added by the layer because Typst does not print them yet
  (typst#8117). When it does, set `number-equations: false`.

## Updating the layer

The copies of `web.typ`, `web-content.css`, `web.css`, `web.js` and `epub.py` in your
project are meant to stay unmodified: record local patches in the header of `web.typ`. To refresh them from a
checkout of this repository:

```bash
uv run tools/sync.py path/to/your/project/templates/web
```

`web.js` and `epub.py` are refreshed where they already are; `--js` and `--epub` add
them. A copy whose header lists local patches is left alone; `--force` overwrites it.

Each version of the layer is tagged in this repository (`v0.4.1`): the version in the
header of a copy names the tag it comes from.
