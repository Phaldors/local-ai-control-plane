# Same-checkpoint comparison: plan written before the runs (2026-10-15)

Goal: after the retraction in `findings-runtime-confound.md`, compare **one checkpoint** (Qwen3-30B-A3B-Thinking-2507)
on both runtimes: MLX 4-bit (`mlx-community/Qwen3-30B-A3B-Thinking-2507-4bit`, downloaded with approval) and Ollama
GGUF Q4_K_M (`qwen3:30b-a3b`). Remaining differences: quantization format, chat template and tool-call parser, runtime.

Setup: validation split only; suites tool_call (37), agent (29), agent_security guard off (21), extraction (50);
thinking left at the default (this checkpoint always reasons), `max_tokens` 4096 on both sides (reasoning exceeds 1024);
Ollama is re-run under that setting (earlier Ollama runs used `think=false`, 1024). One run each, temperature 0, seed 0.

Expectation, stated in advance: with the same checkpoint the agent and security pass counts agree within 2 cases and no
paired sign test is significant (p >= 0.05). If a gap larger than that appears, its cause is quantization, template or
tool-call parsing, and it will be reported as such, not as model quality.
