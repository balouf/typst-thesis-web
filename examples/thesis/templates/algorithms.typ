// =============================================================================
// Algorithm environments
// =============================================================================
//
// Usage in a chapter (one line per `\`, `#i` indents, `#d` dedents):
//   #alg(caption: [...])[
//     while $b != 0$ #i\
//       $(a, b) <- (b, a mod b)$ #d\
//     return $a$
//   ] <alg:gcd>
// =============================================================================

#import "@preview/algo:0.3.6": algo, i, d, no-emph, comment
#import "i18n.typ": t
#import "web/web.typ": algo-lines

// TODO: adapt — the words set in bold, the indent, the look of the block.
#let alg-keywords = t(
  ("si", "alors", "sinon", "tant que", "faire", "pour", "retourner"),
  ("if", "then", "else", "while", "do", "for", "return"),
)
#let alg-indent = 15pt

// `algo-lines` makes the algorithm text on the web (it is a drawing otherwise:
// see `frame-kinds` in main-html.typ); it changes nothing in the PDF.
#let alg(..args, body) = figure(
  algo-lines(indent: alg-indent, algo(
    line-numbers: false,
    keywords: alg-keywords,
    indent-size: alg-indent,
    indent-guides: 1pt + gray,
    comment-prefix: [#sym.triangle.stroked.r ],
  )[#body]),
  kind: "algorithm",
  supplement: t("Algorithme", "Algorithm"),
  ..args,
)
