= Example Chapter <ch:example>

#import "../templates/prelude.typ": *

This chapter illustrates the main features of the bilingual thesis template
with HTML export. It contains a theorem, a proof, a figure, a footnote,
and an equation.

#theoreme("Example")[
  Let $n in NN$ be a natural number. Then $n^2 >= 0$.
] <thm:example>

#demo[
  The proof follows directly from the fact that the square of any real number
  is non-negative, and that $NN subset RR$.
]

We can also write block equations#footnote[Equations are numbered
automatically.]:

$ sum_(k=0)^n k = n(n+1) / 2 $ <eq:gauss>

#figure(
  rect(width: 6cm, height: 3cm, stroke: 0.5pt, fill: luma(240))[
    #align(center + horizon)[_Placeholder for a figure_]
  ],
  caption: [An example figure.],
) <fig:example>

As shown in @fig:example, we can reference figures, theorems
(@thm:example), and equations (@eq:gauss) in the standard way.

An algorithm is written line by line (@alg:gcd).

#alg(caption: [Euclid's algorithm.])[
  while $b != 0$ #i #comment[invariant: the gcd of $a$ and $b$]\
    if $a < b$ then #i\
      swap $a$ and $b$ #d\
    $(a, b) <- (b, a mod b)$ #d\
  return $a$
] <alg:gcd>
