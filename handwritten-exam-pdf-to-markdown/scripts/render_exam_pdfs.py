#!/usr/bin/env python3
"""Render handwritten exam PDFs to page images and write a manifest."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def render_with_pdfium(pdf_path: Path, out_dir: Path, scale: float) -> int:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    for index, page in enumerate(pdf, start=1):
        out_path = out_dir / f"page-{index:02d}.png"
        if out_path.exists():
            continue
        bitmap = page.render(scale=scale, rotation=0)
        image = bitmap.to_pil()
        image.save(out_path)
    return len(pdf)


def render_with_fitz(pdf_path: Path, out_dir: Path, scale: float) -> int:
    import fitz

    doc = fitz.open(pdf_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix = fitz.Matrix(scale, scale)
    for index, page in enumerate(doc, start=1):
        out_path = out_dir / f"page-{index:02d}.png"
        if out_path.exists():
            continue
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pix.save(out_path)
    return doc.page_count


def render_pdf(pdf_path: Path, out_dir: Path, scale: float) -> int:
    try:
        return render_with_pdfium(pdf_path, out_dir, scale)
    except ImportError:
        return render_with_fitz(pdf_path, out_dir, scale)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render exam PDFs into page images and write ocr-work/manifest.csv."
    )
    parser.add_argument("pdf_folder", type=Path, help="Folder containing student PDFs.")
    parser.add_argument(
        "--exclude",
        action="append",
        default=["elenco studenti.pdf"],
        help="PDF basename to exclude. May be passed multiple times.",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=3.0,
        help="Rendering scale. 3.0 is a good default for handwriting.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing page images.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = args.pdf_folder.expanduser().resolve()
    pages_root = base / "ocr-work" / "pages"
    markdown_dir = base / "markdown"
    manifest_path = base / "ocr-work" / "manifest.csv"
    exclude = {name.lower() for name in args.exclude}

    if not base.is_dir():
        raise SystemExit(f"Not a directory: {base}")

    markdown_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str | int]] = []
    for pdf_path in sorted(base.glob("*.pdf")):
        if pdf_path.name.lower() in exclude:
            continue

        out_dir = pages_root / pdf_path.stem
        if args.force and out_dir.exists():
            for existing in out_dir.glob("page-*.png"):
                existing.unlink()

        page_count = render_pdf(pdf_path, out_dir, args.scale)
        page_images = [out_dir / f"page-{index:02d}.png" for index in range(1, page_count + 1)]
        rows.append(
            {
                "student": pdf_path.stem,
                "pdf": str(pdf_path),
                "pages": page_count,
                "page_images": ";".join(str(path) for path in page_images),
                "markdown": str(markdown_dir / f"{pdf_path.stem}.md"),
                "status": "rendered",
            }
        )

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["student", "pdf", "pages", "page_images", "markdown", "status"],
        )
        writer.writeheader()
        writer.writerows(rows)

    total_pages = sum(int(row["pages"]) for row in rows)
    print(f"wrote {manifest_path}")
    print(f"rendered/confirmed {total_pages} pages across {len(rows)} PDFs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
