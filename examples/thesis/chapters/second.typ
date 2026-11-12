= Renvois entre pages <ch:second>

#import "../templates/prelude.typ": *

Ce second chapitre vit sur sa propre page. Les renvois traversent les pages :
le @thm:example, l'@eq:gauss et la @fig:example sont dans le
@ch:example, et la bibliographie est sur une page à part @knuth1984.

== Une section <sec:second-section>

Les compteurs repartent à chaque chapitre#footnote[Cette note est la première
de sa page, comme l'équation qui suit.] :

$ e^(i pi) + 1 = 0 $ <eq:euler>

#theoreme[Tout renvoi vers @eq:euler reste sur cette page.] <thm:second>

=== Une sous-section

Voir aussi @lamport1994 et le @thm:second.
