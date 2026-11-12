// Web edition. From the repository root:
//   typst compile --root . --features html examples/torture/web.typ torture.html
//
// Same body as main.typ, no layout template. Order: rules that replace
// elements, then web-rules, then rules that return `it`.

#import "../../lib/web.typ": article, web-rules
#import "template.typ": content-rules, counter-rules

#show: content-rules
#show: web-rules
#show: counter-rules
#show: article.with(
  title: [A hostile template],
  authors: (
    (name: "Ada Lovelace", orcid: "0000-0000-0000-0000", affiliations: [Analytical Engine Works]),
    "Alan Turing",
  ),
  abstract: [Every construct of this document is dropped or mangled by a plain HTML export.],
  keywords: ("typst", "html"),
  links: (("PDF", "main.pdf"),),
)

#include "body.typ"

#bibliography("refs.bib")
