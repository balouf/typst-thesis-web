# Introduction

This guide walks you through giving an academic document written in
[Typst](https://typst.app/) a web edition, next to its PDF:

- **A paper** becomes one self-contained HTML page.
- **A thesis** becomes a responsive, searchable site, one page per chapter.
- **The sections are not touched.** The web edition is one more entry file; a
  small vendored layer does the rest, and a script checks that nothing was lost.

It also covers what surrounds that for a thesis: converting from LaTeX,
**bilingual PDF output** from a single source, and **GitHub Pages deployment**.

The techniques were developed on two theses:

| Project | Source | Live site |
|---------|--------|-----------|
| PhD thesis (PageRank) | [balouf/phd-pagerank](https://github.com/balouf/phd-pagerank) | [balouf.github.io/phd-pagerank](https://balouf.github.io/phd-pagerank/) |
| HDR thesis (P2P) | [balouf/hdr-p2p](https://github.com/balouf/hdr-p2p) | [balouf.github.io/hdr-p2p](https://balouf.github.io/hdr-p2p/) |

Browse them to see what the end result looks like -- bilingual toggle, chapter
navigation, full-text search, downloadable PDFs. A research paper (a report in a
LIPIcs layout, with home-made theorem environments and cetz plots) was the second
client, and the reason the method no longer assumes a thesis.


## Modular structure

Each section of this guide is self-contained. Pick the ones you need:

| Section | You need this if... |
|---------|---------------------|
| [LaTeX to Typst](01-latex-to-typst.md) | Your thesis is currently in LaTeX |
| [Bilingual PDF](02-bilingual-pdf.md) | You want French + English output |
| [HTML Export](03-html-export.md) | You want a web version of a paper or a thesis |
| [GitHub Deployment](04-github-deploy.md) | You want automated build + hosting of a thesis site |
| [Working with an LLM](05-llm-workflow.md) | You want to use AI assistants effectively |

Already have a Typst project? Skip section 1.
Monolingual document? Skip section 2.
A paper rather than a thesis? Section 3 is all you need.


## Prerequisites

- **Typst 0.15.1** -- HTML export with native MathML and multi-page output
  arrived in 0.15. It is still experimental, so pin the version. Install from
  [typst.app](https://typst.app/) or via `cargo install typst-cli`.
- **Python >= 3.11 and uv** -- for the checking script, and for the build script
  of a thesis site. Install uv from
  [docs.astral.sh/uv](https://docs.astral.sh/uv/); the scripts declare their own
  dependencies and `uv run` takes care of them. A single-page paper needs
  neither: `typst compile` is enough.
- **Git and GitHub** -- for the deployment chapter only.


## What is in the repository

```
lib/                    # the web layer: copy these into your project
  web.typ               #   show rules, article page, site pages
  web.css               #   stylesheet, light and dark
  web.js                #   sites only: theme toggle, search, small screens
tools/
  check.py              # did anything get lost on the way to HTML?
  sync.py               # refresh a vendored copy of lib/
examples/
  article/              # a paper: PDF and one web page
  thesis/               # a bilingual thesis: PDF and a site, with its build script
  torture/              # a deliberately hostile PDF template, the layer's test bench
```

[`examples/article`](https://github.com/balouf/typst-thesis-web/tree/main/examples/article)
and [`examples/thesis`](https://github.com/balouf/typst-thesis-web/tree/main/examples/thesis)
are meant to be copied: each one builds as it is and holds its own copy of the
layer. Follow the `TODO: adapt` comments. The guide sections below explain the
reasoning behind each piece.


## Section overview

**[Section 1 -- LaTeX to Typst](01-latex-to-typst.md)**
Strategy and tooling for converting a LaTeX thesis to Typst. When to let an LLM
do the heavy lifting and when to review by hand.

**[Section 2 -- Bilingual PDF](02-bilingual-pdf.md)**
The `i18n.typ` architecture: the `#t()` function, when to use it vs. separate
`.en.typ` files, and the translation workflow.

**[Section 3 -- HTML Export](03-html-export.md)**
What Typst's HTML export does and what it drops, the web entry file and the
order of its rules, a paper as one page, a thesis as a site, and how to check
the result.

**[Section 4 -- GitHub Deployment](04-github-deploy.md)**
Building a thesis site (languages, PDFs, search index) and publishing it to
GitHub Pages automatically.

**[Section 5 -- Working with an LLM](05-llm-workflow.md)**
Practical advice for using large language models as coding partners throughout
this workflow -- what they excel at and where human judgment is essential.
