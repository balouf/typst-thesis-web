// The sections, shared by both editions. Nothing here knows about HTML.

#import "template.typ": lemma, proof, theorem

= Introduction <sec:intro>

Gauss is said to have found @eq:gauss as a schoolboy @knuth1984. We prove it in
@sec:result and draw it in @fig:triangle#footnote[The drawing is rendered as an
SVG image in the web edition.].

= Result <sec:result>

#lemma(name: "Pairing")[
  For every $n >= 1$ and $1 <= k <= n$, the terms $k$ and $n + 1 - k$ add up to
  $n + 1$.
] <lem:pairing>

#theorem[
  For every $n >= 1$,
  $ sum_(k=1)^n k = (n (n + 1)) / 2. $ <eq:gauss>
] <thm:gauss>

#proof[
  Write the sum twice, once in each order, and add term by term: by
  @lem:pairing, each of the $n$ columns adds up to $n + 1$.
]

#figure(
  grid(
    columns: 4,
    gutter: 3pt,
    ..range(16).map(i => if calc.rem(i, 4) <= calc.quo(i, 4) { circle(radius: 5pt, fill: blue) } else { circle(radius: 5pt, stroke: gray) }),
  ),
  caption: [The triangular number $1 + 2 + 3 + 4$: half of a $4 times 5$ rectangle, see @thm:gauss.],
) <fig:triangle>

Typesetting is discussed in @lamport1994.
