# LaTeX to Typst

This section covers converting a LaTeX thesis to Typst. If your thesis is
already in Typst, skip ahead to [Bilingual PDF](02-bilingual-pdf.md).


## When and why convert

There are several good reasons to move from LaTeX to Typst:

- **Bit rot.** Old LaTeX sources often stop compiling after a few years --
  packages vanish, engines change, build toolchains break. Typst is a single
  binary with no dependency hell.
- **HTML export.** Typst exports HTML natively, with the mathematics as MathML
  (experimental; this guide targets Typst 0.15). LaTeX-to-HTML pipelines
  (tex4ht, LaTeXML, Pandoc) are fragile and rarely produce clean results.
- **Modern tooling.** Incremental compilation, built-in package manager,
  readable error messages, and a scripting language that feels closer to Python
  than TeX macros.

You do *not* need to convert if you only need the original PDF. This process
is worthwhile when you want to maintain, extend, or republish the thesis.


## Strategy: chapter by chapter

Do not try to convert the entire thesis in one pass. Work incrementally:

1. **Create the skeleton.** Set up `main.typ` with page layout, fonts, and
   imports. The `main.typ` of `examples/thesis` is a good starting point. Get it
   to compile (even if empty).

2. **Convert one chapter at a time.** Pick the simplest chapter first to
   establish patterns. Copy the LaTeX source into a `.typ` file, convert the
   markup, compile, and fix errors. Once it looks right, move to the next.

3. **Keep the LaTeX source.** Don't delete the original `.tex` files until the
   entire thesis compiles in Typst. You will refer back to them constantly.

4. **Validate the PDF.** After each chapter, compare the Typst PDF against the
   original LaTeX PDF. Check that equations render correctly, figures are
   placed, and cross-references resolve.


## Who does what

The conversion is a collaboration between you, an LLM, and Typst packages.

### LLM: bulk markup conversion

Large language models are excellent at the mechanical part of
LaTeX-to-Typst conversion. Give the LLM a LaTeX chapter and ask it to
produce the Typst equivalent. Be explicit in your instructions:

- Preserve all `\label{}` as Typst labels (`<label-name>`).
- Preserve all `\ref{}` / `\cite{}` as Typst references (`@label-name`).
- Keep all math content exactly as-is (only change LaTeX math syntax to Typst).
- Maintain the same section/subsection structure.

An LLM can typically convert a 20-page chapter in a single pass with ~90%
accuracy. The remaining 10% is where human review matters.

### Human: review and judgment

After the LLM produces a draft, review carefully:

- **Mathematics.** LLMs sometimes subtly alter mathematical notation --
  swapping a subscript, dropping a superscript, changing a symbol. Compare every
  equation against the original. This is the highest-risk area.
- **Cross-references.** Verify that labels and references compile without
  warnings. Typst will tell you about unresolved references.
- **Editorial decisions.** Some LaTeX constructs have no direct Typst
  equivalent. You decide how to handle custom environments, unusual layouts,
  or legacy formatting.

### Typst packages

Use established community packages instead of reimplementing LaTeX environments:

| LaTeX | Typst package | Notes |
|-------|---------------|-------|
| `amsthm` / `thmtools` | [ctheorems](https://typst.app/universe/package/ctheorems) | Theorem, lemma, definition, proof |
| `algorithm2e` / `algorithmicx` | [algo](https://typst.app/universe/package/algo) | Pseudocode algorithms |
| `glossaries` / `acronym` | [acrostiche](https://typst.app/universe/package/acrostiche) | Acronym management |
| `subcaption` / `subfig` | [subpar](https://typst.app/universe/package/subpar) | Subfigures with individual captions |

Check the [Typst Universe](https://typst.app/universe/) for other packages you
may need.


## Common pitfalls

### Bibliography

Typst supports two bibliography formats:

- **`.bib` (BibLaTeX/BibTeX)** -- if you already have a `.bib` file, just use
  it directly. This is the path of least resistance.
- **`.yml` (Hayagriva)** -- Typst's native format. Cleaner, but converting from
  `.bib` is rarely worth the effort for an existing thesis.

Point to your bibliography file in `main.typ`:

```typst
#bibliography("references.bib", style: "springer-lncs-alphabetical.csl")
```

CSL style files let you match the citation style of your original thesis.
Download the right one from the
[CSL repository](https://github.com/citation-style-language/styles).

### Figures

- **PDF figures** from LaTeX work directly in Typst. If your LaTeX project
  generated figures as `.pdf` files, copy them over and use
  `image("figures/foo.pdf")`.
- **EPS files** need conversion to PDF or SVG first. Use `epstopdf` or
  Inkscape for batch conversion.
- **TikZ figures** do not exist in Typst. Either keep the compiled PDF output
  from LaTeX, or redraw with Typst's drawing primitives or the
  [CeTZ](https://typst.app/universe/package/cetz) package.

### French ligatures (oe, ae)

French text contains ligatures like "œuvre" or "nœud". LaTeX handles these
through font ligatures, but Typst needs the actual Unicode characters.

`examples/thesis` defines shorthand variables in `templates/prelude.typ`:

```typst
#let oe = "œ"
#let OE = "Œ"
#let ae = "æ"
#let AE = "Æ"
```

Use them inline with `#{}` syntax: `n#{oe}ud`, `c#{oe}ur`, `#{oe}uvre`.
You can also type the Unicode characters directly (`œ`, `æ`) if your keyboard
layout supports it.

> **Why not a global show rule?** A blanket `show "oe": "œ"` would produce
> false positives: "coefficient" → "cœfficient", and every English "oe"
> (does, goes, poem…) would be corrupted. Explicit characters avoid this
> entirely.

### Encoding

Typst is strictly UTF-8. Old LaTeX files may use Latin-1 or other encodings.
If you see garbled characters, convert the source file:

```bash
iconv -f latin1 -t utf-8 chapter.tex > chapter-utf8.tex
```

Then feed the UTF-8 version to the LLM for conversion.

### Equation numbering

LaTeX and Typst number equations differently. LaTeX typically numbers by
section (e.g., Equation 3.2), while Typst numbers sequentially by default.

You can configure Typst's equation numbering, but don't waste time trying to
reproduce the exact LaTeX numbering. Readers of the new version don't care
about matching the old equation numbers -- they care about internal consistency.


## Reference projects

Both reference projects started as LaTeX theses and were converted to Typst
following this approach:

- [balouf/phd-pagerank](https://github.com/balouf/phd-pagerank) -- PhD thesis,
  ~200 pages, heavy on linear algebra and graph theory.
- [balouf/hdr-p2p](https://github.com/balouf/hdr-p2p) -- HDR thesis, ~80
  pages, combinatorics and distributed systems.

Browse their Git history to see the conversion unfold chapter by chapter.
