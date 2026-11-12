// Metadata shared by main.typ (PDF) and web.typ (HTML).
// TODO: adapt

#let title = [A Short Paper With Two Editions]

#let authors = (
  (name: "Ada Lovelace", orcid: "0000-0000-0000-0000", affiliations: [Analytical Engine Works, London]),
  (name: "Alan Turing", affiliations: [Bletchley Park]),
)

#let abstract = [
  This paper compiles to a PDF and to a self-contained web page from the same
  sections. The web edition keeps the mathematics as MathML, the statements and
  their numbers, the figures and every cross-reference.
]

#let keywords = ("typst", "html export", "mathml")
