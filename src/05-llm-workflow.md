# Working with an LLM

Both reference projects ([phd-pagerank](https://github.com/balouf/phd-pagerank) and
[hdr-p2p](https://github.com/balouf/hdr-p2p)) were built with heavy LLM assistance. This
chapter shares what worked, what did not, and how to structure the collaboration
effectively.

## What LLMs Excel At

### LaTeX to Typst conversion

Give an LLM a LaTeX chapter and ask for clean Typst output. This works remarkably well for
standard academic markup: sections, theorems, equations, figures, tables, citations,
cross-references. A 30-page chapter typically converts in one pass with only minor fixes
needed (usually around label formatting or package-specific commands).

### Translation

Academic prose translates very well. The mathematical content stays unchanged (equations,
labels, references are language-neutral), so the LLM only needs to handle the surrounding
text. For a bilingual thesis, translating a French chapter to English (or vice versa) is
one of the highest-value uses of an LLM.

### Boilerplate generation

CSS stylesheets, build scripts, GitHub Actions workflows, README files — all the
infrastructure around the thesis content. These follow well-known patterns and an LLM can
produce working versions quickly. The stylesheet, the scripts and the workflows of this
repository were LLM-generated with iterative refinement.

### Adapting existing patterns

"Make this file follow the same pattern as that file" is a prompt that works consistently.
If you have one chapter converted and want to convert the next one in the same style, give
the LLM both the source and the example output. It will replicate conventions (heading
levels, label naming, theorem usage) accurately.

### Porting a document to the web

Writing the web entry file of an existing paper or thesis (see
[HTML Export](03-html-export.md)) is a task an LLM does well, because the result can be
checked mechanically. The loop that works:

1. Give it the PDF entry file, the template, and `web.typ` (the layer documents itself
   in its comments). Ask for a web entry file next to the PDF one, **without modifying
   any section or chapter**.
2. Have it run `uv run tools/check.py <entry> --json`. The report lists every element
   Typst dropped, with file and line, the broken links, the invalid nesting, and a
   census of headings, figures and equations against the source.
3. Each item points at a rule of the template that needs to move (a layout rule applied
   in the web entry, a rule declared on the wrong side of `web-rules`) or at a construct
   to tag. Fix, run again, until the report is clean.
4. Look at the page yourself. The check proves that the content is there, not that it
   looks right.

Two instructions save a lot of back and forth: "the PDF must not change" (compile it
before and after with `SOURCE_DATE_EPOCH=0` and compare the files: Typst is
deterministic), and "do not edit the vendored `web.typ`; if a rule is missing, say so".

## What Humans Must Do

### Review all mathematical content

LLMs can subtly alter notation, drop indices, change quantifier scope, or rephrase a
condition in a way that changes its meaning. Every equation, theorem statement, and proof
step needs human verification. This is non-negotiable.

### Make editorial decisions

Which chapters to include, how to structure the HTML navigation, what to translate versus
keep in the original language, whether to split a long chapter into sub-pages — these are
judgment calls that define the final product.

### Verify cross-references

After conversion or translation, compile immediately. Broken labels (`@some-label` that no
longer exists) will show as errors. Cross-references between chapters are especially
fragile during restructuring.

### Check specialized terminology

Domain-specific terms may not translate correctly. A "stable matching" in game theory is
not the same as a "matching stable" in French (the adjective placement matters). Review
translated terminology against the conventions of your field.

### Final visual review

Both the PDF and the HTML output need a visual pass. Check that figures render correctly,
theorem boxes have the right colors, math is not clipped, and the sidebar navigation makes
sense.

## Prompting Tips

### Provide full context

Always give the LLM both the source file content and the target pattern or conventions.
Do not rely on it guessing your project structure.

### Be explicit about preservation

For conversion tasks, use prompts like: "Convert this LaTeX to Typst. Preserve ALL labels
(`@xxx`), references, math (`$...$`), footnotes, and heading structure. Do not summarize
or rephrase any content."

### For translation, be surgical

"Translate ONLY the French prose to English. Keep all Typst markup, labels, references,
math environments, and code exactly as they are. Do not translate proper nouns or
established technical terms."

### One file at a time

Process files individually for better quality. Bulk processing (multiple chapters in one
prompt) leads to more errors, truncation, and inconsistencies. The overhead of separate
prompts is small compared to the debugging cost.

### Use parallel agents for independent work

If you have six chapters to translate, you can run six parallel agent sessions — one per
chapter. They are independent tasks with no shared state. This is where LLMs save the
most wall-clock time.

## Iterative Workflow

The most effective process is a tight loop:

1. **Convert or translate** a single file with the LLM.
2. **Compile immediately** (`typst compile main.typ` or the HTML pipeline).
3. **Fix any errors** — broken references, missing imports, syntax issues.
4. **Visual check** — open the PDF or HTML and scan for rendering problems.
5. **Commit** the working state.
6. **Repeat** for the next file.

This catches problems early. Do not batch too many LLM-generated changes before
compiling — if you convert five chapters and then try to compile, debugging the
accumulated errors is painful.

For the HTML pipeline specifically, a useful shortcut is:

```bash
uv run web/build.py --lang fr --skip-pdf --skip-search
```

This builds only the French site, which takes a second or two.

## Cost-Effective Split

The most efficient workflow is:

- **LLM for the 90% mechanical work**: LaTeX-to-Typst conversion, prose translation,
  CSS/JS boilerplate, build script generation, README writing.
- **Human for the 10% that requires judgment**: mathematical review, editorial decisions,
  terminology verification, visual checks, project structure.

This matches how the two reference projects were actually built. The LLM produced the
first draft of nearly every file; the human reviewed, corrected, and made structural
decisions. The total effort was a fraction of doing everything manually, with the human
time focused where it matters most.
