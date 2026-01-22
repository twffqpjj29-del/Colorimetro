# src/core/colorimetry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

import numpy as np

# ------------------------------------------------------------
# Pipeline colorimetrica (v1)
# Assunzione: i valori RGB campionati sono sRGB (IEC 61966-2-1).
# Conversione: sRGB (D65) -> XYZ (D65) -> CIELAB (D65/2°)
# ------------------------------------------------------------

@dataclass(frozen=True)
class ColorimetryConfig:
    rgb_encoding: str = "sRGB"
    illuminant: str = "D65"
    observer: str = "2°"
    lab_space: str = "CIELAB"
    xyz_space: str = "CIE 1931 XYZ"
    adaptation: str = "None (sRGB uses D65 as reference white)"


CFG = ColorimetryConfig()

# Whitepoint D65 (2°) in XYZ (normalized Y=1)
# Valori standard comunemente usati: [0.95047, 1.00000, 1.08883]
D65_XYZ = np.array([0.95047, 1.00000, 1.08883], dtype=np.float64)


def describe_pipeline() -> str:
    """
    Stringa breve e riproducibile, da stampare in PDF/GUI.
    """
    return (
        f"Pipeline: {CFG.rgb_encoding} -> XYZ({CFG.illuminant}) -> {CFG.lab_space}({CFG.illuminant}/{CFG.observer}). "
        f"Adaptation: {CFG.adaptation}."
    )


# ----------------- sRGB transfer functions -----------------

def _srgb_to_linear(u: np.ndarray) -> np.ndarray:
    """
    u: array float in [0,1]
    """
    u = np.asarray(u, dtype=np.float64)
    a = 0.055
    return np.where(u <= 0.04045, u / 12.92, ((u + a) / (1 + a)) ** 2.4)


def _linear_to_srgb(u: np.ndarray) -> np.ndarray:
    """
    u: array float in [0,1]
    """
    u = np.asarray(u, dtype=np.float64)
    a = 0.055
    return np.where(u <= 0.0031308, 12.92 * u, (1 + a) * (u ** (1 / 2.4)) - a)


# ----------------- Matrici sRGB <-> XYZ (D65) -----------------

# sRGB (linear) -> XYZ (D65), matrice standard
_M_RGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float64,
)

# XYZ (D65) -> sRGB (linear)
_M_XYZ_TO_RGB = np.linalg.inv(_M_RGB_TO_XYZ)


# ----------------- XYZ <-> Lab -----------------

def _f_lab(t: np.ndarray) -> np.ndarray:
    """
    Funzione f(t) per Lab, con delta = 6/29.
    """
    t = np.asarray(t, dtype=np.float64)
    delta = 6 / 29
    return np.where(t > delta**3, np.cbrt(t), (t / (3 * delta**2)) + (4 / 29))


def _finv_lab(t: np.ndarray) -> np.ndarray:
    t = np.asarray(t, dtype=np.float64)
    delta = 6 / 29
    return np.where(t > delta, t**3, 3 * delta**2 * (t - 4 / 29))


def xyz_to_lab(xyz: np.ndarray, white_xyz: np.ndarray = D65_XYZ) -> np.ndarray:
    """
    xyz: (...,3) float
    return: (...,3) float [L*, a*, b*]
    """
    xyz = np.asarray(xyz, dtype=np.float64)
    wp = np.asarray(white_xyz, dtype=np.float64)
    x, y, z = xyz[..., 0] / wp[0], xyz[..., 1] / wp[1], xyz[..., 2] / wp[2]

    fx, fy, fz = _f_lab(x), _f_lab(y), _f_lab(z)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return np.stack([L, a, b], axis=-1)


def lab_to_xyz(lab: np.ndarray, white_xyz: np.ndarray = D65_XYZ) -> np.ndarray:
    """
    lab: (...,3)
    return: (...,3) XYZ (Y normalizzato a 1 sul whitepoint)
    """
    lab = np.asarray(lab, dtype=np.float64)
    wp = np.asarray(white_xyz, dtype=np.float64)

    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16) / 116
    fx = fy + (a / 500)
    fz = fy - (b / 200)

    x = _finv_lab(fx) * wp[0]
    y = _finv_lab(fy) * wp[1]
    z = _finv_lab(fz) * wp[2]
    return np.stack([x, y, z], axis=-1)


# ----------------- API principale: RGB <-> Lab -----------------

def rgb8_to_lab(rgb: Iterable[int]) -> np.ndarray:
    """
    rgb: (R,G,B) in 0..255 (assunti sRGB)
    return: Lab (3,) float64
    """
    r, g, b = rgb
    rgb01 = np.array([r, g, b], dtype=np.float64) / 255.0
    rgb_lin = _srgb_to_linear(rgb01)
    xyz = _M_RGB_TO_XYZ @ rgb_lin
    lab = xyz_to_lab(xyz, D65_XYZ)
    return lab


def rgb8_array_to_lab(rgb: np.ndarray) -> np.ndarray:
    """
    rgb: (N,3) uint8/int in 0..255
    return: (N,3) float64
    """
    rgb = np.asarray(rgb, dtype=np.float64)
    rgb01 = rgb / 255.0
    rgb_lin = _srgb_to_linear(rgb01)
    xyz = rgb_lin @ _M_RGB_TO_XYZ.T
    lab = xyz_to_lab(xyz, D65_XYZ)
    return lab


def lab_to_rgb8(lab: np.ndarray) -> Tuple[int, int, int]:
    """
    Per completezza (non essenziale in v1).
    """
    xyz = lab_to_xyz(lab, D65_XYZ)
    rgb_lin = _M_XYZ_TO_RGB @ xyz
    rgb01 = _linear_to_srgb(rgb_lin)
    rgb01 = np.clip(rgb01, 0.0, 1.0)
    rgb8 = (rgb01 * 255.0).round().astype(np.int32)
    return int(rgb8[0]), int(rgb8[1]), int(rgb8[2])