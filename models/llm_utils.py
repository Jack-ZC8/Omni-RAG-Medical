import json
import os, sys
sys.path.append(os.path.abspath("./"))
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest


class VLLMChatLLM():
    def __init__(self, llm_name):
        assert "CUDA_VISIBLE_DEVICES" in os.environ
        self.llm = LLM(
            model=f"data/{llm_name}",
            enable_prefix_caching=True,
            max_model_len=32000,
            max_num_seqs=2
        )
        self.tokenizer = AutoTokenizer.from_pretrained(f"data/{llm_name}")
        self.if_print = True

    def run(self, prompt_ls):
        output_ls = []
        text_ls = [self.tokenizer.apply_chat_template(
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            tokenize=False,
            add_generation_prompt=True
        ) for prompt in prompt_ls]
        sample_params = SamplingParams(
            n=1,
            temperature=0,
            stop=[],
            max_tokens=1000,
            seed=0,
        )
        response = self.llm.generate(
            prompts=text_ls,
            sampling_params=sample_params,
            use_tqdm=False
        )
        for i in range(len(prompt_ls)):
            prompt = prompt_ls[i]
            output = []
            for ii in range(len(response[i].outputs)):
                output.append(response[i].outputs[ii].text)
            if self.if_print:
                print('='*40)
                print(prompt)
                print('-'*40)
                print(output[0])
                print('='*40)
            output_ls.append(output)
        return output_ls


if __name__ == "__main__":
    llm_name = "Qwen2.5-7B-Instruct"
    llm = VLLMChatLLM(llm_name=llm_name)
    print(llm.run(["Tell me a joke, don't use newline"]))