def calc_error_rate(result, ground_truth):
    from difflib import SequenceMatcher
    pred = ''.join([line[1][0] for line in result[0]])
    sm = SequenceMatcher(None, pred, ground_truth)
    error = 1 - sm.ratio()
    print(f"誤字率: {error:.2%}")
