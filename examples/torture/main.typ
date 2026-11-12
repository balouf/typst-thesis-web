// PDF edition. From the repository root:
//   typst compile --root . examples/torture/main.typ

#import "template.typ": content-rules, counter-rules, layout

#show: content-rules
#show: counter-rules
#show: layout.with(title: [A hostile template], authors: ("Ada Lovelace", "Alan Turing"))

#include "body.typ"

#bibliography("refs.bib")
