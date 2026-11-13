# GitHub Deployment

This chapter covers building a thesis site and publishing it to GitHub Pages on every
push. A single-page paper needs none of this: `typst compile` writes one HTML file that
you host wherever you like (see the end of this chapter).

## Repository Structure

```
your-thesis/
├── .github/workflows/deploy.yml
├── .gitignore
├── README.md
├── main.typ              # PDF entry point
├── main-html.typ         # web entry point: one page(...) per chapter
├── templates/            # your templates
│   └── web/              # the web layer, vendored: web.typ, its stylesheets, web.js, epub.py
├── chapters/             # chapter source files (.typ)
├── figures/
├── web/
│   ├── build.py          # runs the build commands
│   └── assets/           # your own files: favicon.svg, extra CSS
└── references.bib
```

[`examples/thesis`](https://github.com/balouf/typst-thesis-web/tree/main/examples/thesis)
has exactly this layout and builds as it is: copy it and follow the `TODO: adapt`
comments.

## .gitignore

```gitignore
# Build output
web/dist/

# PDFs (except figure PDFs)
*.pdf
!figures/**/*.pdf

# Python
__pycache__/
.venv/

# OS
.DS_Store
Thumbs.db
```

## build.py

```bash
uv run web/build.py                       # everything
uv run web/build.py --lang fr --skip-pdf  # quick loop on one language
```

The script runs, for each language:

1. `typst compile --features html,bundle --format bundle --input lang=<lang> main-html.typ web/dist/<lang>`:
   Typst writes the site, one HTML page per chapter;
2. `typst compile --input lang=<lang> main.typ web/dist/pdf/thesis-<lang>.pdf`;
3. `templates/web/epub.py`, which packages `web/dist/<lang>` as
   `web/dist/epub/thesis-<lang>.epub`, with the first page of the PDF as its cover
   (see [An EPUB edition](03-html-export.md#an-epub-edition));
4. [Pagefind](https://pagefind.app/), which indexes `web/dist/<lang>` for the search box.

It also writes `web/dist/index.html`, which sends visitors to their language, and it
empties each language folder first: Typst never removes files from a bundle directory,
so a renamed chapter would otherwise leave its old page online.

That is all it does. It does not parse, split or rewrite HTML, and it holds no list of
chapters: the pages are declared once, in `main-html.typ`. The settings at the top are
the list of languages and the names of the PDF and of the EPUB (which
`chapters/cover.typ` links to). `--skip-pdf`, `--skip-epub` and `--skip-search` leave
a step out.

The result:

```
web/dist/
├── index.html            # language redirect
├── fr/                   # a complete site: pages, assets/web.js, assets/pagefind/
├── en/
├── pdf/
└── epub/
```

Every link inside a language folder is relative, so the site works at any URL, in a
sub-folder of GitHub Pages as well as from a local server. The search needs HTTP: to
try it locally, run `python -m http.server -d web/dist` and open
`http://localhost:8000`.

## deploy.yml

The workflow (in `examples/thesis/deploy.yml`, to be moved to
`.github/workflows/deploy.yml`) checks out the repository, installs Typst and uv, runs
`build.py` and publishes `web/dist`.

- **Triggers**: push to `main` and manual dispatch.
- **Permissions**: `pages: write` and `id-token: write`.
- **Typst version**: pinned (`typst-version: '0.15.1'`). HTML export is experimental;
  upgrade deliberately, and run `check.py` when you do.
- **`enable-cache: false`** on `setup-uv`: `build.py` declares its dependencies inline
  (the `# /// script` header) and there is no lock file for the cache to key on.
- **Action versions**: major tags (`actions/checkout@v7`), except `setup-uv`, which has
  published no moving major tag since v8 and is pinned to a full version.

## Enabling GitHub Pages

Before the first deployment:

1. Go to your repository on GitHub.
2. Navigate to **Settings** > **Pages**.
3. Under **Source**, select **GitHub Actions**.

The workflow handles the rest on the next push to `main`.

## Favicon

Put an SVG in `web/assets/` and declare it in `main-html.typ`:

```typ
#let site = (title: "...", favicon: "assets/favicon.svg")
#site-assets(extra: ("assets/favicon.svg": read("web/assets/favicon.svg")))
```

A minimal one, with initials on a colored square:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="4" fill="#2196F3"/>
  <text x="16" y="22" text-anchor="middle"
        font-family="sans-serif" font-size="16" font-weight="bold"
        fill="white">FM</text>
</svg>
```

## Checking in CI

To fail the build when content is dropped, add a step before the build. It needs a
copy of [`tools/check.py`](https://github.com/balouf/typst-thesis-web/tree/main/tools/check.py)
in your repository (one file, standard library only):

```yaml
- name: Check the web edition
  run: |
    uv run tools/check.py main-html.typ --format bundle --input lang=fr
    uv run tools/check.py main-html.typ --format bundle --input lang=en
```

## Deployment Checklist

1. Copy `examples/thesis` into your repository; move `deploy.yml` to
   `.github/workflows/`.
2. Edit `main-html.typ`: site title, repository URL, one `chapter(...)` per page.
3. Edit `web/build.py` if your languages or the names of the PDF and EPUB differ.
4. Add your `favicon.svg`.
5. Enable GitHub Pages (source: GitHub Actions).
6. Push to `main`, check the Actions tab, then visit
   `https://username.github.io/your-repo-name/`.

The reference projects [phd-pagerank](https://github.com/balouf/phd-pagerank) and
[hdr-p2p](https://github.com/balouf/hdr-p2p) follow this structure.

## Publishing a single-page paper

`typst compile --features html web.typ paper.html` gives one file with everything
inside. Typical homes for it:

- next to the PDF, on your own page or a project site (a documentation site can copy
  it as a static file);
- GitHub Pages, as the only file of an artifact.

If the sources are private (a paper under review, margin notes), build the page on
your side and publish only the generated file.
