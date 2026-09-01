"""
Region definitions for FORM 8014 (relative coordinates 0.0 – 1.0)

Chỉ áp dụng trên trang chứa "FORM 8014".
Tọa độ đã tinh chỉnh theo layout thực tế của form mẫu.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
from PIL import Image


@dataclass(frozen=True)
class Region:
    name: str
    box: Tuple[float, float, float, float]  # left, top, right, bottom
    description: str = ""


# Calibrated on sample form (~2560x1820 @ 220dpi)
FORM8014_REGIONS: Dict[str, Region] = {
    "form_code": Region(
        "form_code",
        (0.80, 0.005, 0.995, 0.065),
        "FORM 8014",
    ),
    "dispatch_line": Region(
        "dispatch_line",
        (0.08, 0.065, 0.92, 0.115),
        "Dispatch No + Issue Date",
    ),
    "header_info": Region(
        "header_info",
        (0.005, 0.11, 0.995, 0.22),
        "Title / Code / Duration / Location",
    ),
    "stats_row": Region(
        "stats_row",
        (0.005, 0.195, 0.995, 0.255),
        "Participants / Hours / Chapters",
    ),
    "employee_table": Region(
        "employee_table",
        (0.005, 0.25, 0.995, 0.70),
        "Employee result table",
    ),
    "signature_area": Region(
        "signature_area",
        (0.30, 0.68, 0.98, 0.95),
        "Prepared by + Checked by names",
    ),
}


def crop_region(image: Image.Image, region: Region, padding: float = 0.003) -> Image.Image:
    w, h = image.size
    left = max(0, int((region.box[0] - padding) * w))
    top = max(0, int((region.box[1] - padding) * h))
    right = min(w, int((region.box[2] + padding) * w))
    bottom = min(h, int((region.box[3] + padding) * h))
    return image.crop((left, top, right, bottom))


def crop_all_regions(image: Image.Image) -> Dict[str, Image.Image]:
    return {name: crop_region(image, reg) for name, reg in FORM8014_REGIONS.items()}
