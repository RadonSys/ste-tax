"""Backends: thin adapters from chat messages to a Generation.

Heavy imports (torch, transformers, vllm) live inside the adapter that
needs them, so the core and the mock run on the standard library.

- mock: canned text. Tests plumbing, never accuracy.
- hf: transformers. CPU or GPU. The watermark path.
- vllm: offline LLM. The DCS cluster path; vllm comes from the ROCm
  image, not from this project's dependencies.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .harness import THINK_END, THINK_START, Messages
from .records import Generation


@dataclass(frozen=True, slots=True)
class Sampling:
    """Decoding settings of one run. temperature 0 = greedy; top_k 0 =
    off; top_p 1.0 = off. `seed` is the base seed; each call may pass
    its own (sample s of a task uses seed + s)."""

    max_new_tokens: int
    temperature: float
    seed: int
    top_p: float = 1.0
    top_k: int = 0


class HFTokenizer:
    """harness.Tokenizer over a Hugging Face tokenizer."""

    def __init__(self, tok: Any):
        self.tok = tok

    def think_ids(self) -> tuple[int, int]:
        return (
            self.tok.convert_tokens_to_ids(THINK_START),
            self.tok.convert_tokens_to_ids(THINK_END),
        )

    def decode(self, ids: Sequence[int]) -> str:
        return self.tok.decode(list(ids), skip_special_tokens=True)

    def count(self, text: str) -> int:
        return len(self.tok.encode(text))


def opens_think(prompt: str) -> bool:
    """The chat template ended the prompt inside a think segment."""
    return prompt.rstrip().endswith(THINK_START)


class MockBackend:
    """Deterministic canned text. Tests plumbing only, never accuracy."""

    tokenizer = None

    def __init__(self, model: str, sampling: Sampling):
        self.model = model

    def generate(
        self, messages: Messages, processor: Any = None, seed: int | None = None
    ) -> Generation:
        blob = " ".join(m["content"] for m in messages)
        if "Rewrite the text below" in blob:
            text = (
                "<think>Use approved words only.</think>"
                "Open the cover. Remove the old part. "
                "Install the new part. Answer: 200"
            )
        elif "ASD-STE100" in blob:
            text = (
                "<think>Plan the answer with approved words.</think>"
                "The pump removes the water. Answer: 200"
            )
        else:
            text = (
                "<think>Compute: 480 - 35 * 8 = 200.</think>"
                "After 8 minutes the tank holds less water. Answer: 200"
            )
        return Generation(text=text, token_ids=None, latency_s=0.0)


class HFBackend:
    def __init__(self, model: str, sampling: Sampling, thinking: bool = True):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(model)
        self.tokenizer = HFTokenizer(self.tok)
        self.model = AutoModelForCausalLM.from_pretrained(
            model, torch_dtype="auto", device_map="auto"
        )
        self.model.eval()
        self.thinking = thinking
        self.sampling = sampling
        self._torch = torch

    def _prompt(self, messages: Messages) -> str:
        try:
            return self.tok.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=self.thinking,
            )
        except TypeError:
            return self.tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

    def generate(
        self, messages: Messages, processor: Any = None, seed: int | None = None
    ) -> Generation:
        torch = self._torch
        from transformers import LogitsProcessorList

        s = self.sampling
        prompt = self._prompt(messages)
        inputs = self.tok(prompt, return_tensors="pt").to(self.model.device)
        n_prompt = inputs["input_ids"].shape[1]
        kwargs: dict[str, Any] = {
            "max_new_tokens": s.max_new_tokens,
            "do_sample": s.temperature > 0,
        }
        if s.temperature > 0:
            kwargs["temperature"] = s.temperature
            kwargs["top_p"] = s.top_p
            kwargs["top_k"] = s.top_k
        if processor is not None:
            kwargs["logits_processor"] = LogitsProcessorList([processor])
        torch.manual_seed(s.seed if seed is None else seed)
        t0 = time.perf_counter()
        with torch.no_grad():
            out = self.model.generate(**inputs, **kwargs)
        latency = time.perf_counter() - t0
        new_ids = tuple(out[0][n_prompt:].tolist())
        return Generation(
            text=self.tok.decode(list(new_ids), skip_special_tokens=False),
            token_ids=new_ids,
            latency_s=latency,
            think_open=opens_think(prompt),
            truncated=len(new_ids) >= s.max_new_tokens,
        )


# vLLM engine settings (docs/dcs-amd-hardware.md, KV cache). Recorded in
# the manifest. Context = prompt (A1 word list: a few thousand tokens)
# plus the 16384-token generation default, so 32768.
VLLM_MAX_MODEL_LEN = 32768
VLLM_GPU_MEMORY_UTILIZATION = 0.90


class VLLMBackend:
    """Offline vLLM. The DCS cluster path (ROCm build of vLLM).

    prefix_caching False (default): every call pays its full prefill,
    the cold-prompt number. True: the shared A1/A2 system prompt is paid
    once per process, which understates A1's deployed cost."""

    def __init__(
        self,
        model: str,
        sampling: Sampling,
        tp: int = 1,
        thinking: bool = True,
        prefix_caching: bool = False,
    ):
        from vllm import LLM

        self.llm = LLM(
            model=model,
            tensor_parallel_size=tp,
            max_model_len=VLLM_MAX_MODEL_LEN,
            gpu_memory_utilization=VLLM_GPU_MEMORY_UTILIZATION,
            enable_prefix_caching=prefix_caching,
            seed=sampling.seed,
        )
        self.tok = self.llm.get_tokenizer()
        self.tokenizer = HFTokenizer(self.tok)
        self.thinking = thinking
        self.sampling = sampling

    def generate(
        self, messages: Messages, processor: Any = None, seed: int | None = None
    ) -> Generation:
        from vllm import SamplingParams

        if processor is not None:
            raise NotImplementedError("watermark logit bias needs the hf backend")
        s = self.sampling
        params = SamplingParams(
            temperature=s.temperature,
            top_p=s.top_p,
            top_k=s.top_k if s.top_k > 0 else -1,
            max_tokens=s.max_new_tokens,
            seed=s.seed if seed is None else seed,
        )
        t0 = time.perf_counter()
        outs = self.llm.chat(
            messages,
            params,
            chat_template_kwargs={"enable_thinking": self.thinking},
            use_tqdm=False,
        )
        latency = time.perf_counter() - t0
        o = outs[0].outputs[0]
        return Generation(
            text=o.text,
            token_ids=tuple(o.token_ids),
            latency_s=latency,
            think_open=opens_think(outs[0].prompt or ""),
            truncated=o.finish_reason == "length",
        )
