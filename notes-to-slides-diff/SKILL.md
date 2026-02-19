---
name: notes-to-slides-diff
description: Update LaTeX/Beamer lecture slides from updated PDF notes with detailed algebra steps, diff outlines, and figure replacement using screenshots from notes. Use for syncing slide sections to new notes, expanding derivations, replacing figures with crops from PDFs, and refreshing equations/assumptions in slides.
---

# Notes to Slides Diff

## Overview
Update slide content to match updated notes, extract figures from PDFs, and replace slide graphics without regenerating a new virtual environment.

## Preconditions
- Always use `~/.venvs/jupyter/bin/python` for PDF/image tooling.
- Never create a new venv for this workflow.
- Prefer `rg` for searching LaTeX sources.

## Inputs to confirm
- Slide `.tex` file path and target sections.
- Notes source path(s): prefer notes `.tex` when available; otherwise notes PDF path(s).
- Figure filenames to replace and their target destinations.
- Whether the task is content-only or also includes figure replacement.

## Workflow
1. Locate the target section in the slide file with `rg` and surrounding context.
2. Extract structure from the notes (headings, equations, key definitions).
3. If notes are `.tex`, run a section-by-section coverage audit (headings, frame titles, equation anchors) instead of a raw whole-file text diff.
4. Produce a diff-outline against the current slides and confirm changes.
5. Update slide frames: align notation, assumptions, ordering, and expand algebra step-by-step.
6. Replace figures using PDF screenshots (only when needed):
   - Render PDF pages to images.
   - Crop the figure regions.
   - Save into the slide `figures/` directory using the existing filenames.
7. Run a consistency pass on notation, equations, and figure references.

## Coverage-audit mode (`notes.tex` -> `slides.tex`)
- Ignore Pandoc/export boilerplate (preamble, class/package blocks, metadata) before comparing content.
- Compare chunk-by-chunk by topic/subsection (e.g., deterministic, stochastic, infinite horizon), not with one global text diff.
- For each derivation block, verify this chain is complete:
  1. setup/problem and constraints
  2. Lagrangian
  3. FOCs
  4. elimination/substitution steps
  5. market-clearing/equilibrium closure
  6. economic intuition sentence
- Add missing intermediate algebra when slides jump from FOCs to the final result.
- Keep existing notation and slide style unless notes explicitly change notation.

## Detail policy for derivations
- Prefer more steps over fewer: show intermediate algebra, substitutions, and rearrangements.
- Split long derivations into multiple frames (e.g., Problem -> Lagrangian -> FOCs -> Combine -> Result).
- When notes include a specific sequence (e.g., log-utility substitution or market clearing algebra), mirror it.
- Add a short numeric example when the notes provide one and it clarifies the mechanism.
- Use `\pause` only when the slide already relies on incremental reveals.

## LaTeX safety
- For multi-line equations use `align*` or `equation*` + `aligned`.
- Use `\\` only inside `align`/`aligned`; avoid trailing `\\`.
- If a long line is needed, prefer `aligned` instead of manual line breaks.

## Scripts
### Render PDF pages
Use `scripts/render_pdf_pages.py` to render specific pages to PNG.

Example:
```bash
~/.venvs/jupyter/bin/python scripts/render_pdf_pages.py \
  --pdf "path/to/notes.pdf" \
  --pages 8,9,10,11 \
  --out-dir /tmp/notes_pages \
  --dpi 200
```

### Crop figures
Use `scripts/crop_pdf_figs.py` with a JSON map of figure crops.

Example:
```bash
~/.venvs/jupyter/bin/python scripts/crop_pdf_figs.py \
  --images-dir /tmp/notes_pages \
  --map references/figure_map_template.json \
  --out-dir "Topic 1/figures"
```

## Figure map format
See `references/figure_map_template.json`. Define a list of figures with:
- `name`: output filename
- `page`: page number in the PDF (1-indexed)
- `bbox`: crop box as `[x0, y0, x1, y1]` in pixels on the rendered page
- `pad`: optional padding in pixels

## Quality checks
- Verify crops with `view_image` before replacing the slide assets.
- Ensure `\includegraphics` paths still resolve.
- Inspect modified slide ranges with `nl -ba <slide.tex> | sed -n '<start>,<end>p'`.
- Confirm `git diff -- <slide.tex>` only touches intended frames.
- Compile slides only if requested.
