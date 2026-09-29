#!/usr/bin/env python3
"""Build the print-ready wraparound cover for Simply Automation.

    pip install Pillow numpy segno
    python3 book/cover/build_cover.py --pages 152            # KDP, white paper
    python3 book/cover/build_cover.py --pages 152 --paper cream
    python3 book/cover/build_cover.py --spine 0.42           # spine width from the printer's template
    python3 book/cover/build_cover.py --no-qr                # leave the barcode box clear for an ISBN

The artwork master (art-master-4x.jpg) is the original wraparound illustration,
upscaled 4x with Real-ESRGAN (x4plus). The back and front panels are cropped from it
at the exact trim + bleed; the spine is rebuilt at the width the page count requires,
using the artwork's own gold glow and freshly set type.

Outputs go to book/cover/print/:
  cover-print-<trim>-<spine>in.pdf   upload file for the printer (300 dpi, RGB)
  cover-print-<trim>-<spine>in.png   the same, lossless
  cover-front-6x9.jpg                front cover alone at trim size, for ebooks and stores

The barcode box on the back cover holds a QR code to the free web edition. For a retail
edition, pass --no-qr: KDP and IngramSpark print the ISBN barcode in that box.
"""

import argparse
from pathlib import Path

import numpy as np
import segno
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MASTER = HERE / "art-master-4x.jpg"
FONTS = HERE / "fonts"
OUT = HERE / "print"

DPI = 300
TRIM_W, TRIM_H = 6.0, 9.0
BLEED = 0.125
SPINE_MARGIN = 0.0625          # KDP: keep spine text this far from each fold
PAGE_THICKNESS = {"white": 0.002252, "cream": 0.0025, "color": 0.002347}  # KDP, inches per page

# Where things sit in the 4x master (6144 x 4096 px, 1x coordinates * 4).
BACK_X = (200, 2900)           # back panel, outer edge to the spine glow
SPINE_X = (2900, 3304)         # the glowing spine band in the artwork
FRONT_X = (3304, 6144)         # front panel, spine glow to outer edge
CLEAN_ROWS = [(0, 400), (3900, 4096)]   # spine rows with no lettering on them
BARCODE_BOX = (1742, 3186, 2478, 3612)  # clear area inside the back-cover label (x0, y0, x1, y1)
SITE_URL = "https://lana-20.github.io/simply-automation/"

INK = (28, 26, 23)
RUST = (156, 59, 39)


def font(name, size, weight):
    f = ImageFont.truetype(str(FONTS / name), size)
    f.set_variation_by_axes([weight])
    return f


def panel(master, x0, x1, width_px, height_px, anchor):
    """Crop a panel to the target aspect ratio, trimming from the outer edge only."""
    src_h = master.height
    need_w = round(width_px * src_h / height_px)
    if anchor == "right":            # back panel: keep the spine side, trim the outer (left) edge
        box = (x1 - need_w, 0, x1, src_h)
    else:                            # front panel: keep the spine side, trim the outer (right) edge
        box = (x0, 0, x0 + need_w, src_h)
    if box[0] < 0 or box[2] > master.width:
        raise SystemExit("Artwork is too narrow for this trim size.")
    return master.crop(box).resize((width_px, height_px), Image.LANCZOS)


def spine(master, width_px, height_px, spine_in):
    """Rebuild the spine band at the required width from the artwork's glow profile."""
    arr = np.asarray(master).astype(np.float32)
    band = arr[:, SPINE_X[0]:SPINE_X[1]]
    rows = np.concatenate([band[a:b] for a, b in CLEAN_ROWS])
    profile = np.median(rows, axis=0)                          # (w, 3)
    xs = np.linspace(0, profile.shape[0] - 1, width_px)
    resampled = np.stack([np.interp(xs, np.arange(profile.shape[0]), profile[:, c]) for c in range(3)], axis=1)
    # Gentle vertical grain so the band matches the paper texture around it.
    rng = np.random.default_rng(11)
    grain = rng.normal(0, 2.2, (height_px, width_px, 1)).astype(np.float32)
    img = np.clip(resampled[None, :, :] + grain, 0, 255).astype(np.uint8)
    spine_img = Image.fromarray(img, "RGB")

    usable = spine_in - 2 * SPINE_MARGIN
    if usable < 0.12:
        return spine_img             # too thin for lettering (KDP: under ~80 pages)

    # Set the type horizontally, then rotate so it reads top to bottom (US convention).
    cap = min(0.5 * spine_in, usable * 0.82) * DPI
    title_f = font("Oswald.ttf", round(cap / 0.72), 600)
    author_f = font("Jost.ttf", round(cap * 0.62 / 0.70), 500)
    length = height_px
    strip = Image.new("RGBA", (length, width_px), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    mid = width_px / 2
    top = round((BLEED + 0.55) * DPI)
    bottom = length - round((BLEED + 0.55) * DPI)
    d.text((top, mid), "SIMPLY AUTOMATION", font=title_f, fill=INK, anchor="lm")
    title_end = top + d.textlength("SIMPLY AUTOMATION", font=title_f)
    author = "SERENE DIPSTER"
    spacing = cap * 0.28
    widths = [d.textlength(ch, font=author_f) for ch in author]
    author_len = sum(widths) + spacing * (len(author) - 1)
    x = bottom - author_len
    for ch, w in zip(author, widths):
        d.text((x, mid), ch, font=author_f, fill=RUST, anchor="lm")
        x += w + spacing
    # The cover's hairline-and-dot divider between title and author.
    gap_l, gap_r = title_end + cap, bottom - author_len - cap
    if gap_r - gap_l > cap * 3:
        cx = (gap_l + gap_r) / 2
        r = max(2, cap * 0.09)
        line = max(1, round(cap * 0.035))
        d.line([(cx - cap * 1.6, mid), (cx - r * 1.8, mid)], fill=INK, width=line)
        d.line([(cx + r * 1.8, mid), (cx + cap * 1.6, mid)], fill=INK, width=line)
        d.ellipse([cx - r, mid - r, cx + r, mid + r], outline=INK, width=line)
    spine_img.paste(strip.rotate(-90, expand=True), (0, 0), strip.rotate(-90, expand=True))
    return spine_img


def draw_qr(cover, back_x0, scale, url):
    """Place a QR code and a short caption in the back-cover label box."""
    x0, y0, x1, y1 = [round(v) for v in ((BARCODE_BOX[0] - back_x0) * scale, BARCODE_BOX[1] * scale,
                                          (BARCODE_BOX[2] - back_x0) * scale, BARCODE_BOX[3] * scale)]
    qr = segno.make(url, error="q")
    modules = qr.symbol_size(border=0)[0]
    pad = round(0.07 * DPI)
    module = max(1, (y1 - y0 - 2 * pad) // modules)
    size = module * modules
    qr_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(qr_img)
    for r, row in enumerate(qr.matrix):
        for c, dark in enumerate(row):
            if dark:
                d.rectangle([c * module, r * module, (c + 1) * module - 1, (r + 1) * module - 1], fill=INK)
    qx, qy = x0 + pad, y0 + (y1 - y0 - size) // 2
    cover.paste(qr_img, (qx, qy), qr_img)

    d = ImageDraw.Draw(cover)
    tx = qx + size + round(0.07 * DPI)
    caps = font("Jost.ttf", round(0.06 * DPI), 500)
    small = font("Jost.ttf", round(0.052 * DPI), 400)
    y = qy + round(0.02 * DPI)
    for line in ("SCAN TO READ", "FREE ONLINE"):
        x = tx
        for ch in line:
            d.text((x, y), ch, font=caps, fill=INK, anchor="lt")
            x += d.textlength(ch, font=caps) + round(0.008 * DPI)
        y += round(0.088 * DPI)
    y += round(0.05 * DPI)
    for line in ("Feedback and", "contributions", "welcome."):
        d.text((tx, y), line, font=small, fill=INK, anchor="lt")
        y += round(0.072 * DPI)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int, default=152, help="interior page count (default: 152, an estimate)")
    ap.add_argument("--paper", choices=PAGE_THICKNESS, default="white")
    ap.add_argument("--spine", type=float, help="spine width in inches; overrides --pages/--paper")
    ap.add_argument("--qr", default=SITE_URL, help="URL for the back-cover QR code")
    ap.add_argument("--no-qr", action="store_true", help="leave the barcode box clear for an ISBN barcode")
    args = ap.parse_args()

    spine_in = args.spine if args.spine else args.pages * PAGE_THICKNESS[args.paper]
    master = Image.open(MASTER).convert("RGB")

    panel_w = round((TRIM_W + BLEED) * DPI)
    full_h = round((TRIM_H + 2 * BLEED) * DPI)
    spine_w = round(spine_in * DPI)
    full_w = 2 * panel_w + spine_w

    back = panel(master, *BACK_X, panel_w, full_h, anchor="right")
    front = panel(master, *FRONT_X, panel_w, full_h, anchor="left")
    spine_img = spine(master, spine_w, full_h, spine_in)

    cover = Image.new("RGB", (full_w, full_h))
    cover.paste(back, (0, 0))
    cover.paste(spine_img, (panel_w, 0))
    cover.paste(front, (panel_w + spine_w, 0))
    if not args.no_qr:
        need_w = round(panel_w * master.height / full_h)
        draw_qr(cover, BACK_X[1] - need_w, full_h / master.height, args.qr)

    OUT.mkdir(exist_ok=True)
    stem = f"cover-print-6x9-{spine_in:.3f}in"
    cover.save(OUT / f"{stem}.png", dpi=(DPI, DPI), optimize=True)
    cover.save(OUT / f"{stem}.pdf", "PDF", resolution=DPI, quality=95)
    # Front cover alone, trimmed (no bleed), for ebook stores and the website.
    trim = front.crop((0, round(BLEED * DPI), round(TRIM_W * DPI), full_h - round(BLEED * DPI)))
    trim.save(OUT / "cover-front-6x9.jpg", quality=94, dpi=(DPI, DPI))
    # Screen preview of the whole wrap, for the README and the website.
    cover.resize((1536, round(1536 * full_h / full_w)), Image.LANCZOS).save(OUT / "cover-wrap-preview.jpg", quality=85)

    print(f"Spine {spine_in:.3f} in ({spine_w} px) · cover {full_w / DPI:.3f} × {full_h / DPI:.3f} in "
          f"({full_w} × {full_h} px at {DPI} dpi)")
    print(f"Wrote {OUT.relative_to(HERE.parent.parent)}/{stem}.pdf, .png and cover-front-6x9.jpg")


if __name__ == "__main__":
    main()
