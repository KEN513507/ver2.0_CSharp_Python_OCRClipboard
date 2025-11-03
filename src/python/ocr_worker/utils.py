"""
Utility functions for OCR processing.
Pure functions for text processing, bbox calculations, and other low-level operations.
"""

import re
from typing import List, Optional


def clean_text(text: str) -> str:
    """
    Clean and normalize OCR text.
    - Remove extra whitespace
    - Normalize full-width characters to half-width where appropriate
    - Remove common OCR artifacts
    """
    if not text:
        return ""

    # Remove leading/trailing whitespace
    text = text.strip()

    # Replace multiple spaces with single space
    text = re.sub(r"\s+", " ", text)

    # Normalize common full-width punctuation to half-width
    text = text.replace("　", " ")  # Full-width space to half-width
    text = text.replace("！", "!")  # Full-width exclamation
    text = text.replace("？", "?")  # Full-width question
    text = text.replace("…", "...")  # Full-width ellipsis

    # Remove non-printable characters except common punctuation
    text = re.sub(r"[^\w\s\.\,\!\?\-\(\)\[\]\{\}\:;]", "", text, flags=re.UNICODE)

    return text


def calculate_bbox_area(bbox: List[int]) -> int:
    """
    Calculate the area of a bounding box.
    Assumes format [x1, y1, x2, y2].
    """
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])


def is_bbox_valid(bbox: List[int]) -> bool:
    """
    Check if a bounding box is valid (x2 > x1 and y2 > y1).
    """
    return len(bbox) == 4 and bbox[2] > bbox[0] and bbox[3] > bbox[1]


def normalize_bbox_coordinates(
    bbox: List[int], image_width: int, image_height: int
) -> List[float]:
    """
    Normalize bbox coordinates to [0,1] range relative to image dimensions.
    """
    if not is_bbox_valid(bbox):
        return [0.0, 0.0, 0.0, 0.0]

    if image_width == 0 or image_height == 0:
        return [0.0, 0.0, 0.0, 0.0]

    return [
        bbox[0] / image_width,
        bbox[1] / image_height,
        bbox[2] / image_width,
        bbox[3] / image_height,
    ]


HORIZONTAL_GAP_TOLERANCE = 10  # pixels


def merge_text_boxes(
    boxes: List[List[int]],
    *,
    x_gap: Optional[int] = None,
    y_overlap_ratio: float = 0.5,
) -> List[List[int]]:
    """
    Merge intersecting or adjacent bounding boxes.

    Args:
        boxes: Bounding boxes in [x1, y1, x2, y2] format.
        x_gap: Maximum horizontal gap (pixels) tolerated between boxes. Defaults to constant.
        y_overlap_ratio: Minimum vertical overlap ratio required to merge boxes.
    """
    if not boxes:
        return []

    gap_limit = HORIZONTAL_GAP_TOLERANCE if x_gap is None else x_gap

    candidates = [list(b) for b in boxes if is_bbox_valid(b)]
    if not candidates:
        return []

    merged = True
    while merged:
        merged = False
        candidates.sort(key=lambda b: (b[1], b[0]))
        i = 0
        while i < len(candidates) - 1:
            box_a = candidates[i]
            j = i + 1
            while j < len(candidates):
                box_b = candidates[j]
                if _should_merge(
                    box_a, box_b, x_gap=gap_limit, y_overlap_ratio=y_overlap_ratio
                ):
                    new_box = _union_boxes(box_a, box_b)
                    candidates[i] = new_box
                    del candidates[j]
                    merged = True
                    box_a = new_box
                else:
                    j += 1
            i += 1

    candidates.sort(key=lambda b: (b[1], b[0]))
    return candidates


def _should_merge(
    b1: List[int], b2: List[int], *, x_gap: int, y_overlap_ratio: float
) -> bool:
    if _vertical_overlap_ratio(b1, b2) < y_overlap_ratio:
        return False
    if _horizontal_gap(b1, b2) >= x_gap:
        return False
    return True


def _vertical_overlap_ratio(b1: List[int], b2: List[int]) -> float:
    overlap = min(b1[3], b2[3]) - max(b1[1], b2[1])
    if overlap <= 0:
        return 0.0
    height_a = b1[3] - b1[1]
    height_b = b2[3] - b2[1]
    min_height = min(height_a, height_b)
    if min_height <= 0:
        return 0.0
    return overlap / min_height


def _horizontal_gap(b1: List[int], b2: List[int]) -> int:
    if b1[2] >= b2[0] and b2[2] >= b1[0]:
        return 0
    return min(abs(b2[0] - b1[2]), abs(b1[0] - b2[2]))


def _union_boxes(b1: List[int], b2: List[int]) -> List[int]:
    """Return the union of two boxes."""
    return [
        min(b1[0], b2[0]),
        min(b1[1], b2[1]),
        max(b1[2], b2[2]),
        max(b1[3], b2[3]),
    ]
