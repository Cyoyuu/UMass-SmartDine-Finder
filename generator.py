import os
import json
import time
import requests
import traceback
from openai import OpenAI, AzureOpenAI
import random


# ============================
# Provider Implementations
# ============================

class OpenAIProvider:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def chat(self, messages, model, **params):
        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **params
        )
        return resp.choices[0].message.content, resp.usage


class OpenRouterProvider:
    ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key):
        self.api_key = api_key
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/Cyoyuu/UMass-SmartDine-Finder",  # Optional: for analytics
                "X-Title": "UMass SmartDine Finder",  # Optional: app name
            }
        ) if api_key else None

    def chat(self, messages, model, **params):
        payload = {"model": model, "messages": messages, **params}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.post(self.ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        return content, usage


class QwenProvider:
    ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    def __init__(self, api_key):
        self.api_key = api_key

    def chat(self, messages, model, **params):
        prompt = messages[-1]["content"]
        payload = {"model": model, "input": {"prompt": prompt}}
        payload.update(params)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.post(self.ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        content = data["output"]["text"]
        # Qwen does not give tokens; approximate zeros
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        return content, usage

class AzureProvider:
    def __init__(self, endpoint, key, api_version="2024-12-01-preview"):
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=api_version,
        )

    def chat(self, messages, model, **params):
        resp = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **params
        )
        return resp.choices[0].message.content, resp.usage



# ============================
# Provider Factory
# ============================

def get_provider(lm_source, api_key, azure_cfg=None):
    lm_source = lm_source.lower()
    if lm_source == "openai":
        return OpenAIProvider(api_key)
    if lm_source == "openrouter":
        return OpenRouterProvider(api_key)
    if lm_source == "qwen" or lm_source == "dashscope":
        return QwenProvider(api_key)
    if lm_source == "azure":
        if azure_cfg is None:
            raise ValueError("Azure provider requires azure_cfg")
        return AzureProvider(
            endpoint=azure_cfg["AZURE_ENDPOINT"],
            key=azure_cfg["OPENAI_API_KEY"],
            api_version=azure_cfg.get("API_VERSION", "2024-12-01-preview"),
        )
    raise ValueError(f"Unknown lm_source: {lm_source}")


# ============================
# Unified Generator
# ============================

class Generator:
    def __init__(self, lm_source, lm_id, max_tokens=4096, temperature=0.7, top_p=1.0):
        self.lm_source = lm_source
        self.lm_id = lm_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p

        self.cost = 0
        self.caller_analysis = {}
        if self.lm_id == "gpt-4o":
            self.input_token_price = 2.5 * 10 ** -6
            self.output_token_price = 10 * 10 ** -6
        elif self.lm_id == "gpt-4.1":
            self.input_token_price = 2 * 10 ** -6
            self.output_token_price = 8 * 10 ** -6
        elif self.lm_id == "o3-mini" or self.lm_id == "o4-mini":
            self.input_token_price = 1.1 * 10 ** -6
            self.output_token_price = 4.4 * 10 ** -6
        elif self.lm_id == "gpt-35-turbo":
            self.input_token_price = 1 * 10 ** -6
            self.output_token_price = 2 * 10 ** -6
        else:
            self.input_token_price = -1 * 10 ** -6
            self.output_token_price = -2 * 10 ** -6

        # API key lookup
        azure_cfg = None
        if lm_source == "openai":
            self.api_key = os.environ.get("OPENAI_API_KEY", None)
        elif lm_source == "openrouter":
            self.api_key = os.environ.get("OPENROUTER_API_KEY", None)
        elif lm_source == "azure":
            keys = json.load(open(".api_keys.json"))
            azure_cfg = random.choice(keys["all"]) if "embedding" not in lm_id else random.choice(keys["embedding"])
            self.api_key = azure_cfg.get("OPENAI_API_KEY", None)
        elif lm_source in ("qwen", "dashscope"):
            self.api_key = os.environ.get("DASHSCOPE_API_KEY", None)
        else:
            raise ValueError(f"Unsupported provider {lm_source}")
        
        if self.api_key is None:
            raise ValueError(f"API key not found! Please check your `lm_config.json` and set API key accordingly.")

        self.provider = get_provider(lm_source, self.api_key, azure_cfg=azure_cfg)
        self.client = self.provider.client

    def generate(self, prompt, max_tokens=None, temperature=None, top_p=None,
                 json_mode=False, chat_history=None, caller="none"):

        if max_tokens is None: max_tokens = self.max_tokens
        if temperature is None: temperature = self.temperature
        if top_p is None: top_p = self.top_p

        if self.lm_source in ['azure', 'openai', 'openrouter']:
            return self._generate_openai(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                json_mode=json_mode,
                chat_history=chat_history,
                caller=caller,
            )
        elif self.lm_source in ['qwen', 'dashscope']:
            return self._generate_qwen(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

    def _generate_openai(self, prompt, max_tokens, temperature, top_p,
                               json_mode, chat_history, caller):

        def _call():
            messages = chat_history[:] if chat_history else []
            if json_mode:
                messages.append({"role": "system", "content": "You output ONLY JSON. No explanations."})
            messages.append({"role": "user", "content": prompt})

            start = time.perf_counter()
            response = self.client.chat.completions.create(
                model=self.lm_id,
                messages=messages,
                max_completion_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
            print(f"API request time: {time.perf_counter() - start:.2f}s")

            usage = dict(response.usage)
            self.cost += (
                usage["completion_tokens"] * self.output_token_price +
                usage["prompt_tokens"] * self.input_token_price
            )
            if caller not in self.caller_analysis:
                self.caller_analysis[caller] = []
            self.caller_analysis[caller].append(usage["total_tokens"])

            return response.choices[0].message.content

        try:
            return _call()
        except Exception as e:
            print(f"[ERROR] generate: {e}")
            return ""
        
    def _generate_qwen(self, prompt, max_tokens, temperature, json_mode=False):

        def _call():
            start = time.perf_counter()

            if json_mode:
                prompt = prompt + "\nYou output ONLY JSON. No explanations."

            resp = self.client.Generation.call(
                model=self.lm_id,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                result_format="message",
            )

            if resp.status_code != 200:
                raise RuntimeError(f"Qwen request failed: {resp}")

            print(f"[Qwen] API time: {time.perf_counter() - start:.2f}s")

            return resp.output.choices[0].message.content.strip()

        try:
            return _call()
        except Exception as e:
            print(f"[ERROR] Qwen generate: {e}")
            return ""
