# GitHub Deployment

This chapter covers publishing your thesis website to GitHub Pages with automated builds.

## Repository Structure

A typical repository layout:

```
your-thesis/
├── .github/workflows/deploy.yml
├── .gitignore
├── README.md
├── main.typ              # PDF entry point
├── main-html.typ         # HTML entry point
├── templates/            # Shared Typst templates
├── chapters/             # Chapter source files (.typ)
├── figures/              # Images and diagrams
├── web/
│   ├── build.py          # Build script
│   └── assets/
│       ├── style.css
│       ├── nav.js
│       └── favicon.svg
├── references.bib
└── springer-lncs-alphabetical.csl
```

## .gitignore

Essential entries to keep the repository clean:

```gitignore
# Build output
web/dist/

# PDFs (except figure PDFs)
*.pdf
!figures/**/*.pdf

# Typst cache
.typst-cache/

# Python
__pycache__/
.venv/

# OS
.DS_Store
Thumbs.db
```

## deploy.yml

The GitHub Actions workflow (provided in `boilerplate/deploy.yml`) automates the full
build-and-deploy cycle. Key points:

- **Triggers**: push to `main` and manual dispatch (`workflow_dispatch`).
- **Permissions**: needs `pages: write` and `id-token: write` for GitHub Pages deployment.
- **Steps**: checkout, install Typst (`typst-community/setup-typst@v4`), install uv
  (`astral-sh/setup-uv@v5`), run `build.py`, upload artifact, deploy to Pages.

Three settings deserve attention:

**`--base-url`** is critical. GitHub Pages serves your site at
`https://username.github.io/repo-name/`, so all asset paths (CSS, JS, Pagefind index)
must be prefixed with `/repo-name/`. The build command in the workflow should read:

```yaml
run: uv run web/build.py --base-url /your-repo-name/
```

If you forget this, the site will load with no styles and broken search.

**`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`** is set as an environment variable to
suppress Node.js deprecation warnings from older GitHub Actions.

**`enable-cache: false`** on `setup-uv` is necessary because `build.py` uses inline
script dependencies (the `# /// script` header) rather than a `uv.lock` file. With
caching enabled, uv would look for a lock file and fail.

## Enabling GitHub Pages

Before the first deployment:

1. Go to your repository on GitHub.
2. Navigate to **Settings** > **Pages**.
3. Under **Source**, select **GitHub Actions**.

That is all. The workflow will handle the rest on the next push to `main`.

## Favicon

Create a simple SVG favicon in `web/assets/`. The `<link rel="icon">` tag is generated
by `build_page()` in `build.py`, pointing to `../assets/favicon.svg`.

A minimal SVG with colored background and text initials works well:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="4" fill="#2196F3"/>
  <text x="16" y="22" text-anchor="middle"
        font-family="sans-serif" font-size="16" font-weight="bold"
        fill="white">FM</text>
</svg>
```

Replace the initials and color to match your identity.

## README.md

Include at minimum:

- A "Read online" link: `https://username.github.io/repo-name/`
- Build instructions for local development:
  ```bash
  uv run web/build.py --base-url /
  open web/dist/index.html
  ```
- PDF compilation instructions:
  ```bash
  typst compile --input lang=fr main.typ thesis-fr.pdf
  typst compile --input lang=en main.typ thesis-en.pdf
  ```
- License information (your thesis content license).

## Deployment Checklist

When setting up a new thesis repository:

1. Copy the boilerplate files into your project.
2. Edit `build.py`: set `CHAPTERS`, `PARTS`, `SUB_CHAPTERS`, `THESIS_TITLE`, and
   `GITHUB_URL`.
3. Edit `deploy.yml`: change `--base-url /your-repo-name/`.
4. Create your `favicon.svg`.
5. Push to `main` and verify the Actions tab shows a successful build.
6. Visit `https://username.github.io/your-repo-name/` to confirm the site is live.

The reference projects [phd-pagerank](https://github.com/balouf/phd-pagerank) and
[hdr-p2p](https://github.com/balouf/hdr-p2p) both follow this exact structure and can
serve as working examples.
