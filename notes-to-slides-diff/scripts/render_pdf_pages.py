#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys


def parse_pages(pages_str):
    pages = set()
    for part in pages_str.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            start_s, end_s = part.split('-', 1)
            start = int(start_s)
            end = int(end_s)
            if end < start:
                raise ValueError(f"Invalid range: {part}")
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    return sorted(pages)


def main():
    parser = argparse.ArgumentParser(description="Render selected PDF pages to PNG images.")
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument("--pages", required=True, help="Comma-separated pages or ranges (e.g., 8,9,10-12)")
    parser.add_argument("--out-dir", required=True, help="Output directory for PNG files")
    parser.add_argument("--dpi", type=int, default=200, help="Render resolution in DPI")
    args = parser.parse_args()

    try:
        import fitz  # PyMuPDF
    except Exception as exc:
        print("PyMuPDF not available. Install with: ~/.venvs/jupyter/bin/python -m pip install pymupdf", file=sys.stderr)
        raise exc

    pdf_path = Path(args.pdf)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = parse_pages(args.pages)
    if not pages:
        print("No pages specified.", file=sys.stderr)
        sys.exit(1)

    zoom = args.dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    with fitz.open(pdf_path) as doc:
        for page_num in pages:
            page_index = page_num - 1
            if page_index < 0 or page_index >= len(doc):
                print(f"Page {page_num} out of range (1-{len(doc)}).", file=sys.stderr)
                continue
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            out_path = out_dir / f"page_{page_num}.png"
            pix.save(out_path)
            print(out_path)


if __name__ == "__main__":
    main()
