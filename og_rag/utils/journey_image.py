"""
utils/journey_image.py
───────────────────────
Generates a clean "Tomorrow's Requirements" card image
for the Agrithm Crop Journey feature.

Dependencies: Pillow (pip install Pillow)
"""

from __future__ import annotations

import os
import textwrap
from typing import Optional

# ── PIL import with helpful error ───────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise ImportError(
        "Pillow is required for journey images.\n"
        "Install it with:  pip install Pillow"
    )

_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR  = os.path.join(_ROOT, "data", "journey_images")
os.makedirs(IMAGE_DIR, exist_ok=True)

# ── Font discovery (Windows + Linux fallbacks) ───────────────────────
_FONT_CANDIDATES = [
    # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    # Ubuntu / Debian
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    # macOS
    "/System/Library/Fonts/Helvetica.ttc",
]


def _load_font(size: int, bold: bool = False) -> "ImageFont.FreeTypeFont":
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── Colour palette ───────────────────────────────────────────────────
PALETTE = {
    "bg":          "#F0F7E8",   # light green background
    "header_bg":   "#2E7D32",   # deep green header
    "header_txt":  "#FFFFFF",
    "section_bg":  "#C8E6C9",   # mint section heading bg
    "section_txt": "#1B5E20",
    "body_txt":    "#212121",
    "fert_bg":     "#FFF9C4",   # yellow for fertilizer row
    "fert_txt":    "#F57F17",
    "footer_bg":   "#A5D6A7",
    "footer_txt":  "#1B5E20",
    "bullet_ok":   "#43A047",
    "bullet_warn": "#F57F17",
    "border":      "#388E3C",
}

# ── Card dimensions ──────────────────────────────────────────────────
W      = 720
PAD    = 28
RADIUS = 16  # corner radius (drawn manually via polygon approximation)


def _rounded_rect(draw: "ImageDraw.Draw", xy, radius: int, fill: str) -> None:
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.ellipse([x0, y0, x0 + 2 * radius, y0 + 2 * radius], fill=fill)
    draw.ellipse([x1 - 2 * radius, y0, x1, y0 + 2 * radius], fill=fill)
    draw.ellipse([x0, y1 - 2 * radius, x0 + 2 * radius, y1], fill=fill)
    draw.ellipse([x1 - 2 * radius, y1 - 2 * radius, x1, y1], fill=fill)


# ────────────────────────────────────────────────────────────────────
def generate_tomorrow_requirements_image(
    crop:        str,
    day:         int,
    stage_name:  str,
    tasks:       list[str],
    dos:         list[str]   = None,
    fertilizer:  Optional[dict] = None,
    total_days:  int         = 120,
    farmer_name: str         = "Farmer",
) -> str:
    """
    Generate a requirements card image and return the file path.

    Parameters
    ----------
    crop        : Crop name (e.g. 'rice')
    day         : Current day number
    stage_name  : Current growth stage name
    tasks       : List of today's key tasks (up to 4 shown)
    dos         : List of do's (up to 3 shown)
    fertilizer  : fertilizer dict from crop_journey.py  (may be None)
    total_days  : Total crop duration in days
    farmer_name : Farmer's name for personalisation
    """

    dos       = dos or []
    tasks     = tasks[:4]
    dos_shown = dos[:3]

    # ── Build content rows ───────────────────────────────────────────
    rows: list[tuple[str, str, str]] = []  # (bullet, text, style)

    # Tasks section
    rows.append(("", "TODAY'S TASKS", "section"))
    for i, t in enumerate(tasks, 1):
        rows.append((f"{i}.", textwrap.fill(t, width=62), "task"))

    # Fertilizer section (highlighted)
    if fertilizer and fertilizer.get("product"):
        rows.append(("", "FERTILIZER DUE TODAY", "section_fert"))
        rows.append(("💊", f"Product : {fertilizer['product']}", "fert"))
        rows.append(("   ", f"Dose    : {fertilizer.get('dose', '—')}", "fert"))
        rows.append(("   ", f"Method  : {fertilizer.get('method', '—')}", "fert"))
        rows.append(("   ", f"Est.Cost: {fertilizer.get('cost', '—')}", "fert"))
    else:
        rows.append(("", "FERTILIZER", "section"))
        rows.append(("✓", "No fertilizer application today.", "task"))

    # Do's section
    if dos_shown:
        rows.append(("", "DO THIS TODAY", "section"))
        for d in dos_shown:
            rows.append(("✅", textwrap.fill(d, width=60), "do"))

    # ── Measure total height needed ─────────────────────────────────
    LINE_H     = 28
    SECTION_H  = 36
    HEADER_H   = 88
    FOOTER_H   = 44
    PROGRESS_H = 32

    total_row_h = 0
    for bullet, text, style in rows:
        if style.startswith("section"):
            total_row_h += SECTION_H + 6
        else:
            n_lines = text.count("\n") + 1
            total_row_h += LINE_H * n_lines + 6

    H = HEADER_H + PROGRESS_H + PAD + total_row_h + PAD + FOOTER_H + 16

    # ── Create image ─────────────────────────────────────────────────
    img  = Image.new("RGB", (W, H), color=PALETTE["bg"])
    draw = ImageDraw.Draw(img)

    # Draw outer border
    draw.rectangle([0, 0, W - 1, H - 1], outline=PALETTE["border"], width=3)

    # ── Header ───────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, HEADER_H], fill=PALETTE["header_bg"])

    f_title  = _load_font(26, bold=True)
    f_sub    = _load_font(16)
    f_body   = _load_font(17)
    f_bold   = _load_font(17, bold=True)
    f_sect   = _load_font(14, bold=True)
    f_footer = _load_font(14)

    draw.text((PAD, 14), f"🌾  {crop.title()} Crop Journey — Day {day} of {total_days}",
              font=f_title, fill=PALETTE["header_txt"])
    draw.text((PAD, 52), f"Stage: {stage_name}   •   Good morning, {farmer_name}!",
              font=f_sub, fill="#C8E6C9")

    # ── Progress bar ─────────────────────────────────────────────────
    BAR_Y  = HEADER_H + 8
    BAR_H  = 16
    BAR_W  = W - 2 * PAD
    pct    = min(day / total_days, 1.0)
    filled = int(BAR_W * pct)

    draw.rectangle([PAD, BAR_Y, PAD + BAR_W, BAR_Y + BAR_H],
                   fill="#DCEDC8", outline=PALETTE["border"], width=1)
    if filled > 0:
        draw.rectangle([PAD, BAR_Y, PAD + filled, BAR_Y + BAR_H],
                       fill=PALETTE["header_bg"])
    pct_lbl = f"{int(pct * 100)}% complete"
    draw.text((PAD + BAR_W + 6, BAR_Y), pct_lbl, font=f_footer,
              fill=PALETTE["section_txt"])

    # ── Content rows ─────────────────────────────────────────────────
    y = HEADER_H + PROGRESS_H + PAD

    for bullet, text, style in rows:

        if style == "section":
            # Mint section header
            _rounded_rect(draw, [PAD, y, W - PAD, y + SECTION_H - 4], 6,
                          PALETTE["section_bg"])
            draw.text((PAD + 10, y + 7), text, font=f_sect,
                      fill=PALETTE["section_txt"])
            y += SECTION_H + 6
            continue

        if style == "section_fert":
            _rounded_rect(draw, [PAD, y, W - PAD, y + SECTION_H - 4], 6,
                          PALETTE["fert_bg"])
            draw.text((PAD + 10, y + 7), text, font=f_sect,
                      fill=PALETTE["fert_txt"])
            y += SECTION_H + 6
            continue

        # Regular row
        txt_x = PAD + 26
        if bullet:
            b_color = (
                PALETTE["fert_txt"]  if style == "fert" else
                PALETTE["bullet_ok"] if style == "do"   else
                PALETTE["body_txt"]
            )
            draw.text((PAD, y), bullet, font=f_bold, fill=b_color)

        txt_color = (
            PALETTE["fert_txt"] if style == "fert" else PALETTE["body_txt"]
        )
        font_choice = f_bold if style == "fert" and bullet.startswith("💊") else f_body

        for line in text.split("\n"):
            draw.text((txt_x, y), line, font=font_choice, fill=txt_color)
            y += LINE_H
        y += 6

    # ── Footer ────────────────────────────────────────────────────────
    draw.rectangle([0, H - FOOTER_H, W, H], fill=PALETTE["footer_bg"])
    draw.text((PAD, H - FOOTER_H + 14),
              "Agrithm — AI Farming Assistant  🌿  Reply 'crop status' anytime",
              font=f_footer, fill=PALETTE["footer_txt"])

    # ── Save ─────────────────────────────────────────────────────────
    filename = os.path.join(IMAGE_DIR, f"req_{crop}_{day}.png")
    img.save(filename, "PNG", optimize=True)
    return filename