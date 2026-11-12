// =============================================================================
// Thesis style
// =============================================================================
//
// The style comes in separate functions because the web edition needs some of
// them and must never apply the others:
//
//   thesis-content    what the document means: language, numbering. Applied by
//                     both editions.
//   thesis-layout     how the PDF looks: page, fonts, heading typography. PDF
//                     only (HTML export drops layout elements with their content).
//   chapter-counters  counters that restart with each chapter. Applied by both
//                     editions, always last: it returns the heading itself, so a
//                     rule that replaces headings must be declared before it.
//
// TODO: adapt — replace with your own style, keeping the split.
// =============================================================================

#import "i18n.typ": t, reset-chapter-counters
#import "meta-data.typ": *

#let thesis-content(doc) = {
  set text(lang: t("fr", "en"), region: t("FR", "US"))
  set heading(numbering: "1.1")
  // Equations and figures are numbered within chapters: (2.1), Figure 2.1.
  set math.equation(numbering: n => numbering("(1.1)", counter(heading).get().first(), n))
  set figure(numbering: n => numbering("1.1", counter(heading).get().first(), n))
  doc
}

#let thesis-layout(doc) = {
  set page(paper: "a4", margin: 2.5cm, numbering: "1")
  set text(font: "New Computer Modern", size: 12pt)
  set par(justify: true)
  show heading.where(level: 1): it => {
    pagebreak(weak: true)
    v(2cm)
    text(size: 1.6em, weight: "bold", block[
      #if it.numbering != none [#t([Chapitre], [Chapter]) #counter(heading).display() \ ]
      #it.body
    ])
    v(1cm)
  }
  doc
}

#let chapter-counters(doc) = {
  show heading.where(level: 1): it => it + reset-chapter-counters()
  doc
}

// The PDF edition applies everything.
#let thesis-style(doc) = {
  show: thesis-content
  show: thesis-layout
  show: chapter-counters
  doc
}
