import os
import sys
sys.path.append(os.path.abspath("./"))


SEARCH_ACTION_DESC = {
    "book":         "The API provides access to medical knowledge resource including various educational resources and textbooks.",
    "guideline":    "The API provides access to clinical guidelines from leading health organizations.",
    "research":     "The API provides access to advanced biomedical research, facilitating access to specialized knowledge and resources.",
    "wiki":         "The API provides access to general knowledge across a wide range of topics.",
    "graph":        "The API provides a structured knowledge graph that connects medical definitions and related terms.",
}

SEARCH_ACTION_PARAM = {
    "book":         r"{search_query0} ; {search_query1} ; ... (Use ; to separate the queries, 0 to 3 queries)",
    "guideline":    r"{search_query0} ; {search_query1} ; ... (Use ; to separate the queries, 0 to 3 queries)",
    "research":     r"{search_query0} ; {search_query1} ; ... (Use ; to separate the queries, 0 to 3 queries)",
    "wiki":         r"{search_query0} ; {search_query1} ; ... (Use ; to separate the queries, 0 to 3 queries)",
    "graph":        r"{medical_term0} , {query_for_term0} ; {medical_term1} , {query_for_term1} ; ... (Use ; to separate the queries, 0 to 3 queries. Each query should use , to separate the {medical_term} and {query_for_term})",
}


class Retriever:
    def __init__(self, topk):
        self.topk = topk

    def run(self, source_and_queries):
        args = []
        for source, queries in source_and_queries:
            assert source in SEARCH_ACTION_DESC
            for q in queries:
                args.append({"source": source, "query": q, "topk": self.topk})
        ######################
        for index, ar in enumerate(args):
            # DEMO
            single_text = """(Title: Blocking set) Definition In a finite projective plane π of order n, a blocking set is a set of points of π that every line intersects and that contains no line completely. Under this definition, if B is a blocking set, then complementary set of points, π\B is also a blocking set. A blocking set B is minimal if the removal of any point of B leaves a set which is not a blocking set. A blocking set of smallest size is called a committee. Every committee is a minimal blocking set, but not all minimal blocking sets are committees. Blocking sets exist in all projective planes except for the smallest projective plane of order 2, the Fano plane. It is sometimes useful to drop the condition that a blocking set does not contain a line. Under this extended definition, and since, in a projective plane every pair of lines meet, every line would be a blocking set. Blocking sets which contained lines would be called trivial blocking sets, in this setting.
(Title: Blocking set) Theorem: In PG(2,p), with p a prime, there exists a projective triad of side (p + 1)/2 which is a blocking set of size (3p+ 1)/2. Size One typically searches for small blocking sets. The minimum size of a blocking set of is called . In the Desarguesian projective plane of order q, PG(2,q), the size of a blocking set B is bounded: When q is a square the lower bound is achieved by any Baer subplane and the upper bound comes from the complement of a Baer subplane. A more general result can be proved, Any blocking set in a projective plane π of order n has at least points. Moreover, if this lower bound is met, then n is necessarily a square and the blocking set consists of the points in some Baer subplane of π. An upper bound for the size of a minimal blocking set has the same flavor,""" 
            ar["docs"] = single_text

        return args


if __name__ == "__main__":
    a = Retriever(topk=10)
    print(a.run(
        [
            ["book", ["fever", "HIV"]],
            ["graph", ["HIV , definition", "fever, definition"]]
        ]
    ))
