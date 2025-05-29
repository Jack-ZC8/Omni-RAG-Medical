import json
import os
import sqlite3
import time
import numpy as np
import os, sys
sys.path.append(os.path.abspath('./'))

import torch
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification


device = "cuda"
dense_model = AutoModel.from_pretrained("model/MedCPT-Query-Encoder")
dense_tokenizer = AutoTokenizer.from_pretrained("model/MedCPT-Query-Encoder")
rerank_tokenizer = AutoTokenizer.from_pretrained("model/MedCPT-Cross-Encoder")
rerank_model = AutoModelForSequenceClassification.from_pretrained("model/MedCPT-Cross-Encoder", device_map=device)


@torch.no_grad()
def get_reranked_scores(query, articles, batch_size=32):
    pairs = [[query, article] for article in articles]
    all_logits = []
    for i in range(0, len(pairs), batch_size):
        batch_pairs = pairs[i:i+batch_size]
        encoded = rerank_tokenizer(
            batch_pairs,
            truncation=True,
            padding=True,
            return_tensors="pt",
            max_length=512,
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}
        logits = rerank_model(**encoded).logits.squeeze(dim=1)
        all_logits.extend([i.item() for i in logits])
        del logits, encoded

    return all_logits

class UMLS_Search:
    def __init__(self):
        db_path = 'umls.sqlite3'
        self.memory_conn = sqlite3.connect(':memory:', check_same_thread=False)
        # load to memory
        file_conn = sqlite3.connect(db_path)
        file_conn.backup(self.memory_conn)
        file_conn.close()
        # set to only-read mode
        self.memory_conn.execute('PRAGMA query_only = ON')
        self.memory_conn.execute('PRAGMA synchronous = OFF')
        self.memory_conn.execute('PRAGMA journal_mode = OFF')
        self.memory_conn.execute('PRAGMA temp_store = MEMORY')
        
        self.cui_to_names = {}
        res = self.memory_conn.cursor().execute(f'SELECT * FROM MRCONSOEM').fetchall()
        for i in res:
            cui = i[0]
            name = i[2]
            if cui not in self.cui_to_names:
                self.cui_to_names[cui] = [set(), set()]
            if name.lower() not in self.cui_to_names[cui][1]:
                self.cui_to_names[cui][0].add(name)
                self.cui_to_names[cui][1].add(name.lower())
        self.cui_to_names = {k: sorted(list(v[0])) for k, v in self.cui_to_names.items()}
        

    def term_to_cui(self, term):
        # EXACT MATCH "COLLATE NOCASE" is set when creating the table!
        term = term.replace("\"", " ").strip()
        res = self.memory_conn.cursor().execute(f'SELECT * FROM MRCONSOEM WHERE STR="{term}" LIMIT 1').fetchone()
        if res is None:
            # FUZZY MATCH
            term = term.replace("'", " ").strip()
            res = self.memory_conn.cursor().execute(f'SELECT * FROM MRCONSO WHERE STR MATCH \'"{term}"\' ORDER BY rank LIMIT 1').fetchone()
        if res is not None:
            cui = res[0]
            return cui
        return None
    
    def cui_to_definition(self, cui):
        res = self.memory_conn.cursor().execute(f'SELECT * FROM MRDEF WHERE CUI="{cui}"').fetchall()
        if res is not None:
            msh_def = None
            nci_def = None
            icf_def = None
            csp_def = None
            hpo_def = None
            other_def = None
            for definition in res:
                source = definition[1]
                if source == "MSH":
                    msh_def = definition[2]
                    break
                elif source == "NCI":
                    nci_def = definition[2]
                elif source == "ICF":
                    icf_def = definition[2]
                elif source == "CSP":
                    csp_def = definition[2]
                elif source == "HPO":
                    hpo_def = definition[2]
                else:
                    other_def = definition[2]
            defi = msh_def or nci_def or icf_def or csp_def or hpo_def or other_def
            return defi
        return None
    
    def cui_to_relations(self, cui):
        res = self.memory_conn.cursor().execute(f'SELECT STR2,RELA,STR1 FROM MRREL WHERE CUI1="{cui}" OR CUI2="{cui}"').fetchall()
        if res is not None:
            res = list(set(res))        
        return res

umls_search = UMLS_Search()

def get_graph_docs(term, query, topk):
    tmp_t = time.time()
    cui = umls_search.term_to_cui(term)
    if cui is not None:
        # 1. search
        definition = umls_search.cui_to_definition(cui)
        rels=umls_search.cui_to_relations(cui)
        # 2. rerank
        rel_texts = [f"{rel[0]} {rel[1]} {rel[2]}" for rel in rels]
        scores = get_reranked_scores(
            query=query,
            articles=rel_texts
        )
        zipped_score_rel = list(zip(scores, rels))
        zipped_score_rel.sort(key=lambda x: x[0], reverse=True)
        rerank_rels = [i[1] for i in zipped_score_rel[:topk]]

        relation = "; ".join([f"({rel[0]}, {rel[1]}, {rel[2]})" for rel in rerank_rels])
        para_text = f"Definition: {definition}" if definition else ""
        para_text += f"\nRelation: {relation}." if relation else ""
        print("graph_search:", time.time() - tmp_t)
        if para_text:
            return [{"title": "/".join(umls_search.cui_to_names[cui]), "para": para_text, "dataset": "umls"}]
    return []


if __name__ == "__main__":
    print(get_graph_docs(term="1-Carboxyglutamic Acid", query="what is it?", topk=10))
