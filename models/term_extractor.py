import re


term_extractor_template = """You are a helpful medical expert. Please return all medical terminologies in the input # Question. Each term should be splited by `,`.
The output format should be like:
<term>term0 , term1 , ...</term> (The number of terms should be less than 4)

# Question
{question}"""


class Term_Extractor():
    def __init__(self, llm, args):
        self.llm = llm
        self.args = args

    def run(self, question):
        prompt = term_extractor_template.format(question=question)
        
        format_feedback = None
        for _ in range(5):
            if format_feedback is not None:
                prompt += format_feedback
            format_feedback = None
            llm_output = self.llm.run([prompt])[0][0]
            if "<term>" not in llm_output or "</term>" not in llm_output:
                format_feedback = "\n\n# Your previous response does not contain <term> and </term>. Please response again following the specified format."
            if format_feedback is None:
                break

        term_ls = []
        pattern = f'<term>(.*?)</term>'
        match = re.search(pattern, llm_output, re.DOTALL)
        if match is not None:
            result = match.group(1)
            term_ls = result.split(",")
            term_ls = [i.strip() for i in term_ls if i.strip()][:3]
            
        return term_ls
