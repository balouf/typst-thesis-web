# Bilingual PDF

This section explains how to produce French and English PDFs from a single
Typst project. If your thesis is monolingual, skip to
[HTML Export](03-html-export.md).


## Architecture: i18n.typ

The bilingual system lives in `templates/i18n.typ` (included in the
boilerplate). It defines two things:

```typst
#let lang = sys.inputs.at("lang", default: "fr")

#let t(fr, en) = if lang == "en" { en } else { fr }
```

- **`lang`** -- read from the command line via `--input lang=fr` or
  `--input lang=en`. Defaults to French.
- **`#t(french, english)`** -- the core bilingual function. Pass two values;
  the one matching the current language is returned.

Compile with:

```bash
typst compile --input lang=fr main.typ thesis-fr.pdf
typst compile --input lang=en main.typ thesis-en.pdf
```

Import `lang` and `t` wherever you need them:

```typst
#import "templates/i18n.typ": lang, t
```


## When to use #t() vs. separate files

There are two strategies for bilingual content, and you will use both.

### Inline #t(): short, mixed content

Use `#t()` for anything where both languages fit naturally on the same line
or in the same block:

```typst
// Headings
= #t([Introduction], [Introduction])

// Figure captions
#figure(
  image("figures/graph.pdf"),
  caption: t([Graphe de convergence.], [Convergence graph.]),
)

// Metadata
#let thesis-title = t(
  [#smallcaps[Analyse des réseaux pair-à-pair]],
  [#smallcaps[Analysis of Peer-to-Peer Networks]],
)

// Table of contents
#outline(title: t([Table des matières], [Table of Contents]))
```

This works well for labels, captions, UI text, and any short bilingual string.

### Separate .en.typ files: chapter prose

When a chapter is mostly prose (paragraphs of text with embedded math and
references), maintaining both languages interleaved with `#t()` becomes
unreadable. Instead, create a parallel English file:

```
chapters/
  ch1.typ       # French prose
  ch1.en.typ    # English prose
  ch2.typ
  ch2.en.typ
```

In `main.typ`, switch between them:

```typst
#if lang == "en" {
  include "chapters/ch1.en.typ"
} else {
  include "chapters/ch1.typ"
}
```

The key insight: **math, labels, figures, and references are the same in both
files**. Only the surrounding prose changes. Compare the boilerplate's
`example.typ` and `example.en.typ` to see this in practice.

### Rule of thumb

If more than about 5 consecutive lines need translation, use a separate file.
Short labels and captions stay inline with `#t()`.


## Translation workflow

### Step 1: Write the primary language first

Get the French (or English) chapter fully working -- correct math, figures
placed, cross-references resolving, no compilation warnings.

### Step 2: Let an LLM translate

Give the LLM the complete `.typ` file and ask for a translation. Be explicit:

- Translate all prose to English (or French).
- Preserve **all** Typst markup exactly: `#import`, labels (`<...>`),
  references (`@...`), math (`$...$`), function calls.
- Do not rename labels or references.
- Preserve the `#import` line at the top of the file.

An LLM can translate a 15-page chapter in seconds. The output is usually
syntactically correct on the first try.

### Step 3: Human review

After the LLM produces the translation:

- **Specialized terminology.** Academic fields have precise vocabulary. Verify
  that the LLM used the correct English (or French) terms for your domain.
- **Mathematical prose.** Sentences like "Let $f$ be a continuous function on
  $[0,1]$" need to read naturally in both languages. The LLM usually handles
  this well, but check.
- **Cultural references.** French academic conventions (e.g., "on montre que")
  don't always translate literally.

### Step 4: Compile and compare

```bash
typst compile --input lang=fr main.typ thesis-fr.pdf
typst compile --input lang=en main.typ thesis-en.pdf
```

Open both PDFs side by side. Check that all figures, equations, and references
appear in both versions.


## Pitfall: smart quotes around math in HTML

This issue is specific to HTML export but surfaces during bilingual work.
Typst's smart quote algorithm can misidentify the direction of quotation marks
when they appear adjacent to math (`$...$`). For example:

```typst
the "value of $x$"   // may produce wrong quote direction in HTML
```

The fix is to use explicit Unicode quote characters:

| Language | Opening | Closing | Unicode |
|----------|---------|---------|---------|
| English | \u201C | \u201D | `\u{201C}` / `\u{201D}` |
| French | \u00AB | \u00BB | `\u{AB}` / `\u{BB}` |

In practice, this only matters for the handful of places where quotes sit next
to math. Most prose is unaffected.
