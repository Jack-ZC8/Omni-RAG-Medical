import argparse
import copy
from glob import glob
import json
from pprint import pprint
import re
import sys, os
sys.path.append(os.path.abspath("./"))
from os.path import join as pjoin
import uuid

from filelock import SoftFileLock
from tqdm import tqdm
from utils.mizhi import Errorer, Printer

from models.llm_utils import VLLMChatLLM
from models.reader import Reader
from models.term_extractor import Term_Extractor
from models.judger import Judger
from models.retriever import Retriever
from models.rewriter import Rewriter

def extract_answer(pred):
    pattern = r'(<answer>.*?</answer>)'
    match = re.search(pattern, pred, re.DOTALL)
    if match is not None:
        pred = match.group(1)
    pred = pred.strip()
    return pred

class RAG:
    def __init__(self, args):
        self.args = args
        self.llm = VLLMChatLLM(args.llm_name)

        if args.system.startswith("planner"):
            self.rewriter = Rewriter(self.llm, self.args)
            self.retriever = Retriever(topk=10)
            self.judger = Judger(self.llm, self.args)
        elif self.args.system == "reader":
            self.reader = Reader(self.llm, self.args)
            if self.args.plan_name != "":
                self.plan_data = json.load(open(f"alog/{self.args.plan_name}/output_all.json"))
        elif args.system in ("planner_origin", ):
            self.term_extractor = Term_Extractor(self.llm, args)
        else:
            raise NotImplementedError

    def run(self, question, gold, is_long, idx):
        all_actions = ["book", "guideline", "research", "wiki", "graph"]

        if self.args.system == "planner_origin":
            source_and_queries = []
            for act in all_actions:
                if act == "graph":
                    term_ls = self.term_extractor.run(question)
                    for term in term_ls:
                        source_and_queries.append([act, [f"{term} , {question}"]])
                else:
                    source_and_queries.append([act, [question]])
            retrieval_result = []
            for i in source_and_queries:
                retrieval_result.extend(self.retriever.run([i]))
            documents = "\n".join(i["docs"] for i in retrieval_result)
            doc_path = pjoin("alog", exp_name, "docs", f"{uuid.uuid4()}.txt")
            with open(doc_path, "w") as f:
                f.write(documents)
            pred = {"source_and_queries": source_and_queries, "doc_path": doc_path}
        
        elif self.args.system in ("planner_prompt",):
            source_and_queries = self.rewriter.run(question, actions=all_actions)
            retrieval_result = self.retriever.run(source_and_queries)
            documents = "\n".join(i["docs"] for i in retrieval_result)
            doc_path = pjoin("alog", exp_name, "docs", f"{uuid.uuid4()}.txt")
            with open(doc_path, "w") as f:
                f.write(documents)
            pred = {"source_and_queries": source_and_queries, "doc_path": doc_path}

        elif self.args.system == "planner_find":
            question_ls = []
            documents_ls = []
            gold_ls = []
            source_and_queries = self.rewriter.run(question, actions=all_actions)
            retrieval_result = self.retriever.run(source_and_queries)
            for ret in retrieval_result:
                question_ls.append(question)
                documents_ls.append(ret["docs"])
                gold_ls.append(gold)
            llmjudge_ls = self.judger.run(
                question_ls=question_ls,
                documents_ls=documents_ls,
                gold_ls=gold_ls
            )
            pred = [{"source": i['source'], "query": i['query']} for i in retrieval_result]
            for i in range(len(retrieval_result)):
                pred[i]["llmjudge"] = extract_answer(llmjudge_ls[i][0])
                doc_path = pjoin("alog", exp_name, "docs", f"{uuid.uuid4()}.txt")
                with open(doc_path, "w") as f:
                    f.write(documents_ls[i])
                    pred[i]["doc_path"] = doc_path

        elif self.args.system == "reader":
            if self.args.plan_name == "":
                documents = None
            else:
                documents = open(self.plan_data[idx]["pred"]["doc_path"]).read()
            llm_output = self.reader.run(question, documents, is_long)
            pred = {"llm_output": llm_output}
        else:
            raise NotImplementedError
        return pred


def change_arg_to_str(args):
    s = ""
    for k in list(args.__dict__.keys()):
        if k == "subset" and args.__dict__[k] < 0:
            continue
        str_v = str(args.__dict__[k]).replace('-Instruct', '').replace('Meta-', '').replace('-INT4', '').replace('-AWQ', '').replace("-Distill", "")
        s += f"{k}={str_v},"
    s = s[:-1]
    return s


def get_args(sys_argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", type=str, required=True)
    parser.add_argument("--dataset", type=str, required=True)
    parser.add_argument("--llm_name", type=str, required=True)
    parser.add_argument("--plan_name", type=str, default="")

    parser.add_argument("--debug", action="store_true")
    
    args = parser.parse_args(sys_argv)
    return args


def work_item(item, idx):
    question = item["question"]
    gold = item["gold"]
    is_long = item["long"]
    pred = rag_system.run(question, gold, is_long, idx)
    return pred


if __name__ == "__main__":
    args = get_args()
    exp_name = change_arg_to_str(args)
    if args.debug:
        os.popen(f"rm -r {pjoin('alog', exp_name)}").read()
    os.makedirs(pjoin("alog", exp_name, "docs"), exist_ok=True)
    if len(glob(pjoin("alog", exp_name, "*.log"))) < 3:
        log_path = pjoin("alog", exp_name, f"{uuid.uuid4()}.log")
        sys.stdout = Printer(log_path)
        sys.stderr = Errorer(log_path)

    rag_system = RAG(args)
    ################ work ################
    output_all_path = pjoin("alog", exp_name, "output_all.json")
    lock_path = output_all_path + ".lock"
    with SoftFileLock(lock_path):
        if os.path.exists(output_all_path):
            output_all = json.load(open(output_all_path, encoding="utf-8"))
        else:
            output_all = json.load(open(f"data/data_processed/{args.dataset}.json", encoding="utf-8"))
            with open(output_all_path, "w") as output_fp:
                json.dump(output_all, output_fp, indent=2, ensure_ascii=False)

    assert len(output_all) > 0

    BATCH_SIZE = 10 if args.debug else 15
    while True:
        with SoftFileLock(lock_path):
            output_all = json.load(open(output_all_path, encoding="utf-8"))
            jobs = [example_index for example_index, example in enumerate(output_all) if "pred" not in example][:BATCH_SIZE]
            if len(jobs) == 0:
                jobs = [example_index for example_index, example in enumerate(output_all) if example["pred"] is None][:BATCH_SIZE]
            if len(jobs) == 0:
                print("All jobs are done ~")
                break
            for example_index in jobs:
                output_all[example_index]["pred"] = None
            with open(output_all_path, "w") as output_fp:
                json.dump(output_all, output_fp, indent=2, ensure_ascii=False)

        jobs_output = []
        for example_index in tqdm(jobs):
            pred = work_item(output_all[example_index], example_index)
            jobs_output.append([example_index, pred])
        rag_system.llm.if_print = False

        with SoftFileLock(lock_path):
            output_all = json.load(open(output_all_path, encoding="utf-8"))
            for example_index, pred in jobs_output:
                output_all[example_index]["pred"] = pred
            with open(output_all_path, "w") as output_fp:
                json.dump(output_all, output_fp, indent=2, ensure_ascii=False)

        if args.debug:
            break
