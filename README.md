# Typst Thesis Web

A guide and boilerplate for converting academic theses to [Typst](https://typst.app/) with bilingual PDF output, HTML website generation, and GitHub Pages deployment.

**[Read the guide](https://balouf.github.io/typst-thesis-web/)**

## Live examples

- [PhD thesis (2004)](https://balouf.github.io/phd-pagerank/) — Web Graphs, PageRank-like Importance Measures ([source](https://github.com/balouf/phd-pagerank))
- [HDR thesis (2009)](https://balouf.github.io/hdr-p2p/) — On Peer-to-peer, Content Distribution, Acyclic Preference Networks ([source](https://github.com/balouf/hdr-p2p))

## Quick start

1. Copy the `boilerplate/` directory as your new project
2. Edit `templates/meta-data.typ` with your thesis metadata
3. Replace `chapters/example.typ` with your own chapters
4. Update `CHAPTERS` and `PARTS` in `web/build.py`
5. Run `typst compile main.typ` for PDF, `uv run web/build.py` for the website

See the [guide](https://balouf.github.io/typst-thesis-web/) for detailed instructions on each step.

## License

Guide and boilerplate are licensed under the [MIT License](LICENSE).
