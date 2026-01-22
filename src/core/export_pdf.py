# src/core/export_pdf.py
from __future__ import annotations

from datetime import datetime
from typing import Tuple

import math
from PIL import Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from core.report_model import ReportState
from core.version import APP_NAME, APP_VERSION, APP_COPYRIGHT
from core.colorimetry import describe_pipeline


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _isfinite(x: float) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def _hex_to_rgb01(hex_code: str) -> Tuple[float, float, float]:
    h = (hex_code or "").strip().lstrip("#")
    if len(h) != 6:
        return 0.0, 0.0, 0.0
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return r, g, b


def _fit_to_width(c: canvas.Canvas, text: str, max_w: float, font_name: str, font_size: float) -> str:
    text = (text or "").strip()
    if c.stringWidth(text, font_name, font_size) <= max_w:
        return text
    ell = "…"
    if c.stringWidth(ell, font_name, font_size) > max_w:
        return ""
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        cand = text[:mid].rstrip() + ell
        if c.stringWidth(cand, font_name, font_size) <= max_w:
            lo = mid + 1
        else:
            hi = mid
    return text[: max(0, lo - 1)].rstrip() + ell


def _compute_center_crop(iw: int, ih: int, target_aspect: float) -> Tuple[int, int, int, int]:
    img_aspect = iw / ih if ih else 1.0
    if abs(img_aspect - target_aspect) < 1e-6:
        return 0, 0, iw, ih
    if img_aspect > target_aspect:
        new_w = int(round(ih * target_aspect))
        left = (iw - new_w) // 2
        return left, 0, left + new_w, ih
    new_h = int(round(iw / target_aspect))
    top = (ih - new_h) // 2
    return 0, top, iw, top + new_h


def export_pdf(path_out: str, state: ReportState, title: str = "Colour Sampling Report") -> None:
    if not state.image_path:
        raise ValueError("Nessuna immagine caricata nel ReportState.")

    page_w, page_h = landscape(A4)
    c = canvas.Canvas(path_out, pagesize=(page_w, page_h))

    margin = 10 * mm
    gutter = 6 * mm
    header_h = 14 * mm
    footer_h = 28 * mm

    total_w = page_w - 2 * margin
    content_h = page_h - 2 * margin - header_h - footer_h

    # Layout: immagine più piccola a sinistra, tabella ampia a destra
    left_w = total_w * 0.34
    right_w = total_w - left_w - gutter

    left_x = margin
    right_x = margin + left_w + gutter

    header_top_y = page_h - margin
    content_top_y = header_top_y - header_h
    content_bottom_y = margin + footer_h

    # ---------------- Header ----------------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, header_top_y, title)

    gen_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.setFont("Helvetica", 9)
    c.drawRightString(page_w - margin, header_top_y, f"{APP_NAME} v{APP_VERSION}  |  Generated: {gen_date}")

    # ---------------- LEFT: image box + info box ----------------
    img_box_h = content_h * 0.52
    img_box_w = left_w
    img_box_x = left_x
    img_box_y = content_top_y - img_box_h

    info_box_x = left_x
    info_box_y = content_bottom_y
    info_box_w = left_w
    info_box_h = (img_box_y - gutter) - info_box_y

    c.setLineWidth(0.8)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(img_box_x, img_box_y, img_box_w, img_box_h)
    c.rect(info_box_x, info_box_y, info_box_w, info_box_h)

    # Carica immagine e cover-fit nel box
    pil = Image.open(state.image_path).convert("RGB")
    iw, ih = pil.size
    state.image_width = iw
    state.image_height = ih

    target_aspect = img_box_w / img_box_h if img_box_h else 1.0
    crop_l, crop_t, crop_r, crop_b = _compute_center_crop(iw, ih, target_aspect)
    crop_w = crop_r - crop_l
    crop_h = crop_b - crop_t

    pil_cropped = pil.crop((crop_l, crop_t, crop_r, crop_b))
    c.drawImage(ImageReader(pil_cropped), img_box_x, img_box_y, width=img_box_w, height=img_box_h, mask=None)

    # mapping immagine -> pdf (tenendo conto del crop)
    def map_xy(x_img: int, y_img: int):
        xc = x_img - crop_l
        yc = y_img - crop_t
        if xc < 0 or yc < 0 or xc >= crop_w or yc >= crop_h:
            return None
        denom_w = (crop_w - 1) if crop_w > 1 else 1
        denom_h = (crop_h - 1) if crop_h > 1 else 1
        px = img_box_x + (xc / denom_w) * img_box_w
        py = img_box_y + ((crop_h - 1 - yc) / denom_h) * img_box_h
        return px, py

    # overlay campioni
    c.setLineWidth(1.0)
    for s in state.samples:
        mapped = map_xy(s.x, s.y)
        if mapped is None:
            continue
        px, py = mapped

        cross = 5 * mm
        c.setStrokeColorRGB(1, 1, 1)
        c.line(px - cross / 2, py, px + cross / 2, py)
        c.line(px, py - cross / 2, px, py + cross / 2)

        half = int(s.spot) // 2
        x0 = _clamp(s.x - half, 0, iw - 1)
        y0 = _clamp(s.y - half, 0, ih - 1)
        x1 = _clamp(s.x + half, 0, iw - 1)
        y1 = _clamp(s.y + half, 0, ih - 1)

        x0c = _clamp(x0 - crop_l, 0, max(0, crop_w - 1))
        x1c = _clamp(x1 - crop_l, 0, max(0, crop_w - 1))
        y0c = _clamp(y0 - crop_t, 0, max(0, crop_h - 1))
        y1c = _clamp(y1 - crop_t, 0, max(0, crop_h - 1))

        def map_crop(xc: int, yc: int):
            denom_w = (crop_w - 1) if crop_w > 1 else 1
            denom_h = (crop_h - 1) if crop_h > 1 else 1
            px2 = img_box_x + (xc / denom_w) * img_box_w
            py2 = img_box_y + ((crop_h - 1 - yc) / denom_h) * img_box_h
            return px2, py2

        rx0, ry0 = map_crop(x0c, y0c)
        rx1, ry1 = map_crop(x1c, y1c)

        rect_x = min(rx0, rx1)
        rect_y = min(ry0, ry1)
        rect_w = abs(rx1 - rx0)
        rect_h = abs(ry1 - ry0)

        c.setStrokeColorRGB(1, 0.2, 0.2)
        c.rect(rect_x, rect_y, rect_w, rect_h)

        c.setFont("Helvetica-Bold", 8)
        c.setFillColorRGB(1, 0.2, 0.2)
        c.drawString(px + 1.5, py + 1.5, str(s.idx))
        c.setFillColorRGB(0, 0, 0)

    # ---------------- LEFT: info box content ----------------
    pad = 6
    y = info_box_y + info_box_h - pad

    c.setFont("Helvetica-Bold", 11)
    c.drawString(info_box_x + pad, y - 4, "Info")
    y -= 18

    c.setFont("Helvetica", 9)
    img_name = (state.image_path or "").split("/")[-1]
    c.drawString(info_box_x + pad, y, f"Image: {_fit_to_width(c, img_name, info_box_w - 2*pad, 'Helvetica', 9)}")
    y -= 12
    c.drawString(info_box_x + pad, y, f"Size: {iw} × {ih} px")
    y -= 12
    c.drawString(info_box_x + pad, y, f"Samples: {len(state.samples)}")
    y -= 14

    # Pipeline scientifica (tracciabilità)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(info_box_x + pad, y, "Colorimetry")
    y -= 12
    c.setFont("Helvetica", 8.5)

    pipeline = describe_pipeline()
    max_w = info_box_w - 2 * pad

    # wrap semplice su 2 righe max (box piccolo)
    if c.stringWidth(pipeline, "Helvetica", 8.5) <= max_w:
        c.drawString(info_box_x + pad, y, pipeline)
        y -= 14
    else:
        cut = max(40, int(len(pipeline) * 0.60))
        line1 = pipeline[:cut].rstrip() + "…"
        line2 = pipeline[cut:].lstrip()
        c.drawString(info_box_x + pad, y, _fit_to_width(c, line1, max_w, "Helvetica", 8.5))
        y -= 11
        c.drawString(info_box_x + pad, y, _fit_to_width(c, line2, max_w, "Helvetica", 8.5))
        y -= 13

    # Ultimo campione (se presente)
    if state.samples:
        s = state.samples[-1]
        c.setFont("Helvetica-Bold", 9)
        c.drawString(info_box_x + pad, y, "Last sample")
        y -= 12
        c.setFont("Helvetica", 9)
        c.drawString(info_box_x + pad, y, f"#{s.idx}  X,Y: {s.x},{s.y}  Spot: {s.spot}  Mode: {s.mode}")
        y -= 12

        r, g, b = _hex_to_rgb01(s.hex)
        c.setFillColorRGB(r, g, b)
        c.rect(info_box_x + pad, y - 9, 10, 10, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.setLineWidth(0.3)
        c.rect(info_box_x + pad, y - 9, 10, 10, fill=0, stroke=1)

        c.drawString(info_box_x + pad + 14, y, f"RGB: {s.rgb[0]},{s.rgb[1]},{s.rgb[2]}")
        y -= 12
        c.drawString(info_box_x + pad + 14, y, f"HEX: {s.hex}   Munsell: {s.munsell}")
        y -= 12

        match_de = "-" if not _isfinite(s.munsell_de) else f"{s.munsell_de:.2f}"
        c.drawString(info_box_x + pad + 14, y, f"Match ΔE: {match_de}   ΔE method: {s.de_method}")
    else:
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(info_box_x + pad, y, "No samples yet.")

    # ---------------- RIGHT: table ----------------
    table_x = right_x
    table_y_top = content_top_y
    table_h = content_h
    table_y_bottom = content_bottom_y

    c.setLineWidth(0.8)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(table_x, table_y_bottom, right_w, table_h)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(table_x + 6, table_y_top - 16, "Samples")

    inner_w = right_w - 12

    # colonne: swatch, idx, xy, spot, mode, de_method, hex, munsell, match_de
    col_sw = 12
    col_idx = 16
    col_xy = 70
    col_spot = 34
    col_mode = 48
    col_de = 54
    col_hex = 58
    col_match = 54

    fixed = col_sw + col_idx + col_xy + col_spot + col_mode + col_de + col_hex + col_match
    col_munsell = max(90, inner_w - fixed)

    x0 = table_x + 6
    x_sw = x0
    x_idx = x_sw + col_sw
    x_xy = x_idx + col_idx
    x_spot = x_xy + col_xy
    x_mode = x_spot + col_spot
    x_de = x_mode + col_mode
    x_hex = x_de + col_de
    x_mun = x_hex + col_hex
    x_match = x_mun + col_munsell

    header_y = table_y_top - 30
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_idx, header_y, "#")
    c.drawString(x_xy, header_y, "X,Y")
    c.drawString(x_spot, header_y, "Spot")
    c.drawString(x_mode, header_y, "Mode")
    c.drawString(x_de, header_y, "ΔE")
    c.drawString(x_hex, header_y, "HEX")
    c.drawString(x_mun, header_y, "Munsell")
    c.drawString(x_match, header_y, "Match ΔE")

    line_y = header_y - 6
    c.setLineWidth(0.4)
    c.line(x0, line_y, x0 + inner_w, line_y)

    font = "Helvetica"
    fs = 8.0
    row_h = 11
    row_y = line_y - 11
    max_rows = int((table_h - 48) // row_h)
    shown = state.samples[:max_rows]

    for i, s in enumerate(shown):
        if i % 2 == 1:
            c.setFillColorRGB(0.96, 0.96, 0.96)
            c.rect(x0, row_y - 8, inner_w, row_h, fill=1, stroke=0)
            c.setFillColorRGB(0, 0, 0)

        r, g, b = _hex_to_rgb01(s.hex)
        c.setFillColorRGB(r, g, b)
        c.rect(x_sw + 1, row_y - 7, 9, 9, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.setLineWidth(0.3)
        c.rect(x_sw + 1, row_y - 7, 9, 9, fill=0, stroke=1)

        c.setFont(font, fs)
        c.drawString(x_idx, row_y, str(s.idx))
        c.drawString(x_xy, row_y, f"{s.x},{s.y}")
        c.drawString(x_spot, row_y, str(s.spot))
        c.drawString(x_mode, row_y, _fit_to_width(c, s.mode, col_mode - 2, font, fs))
        c.drawString(x_de, row_y, _fit_to_width(c, s.de_method, col_de - 2, font, fs))
        c.drawString(x_hex, row_y, _fit_to_width(c, s.hex, col_hex - 2, font, fs))
        c.drawString(x_mun, row_y, _fit_to_width(c, s.munsell, col_munsell - 2, font, fs))

        match_de = "-" if not _isfinite(s.munsell_de) else f"{s.munsell_de:.2f}"
        c.drawString(x_match, row_y, _fit_to_width(c, match_de, col_match - 2, font, fs))

        row_y -= row_h

    if len(state.samples) > len(shown):
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(x0, row_y, f"... {len(state.samples) - len(shown)} more")

    # ---------------- Footer: notes + copyright ----------------
    footer_x = margin
    footer_y = margin
    footer_w = page_w - 2 * margin

    c.setLineWidth(0.8)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(footer_x, footer_y, footer_w, footer_h)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(footer_x + 6, footer_y + footer_h - 14, "Notes")

    notes = (state.notes or "").strip() or "-"
    c.setFont("Helvetica", 9)

    text = c.beginText(footer_x + 6, footer_y + footer_h - 28)
    text.setLeading(11)

    max_chars = 190
    for line in notes.splitlines():
        line = line.strip()
        if not line:
            text.textLine("")
            continue
        while len(line) > max_chars:
            text.textLine(line[:max_chars])
            line = line[max_chars:]
        text.textLine(line)

    c.drawText(text)

    c.setFont("Helvetica", 8)
    c.drawRightString(page_w - margin, footer_y + 5, APP_COPYRIGHT)

    c.showPage()
    c.save()