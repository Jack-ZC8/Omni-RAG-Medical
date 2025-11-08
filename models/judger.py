
llmjudge_template = """You are a professional medical expert. Please judge whether the information in the # Documents supports the # Gold Answer as a response to the # Question. Please first think step-by-step and then show your judgement. Your responses will be used for research purposes only, so please have a definite answer.
You should respond to the following question using the format <answer>yes/no</answer> at the end of your response. Please keep your entire response simple and complete, up to 100 words.

# Question
{question}

# Gold Answer
{gold}

# Documents
{documents}

Hint: Please judge whether # Documents supports the # Gold Answer in response to the # Question, rather than evaluating if the # Question's answer is the # Gold Answer."""


class Judger():
    def __init__(self, llm, args):
        self.llm = llm
        self.args = args

    def run(self, question_ls, documents_ls, gold_ls):
        assert isinstance(question_ls, list) and isinstance(documents_ls, list) and isinstance(gold_ls, list)
        
        prompt_ls = []
        for question, documents, gold in zip(question_ls, documents_ls, gold_ls):
            prompt = llmjudge_template.format(question=question, gold=gold, documents=documents)
            prompt_ls.append(prompt)
        
        llm_output = self.llm.run(prompt_ls)

        return llm_output
