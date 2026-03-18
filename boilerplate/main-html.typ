// =============================================================================
// Thesis — HTML export entry point
// =============================================================================
//
// Compilation:
//   typst compile --features html --format html --input lang=fr --input html=true main-html.typ web/dist/full.html
//   typst compile --features html --format html --input lang=en --input html=true main-html.typ web/dist/full.html
// =============================================================================

// -----------------------------------------------------------------------------
// Imports
// -----------------------------------------------------------------------------

#import "templates/i18n.typ": lang, t
#import "templates/meta-data.typ": *
#import "templates/math-macros.typ": *
#import "templates/environments.typ": *
#import "templates/algorithms.typ": *
#import "templates/acronyms.typ": *
#import "templates/html-overrides.typ": *
#import "templates/prelude.typ": double-vowels

// TODO: adapt — initialize acronyms if you use them
// #init-acronyms(acronyms)

// TODO: adapt — apply your thesis style if needed (page/headers are ignored in HTML)
// #import "templates/thesis-style.typ": *
// #show: thesis-style

// Show rules
#show: double-vowels
#show: html-show-rules
#show: thmrules

// -----------------------------------------------------------------------------
// HTML metadata
// -----------------------------------------------------------------------------

// TODO: adapt — set your document title and author
#set document(
  title: t(
    "Titre de la thèse en français",
    "Thesis Title in English",
  ),
  author: "Prénom Nom",
)

// -----------------------------------------------------------------------------
// Cover page (HTML version)
// -----------------------------------------------------------------------------

// TODO: adapt — include your HTML cover page
#chapter-section("cover")[
  // #include "chapters/cover.typ"
  = #thesis-title
]

// -----------------------------------------------------------------------------
// Example chapter
// -----------------------------------------------------------------------------

// TODO: adapt — add your chapters here
#chapter-section("example")[
  #if lang == "en" {
    include "chapters/example.en.typ"
  } else {
    include "chapters/example.typ"
  }
]

// -----------------------------------------------------------------------------
// Bibliography
// -----------------------------------------------------------------------------

// TODO: adapt — point to your .bib and .csl files
// #chapter-section("bibliography")[
//   #bibliography("references.bib", style: "springer-lncs-alphabetical.csl")
// ]
