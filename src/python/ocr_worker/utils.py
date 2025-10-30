"""
Utility functions for OCR processing.
Pure functions for text processing, bbox calculations, and other low-level operations.
"""

import re
from typing import List


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
    text = re.sub(r'\s+', ' ', text)

    # Normalize common full-width punctuation to half-width
    text = text.replace('　', ' ')  # Full-width space to half-width
    text = text.replace('！', '!')  # Full-width exclamation
    text = text.replace('？', '?')  # Full-width question
    text = text.replace('…', '...')  # Full-width ellipsis

    # Remove non-printable characters except common punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\-\(\)\[\]\{\}\:;]', '', text, flags=re.UNICODE)

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


def normalize_bbox_coordinates(bbox: List[int], image_width: int, image_height: int) -> List[float]:
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
        bbox[3] / image_height
    ]


def merge_text_boxes(boxes: List[List[int]]) -> List[List[int]]:
    """
    Merge intersecting or adjacent bounding boxes.
    Boxes are in format [x1, y1, x2, y2].
    Merges boxes that overlap or touch.
    """
    if not boxes:
        return []

    boxes = [list(b) for b in boxes]  # copy to avoid modifying original

    while True:
        merged_any = False
        i = 0
        while i < len(boxes):
            j = i + 1
            while j < len(boxes):
                if _boxes_intersect(boxes[i], boxes[j]):
                    boxes[i] = _union_boxes(boxes[i], boxes[j])
                    del boxes[j]
                    merged_any = True
                else:
                    j += 1
            i += 1
        if not merged_any:
            break

    return boxes


def _boxes_intersect(b1: List[int], b2: List[int]) -> bool:
    """Check if two boxes intersect (including touching)."""
    return (b1[2] >= b2[0] and b1[0] <= b2[2] and
            b1[3] >= b2[1] and b1[1] <= b2[3])


def _union_boxes(b1: List[int], b2: List[int]) -> List[int]:
    """Return the union of two boxes."""
    return [min(b1[0], b2[0]), min(b1[1], b2[1]),
            max(b1[2], b2[2]), max(b1[3], b2[3])]
