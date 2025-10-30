from difflib import SequenceMatcher
from typing import Iterable, Sequence, Union


def _extract_texts_from_result(result: Union[dict, Sequence]) -> Iterable[str]:
    """Normalize PaddleOCR output (dict or legacy list) into an iterable of text strings."""
    if not result:
        return []

    if isinstance(result, dict):
        return result.get("rec_texts") or []

    first_entry = result[0] if len(result) > 0 else []

    if isinstance(first_entry, dict):
        return first_entry.get("rec_texts") or []

    texts = []
    for line in first_entry:
        if isinstance(line, (list, tuple)) and len(line) > 1:
            text_candidate = line[1][0] if isinstance(line[1], (list, tuple)) and line[1] else None
            if isinstance(text_candidate, str):
                texts.append(text_candidate)
    return texts


def calc_error_rate(result, ground_truth):
    texts = list(_extract_texts_from_result(result))
    predicted = "".join(texts)

    if not predicted and ground_truth:
        return 1.0

    sm = SequenceMatcher(None, predicted, ground_truth)
    return 1 - sm.ratio()
