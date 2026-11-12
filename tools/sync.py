# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Copy the layer (lib/web.typ, web-content.css, web.css, web.js) to where it is vendored.

    uv run tools/sync.py                 # refresh the copies kept in examples/
    uv run tools/sync.py DEST [DEST...]  # vendor into other folders
    uv run tools/sync.py --check         # exit 1 if a copy in examples/ differs

web.js is only needed by multi-page sites: it is copied when the destination
already has one, or with --js. A copy whose web.typ header lists local patches
is left alone, unless --force is given.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "lib"
FILES = ["web.typ", "web-content.css", "web.css", "web.js"]


def copies_in_repo() -> list[Path]:
    """Folders under examples/ that hold a vendored web.typ."""
    return sorted(p.parent for p in (REPO / "examples").rglob("web.typ") if p.parent.name == "web")


def wanted(dest: Path, with_js: bool) -> list[str]:
    return [f for f in FILES if f != "web.js" or with_js or (dest / f).exists()]


def patched(dest: Path) -> bool:
    """Whether the header of a vendored web.typ lists local patches."""
    target = dest / "web.typ"
    if not target.exists():
        return False
    head = target.read_text(encoding="utf-8").splitlines()[:12]
    return not any("Local patches: none" in line for line in head)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("dest", nargs="*", type=Path, help="destination folders (default: the copies in examples/)")
    p.add_argument("--js", action="store_true", help="copy web.js too")
    p.add_argument("--check", action="store_true", help="compare instead of copying")
    p.add_argument("--force", action="store_true", help="overwrite a copy that lists local patches")
    args = p.parse_args()
    dests = args.dest or copies_in_repo()
    stale = 0
    for dest in dests:
        if not args.check and not args.force and patched(dest):
            stale += 1
            print(f"skipped: {dest} lists local patches in web.typ (--force overwrites them)")
            continue
        for name in wanted(dest, args.js):
            target = dest / name
            same = target.exists() and filecmp.cmp(LIB / name, target, shallow=False)
            if args.check:
                if not same:
                    stale += 1
                    print(f"out of date: {target}")
            elif not same:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(LIB / name, target)
                print(f"updated: {target}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
