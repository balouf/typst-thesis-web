// =============================================================================
// HTML Export Overrides
// Show rules and functions specific to HTML export
// =============================================================================

#import "i18n.typ": lang, t, _appendix-state, reset-chapter-counters

// -----------------------------------------------------------------------------
// Show rules for HTML export
// -----------------------------------------------------------------------------

#let html-show-rules(doc) = {
  // --- Headings: produce semantic <h1>/<h2>/<h3>/<h4> ---
  // The show rules in thesis-style.typ replace headings with blocks,
  // which loses HTML semantics. We override them here.
  show heading: it => context {
    if target() != "html" { return it }
    let level = calc.min(it.level, 4)
    let tag = ("h1", "h2", "h3", "h4").at(level - 1)
    let num-display = if it.numbering != none {
      if level == 1 {
        let prefix = if _appendix-state.get() { t([Annexe ], [Appendix ]) } else { t([Chapitre ], [Chapter ]) }
        prefix + counter(heading).display() + [ — ]
      } else if level <= 3 {
        counter(heading).display() + [ ]
      }
    }
    let label-id = if it.has("label") { str(it.label) } else { none }
    let content = [#num-display#it.body]
    if label-id != none {
      html.elem(tag, attrs: (id: label-id), content)
    } else {
      html.elem(tag, content)
    }
    if level == 1 {
      reset-chapter-counters(include-theorems: true)
    }
  }

  // --- Inline equations: inline SVG rendering in a box ---
  show math.equation.where(block: false): it => context {
    if target() == "html" {
      box(html.frame(it))
    } else {
      it
    }
  }

  // --- Block equations: SVG rendering ---
  show math.equation.where(block: true): it => context {
    if target() == "html" {
      html.frame(it)
    } else {
      it
    }
  }

  // --- Layout grids (e.g. side-by-side figures) ---
  // html.frame is needed to preserve internal figure labels.
  // Width is constrained to avoid an oversized SVG.
  show grid: it => context {
    if target() == "html" {
      html.frame(block(width: 42em, it))
    } else {
      it
    }
  }

  // --- Theorems in HTML: the figure passes through as <figure> ---
  // No show rule needed: the figure renders directly in HTML.

  // --- Algorithms: SVG rendering (too complex for native HTML) ---
  // Width is constrained to force line wrapping in the SVG,
  // otherwise text renders at the PDF page width (~16cm) and the
  // image is too wide for the HTML content area (~800px).
  show figure.where(kind: "algorithm"): it => context {
    if target() == "html" {
      html.frame(block(width: 38em, it))
    } else {
      it
    }
  }

  doc
}

// -----------------------------------------------------------------------------
// Section marker for the build.py chunking script
// Each chapter is wrapped in <section class="chapter" id="...">
// -----------------------------------------------------------------------------

#let chapter-section(id, body) = context {
  if target() == "html" {
    html.elem("section", attrs: (class: "chapter", id: id), body)
  } else {
    body
  }
}

// Marker for parts (Part I, Part II)
#let part-marker(id, title) = context {
  if target() == "html" {
    html.elem("section", attrs: (class: "part", id: id), {
      html.elem("h1", attrs: (class: "part-title"), title)
    })
  }
}
