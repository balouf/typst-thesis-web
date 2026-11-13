// =============================================================================
// Thesis — web entry point (one HTML page per chapter)
// =============================================================================
//
// Whole site (both languages, PDFs, EPUBs, search index):
//   uv run web/build.py
// One language by hand:
//   typst compile --features html,bundle --format bundle --input lang=fr main-html.typ web/dist/fr
//
// The chapters are the same files as in main.typ and contain nothing specific
// to HTML. What differs is here: no layout template, the web layer instead, and
// one `chapter(...)` per page of the site.
// =============================================================================

#import "templates/i18n.typ": lang, t
#import "templates/thesis-style.typ": thesis-content, chapter-counters
#import "templates/meta-data.typ": *
#import "templates/prelude.typ": *
#import "templates/web/web.typ": page, part, site-assets, web-rules

// TODO: adapt — initialize acronyms if you use them
// #init-acronyms(acronyms)

// Order matters: rules that replace elements, then the web layer, then rules
// that return the element they receive.
#show: thesis-content
#show: thmrules
#show: web-rules.with(
  heading-offset: 0, // a chapter title is the <h1> of its page
  heading-number: (it, n) => if it.level == 1 [#t([Chapitre], [Chapter]) #n — ] else [#n ],
)
#show: chapter-counters

// TODO: adapt — author, site title, repository
#set document(author: "Prénom Nom")
#let site = (
  title: t("Titre de la thèse en français", "Thesis Title in English"),
  repo: "https://github.com/your-user/your-repo",
  other-lang: t("en", "fr"),
)
#let chapter = page.with(site: site)

#site-assets()

// -----------------------------------------------------------------------------
// Pages. The path is the file name on the site: keep it stable, it is the URL.
// The title is the entry in the navigation.
// -----------------------------------------------------------------------------

// TODO: adapt — customize your cover page in chapters/cover.typ
#chapter("index.html", title: t([Accueil], [Home]))[
  #include "chapters/cover.typ"
]

// TODO: adapt — add your chapters here; `#part[...]` names a group of pages
#part(t([Partie I — Exemples], [Part I — Examples]))

#chapter("example.html", title: t([Ch. 1 — Exemple], [Ch. 1 — Example]))[
  #if lang == "en" { include "chapters/example.en.typ" } else { include "chapters/example.typ" }
]

#chapter("second.html", title: t([Ch. 2 — Renvois], [Ch. 2 — Cross-references]))[
  #if lang == "en" { include "chapters/second.en.typ" } else { include "chapters/second.typ" }
]

// TODO: adapt — point to your .bib (and .csl) file
#chapter("bibliography.html", title: t([Bibliographie], [Bibliography]))[
  #bibliography("references.bib")
]
