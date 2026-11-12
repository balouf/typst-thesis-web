// Shared by main.typ (PDF) and web.typ (HTML). It must never need to know
// which one includes it.

#import "template.typ": *
#import "@preview/cetz:0.4.2": canvas, draw
#import "@preview/fletcher:0.5.8": diagram, node, edge
#import "@preview/algo:0.3.6": algo, i, d
#import "@preview/droplet:0.3.1": dropcap

= Containers and spacing <sec:containers>

#dropcap(height: 2, gap: 2pt)[Layout containers are dropped with their content by HTML export.] The
words in this paragraph must all survive: #pad(left: 1em)[padded], #align(right)[aligned],
#place(top + right)[placed], #move(dx: 1pt)[moved].

#stack(dir: ltr, [first], h(1em), [second])

#columns(2)[Two columns of text become one. #colbreak() Second column.]

Spacing words apart#h(1em)with `h`, pushing#h(1fr)to the right. #v(5mm)
#pagebreak(weak: true)
A page reference#footnote[A footnote, with math $a^2 + b^2$ and a citation @knuth1984.] is an
error in HTML: see @sec:math#ref(<sec:math>, form: "page").

+ first item
+ second item
+ third item

#block(fill: rgb("#fff0f0"), stroke: (left: 2pt + red), inset: 8pt)[A colored block keeps its colors.]

A fixed-size box #box(width: 8mm, height: 3mm, fill: blue) and a shape with text:
#rect(inset: 4pt)[inside a rectangle]

== Sub-heading with math $x^2$ and a reference to @sec:math <sec:sub>

Text under the sub-heading.

= Mathematics <sec:math>

Inline $a quad b thin c$ and $overline(A) = A + underline(s)$.

$ E = m c^2 $ <eq:einstein>

$ f(x) &= sum_(k=0)^n binom(n, k) x^k \
       &= (1 + x)^n $ <eq:binom>

#math.equation(block: true, numbering: none)[$ integral_0^1 x dif x = 1 / 2 $]

$ cancel(a) + b = b $

See @eq:einstein and @eq:binom.

= Statements <sec:statements>

#theorem("Euclid")[There are infinitely many primes.] <thm:euclid>

#cproof[Suppose not, and multiply them all. #lorem(6)]

#remark[Remarks are boxes too.]

#lemma(name: "Blocks in italics")[
  A statement with several paragraphs.

  A second paragraph, a list and a displayed equation:
  + one;
  + two.
  $ a + b = c $ <eq:in-lemma>
] <lem:blocks>

#proof[By @thm:euclid, @lem:blocks and @eq:in-lemma.]

= Figures <sec:figures>

#figure(image("fig.svg", width: 40%), caption: [A wrapped image stays an `<img>`.]) <fig:image>

#figure(
  canvas({
    draw.circle((0, 0), radius: 1)
    draw.content((0, 0), [$x^2$])
  }),
  caption: [A cetz drawing, with a reference to @thm:euclid in its caption.],
) <fig:cetz>

#figure(
  grid(columns: 2, gutter: 1em, rect(width: 2cm, height: 1cm, fill: aqua), rect(width: 2cm, height: 1cm, fill: orange)),
  caption: [A grid of drawings.],
) <fig:grid>

A bare canvas, outside any figure:

#canvas({ draw.rect((0, 0), (2, 1)) })

A fletcher diagram:

#diagram(node((0, 0), $A$), edge("->"), node((1, 0), $B$))

#figure(
  kind: "algorithm",
  supplement: [Algorithm],
  caption: [Euclid's algorithm.],
  algo(title: "Gcd", parameters: ("a", "b"))[
    while $b != 0$:#i\
      $(a, b) <- (b, a mod b)$#d\
    return $a$
  ],
) <alg:gcd>

#figure(
  table(columns: 2, table.header([Key], [Value]), [a], [1], [b], [2]),
  caption: [A table.],
) <tab:kv>

See @fig:image, @fig:cetz, @fig:grid, @alg:gcd, @tab:kv and @lamport1994.
