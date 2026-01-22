# src/core/deltae2000.py
from __future__ import annotations
import numpy as np


def delta_e_ciede2000(lab1, lab2):
    """
    Calcola Delta E CIEDE2000 tra:
    - lab1: array-like (3,)
    - lab2: array-like (N, 3)
    Ritorna array (N,).
    """
    lab1 = np.asarray(lab1, dtype=np.float32).reshape(1, 3)
    lab2 = np.asarray(lab2, dtype=np.float32)

    L1, a1, b1 = lab1[:, 0], lab1[:, 1], lab1[:, 2]
    L2, a2, b2 = lab2[:, 0], lab2[:, 1], lab2[:, 2]

    kL = kC = kH = 1.0

    C1 = np.sqrt(a1 * a1 + b1 * b1)
    C2 = np.sqrt(a2 * a2 + b2 * b2)
    Cbar = 0.5 * (C1 + C2)

    G = 0.5 * (1.0 - np.sqrt((Cbar**7) / (Cbar**7 + 25**7)))

    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2

    C1p = np.sqrt(a1p * a1p + b1 * b1)
    C2p = np.sqrt(a2p * a2p + b2 * b2)

    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    dLp = L2 - L1
    dCp = C2p - C1p

    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, dhp)
    dhp = np.where(dhp < -180, dhp + 360, dhp)

    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp) / 2)

    Lbar = 0.5 * (L1 + L2)
    Cbarp = 0.5 * (C1p + C2p)

    hbarp = np.where(
        np.abs(h1p - h2p) <= 180,
        0.5 * (h1p + h2p),
        np.where(
            h1p + h2p < 360,
            0.5 * (h1p + h2p + 360),
            0.5 * (h1p + h2p - 360),
        ),
    )

    T = (
        1
        - 0.17 * np.cos(np.radians(hbarp - 30))
        + 0.24 * np.cos(np.radians(2 * hbarp))
        + 0.32 * np.cos(np.radians(3 * hbarp + 6))
        - 0.20 * np.cos(np.radians(4 * hbarp - 63))
    )

    SL = 1 + (0.015 * (Lbar - 50) ** 2) / np.sqrt(20 + (Lbar - 50) ** 2)
    SC = 1 + 0.045 * Cbarp
    SH = 1 + 0.015 * Cbarp * T

    RT = -2 * np.sqrt((Cbarp**7) / (Cbarp**7 + 25**7)) * np.sin(
        np.radians(60 * np.exp(-((hbarp - 275) / 25) ** 2))
    )

    dE = np.sqrt(
        (dLp / (kL * SL)) ** 2
        + (dCp / (kC * SC)) ** 2
        + (dHp / (kH * SH)) ** 2
        + RT * (dCp / (kC * SC)) * (dHp / (kH * SH))
    )

    return dE.astype(np.float32)