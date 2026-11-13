// Web edition, one self-contained HTML page:
//   typst compile --features html web.typ paper.html
// The same page as an EPUB book:
//   uv run web/epub.py paper.html -o paper.epub
//
// Same sections as main.typ. No layout template: the web layer (web/web.typ, a
// vendored copy of typst-thesis-web) supplies headings, title block and figure
// handling. Order matters: rules that replace elements, then web-rules.

#import "web/web.typ": article, web-rules
#import "template.typ": content-rules
#import "meta.typ": abstract, authors, keywords, title

#show: content-rules
#show: web-rules
#show: article.with(
  title: title,
  authors: authors,
  abstract: abstract,
  keywords: keywords,
  links: (("PDF", "main.pdf"),),
)

#include "body.typ"

#bibliography("refs.bib")
