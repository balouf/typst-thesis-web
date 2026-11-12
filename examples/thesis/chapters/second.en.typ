= Cross-references between pages <ch:second>

#import "../templates/prelude.typ": *

This second chapter lives on its own page. References cross pages:
@thm:example, @eq:gauss and @fig:example are in @ch:example, and the
bibliography is on a page of its own @knuth1984.

== A section <sec:second-section>

Counters restart with each chapter#footnote[This note is the first of its page,
like the equation below.]:

$ e^(i pi) + 1 = 0 $ <eq:euler>

#theoreme[Any reference to @eq:euler stays on this page.] <thm:second>

=== A subsection

See also @lamport1994 and @thm:second.
