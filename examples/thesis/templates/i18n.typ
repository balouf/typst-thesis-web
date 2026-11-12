// =============================================================================
// Internationalization and shared configuration
// =============================================================================
//
// Usage: typst compile --input lang=fr main.typ   (default)
//        typst compile --input lang=en main.typ
//
// In main.typ:
//   #import "templates/i18n.typ": lang, t
//   #if lang == "en" { include "chapters/ch1.en.typ" }
//   #else { include "chapters/ch1.typ" }
// =============================================================================

#let lang = sys.inputs.at("lang", default: "fr")

/// Pick the right value based on the current language.
/// t(french-value, english-value) → value for current lang
#let t(fr, en) = if lang == "en" { en } else { fr }

/// Reset the counters that are numbered within chapters.
#let reset-chapter-counters() = {
  counter(footnote).update(0)
  counter(figure.where(kind: image)).update(0)
  counter(figure.where(kind: table)).update(0)
  counter(math.equation).update(0)
}
