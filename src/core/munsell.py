# src/core/munsell.py
from __future__ import annotations

import numpy as np
from pathlib import Path

from core.colorimetry import rgb8_to_lab, describe_pipeline

# Cache in memoria
_KEYS: np.ndarray | None = None
_LAB: np.ndarray | None = None


def _data_path() -> Path:
    """
    Percorso del dataset Munsell (Lab) incluso localmente.
    Per ora manteniamo la struttura esistente: core/data/munsell_real_lab.npz
    """
    return Path(__file__).resolve().parent / "data" / "munsell_real_lab.npz"


def _init() -> None:
    global _KEYS, _LAB
    if _KEYS is not None and _LAB is not None:
        return

    p = _data_path()
    if not p.exists():
        raise FileNotFoundError(
            f"Dataset Munsell Real non trovato: {p}\n"
            "Generalo con tools/build_munsell_real_npz.py\n"
            f"{describe_pipeline()}"
        )

    z = np.load(p, allow_pickle=True)
    _KEYS = z["keys"]

    # Il dataset deve essere Lab coerente con la pipeline definita in core.colorimetry
    # (sRGB -> XYZ(D65) -> Lab(D65/2°)).
    _LAB = z["lab"].astype(np.float32, copy=False)


def delta_e_cie76(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """
    ΔE*ab 1976 (euclideo in Lab).
    lab1: (3,)
    lab2: (N,3)
    return: (N,)
    """
    lab1 = np.asarray(lab1, dtype=np.float32).reshape(1, 3)
    lab2 = np.asarray(lab2, dtype=np.float32)
    d = lab2 - lab1
    return np.sqrt(np.sum(d * d, axis=1))


def closest_munsell_real(rgb: tuple[int, int, int], method: str = "DE2000") -> str:
    """
    Restituisce la label Munsell (dataset 'real') più vicina al colore campionato.

    Pipeline (v1, esplicita e centralizzata):
    - RGB input interpretato come sRGB
    - sRGB -> XYZ(D65) -> CIELAB (D65/2°)
    - nearest-neighbour in Lab minimizzando ΔE (CIE76 o CIEDE2000)

    Nota: la qualità dell'approssimazione dipende dalla fedeltà cromatica dell'immagine
    e dall'assenza di gestione ICC in questa versione.
    """
    _init()
    assert _KEYS is not None and _LAB is not None

    # Unica fonte di verità per RGB->Lab:
    lab = rgb8_to_lab(rgb).astype(np.float32, copy=False)

    m = (method or "").upper().strip()
    if m in ("CIE76", "DE76"):
        dE = delta_e_cie76(lab, _LAB)
    else:
        # ΔE2000: delega alla funzione dedicata già presente nel progetto
        from core.deltae2000 import delta_e_ciede2000
        dE = delta_e_ciede2000(lab, _LAB)

    i = int(np.argmin(dE))
    return str(_KEYS[i])


def closest_munsell_real_with_de(rgb: tuple[int, int, int], method: str = "DE2000") -> tuple[str, float]:
    """
    Variante utile per stabilizzazione/trasparenza scientifica:
    ritorna anche il ΔE minimo del match (valore numerico).
    """
    _init()
    assert _KEYS is not None and _LAB is not None

    lab = rgb8_to_lab(rgb).astype(np.float32, copy=False)

    m = (method or "").upper().strip()
    if m in ("CIE76", "DE76"):
        dE = delta_e_cie76(lab, _LAB)
    else:
        from core.deltae2000 import delta_e_ciede2000
        dE = delta_e_ciede2000(lab, _LAB)

    i = int(np.argmin(dE))
    return str(_KEYS[i]), float(dE[i])