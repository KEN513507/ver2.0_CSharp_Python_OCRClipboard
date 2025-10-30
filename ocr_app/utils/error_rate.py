from difflib import SequenceMatcher

def calc_error_rate(result, ground_truth):
    # result[0] を参照するように修正 (PaddleOCR predict のデータ構造)
    if not result or not result[0]:
        return 1.0  # Or handle as a full error
    pred = ''.join([line[1][0] for line in result[0]])
    sm = SequenceMatcher(None, pred, ground_truth)
    error = 1 - sm.ratio()
    return error
