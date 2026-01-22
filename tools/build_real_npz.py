# tools/build_real_npz.py
from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping
import numpy as np

OUT_PATH = Path("src/core/data/munsell_real_lab.npz")


def _build_key(hvc_row: np.ndarray) -> str:
    """
    hvc_row: array di 3 stringhe, atteso: [Hue, Value, Chroma]
    """
    hue = str(hvc_row[0]).strip()
    v = str(hvc_row[1]).strip()
    c = str(hvc_row[2]).strip()

    # Neutri: "N V/0" -> spesso si preferisce "N V/"
    if hue.upper() == "N" and (c == "0" or c == "0.0"):
        return f"N {v}/"
    return f"{hue} {v}/{c}"


def main():
    import colour

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    root = colour.MUNSELL_COLOURS
    if not isinstance(root, Mapping):
        raise RuntimeError(f"colour.MUNSELL_COLOURS non è una Mapping (type={type(root)}).")

    real_obj = root["real"] if "real" in root else root["Munsell Colours Real"]
    if not isinstance(real_obj, (tuple, list)):
        raise RuntimeError(f"Dataset 'real' inatteso (type={type(real_obj)}).")

    keys = []
    xyY_list = []

    bad = 0
    for el in real_obj:
        # Ogni el dovrebbe diventare array (2,3) di stringhe
        arr = np.asarray(el)
        if arr.shape != (2, 3):
            bad += 1
            continue

        hvc = arr[0]
        xyY_s = arr[1]

        # Parse xyY
        try:
            xyY = np.array([float(xyY_s[0]), float(xyY_s[1]), float(xyY_s[2])], dtype=np.float64)
        except Exception:
            bad += 1
            continue

        if not np.isfinite(xyY).all():
            bad += 1
            continue

        key = _build_key(hvc)
        keys.append(key)
        xyY_list.append(xyY)

    if not keys:
        raise RuntimeError("Nessuna entry valida estratta dal dataset 'real' (formato (2,3) atteso).")

    xyY = np.vstack(xyY_list).astype(np.float64, copy=False)
    keys_np = np.array(keys, dtype=object)

    # Conversione xyY -> XYZ -> Lab
    XYZ = colour.xyY_to_XYZ(xyY)
    Lab = colour.XYZ_to_Lab(XYZ).astype(np.float32)

    np.savez_compressed(OUT_PATH, keys=keys_np, lab=Lab)
    print(f"Wrote {OUT_PATH} with {len(keys_np)} entries (skipped {bad})")


if __name__ == "__main__":
    main()
