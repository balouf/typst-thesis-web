// Paper template, in separate functions because the web edition needs the
// first and must never apply the second:
//
//   content-rules   what the paper means: numbering. Both editions.
//   layout          how the PDF looks: page, fonts, title block. PDF only.
//
// TODO: adapt — replace with the template of your venue, keeping the split.

#let content-rules(doc) = {
  set heading(numbering: "1.1")
  set math.equation(numbering: "(1)")
  doc
}

#let layout(title: none, authors: (), abstract: none, doc) = {
  set page(paper: "a4", margin: 2.5cm, numbering: "1")
  set text(font: "New Computer Modern", size: 11pt)
  set par(justify: true)
  align(center)[
    #text(size: 17pt, weight: "bold", title)

    #authors.map(a => a.name).join(", ")
  ]
  block(inset: (x: 2em, y: 1em))[*Abstract.* #abstract]
  doc
}

// Statements are figures with a string kind: numbered, referenceable with
// @label, and turned into <div class="env env-theorem"> by the web layer.
#let _statement(kind, supplement) = (body, name: none) => figure(
  kind: kind,
  supplement: supplement,
  numbering: "1",
  block(width: 100%)[
    #set align(left)
    *#supplement #context counter(figure.where(kind: kind)).display()#if name != none [ (#name)].* #emph(body)
  ],
)
#let theorem = _statement("theorem", [Theorem])
#let lemma = _statement("lemma", [Lemma])
#let proof(body) = block(width: 100%)[_Proof._ #body #h(1fr) $square$]
