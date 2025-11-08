import os
import sys
sys.path.append(os.path.abspath("./"))
import json
from os.path import join as pjoin

import numpy as np
from utils.extract_option import extract_option

test_names = ["medqa", "medmcqa", "mmlu", "pubmedqa", "bioasq", "seer", "ddxplus"]

def qa_score(dir_path):
    correct_dict = {i: 0 for i in test_names}
    sum_dict = {i: 0 for i in test_names}

    output_all = json.load(open(pjoin(dir_path, "output_all.json")))
    unfinished_count = sum(["pred" not in i or i["pred"] is None or len(i["pred"]) == 0 for i in output_all])
    if unfinished_count:
        print(f"[Unfinished: {unfinished_count}, Finished: {100 - 100 * unfinished_count / len(output_all):.2f}%]")

    for i in output_all:
        if "pred" not in i or i["pred"] is None or len(i["pred"]) == 0:
            continue
        sum_dict[i["name"]] += 1
        pred = i["pred"]["llm_output"]
        pred = extract_option(pred)
        # right / wrong ?
        if pred == i["gold"]:
            correct_dict[i["name"]] += 1
    
    for i in correct_dict:
        if sum_dict[i] == 0:
            correct_dict[i] = "0"
        else:
            correct_dict[i] = f"{100*correct_dict[i] / sum_dict[i]:.2f}"
    print("\t".join([correct_dict[i] for i in test_names]))



if __name__ == "__main__":
    for dir_path in sys.argv[1:]:
        print(dir_path)
        qa_score(dir_path)

