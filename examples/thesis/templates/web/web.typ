// web.typ — web export layer (HTML and bundle targets) for Typst documents.
// Source: https://github.com/balouf/typst-thesis-web (MIT)
// Version 0.4.1 (2026-11-13), checked with Typst 0.15.1.
// Vendored copy: keep it unmodified and list local patches below.
//   Local patches: none.
// Ships with web-content.css, web.css (and web.js for multi-page sites, epub.py
// for an EPUB edition): keep them next to this file.
//
// A web edition is a small entry file next to the PDF one. Order matters:
//   1. project rules that REPLACE elements (numbering, custom `show ref`, ...)
//   2. #show: web-rules
//   3. project rules that RETURN `it` (counter resets, ...)
//   4. #show: article.with(...)   or   page(...)[...] blocks for a site
//   5. #include of the untouched sections
// Never apply a page-layout template in a web entry: whatever such a template
// emits itself (title block, running heads) stays under its own rules.
//
// Every rule is guarded by the export target, so the PDF build and the content
// of `html.frame` (which is laid out as paged content) are left untouched.

#assert(
  sys.version >= version(0, 15, 0),
  message: "web.typ needs Typst 0.15 or later",
)

#let web-version = version(0, 4, 1)

// -----------------------------------------------------------------------------
// Guards and small helpers
// -----------------------------------------------------------------------------

/// Applies `f` to `it` in web targets (html, bundle); returns `it` unchanged in
/// paged targets, including inside `html.frame`.
#let on-web(it, f) = context if target() != "paged" { f(it) } else { it }

/// Stable HTML id for a label. Colons are not valid in XML names (EPUB) and
/// need escaping in CSS, so `thm:main` becomes `thm-main`. Typst reuses an id
/// set explicitly on the emitted element for `@ref` and `link` targets.
#let anchor-id(label) = str(label).replace(":", "-")

#let _anchor(it) = if it.has("label") { (id: anchor-id(it.label)) } else { (:) }

/// Wraps `body` in an HTML element carrying `class` in web targets; identity in
/// PDF. Lets a template tag proofs, epigraphs, ... for the stylesheet.
#let tag(class, body, elem: "div") = context if target() != "paged" {
  html.elem(elem, attrs: (class: class), body)
} else { body }

/// Renders `body` as an inline SVG in web targets (identity in PDF). Flowing
/// content needs a width: the frame is as wide as `body` wants to be, up to
/// `width`.
#let frame(body, width: 45em) = context if target() != "paged" {
  html.frame(context {
    let w = measure(width: width, body).width
    block(width: if w > 0pt { w } else { width }, body)
  })
} else { body }

#let _children(c) = {
  let out = ()
  for (_, v) in c.fields() {
    if type(v) == content { out.push(v) } else if type(v) == array {
      for x in v { if type(x) == content { out.push(x) } }
    }
  }
  out
}

// Whether `c` or one of its descendants satisfies `pred`.
#let _contains(c, pred) = {
  if type(c) != content { return false }
  if pred(c) { return true }
  for child in _children(c) { if _contains(child, pred) { return true } }
  false
}

// Content that cannot live inside an inline element such as <em>.
#let _is-blocky(c) = (
  c.func() in (parbreak, list, enum, terms, list.item, enum.item, terms.item, figure, table, heading, block)
    or (c.func() in (math.equation, raw) and c.at("block", default: false))
)

// Text-only version of a heading body or title, safe to put inside a link:
// footnotes are dropped (hiding them with a show rule leaves phantom endnotes)
// and links/references are unlinked.
#let _strip(c) = {
  if type(c) != content { return c }
  if c.func() == footnote { return none }
  if c.has("children") { return c.children.map(_strip).join() }
  if c.has("child") { return _strip(c.child) }
  c
}
#let plain(c) = {
  show link: it => it.body
  _strip(c)
}

// -----------------------------------------------------------------------------
// Rules, by family. `web-rules` applies them all.
// -----------------------------------------------------------------------------

/// Layout containers that HTML export drops together with their content become
/// transparent; pure spacing is silenced.
#let transparent-rules(body) = {
  show pad: it => on-web(it, it => it.body)
  show align: it => on-web(it, it => it.body)
  show place: it => on-web(it, it => it.body)
  show move: it => on-web(it, it => it.body)
  show columns: it => on-web(it, it => it.body)
  show stack: it => on-web(it, it => {
    let kids = it.children.filter(c => type(c) == content)
    if it.dir.axis() == "vertical" {
      kids.map(k => html.elem("div", k)).join()
    } else { kids.join([ ]) }
  })
  show v: it => on-web(it, _ => none)
  show pagebreak: it => on-web(it, _ => none)
  show colbreak: it => on-web(it, _ => none)
  show repeat: it => on-web(it, _ => none)
  show hide: it => on-web(it, _ => none)
  body
}

#let _math-marker = metadata("web.typ/in-math")

/// Horizontal spacing becomes a space, except inside equations where MathML
/// export needs the original element (a marker set by `math-rules` tells).
#let spacing-rules(body) = {
  show h: it => on-web(it, it => {
    if math.equation.supplement == _math-marker { it } else if type(it.amount) == fraction { [ ] } else if type(it.amount) == length {
      let w = it.amount.to-absolute()
      if w <= 0pt { none } else if w < 0.25em.to-absolute() { sym.space.thin } else { [ ] }
    } else { [ ] }
  })
  body
}

#let _paint(p) = if type(p) == color { p.to-hex() } else { none }

// A size given as a plain length (stored as a length or as a relative length
// with a zero ratio, depending on the element).
#let _fixed(x) = type(x) == length or (type(x) == relative and x.ratio == 0%)

// The `place` elements some content holds, looking through sequences and
// styles only. A `box` that holds one is an overlay (one drawing set on
// another): its meaning is positional, so it is drawn as a whole.
#let _places(c, depth: 4) = {
  if type(c) != content or depth == 0 { return () }
  if c.func() == place { return (c,) }
  let f = c.fields()
  if "children" in f { f.children.map(k => _places(k, depth: depth - 1)).flatten() }
  else if "child" in f { _places(f.child, depth: depth - 1) }
  else { () }
}

// An overlay box, padded by what its placed content sticks out of it, so that
// the frame covers everything it draws. Placed content with no vertical
// alignment sits at its position in the flow and is left out of the estimate.
#let _overlay(it) = context {
  let (width: w, height: h) = measure(it)
  let abs(x, whole) = if type(x) == relative { x.length.to-absolute() + x.ratio * whole } else { x.to-absolute() }
  let out = (left: 0pt, right: 0pt, top: 0pt, bottom: 0pt)
  for p in _places(it.body) {
    // Only the fields written in the source are known on an element at this point.
    let s = measure(p.body)
    let a = p.at("alignment", default: start)
    if a == auto { a = start }
    let x = abs(p.at("dx", default: 0pt), w) + if a.x == center { (w - s.width) / 2 } else if a.x in (right, end) { w - s.width } else { 0pt }
    out.left = calc.max(out.left, -x)
    out.right = calc.max(out.right, x + s.width - w)
    if a.y != none {
      let y = abs(p.at("dy", default: 0pt), h) + if a.y == horizon { (h - s.height) / 2 } else if a.y == bottom { h - s.height } else { 0pt }
      out.top = calc.max(out.top, -y)
      out.bottom = calc.max(out.bottom, y + s.height - h)
    }
  }
  pad(..out, it)
}

#let _box-style(it) = {
  let parts = ()
  let fill = _paint(it.fill)
  if fill != none { parts.push("--box-fill: " + fill) }
  let s = it.stroke
  if type(s) == dictionary {
    let paints = s.values().filter(x => x != none).map(x => _paint(stroke(x).paint)).filter(x => x != none)
    if s.values().any(x => x != none) {
      parts.push("--box-stroke: " + paints.at(0, default: "currentColor"))
    }
  } else if s != none {
    let paint = _paint(stroke(s).paint)
    parts.push("--box-stroke: " + if paint != none { paint } else { "currentColor" })
  }
  if parts.len() == 0 { none } else { parts.join("; ") }
}

/// What has no HTML equivalent is rendered as SVG: grids, shapes, transforms,
/// `layout` callbacks (fletcher, droplet), fixed-size blocks/boxes (cetz) and
/// boxes that hold a `place` (overlays).
/// Colored blocks hand their colors to the stylesheet as CSS variables.
#let frame-rules(width: 45em, body) = {
  let framed(it) = on-web(it, it => frame(it, width: width))
  show grid: framed
  show layout(_ => []).func(): framed
  show rect: framed
  show square: framed
  show circle: framed
  show ellipse: framed
  show polygon: framed
  show line: framed
  show curve: framed
  show rotate: framed
  show scale: framed
  show skew: framed
  show block: it => on-web(it, it => {
    if _fixed(it.width) and _fixed(it.height) { html.frame(it) } else {
      let style = _box-style(it)
      if style == none { it } else { html.elem("div", attrs: (class: "box", style: style), it.body) }
    }
  })
  show box: it => on-web(it, it => {
    if _fixed(it.width) and _fixed(it.height) { box(html.frame(it)) }
    else if _places(it.body).len() > 0 { box(frame(_overlay(it), width: width)) }
    else { it }
  })
  body
}

#let _space = [ ].func()

// Plain text of simple content, for class names and ids.
#let _text(c) = {
  if type(c) == str { return c }
  if type(c) != content { return "" }
  if c.func() in (_space, linebreak) { return " " }
  if c.func() == smartquote { return "'" }
  if c.has("text") { return c.text }
  if c.has("children") { return c.children.map(_text).join("") }
  if c.has("body") { return _text(c.body) }
  if c.has("child") { return _text(c.child) }
  ""
}

// Letters that Unicode does not decompose into a base letter and an accent.
#let _ascii = ("ø": "o", "œ": "oe", "æ": "ae", "ß": "ss", "ł": "l", "đ": "d", "ð": "d", "þ": "th", "ı": "i")

// Lowercase ASCII words joined by hyphens, for ids and class names. Accents
// go by decomposing each letter (NFKD) and dropping the combining marks, so
// that any accented Latin letter keeps its base: `Erdős–Rényi` gives
// `erdos-renyi`.
#let _slug(s) = {
  lower(s)
    .normalize(form: "nfkd")
    .replace(regex("\p{M}+"), "")
    .replace(regex("[" + _ascii.keys().join() + "]"), m => _ascii.at(m.text))
    .replace(regex("[^a-z0-9]+"), "-")
    .trim("-")
}

/// Id of a heading: its label if it has one, else a slug of its text
/// (`Related work` gives `related-work`), so that a link to a section survives
/// edits elsewhere in the document. Headings of one page that share a text get
/// `-2`, `-3`, ... Returning `none` leaves the id to Typst (`loc-N`, which
/// shifts whenever the document changes). Contextual.
#let heading-id(it) = {
  if it.has("label") { return anchor-id(it.label) }
  let slug = _slug(_text(plain(it.body)))
  if slug == "" { return none }
  // Earlier headings of the same HTML document: of the same page in a bundle
  // (`page` marks its pages), of the whole source otherwise.
  let sel = selector(heading).before(it.location(), inclusive: false)
  let page = query(selector(<web-page>).before(it.location())).at(-1, default: none)
  if page != none and page.value.at("bundle", default: false) { sel = sel.after(page.location()) }
  let same = query(sel).filter(h => not h.has("label") and _slug(_text(plain(h.body))) == slug).len()
  if same == 0 { slug } else { slug + "-" + str(same + 1) }
}

/// Default rendering of a heading number: `<span class="num">1.2</span> `.
#let heading-number(it, number) = {
  html.elem("span", attrs: (class: "num"), number)
  [ ]
}

/// Headings are rebuilt as real `<h1>`-`<h6>`, whatever a template did to them.
/// `offset` is added to the level (1 keeps `<h1>` for the document title);
/// `number` formats the number prefix as `(it, number) => content`; `id` gives
/// the id as `it => str` (or `none`).
#let heading-rules(offset: 1, number: heading-number, id: heading-id, body) = {
  show heading: it => on-web(it, it => {
    let n = if it.numbering != none {
      numbering(it.numbering, ..counter(heading).at(it.location()))
    }
    let anchor = id(it)
    html.elem("h" + str(calc.clamp(it.level + offset, 1, 6)), attrs: if anchor != none { (id: anchor) } else { (:) }, {
      if n != none { number(it, n) }
      it.body
    })
  })
  body
}

/// Figures.
/// - A figure whose kind is a string and that has no caption is a theorem-like
///   statement: `<div class="env env-KIND env-SUPPLEMENT">`, plus `env-plain`
///   when it is not numbered (a proof). So is any figure whose kind is in
///   `env-kinds`, caption or not (ctheorems stores the name of a theorem in the
///   caption and prints it itself).
/// - Kinds listed in `frame-kinds` are rendered as SVG, with their caption.
/// - Everything else stays a `<figure>`; a drawing that contains no image is
///   framed as a whole.
#let figure-rules(frame-kinds: ("algorithm",), env-kinds: ("thmenv",), frame-width: 45em, body) = {
  show figure.caption: it => on-web(it, it => html.elem("figcaption", {
    if it.numbering != none {
      html.elem("span", attrs: (class: "caption-label"), {
        it.supplement
        if it.supplement != none { sym.space.nobreak }
        it.counter.display(it.numbering)
        it.separator
      })
    }
    it.body
  }))
  show figure: it => on-web(it, it => {
    let custom = type(it.kind) == str
    let kind = if custom { it.kind } else { repr(it.kind) }
    let to-frame = custom and it.kind in frame-kinds
    if custom and not to-frame and (it.caption == none or it.kind in env-kinds) {
      let classes = ("env", "env-" + _slug(kind))
      let supplement = _slug(_text(it.supplement))
      if supplement != "" and "env-" + supplement not in classes { classes.push("env-" + supplement) }
      if it.numbering == none { classes.push("env-plain") }
      return html.elem("div", attrs: (class: classes.join(" "), .._anchor(it)), it.body)
    }
    if it.kind == image and not _contains(it.body, c => c.func() == image) { to-frame = true }
    let body = if to-frame { frame(it.body, width: frame-width) } else { it.body }
    let caption-first = it.caption != none and figure.caption.position == top
    html.elem("figure", attrs: (class: "fig fig-" + kind, .._anchor(it)), {
      if caption-first { it.caption }
      body
      if not caption-first { it.caption }
    })
  })
  body
}

// Content tall enough for its delimiters to grow.
#let _tall-math = (math.frac, math.binom, math.mat, math.vec, math.cases, math.root, math.underbrace, math.overbrace, math.limits)
#let _big-operators = ("∑", "∏", "∐", "∫", "∬", "∭", "∮", "⋃", "⋂", "⨁", "⨂", "⨀", "⋁", "⋀", "⨆")
#let _is-tall(c) = (
  c.func() in _tall-math
    or (c.func() == math.op and c.at("limits", default: false))
    or (c.has("text") and c.text in _big-operators)
)

/// Equations.
/// - MathML does not show equation numbers (typst#8117): numbered block
///   equations get one.
/// - `overline`/`underline`, dropped by MathML export, become accents.
/// - Equations using a function listed in `svg` fall back to SVG; `svg: true`
///   draws every equation, for reading apps that have no MathML.
/// - Browsers have no tolerance when they stretch delimiters, so `(x + 1)`
///   gets oversized parentheses. With `tame-delimiters`, delimiters around
///   content that is not tall are emitted as fixed-size ones.
#let math-rules(number: true, svg: (math.cancel,), tame-delimiters: true, frame-width: 45em, body) = {
  show math.lr: it => on-web(it, it => {
    let sized = it.has("size") and it.size not in (auto, 100%, 100% + 0pt)
    // Without `lr` the delimiters come out with stretchy="false"; the class
    // keeps the group in one <mrow>, which browsers do not break across lines.
    if tame-delimiters and not sized and not _contains(it.body, _is-tall) {
      math.class("normal", it.body)
    } else { it }
  })
  show math.overline: it => on-web(it, it => math.accent(it.body, sym.macron))
  show math.underline: it => on-web(it, it => math.attach(math.limits(it.body), b: sym.macron))
  show math.equation: it => on-web(it, it => {
    set math.equation(supplement: _math-marker)
    if svg == true or (type(svg) == array and svg.len() > 0 and _contains(it.body, c => c.func() in svg)) {
      if it.block { frame(it, width: frame-width) } else { box(html.frame(it)) }
    } else if it.block and number and it.numbering != none {
      html.elem("div", attrs: (class: "eq", .._anchor(it)), {
        it
        html.elem("div", attrs: (class: "eq-num"), numbering(
          it.numbering,
          ..counter(math.equation).at(it.location()),
        ))
      })
    } else { it }
  })
  body
}

/// Smaller fixes: page references (an error in HTML), custom enum numbering
/// (lost in a plain `<ol>`), emphasis around block content (invalid nesting).
#let text-rules(body) = {
  show ref.where(form: "page"): it => on-web(it, _ => none)
  show enum: it => on-web(it, it => {
    if type(it.numbering) != str or it.numbering == "1." { return it }
    let n = if it.start == auto { 1 } else { it.start }
    html.elem("ol", attrs: (class: "enum-custom"), {
      for item in it.children {
        let k = item.at("number", default: auto)
        if type(k) != int { k = n }
        html.elem("li", {
          html.elem("span", attrs: (class: "enum-num"), numbering(it.numbering, k))
          [ ]
          item.body
        })
        n = k + 1
      }
    })
  })
  show emph: it => on-web(it, it => {
    if _contains(it.body, _is-blocky) { html.elem("div", attrs: (class: "em"), it.body) } else { it }
  })
  show strong: it => on-web(it, it => {
    if _contains(it.body, _is-blocky) { html.elem("div", attrs: (class: "strong"), it.body) } else { it }
  })
  body
}

/// All the rules. Apply after the project's element-replacing rules.
#let web-rules(
  heading-offset: 1,
  heading-number: heading-number,
  heading-id: heading-id,
  frame-width: 45em,
  frame-kinds: ("algorithm",),
  env-kinds: ("thmenv",),
  number-equations: true,
  svg-math: (math.cancel,),
  tame-delimiters: true,
  body,
) = {
  show: transparent-rules
  show: spacing-rules
  show: frame-rules.with(width: frame-width)
  show: heading-rules.with(offset: heading-offset, number: heading-number, id: heading-id)
  show: figure-rules.with(frame-kinds: frame-kinds, env-kinds: env-kinds, frame-width: frame-width)
  show: math-rules.with(number: number-equations, svg: svg-math, tame-delimiters: tame-delimiters, frame-width: frame-width)
  show: text-rules
  body
}

// -----------------------------------------------------------------------------
// Stylesheets and interface strings
// -----------------------------------------------------------------------------

// What a document contains (also usable alone, inside another site), then the
// page around it.
#let _css() = read("web-content.css") + read("web.css")

#let _strings = (
  en: (abstract: "Abstract", keywords: "Keywords", contents: "Contents", on-page: "On this page", search: "Search", menu: "Menu", theme: "Theme"),
  fr: (abstract: "Résumé", keywords: "Mots-clés", contents: "Sommaire", on-page: "Sur cette page", search: "Rechercher", menu: "Menu", theme: "Thème"),
)

// Contextual: follows `text.lang`.
#let _s(key) = _strings.at(text.lang, default: _strings.en).at(key)

// Number and text of a heading, for a table of contents.
#let _toc-entry(h) = {
  if h.numbering != none {
    html.elem("span", attrs: (class: "num"), numbering(h.numbering, ..counter(heading).at(h.location())))
    [ ]
  }
  plain(h.body)
}

/// Table of contents as a flat list of links (`<li class="toc-lN">`). Unlike
/// `outline()`, it never nests a link inside a link when a heading contains a
/// reference, and never duplicates a footnote.
#let toc(depth: 3, title: auto) = context {
  let hs = query(heading).filter(h => h.outlined and h.level <= depth)
  if hs.len() == 0 { return }
  html.elem("nav", attrs: (class: "toc", role: "doc-toc"), {
    html.elem("h2", if title == auto { _s("contents") } else { title })
    html.elem("ul", hs
      .map(h => html.elem("li", attrs: (class: "toc-l" + str(h.level)), link(h.location(), _toc-entry(h))))
      .join())
  })
}

// -----------------------------------------------------------------------------
// Single-page article
// -----------------------------------------------------------------------------

#let _author-item(a, emails: true) = {
  if type(a) != dictionary { a = (name: a) }
  html.elem("li", {
    html.elem("span", attrs: (class: "name"), a.name)
    let orcid = a.at("orcid", default: none)
    if orcid != none {
      [ ]
      html.elem("a", attrs: (class: "orcid", href: "https://orcid.org/" + orcid, title: "ORCID " + orcid), "iD")
    }
    let email = a.at("email", default: none)
    if emails and email != none {
      [ ]
      html.elem("a", attrs: (class: "email", href: "mailto:" + email, title: email), "✉")
    }
    let affil = a.at("affiliations", default: a.at("affiliation", default: none))
    if affil != none { html.elem("span", attrs: (class: "affil"), affil) }
  })
}

// `article` has a parameter named `toc`.
#let _toc = toc

/// Front matter and shell of a self-contained article page. In PDF it returns
/// `body` unchanged.
///
/// - authors: strings or dictionaries with `name` and optional `orcid`, `email`,
///   `affiliations`.
/// - links: array of `(label, url)` pairs (PDF, code, DOI, ...).
/// - meta: array of `(label, content)` pairs listed under the abstract
///   (supplementary material, funding, acknowledgements, ...).
/// - toc: `true`, `false`, or the depth of the table of contents.
/// - emails: `false` leaves the e-mail addresses out of the page (a `mailto:`
///   link on a public page is harvested more readily than one in a PDF).
/// - css: `auto` inlines web-content.css and web.css; a string replaces them;
///   `none` emits nothing.
#let article(
  title: none,
  authors: (),
  abstract: none,
  keywords: (),
  date: none,
  links: (),
  meta: (),
  toc: true,
  emails: true,
  css: auto,
  body,
) = {
  set document(title: title) if title != none
  context if target() == "paged" { body } else {
    if css != none { html.style(if css == auto { _css() } else { css }) }
    html.elem("header", attrs: (class: "article-header typst"), {
      if title != none { html.elem("h1", attrs: (class: "title"), title) }
      if authors.len() > 0 { html.elem("ul", attrs: (class: "authors"), authors.map(_author-item.with(emails: emails)).join()) }
      if date != none { html.elem("p", attrs: (class: "date"), date) }
      if links.len() > 0 {
        html.elem("p", attrs: (class: "links"), links
          .map(((label, url)) => html.elem("a", attrs: (href: url), label))
          .join([ ]))
      }
      if abstract != none {
        html.elem("section", attrs: (class: "abstract"), {
          html.elem("h2", _s("abstract"))
          abstract
        })
      }
      if keywords.len() > 0 {
        html.elem("p", attrs: (class: "keywords"), {
          html.elem("strong", _s("keywords"))
          [: ]
          keywords.join(", ")
        })
      }
      if meta.len() > 0 {
        html.elem("dl", attrs: (class: "meta"), meta
          .map(((label, value)) => html.elem("dt", label) + html.elem("dd", value))
          .join())
      }
    })
    if toc != false { _toc(depth: if type(toc) == int { toc } else { 3 }) }
    html.elem("main", attrs: (class: "article typst"), body)
  }
}

// -----------------------------------------------------------------------------
// Multi-page site
// -----------------------------------------------------------------------------
//
// One `page(path, ...)[...]` per output page. The same entry compiles as a
// bundle (one HTML document per page), as a single HTML file (one
// `<section class="page" data-path>` per page) and as a PDF (pages are
// transparent). The chrome (top bar, navigation, pager) only uses computed
// relative paths, so it does not depend on the backend.

#let _page-mark = <web-page>
#let _part-mark = <web-part>

#let _rel(from, to) = "../" * (from.split("/").len() - 1) + to

#let _a(href, body, ..attrs) = html.elem("a", attrs: (href: href, ..attrs.named()), body)

#let _current() = query(selector(_page-mark).before(here())).at(-1, default: none)

#let _headings-of(p) = {
  let all = query(_page-mark)
  let i = all.position(q => q.location() == p.location())
  let sel = selector(heading).after(p.location())
  if i != none and i + 1 < all.len() { sel = sel.before(all.at(i + 1).location()) }
  query(sel)
}

#let _title-of(p) = {
  if p.value.title != none { return p.value.title }
  let hs = _headings-of(p)
  if hs.len() > 0 { hs.first().body } else { p.value.path }
}

/// Names a group of pages in the navigation (a thesis part). `part(none)`
/// ends the current group with a blank line.
#let part(title) = [#metadata((title: title))#_part-mark]

#let _sidebar() = context {
  let me = _current()
  if me == none { return }
  html.elem("nav", attrs: (class: "global-nav"), html.elem("ul", {
    for it in query(selector(_page-mark).or(_part-mark)) {
      if it.label == _part-mark {
        if it.value.title == none { html.elem("li", attrs: (class: "nav-sep")) } else {
          html.elem("li", attrs: (class: "nav-part"), plain(it.value.title))
        }
      } else {
        let cls = ()
        if it.location() == me.location() { cls.push("active") }
        if it.value.sub { cls.push("nav-sub") }
        html.elem(
          "li",
          attrs: if cls.len() > 0 { (class: cls.join(" ")) } else { (:) },
          _a(_rel(me.value.path, it.value.path), plain(_title-of(it))),
        )
      }
    }
  }))
}

#let _local-toc() = context {
  let me = _current()
  if me == none { return }
  let hs = _headings-of(me).filter(h => h.level in (2, 3))
  if hs.len() == 0 { return }
  html.elem("nav", attrs: (class: "local-toc"), {
    html.elem("h3", _s("on-page"))
    html.elem("ul", hs.map(h => html.elem("li", attrs: (class: "toc-l" + str(h.level)), link(h.location(), _toc-entry(h)))).join())
  })
}

#let _pager() = context {
  let me = _current()
  if me == none { return }
  let all = query(_page-mark)
  let i = all.position(q => q.location() == me.location())
  if i > 0 {
    let p = all.at(i - 1)
    _a(_rel(me.value.path, p.value.path), class: "nav-prev", [← #plain(_title-of(p))])
  } else { html.elem("span") }
  if i + 1 < all.len() {
    let p = all.at(i + 1)
    _a(_rel(me.value.path, p.value.path), class: "nav-next", [#plain(_title-of(p)) →])
  } else { html.elem("span") }
}

#let _theme-script = "(function(){var t=localStorage.getItem('theme')||'auto';if(t==='auto')t=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';document.documentElement.dataset.theme=t;})();"

// Everything around the page content. It comes BEFORE <main> in the DOM because
// Typst appends the endnotes after the last child of <body>; the stylesheet
// places the pieces with a grid.
//
// The stylesheet is inlined rather than linked: Typst cannot write into <head>,
// and a stylesheet linked from <body> lets browsers paint once before it
// applies (a visible flash of unstyled buttons and links).
#let _chrome(path, site) = {
  let to(p) = _rel(path, p)
  let bare = (data-pagefind-ignore: "")
  html.script(_theme-script)
  html.style(_css() + site.at("css", default: ""))
  if "favicon" in site { html.link(rel: "icon", href: to(site.favicon)) }
  html.elem("header", attrs: (class: "topbar", ..bare), {
    html.elem("div", attrs: (class: "topbar-left"), {
      html.elem("button", attrs: (class: "sidebar-toggle-btn", id: "sidebar-toggle-left", type: "button", aria-label: _s("menu")))
      _a(to(site.at("home", default: "index.html")), class: "topbar-title", site.at("title", default: none))
    })
    html.elem("div", attrs: (class: "topbar-right"), {
      html.elem("button", attrs: (class: "search-trigger", type: "button", aria-label: _s("search")), html.elem("kbd", "Ctrl+K"))
      html.elem("button", attrs: (class: "theme-toggle", type: "button", aria-label: _s("theme")))
      let other = site.at("other-lang", default: none)
      if other != none { _a(to("../" + other + "/" + path), class: "lang-switch", upper(other)) }
      let repo = site.at("repo", default: none)
      if repo != none { _a(repo, class: "github-link", aria-label: "GitHub", target: "_blank", rel: "noopener", none) }
      html.elem("button", attrs: (class: "sidebar-toggle-btn", id: "sidebar-toggle-right", type: "button", aria-label: _s("on-page")))
    })
  })
  html.elem("aside", attrs: (class: "sidebar-left", ..bare), _sidebar())
  html.elem("aside", attrs: (class: "sidebar-right", ..bare), _local-toc())
  html.elem("footer", attrs: (class: "page-nav", ..bare), _pager())
  html.script(src: to("assets/web.js"), defer: true)
}

/// One output page.
///
/// - path: output path inside the site, e.g. `"ch1.html"`.
/// - title: navigation title (defaults to the first heading of the page).
/// - site: dictionary shared by all pages: `title`, and optionally `home`
///   (path of the home page), `repo` (URL), `other-lang` (code of the other
///   language, built as a sibling site), `favicon` (path inside the site),
///   `css` (extra CSS text appended to the stylesheets).
/// - sub: indent the entry in the navigation.
/// - reset: content inserted first (counter resets).
/// - chrome: `false` leaves the navigation out (embedding). Keep it for an
///   EPUB: epub.py reads the order of the pages in it, then drops it.
#let page(path, title: none, site: (:), sub: false, reset: none, chrome: true, body) = {
  let inner(bundle) = {
    [#metadata((path: path, title: title, sub: sub, bundle: bundle))#_page-mark]
    reset
    context if target() != "paged" {
      if chrome { _chrome(path, site) }
      html.elem("main", attrs: (class: "content typst", data-pagefind-body: ""), body)
    } else { body }
  }
  context if target() == "bundle" {
    let site-title = site.at("title", default: none)
    document(
      path,
      title: if title != none and site-title != none [#plain(title) — #site-title] else if title != none { plain(title) } else { site-title },
      inner(true),
    )
  } else if target() == "html" {
    html.elem("section", attrs: (class: "page", data-path: path), inner(false))
  } else { inner(false) }
}

/// Emits web.js (and `extra`, a dictionary path -> data) as bundle assets. A
/// no-op outside bundle export.
#let site-assets(extra: (:)) = context if target() == "bundle" {
  asset("assets/web.js", read("web.js"))
  for (path, data) in extra { asset(path, data) }
}
