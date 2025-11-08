from utils.extract_option import extract_option
import string

cot_template = """You are a professional medical expert to answer the # Question. Please first think step-by-step and then answer the question. Your responses will be used for research purposes only, so please have a definite answer.
You should think step by step and respond in the format <answer>A/B/C/...</answer> (only one option can be chosen) at the end of your response. Please keep your entire response simple and complete, up to 100 words.

# Question
{question}

# You should think step by step and respond in the format <answer>A/B/C/...</answer> (only one option can be chosen) at the end of your response. Please keep your entire response simple and complete, up to 100 words."""

ret_template = """You are a professional medical expert to answer the # Question. Please first think step-by-step using the # Retrieved Documents and then answer the question. Your responses will be used for research purposes only, so please have a definite answer.
You should think step by step and respond in the format <answer>A/B/C/...</answer> (only one option can be chosen) at the end of your response. Please keep your entire response simple and complete, up to 100 words.

# Retrieved Documents
{documents}

# Question
{question}

# You should think step by step and respond in the format <answer>A/B/C/...</answer> (only one option can be chosen) at the end of your response. Please keep your entire response simple and complete, up to 100 words."""

class Reader():
    def __init__(self, llm, args):
        self.llm = llm
        self.args = args

    def run(self, question, documents, is_long):
        if documents is None:
            prompt = cot_template.format(question=question)
        else:
            prompt = ret_template.format(question=question, documents=documents)
        
        format_feedback = None
        for _ in range(5):
            if format_feedback is not None:
                prompt += format_feedback
            format_feedback = None
            if is_long:
                prompt = prompt.replace(
                    "<answer>A/B/C/...</answer> (only one option can be chosen)",
                    "<answer>...</answer>"
                )
            llm_output = self.llm.run([prompt])[0][0]
            if (not is_long) and extract_option(llm_output) not in list(string.ascii_letters):
                format_feedback = "\n\n# You should think step by step and respond in the format <answer>A/B/C/...</answer> (only one option can be chosen) at the end of your response. Please keep your entire response simple and complete, up to 100 words."
            if format_feedback is None:
                break
        return llm_output