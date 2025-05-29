import re
from models.retriever import SEARCH_ACTION_DESC, SEARCH_ACTION_PARAM

forced_proposer_template = """To answer the question labeled as # Question, please construct appropriate queries to get the information you need.

1. Each source in # Source Description must have search queries constructed.
2. Please give the search queries following the format in # Query Format. Each source should have {n_queries} queries, separated by `;`. Please ensure the diversity of queries from the same source.
3. The queries for the source should accurately reflect the specific information needs from that source.

# Question
{question}

# Source Description
{source_desc}

# Query Format
{query_format}"""


adaptive_proposer_template = """To answer the question labeled as # Question, please construct appropriate queries to get the information you need.

1. Please give the search queries following the format in # Query Format. The source can have up to 3 queries, separated by `;`. Please ensure the diversity of queries from the same source. For each source, if you think no information retrieval is needed, simply output an empty tag for that source, for example: <book></book>.
2. The queries for the source should accurately reflect the specific information needs from that source.

# Question
{question}

# Source Description
{source_desc}

# Query Format
{query_format}"""



class Rewriter():
    def __init__(self, llm, args):
        self.llm = llm
        self.args = args
        
        if self.args.system == "planner_find":
            self.n_queries = 6
        else:
            self.n_queries = 3

    def run(self, question, actions, feedback=None):
        source_desc = "\n\n".join([f"{act}: {SEARCH_ACTION_DESC[act]}" for act in actions])
        query_format = "\n\n".join([f"<{act}>{SEARCH_ACTION_PARAM[act]}</{act}>" for act in actions])

        if self.args.system == "planner_find":
            prompt = forced_proposer_template.format(n_queries=self.n_queries, question=question, source_desc=source_desc, query_format=query_format.replace(", 0 to 3 queries", ""))
        elif self.args.system == "planner_prompt":
            prompt = adaptive_proposer_template.format(question=question, source_desc=source_desc, query_format=query_format)
        else:
            raise NotImplementedError

        format_feedback = None
        for _ in range(5):
            if format_feedback is not None:
                prompt += format_feedback # does not contain failed_response, for repeated failure
            format_feedback = None
            llm_output = self.llm.run([prompt])[0][0]
            for pat in actions:
                pattern = f'<{pat}>(.*?)</{pat}>'
                match = re.search(pattern, llm_output, re.DOTALL)
                if match is None and pat in llm_output:
                    if format_feedback is None:
                        format_feedback = "\n\n# "
                    format_feedback += f"Your previous response does not contain <{pat}> and </{pat}>. " 
            if format_feedback is None:
                break
            else:
                format_feedback += "Please response again following the specified format."

        source_and_queries = []
        for act in actions:
            pattern = f'<{act}>(.*?)</{act}>'
            match = re.search(pattern, llm_output, re.DOTALL)
            if match is not None:
                queries = match.group(1)
                queries = queries.replace("{", "").replace("}", "")
                queries = queries.replace("(Use ; to separate the queries, 0 to 3 queries)", "")
                queries = queries.replace("search_query0", "")
                queries = queries.replace("search_query1", "")
                queries = queries.replace("search_query2", "")
            else:
                queries = ""

            queries = queries.split(";", maxsplit=self.n_queries-1)
            for i in range(len(queries)):
                queries[i] = queries[i].replace(";", ',').strip()
            queries = [q for q in queries if q != ""]

            source_and_queries.append([act, queries])

        return source_and_queries