# Introduction

This guide walks you through converting an academic thesis (PhD, HDR, or
similar) into a modern [Typst](https://typst.app/) project with:

- **Bilingual PDF output** -- French and English from a single source.
- **HTML website** -- a responsive, searchable, multi-chapter site.
- **GitHub Pages deployment** -- automated build and publish on every push.

The techniques were developed while converting two real theses:

| Project | Source | Live site |
|---------|--------|-----------|
| PhD thesis (PageRank) | [balouf/phd-pagerank](https://github.com/balouf/phd-pagerank) | [balouf.github.io/phd-pagerank](https://balouf.github.io/phd-pagerank/) |
| HDR thesis (P2P) | [balouf/hdr-p2p](https://github.com/balouf/hdr-p2p) | [balouf.github.io/hdr-p2p](https://balouf.github.io/hdr-p2p/) |

Browse them to see what the end result looks like -- bilingual toggle, chapter
navigation, full-text search, downloadable PDFs.


## Modular structure

Each section of this guide is self-contained. Pick the ones you need:

| Section | You need this if... |
|---------|---------------------|
| [LaTeX to Typst](01-latex-to-typst.md) | Your thesis is currently in LaTeX |
| [Bilingual PDF](02-bilingual-pdf.md) | You want French + English output |
| [HTML Export](03-html-export.md) | You want a web version of your thesis |
| [GitHub Deployment](04-github-deploy.md) | You want automated build + hosting |
| [Working with an LLM](05-llm-workflow.md) | You want to use AI assistants effectively |

Already have a Typst project? Skip section 1.
Monolingual thesis? Skip section 2.
Only need PDF? Skip sections 3 and 4.


## Prerequisites

- **Typst >= 0.14.2** -- HTML export requires a recent version. Install from
  [typst.app](https://typst.app/) or via `cargo install typst-cli`.
- **Python >= 3.11** -- used by the build script that splits HTML into chapters.
- **uv** -- the fast Python package runner. Install from
  [docs.astral.sh/uv](https://docs.astral.sh/uv/). The build script uses
  `uv run` to manage its own dependencies automatically.
- **Git and GitHub** -- basic familiarity with repositories, branches, and
  GitHub Actions.


## The boilerplate

The [`boilerplate/`](https://github.com/balouf/typst-thesis-web/tree/main/boilerplate)
directory in this repository contains ready-to-use template files:

```
boilerplate/
  main.typ            # PDF entry point
  main-html.typ       # HTML entry point
  deploy.yml          # GitHub Actions workflow
  templates/
    i18n.typ           # Bilingual support (#t(), lang variable)
    meta-data.typ      # Thesis metadata (title, author, jury)
    html-overrides.typ # Show rules for HTML export
    prelude.typ        # Common imports for chapters
  chapters/
    example.typ        # Example chapter (French)
    example.en.typ     # Example chapter (English)
  web/
    build.py           # HTML build script (split, nav, search)
    assets/            # CSS and JS for the website
```

Copy the boilerplate into your own repo and follow the `TODO: adapt` comments
in each file. The guide sections below explain the reasoning behind each piece.


## Section overview

**[Section 1 -- LaTeX to Typst](01-latex-to-typst.md)**
Strategy and tooling for converting a LaTeX thesis to Typst. When to let an LLM
do the heavy lifting and when to review by hand.

**[Section 2 -- Bilingual PDF](02-bilingual-pdf.md)**
The `i18n.typ` architecture: the `#t()` function, when to use it vs. separate
`.en.typ` files, and the translation workflow.

**[Section 3 -- HTML Export](03-html-export.md)**
How Typst's HTML backend works, the show rules in `html-overrides.typ`, and
the `build.py` script that turns a single HTML blob into a navigable website.

**[Section 4 -- GitHub Deployment](04-github-deploy.md)**
Setting up GitHub Actions to compile Typst, run the build script, and deploy
to GitHub Pages automatically.

**[Section 5 -- Working with an LLM](05-llm-workflow.md)**
Practical advice for using large language models as coding partners throughout
this workflow -- what they excel at and where human judgment is essential.
