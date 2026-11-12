# Typst Thesis Web

A web edition for academic documents written in [Typst](https://typst.app/): a paper
becomes one self-contained HTML page, a thesis becomes a searchable site, **without
touching the sections**. Mathematics is native MathML.

**[Read the guide](https://balouf.github.io/typst-thesis-web/)**

The repository holds:

- `lib/` — the web layer you copy into your project: `web.typ` (show rules and page
  functions), `web-content.css` and `web.css`, and `web.js` for multi-page sites;
- `tools/check.py` — compiles a web edition and reports what did not reach the HTML;
- `examples/` — a paper and a bilingual thesis, ready to copy;
- `src/` — the guide, which also covers LaTeX conversion, bilingual PDF output and
  GitHub Pages deployment.

It targets **Typst 0.15.1**. HTML export is still experimental in Typst: pin the version.

## Live examples

- [PhD thesis (2004)](https://balouf.github.io/phd-pagerank/) — Web Graphs, PageRank-like Importance Measures ([source](https://github.com/balouf/phd-pagerank))
- [HDR thesis (2009)](https://balouf.github.io/hdr-p2p/) — On Peer-to-peer, Content Distribution, Acyclic Preference Networks ([source](https://github.com/balouf/hdr-p2p))

## Quick start

### A paper, as one page

1. Copy `lib/web.typ`, `lib/web-content.css` and `lib/web.css` into a `web/` folder of
   your project.
2. Write a `web.typ` entry next to your PDF entry file, on the model of
   [`examples/article/web.typ`](examples/article/web.typ): your content rules, then
   `#show: web-rules`, then `#show: article.with(...)`, then the same `#include`s.
3. Compile and check:

   ```bash
   typst compile --features html web.typ paper.html
   uv run tools/check.py web.typ
   ```

### A thesis, as a site

1. Copy [`examples/thesis`](examples/thesis) as your new project.
2. Edit `templates/meta-data.typ`, replace the chapters, and list your pages in
   `main-html.typ` (one `chapter(...)` per page).
3. Run `typst compile main.typ` for the PDF, `uv run web/build.py` for the site.

The [guide](https://balouf.github.io/typst-thesis-web/) explains each step, and the one
rule that matters: the order of the show rules in a web entry file.

## Development

```bash
uv run --with pytest pytest -q   # compiles the examples and checks their output
uv run tools/sync.py             # refreshes the copies of lib/ kept in examples/
```

## License

Guide, layer, tools and examples are licensed under the [MIT License](LICENSE).
