#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys


def clamp(value, low, high):
    return max(low, min(high, value))


def main():
    parser = argparse.ArgumentParser(description="Crop figures from rendered PDF page images.")
    parser.add_argument("--images-dir", required=True, help="Directory with page_#.png files")
    parser.add_argument("--map", required=True, help="JSON map with figure crops")
    parser.add_argument("--out-dir", required=True, help="Output directory for cropped figures")
    parser.add_argument("--default-pad", type=int, default=0, help="Default padding in pixels")
    args = parser.parse_args()

    try:
        from PIL import Image
    except Exception as exc:
        print("Pillow not available. Install with: ~/.venvs/jupyter/bin/python -m pip install pillow", file=sys.stderr)
        raise exc

    images_dir = Path(args.images_dir)
    map_path = Path(args.map)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(map_path.read_text(encoding="utf-8"))
    figures = data.get("figures", [])
    if not figures:
        print("No figures found in map.", file=sys.stderr)
        sys.exit(1)

    for fig in figures:
        name = fig.get("name")
        page = fig.get("page")
        bbox = fig.get("bbox")
        pad = fig.get("pad", args.default_pad)
        if not name or not page or not bbox or len(bbox) != 4:
            print(f"Skipping invalid entry: {fig}", file=sys.stderr)
            continue

        img_path = images_dir / f"page_{page}.png"
        if not img_path.exists():
            print(f"Missing page image: {img_path}", file=sys.stderr)
            continue

        img = Image.open(img_path).convert("RGB")
        x0, y0, x1, y1 = bbox
        x0 = clamp(int(x0) - pad, 0, img.size[0])
        y0 = clamp(int(y0) - pad, 0, img.size[1])
        x1 = clamp(int(x1) + pad, 0, img.size[0])
        y1 = clamp(int(y1) + pad, 0, img.size[1])

        if x1 <= x0 or y1 <= y0:
            print(f"Invalid crop box for {name}: {bbox}", file=sys.stderr)
            continue

        crop = img.crop((x0, y0, x1, y1))
        out_path = out_dir / name
        crop.save(out_path)
        print(out_path)


if __name__ == "__main__":
    main()
