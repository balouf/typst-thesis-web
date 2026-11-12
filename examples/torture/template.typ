// A PDF template written with no thought for HTML: every construct below is
// dropped, mangled or rejected by Typst's HTML export. It is the test bench of
// lib/web.typ, not a model to follow.

#import "@preview/ctheorems:1.1.3": thmbox, thmproof, thmrules

// --- Content rules: what the document MEANS (shared by PDF and web) ----------

// Equations numbered per section, by a function that reads another counter.
#let content-rules(body) = {
  set heading(numbering: "1.1")
  set math.equation(numbering: n => numbering("(1.1)", counter(heading).get().first(), n))
  set enum(numbering: "(i)")
  show: thmrules
  body
}

// A rule that returns `it`: in a web entry it must come AFTER web-rules.
#let counter-rules(body) = {
  show heading.where(level: 1): it => it + counter(math.equation).update(0)
  body
}

// --- Layout: how the PDF LOOKS (never applied in the web entry) --------------

#let layout(title: none, authors: (), body) = {
  set page("a5", margin: 1.6cm, numbering: "1", header: context align(right, text(8pt)[#counter(page).display()]))
  set par(justify: true)
  // Title block built from grids and absolute spacing.
  v(-4mm)
  grid(columns: (1fr, auto), align(left, text(16pt, weight: "bold", title)), rect(width: 1cm, height: 1cm, fill: yellow))
  grid(columns: 1, row-gutter: 2mm, ..authors.map(a => text(10pt, a)))
  v(6mm)
  // Headings as stacks and blocks.
  show heading.where(level: 1): it => {
    v(4mm)
    stack(
      dir: ltr,
      block(fill: yellow, inset: 2mm, numbering("1", ..counter(heading).at(it.location()))),
      h(4mm),
      text(13pt, it.body),
    )
    v(2mm)
  }
  show heading.where(level: 2): it => block(above: 5mm, below: 3mm, {
    numbering("1.1", ..counter(heading).at(it.location()))
    h(4mm)
    it.body
  })
  // Captions restyled, figures centered.
  show figure.caption: it => block(inset: 1mm, text(9pt, it))
  show figure: it => align(center, it)
  body
}

// --- Environments -----------------------------------------------------------

// ctheorems boxes: `pad` + colored `block`, number tied to the section.
#let theorem = thmbox("theorem", "Theorem", fill: rgb("#e8f4f8"), stroke: rgb("#2196F3"), inset: 1em, radius: 4pt, base_level: 1)
#let remark = thmbox("remark", "Remark", fill: rgb("#f8f7e8"), stroke: rgb("#d4b400"), inset: 1em, radius: 4pt, base_level: 1)
#let cproof = thmproof("proof", "Proof")

// Home-made statements: a figure with a string kind, body in italics.
#let _statement(kind, supplement) = (body, name: none) => figure(
  block(width: 100%, breakable: true)[
    #set align(left)
    *#supplement #context counter(figure.where(kind: kind)).display()#if name != none [ (#name)].* #emph(body)
  ],
  kind: kind,
  supplement: supplement,
  numbering: "1",
)
#let lemma = _statement("lemma", [Lemma])
#let proof(body) = block(width: 100%)[_Proof._ #body #h(1fr) $square$]
