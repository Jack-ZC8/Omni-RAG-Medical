import re


def extract_option(pred):
    pred = pred.strip()
    # 1. get A/B/C/D
    for pattern in [
        r'<answer>(.*?)</answer>',
        r'^([A-Za-z])[.,:]',
        r'Answer:\s*([A-Za-z])\s*',
    ]:
        match = re.search(pattern, pred, re.DOTALL)
        if match is not None:
            pred = match.group(1)

    # 2. remove <>
    pred = pred.replace("<", "").replace(">", "")
    pred = pred.strip()
    return pred

def extract_long(pred):
    # 1. get A/B/C/D
    for pattern in [
        r'<answer>(.*?)</answer>',
    ]:
        match = re.search(pattern, pred, re.DOTALL)
        if match is not None:
            pred = match.group(1)

    # 2. remove <>
    pred = pred.replace("<", "").replace(">", "")
    pred = pred.strip()
    return pred