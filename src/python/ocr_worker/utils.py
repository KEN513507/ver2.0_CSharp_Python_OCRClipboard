"""
Utility functions for OCR processing.
Pure functions for text processing, bbox calculations, and other low-level operations.
"""

import re
from typing import List


def merge_text_boxes(boxes: List[List[int]]) -> List[List[int]]:
    """
    Merge overlapping or adjacent text bounding boxes.
    Assumes boxes are in format [x1, y1, x2, y2].
    Merges boxes that overlap or are within 5 pixels of each other.
    """
    if not boxes:
        return []

    # Sort boxes by x1 coordinate
    sorted_boxes = sorted(boxes, key=lambda b: b[0])

    merged = [sorted_boxes[0]]

    for box in sorted_boxes[1:]:
        last = merged[-1]

        # Check if boxes overlap or are adjacent (within 5 pixels)
        if box[0] <= last[2] + 5 and box[2] >= last[0] - 5:
            # Merge: take min x1, min y1, max x2, max y2
            merged[-1] = [
                min(last[0], box[0]),
                min(last[1], box[1]),
                max(last[2], box[2]),
                max(last[3], box[3])
            ]
        else:
            merged.append(box)

    return merged


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

    return [
        bbox[0] / image_width,
        bbox[1] / image_height,
        bbox[2] / image_width,
        bbox[3] / image_height
    ]
