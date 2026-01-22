# src/core/sampling.py
from __future__ import annotations

from typing import Tuple

import numpy as np


def _clamp_int(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _roi_bounds(x: int, y: int, spot: int, w: int, h: int) -> Tuple[int, int, int, int]:
    """
    Ritorna bounds ROI inclusivi-esclusivi: [x0:x1), [y0:y1)
    Clamp ai bordi.
    """
    half = int(spot) // 2
    x0 = _clamp_int(x - half, 0, w - 1)
    y0 = _clamp_int(y - half, 0, h - 1)
    x1 = _clamp_int(x + half, 0, w - 1)
    y1 = _clamp_int(y + half, 0, h - 1)

    # Converti a slicing esclusivo: includi x1,y1
    return x0, y0, x1 + 1, y1 + 1


def _weights_gaussian(h: int, w: int, sigma: float) -> np.ndarray:
    """
    Kernel gaussiano 2D deterministico, normalizzato a somma 1.
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cy = (h - 1) / 2.0
    cx = (w - 1) / 2.0
    g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * sigma * sigma))
    s = g.sum()
    if s <= 0:
        return np.full((h, w), 1.0 / (h * w), dtype=np.float64)
    return (g / s).astype(np.float64)


def sample_rgb_and_std(
    image_rgb: np.ndarray,
    x: int,
    y: int,
    spot: int,
    mode: str,
) -> Tuple[Tuple[int, int, int], Tuple[float, float, float]]:
    """
    Campiona RGB con definizione deterministica e ritorna anche σRGB (dev. std per canale)
    calcolata sul ROI usato.

    image_rgb: array HxWx3, dtype uint8 (o compatibile)
    x,y: coordinate immagine (pixel)
    spot: lato ROI (px)
    mode: 'exact' | 'average' | 'weighted'

    Return:
    - rgb_mean: (R,G,B) int 0..255
    - rgb_std:  (σR,σG,σB) float (su ROI in RGB 0..255)
    """
    if image_rgb is None:
        raise ValueError("image_rgb is None")
    if image_rgb.ndim != 3 or image_rgb.shape[2] < 3:
        raise ValueError(f"image_rgb deve essere HxWx3, ricevuto shape={getattr(image_rgb, 'shape', None)}")

    h, w = int(image_rgb.shape[0]), int(image_rgb.shape[1])
    x = _clamp_int(int(x), 0, w - 1)
    y = _clamp_int(int(y), 0, h - 1)

    spot = int(spot)
    if spot <= 1 or (mode or "").lower().strip() == "exact":
        px = image_rgb[y, x, :3].astype(np.float64)
        rgb_mean = tuple(int(v) for v in np.clip(np.round(px), 0, 255))
        return rgb_mean, (0.0, 0.0, 0.0)

    x0, y0, x1, y1 = _roi_bounds(x, y, spot, w, h)
    roi = image_rgb[y0:y1, x0:x1, :3].astype(np.float64)  # float per stabilità

    # σRGB (sempre calcolata sul ROI non pesato: indicatore di omogeneità locale)
    # ddof=0 per determinismo e comparabilità
    std = roi.reshape(-1, 3).std(axis=0, ddof=0)
    rgb_std = (float(std[0]), float(std[1]), float(std[2]))

    mode_n = (mode or "").lower().strip()
    if mode_n == "average":
        m = roi.reshape(-1, 3).mean(axis=0)
        rgb_mean = tuple(int(v) for v in np.clip(np.round(m), 0, 255))
        return rgb_mean, rgb_std

    if mode_n == "weighted":
        rh, rw = roi.shape[0], roi.shape[1]

        # sigma deterministico: proporzionale alla dimensione ROI
        # (scelta stabile: ~1/3 del raggio)
        sigma = max(1e-6, 0.33 * (min(rh, rw) / 2.0))

        w2 = _weights_gaussian(rh, rw, sigma)  # somma 1
        # media pesata
        m = (roi * w2[..., None]).sum(axis=(0, 1))
        rgb_mean = tuple(int(v) for v in np.clip(np.round(m), 0, 255))
        return rgb_mean, rgb_std

    # fallback: average
    m = roi.reshape(-1, 3).mean(axis=0)
    rgb_mean = tuple(int(v) for v in np.clip(np.round(m), 0, 255))
    return rgb_mean, rgb_std


def sample_rgb(image_rgb: np.ndarray, x: int, y: int, spot: int, mode: str) -> Tuple[int, int, int]:
    """
    Backward-compatible: ritorna solo RGB.
    """
    rgb, _std = sample_rgb_and_std(image_rgb, x, y, spot, mode)
    return rgb