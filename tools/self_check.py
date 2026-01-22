# tools/self_check.py
from __future__ import annotations

import sys
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image

# aggiungi src al path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from core.colorimetry import describe_pipeline
from core.deltae2000 import delta_e_ciede2000
from core.report_model import ReportState
from core.export_pdf import export_pdf

# opzionale: munsell
try:
    from core.munsell import closest_munsell_real_with_de
    HAVE_MUNSELL = True
except Exception:
    HAVE_MUNSELL = False


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    raise SystemExit(1)


def main() -> None:
    # 1) pipeline
    p = describe_pipeline()
    if not isinstance(p, str) or len(p.strip()) < 10:
        _fail("describe_pipeline() non valido.")
    _ok(f"Pipeline: {p}")

    # 2) ΔE2000 shape/finite
    lab1 = np.array([50.0, 2.0, -10.0], dtype=np.float32)
    lab2 = np.array(
        [[50.0, 2.0, -10.0],
         [60.0, 10.0, -5.0],
         [20.0, -5.0, 30.0]],
        dtype=np.float32
    )
    d = delta_e_ciede2000(lab1, lab2)
    if not isinstance(d, np.ndarray) or d.shape != (3,):
        _fail(f"ΔE2000 shape errata: {getattr(d, 'shape', None)}")
    if not np.all(np.isfinite(d)):
        _fail("ΔE2000 contiene NaN/Inf.")
    _ok(f"ΔE2000 ok (shape {d.shape})")

    # 3) Munsell (se disponibile)
    if HAVE_MUNSELL:
        try:
            m, de = closest_munsell_real_with_de((128, 128, 128), method="DE2000")
            if not isinstance(m, str) or not np.isfinite(de):
                _fail("Munsell match non valido.")
            _ok(f"Munsell match ok: {m} (ΔE={de:.2f})")
        except Exception as e:
            _fail(f"Munsell check fallito: {e}")
    else:
        _warn("Modulo Munsell non disponibile/import fallito: skip.")

    # 4) Export PDF di prova
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        img_path = td / "test_image.png"
        pdf_path = td / "test_report.pdf"

        # immagine sintetica deterministica
        arr = np.zeros((240, 320, 3), dtype=np.uint8)
        arr[:, :, 0] = np.linspace(0, 255, 320, dtype=np.uint8)[None, :]
        arr[:, :, 1] = np.linspace(255, 0, 240, dtype=np.uint8)[:, None]
        arr[:, :, 2] = 64
        Image.fromarray(arr, mode="RGB").save(img_path)

        state = ReportState(image_path=str(img_path), notes="Self-check report.")
        # campione fittizio minimo: se il tuo model richiede campioni, aggiungine uno reale via GUI.
        # Qui verifichiamo che export funzioni anche con 0 campioni? In questa versione l'export richiede campioni.
        # Perciò creiamo un campione minimale coerente col modello attuale.
        from core.munsell import closest_munsell_real_with_de as _cm
        from core.color import rgb_to_hex

        rgb = (120, 130, 140)
        munsell, mde = _cm(rgb, method="DE2000")
        state.add_sample(
            x=100, y=80,
            spot=31,
            mode="average",
            de_method="DE2000",
            rgb=rgb,
            rgb_std=(0.0, 0.0, 0.0),
            hex_code=rgb_to_hex(*rgb),
            munsell=munsell,
            munsell_de=mde,
        )

        export_pdf(str(pdf_path), state, title="Colorimetro Self-Check")
        if not pdf_path.exists() or pdf_path.stat().st_size < 10_000:
            _fail("PDF non generato correttamente o troppo piccolo.")
        _ok(f"Export PDF ok: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")

    _ok("Self-check completato.")


if __name__ == "__main__":
    main()