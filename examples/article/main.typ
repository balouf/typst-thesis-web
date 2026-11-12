// PDF edition:  typst compile main.typ

#import "template.typ": content-rules, layout
#import "meta.typ": abstract, authors, title

#show: content-rules
#show: layout.with(title: title, authors: authors, abstract: abstract)

#include "body.typ"

#bibliography("refs.bib")
