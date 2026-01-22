# src/core/report_model.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Sample:
    idx: int
    x: int
    y: int
    spot: int
    mode: str
    de_method: str

    rgb: Tuple[int, int, int]
    rgb_std: Tuple[float, float, float]  # σR, σG, σB (0..255)

    hex: str
    munsell: str
    munsell_de: float  # ΔE minimo del match Munsell

    timestamp_iso: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class ReportState:
    image_path: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    notes: str = ""
    samples: List[Sample] = field(default_factory=list)

    def add_sample(
        self,
        x: int,
        y: int,
        spot: int,
        mode: str,
        de_method: str,
        rgb: Tuple[int, int, int],
        rgb_std: Tuple[float, float, float],
        hex_code: str,
        munsell: str,
        munsell_de: float,
    ) -> Sample:
        s = Sample(
            idx=len(self.samples) + 1,
            x=x,
            y=y,
            spot=spot,
            mode=mode,
            de_method=de_method,
            rgb=rgb,
            rgb_std=(float(rgb_std[0]), float(rgb_std[1]), float(rgb_std[2])),
            hex=hex_code,
            munsell=munsell,
            munsell_de=float(munsell_de),
        )
        self.samples.append(s)
        return s

    def remove_sample_by_idx(self, idx: int) -> None:
        self.samples = [s for s in self.samples if s.idx != idx]
        for i, s in enumerate(self.samples, start=1):
            self.samples[i - 1] = Sample(
                idx=i,
                x=s.x,
                y=s.y,
                spot=s.spot,
                mode=s.mode,
                de_method=s.de_method,
                rgb=s.rgb,
                rgb_std=s.rgb_std,
                hex=s.hex,
                munsell=s.munsell,
                munsell_de=s.munsell_de,
                timestamp_iso=s.timestamp_iso,
            )

    def clear_samples(self) -> None:
        self.samples.clear()