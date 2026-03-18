// =============================================================================
// Prelude - Common imports for all chapters
// =============================================================================
//
// Usage in chapters:
//   #import "../templates/prelude.typ": *
// =============================================================================


#let double-vowels(body) = {
  show "oe": "œ"
  show "Oe": "Œ"
  show "ae": "æ"
  show "Ae": "Æ"
  // other rules...
  body
}

#import "environments.typ": *
#import "math-macros.typ": *
#import "algorithms.typ": *
#import "acronyms.typ": *
