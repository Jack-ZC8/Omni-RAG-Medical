import json
import random
from tqdm import tqdm
import os, sys
sys.path.append(os.path.abspath("."))
from models.retriever import SEARCH_ACTION_DESC, SEARCH_ACTION_PARAM
from models.rewriter import adaptive_proposer_template
from utils.extract_option import extract_option

all_actions = ["book", "guideline", "research", "wiki", "graph"]
source_desc = "\n\n".join([f"{act}: {SEARCH_ACTION_DESC[act]}" for act in all_actions])
query_format = "\n\n".join([f"<{act}>{SEARCH_ACTION_PARAM[act]}</{act}>" for act in all_actions])

def process_file(path):
    content = json.load(open(path))
    file_res = []
    for item in tqdm(content):
        question = item["question"]
        prompt = adaptive_proposer_template.format(question=question, source_desc=source_desc, query_format=query_format)
        
        useful_source_to_queries = {}
        for unit in item["pred"]:
            if extract_option(unit["llmjudge"]) == "yes":
                if unit["source"] not in useful_source_to_queries:
                    useful_source_to_queries[unit["source"]] = []
                useful_source_to_queries[unit["source"]].append(unit["query"])
        if len(useful_source_to_queries) == 0:
            continue
        for src, queries in useful_source_to_queries.items():
            if len(queries) > 3:
                useful_source_to_queries[src] = random.sample(queries, 3)
        
        query_str_ls = []
        for src in all_actions:
            if src in useful_source_to_queries:
                tmp = f"<{src}>{' ; '.join(useful_source_to_queries[src])}</{src}>"
            else:
                tmp = f"<{src}></{src}>"
            query_str_ls.append(tmp)
        assistant = "\n\n".join(query_str_ls)
        file_res.append({"messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": assistant}
        ]})
    return file_res


sft_data = process_file("alog/system=planner_find,dataset=train_short,llm_name=Qwen2.5-72B,plan_name=,debug=True/output_all.json")
with open("sft.jsonl", "w") as f:
    for line in sft_data:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")