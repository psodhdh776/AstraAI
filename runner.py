#!/usr/bin/env python3
"""
AI Engine Runner — unified launcher for the production INT8 inference engine.
Integrates with AbsoluteAssistant and provides CLI for all subsystems.
"""
import sys
import os
import time
import math
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.ai_engine import (
    AiEngine, KVCache, GenerativeOps, LlmSampler,
    MemoryArena, QuantizedOps,
    GenerativeEngine, ExtremeSampler, ContinuousBatchScheduler,
    Sequence, CorpusWordEngine,
    StaticArena,
)
import ctypes

VOCAB_16 = {
    0: "the", 1: "a", 2: "and", 3: "is", 4: "in", 5: "to",
    6: "of", 7: "it", 8: "you", 9: "that", 10: "was",
    11: "for", 12: "are", 13: "with", 14: "this", 15: "have"
}


def _parse_floats(raw):
    """Parse floats from comma-separated string or list of strings."""
    if isinstance(raw, str) and "," in raw:
        return [float(x.strip()) for x in raw.split(",")]
    if isinstance(raw, list):
        return [float(x) if isinstance(x, str) else float(x) for x in raw]
    return [float(raw)]

def cmd_inference(args=None):
    """Run INT8 inference engine with test inputs."""
    engine = AiEngine()
    engine.build()
    if args:
        args = args if isinstance(args, list) else [args]
        data = _parse_floats(",".join(args) if len(args) == 1 and "," in args[0] else args)
        tests = [(data, "custom")]
    else:
        tests = [([1.0, -0.5, 2.0, 0.0], "input"),
                 ([0.5, 1.0, -1.0, 0.0], "alt"),
                 ([2.0, -1.0, 3.0, 0.5], "max")]

    for data, label in tests:
        t0 = time.perf_counter_ns()
        result = engine.predict(data)
        dt = time.perf_counter_ns() - t0
        raw_tv, _ = engine._graph.get_output("out_y")
        raw_str = ""
        if raw_tv is not None:
            raw_str = f"INT8: [{', '.join(f'{raw_tv[i]:3}' for i in range(len(raw_tv)))}]  "
        print(f"  [{label:8s}]  "
              f"FP32: [{', '.join(f'{v:8.4f}' for v in data)}]  "
              f"{raw_str}"
              f"FP32: [{', '.join(f'{v:8.4f}' for v in result)}]  "
              f"({dt} ns)")
    arena = engine.static_arena
    print(f"\n  Arena: {arena.used}/{arena.total} bytes "
          f"({arena.used/arena.total*100:.1f}%)")


def cmd_sampling(args=None):
    """Demonstrate Top-K / Top-P / Temperature sampling."""
    logits = [2.1, 4.5, 0.2, 1.1, 3.8, -1.5, 0.0, 2.8,
              0.5, 1.9, -2.0, 0.8, 3.2, 1.5, 2.3, -0.5]
    print(f"  Logits: [{', '.join(f'{v:5.1f}' for v in logits)}]")
    print(f"  Vocab:  {', '.join(f'{k}:{v}' for k, v in VOCAB_16.items())}\n")

    configs = [
        ("Greedy ArgMax",   {"temperature": 0.001, "top_k": 0, "top_p": 0.0}),
        ("Conservative",    {"temperature": 0.5,   "top_k": 5, "top_p": 0.0}),
        ("Standard",        {"temperature": 0.8,   "top_k": 0, "top_p": 0.9}),
        ("Creative",        {"temperature": 1.5,   "top_k": 0, "top_p": 0.95}),
    ]

    for label, params in configs:
        counts = {}
        for _ in range(200):
            tid = LlmSampler.sample(logits, **params)
            counts[tid] = counts.get(tid, 0) + 1
        top = sorted(counts.items(), key=lambda x: -x[1])[:3]
        dist = ", ".join(f"{VOCAB_16[t]} ({c/200*100:.0f}%)" for t, c in top)
        print(f"  [{label:20s}]  {dist}")


def cmd_kvcache(args=None):
    """KV-Cache append, growth, and memory verification."""
    cache = KVCache()
    seq_len = int(args[0]) if args and str(args[0]).lstrip("-").isdigit() else 7
    for step in range(seq_len):
        k = [0.1 * step, 0.2 * step, 0.3 * step]
        v = [0.4 * step, 0.5 * step, 0.6 * step]
        cache.append(k, v)
    k_bytes = len(cache.keys) * 4
    v_bytes = len(cache.values) * 4
    print(f"  Tokens: {cache.seq_len}")
    print(f"  K floats: {len(cache.keys)} ({k_bytes} bytes)")
    print(f"  V floats: {len(cache.values)} ({v_bytes} bytes)")
    print(f"  Total:    {k_bytes + v_bytes} bytes")


def cmd_generate(args=None):
    """Generate text using CorpusWordEngine (word-level bigram, correct spelling)."""
    prompt = " ".join(args) if args else "привет"
    corpus_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus_ru.txt")
    if os.path.isfile(corpus_path):
        with open(corpus_path, "r", encoding="utf-8") as f:
            corpus = f.read()
        gen = CorpusWordEngine(corpus)
        engine_name = "CorpusWordEngine"
    else:
        gen = GenerativeEngine(embed_dim=16, hidden_dim=32)
        engine_name = "GenerativeEngine"
    print(f"  Engine: {engine_name}")
    print(f"  Prompt: \"{prompt}\"")
    print(f"  Vocab:  {len(gen.word_list) if hasattr(gen, 'word_list') else gen.vocab_size} words\n")
    for temp in (0.7, 0.9, 1.2):
        t0 = time.perf_counter()
        result = gen.generate(prompt, max_tokens=18, temperature=temp, top_k=8, top_p=0.88)
        dt = (time.perf_counter() - t0) * 1000
        print(f"  [temp={temp:.1f}] \"{result[:120]}\" ({dt:.0f} ms)")
    print()

def cmd_batch(args=None):
    """Continuous batching demo: multiple concurrent word-level sequences."""
    n = int(args[0]) if args and str(args[0]).lstrip("-").isdigit() else 3
    corpus_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus_ru.txt")
    if os.path.isfile(corpus_path):
        with open(corpus_path, "r", encoding="utf-8") as f:
            corpus = f.read()
        engine = CorpusWordEngine(corpus)
    else:
        engine = GenerativeEngine()
    scheduler = ContinuousBatchScheduler(engine=engine, max_batch_size=2)
    prompts = [
        ("привет", 12, 0.9),
        ("как дела", 12, 1.0),
        ("расскажи", 15, 1.1),
        ("помоги", 10, 0.8),
        ("что это", 12, 0.95),
    ]
    t0 = time.perf_counter()
    for i in range(min(n, len(prompts))):
        p, mt, t = prompts[i]
        scheduler.submit(prompt=p, max_tokens=mt, temperature=t)
    iters = scheduler.run(max_iterations=60)
    dt = (time.perf_counter() - t0) * 1000
    print(f"  Sequences: {len(scheduler.results())}, Iterations: {iters}, Time: {dt:.0f} ms\n")
    for sid, prompt, text in scheduler.results():
        print(f"  [#{sid}] prompt=\"{prompt}\"")
        print(f"         generated=\"{text[:80]}\"")
        print()

def cmd_help():
    """Show available commands."""
    print("Available commands:")
    print("  inference [v1,v2,...]  — Run INT8 inference (opt: comma-sep floats)")
    print("  sampling              — Show Top-K/Top-P/Temperature distributions")
    print("  kvcache [N]           — KV-Cache growth simulation (N tokens)")
    print("  generate [text]       — Character-level generation with INT8 engine")
    print("  batch [N]             — Continuous batching demo (N concurrent sequences)")
    print("  help                  — Show this message")
    print("  all                   — Run all subsystems")
    print("\nExamples:")
    print("  python runner.py inference")
    print("  python runner.py inference 1.0,-0.5,2.0,0.0")
    print("  python runner.py sampling")
    print("  python runner.py kvcache 10")
    print("  python runner.py generate привет мир")
    print("  python runner.py batch 3")
    print("  python runner.py all")


def cmd_all():
    """Run all subsystems sequentially."""
    print("\n" + "=" * 63)
    print("   [1/5] INT8 INFERENCE ENGINE")
    print("=" * 63)
    cmd_inference()

    print("\n" + "=" * 63)
    print("   [2/5] KV-CACHE")
    print("=" * 63)
    cmd_kvcache()

    print("\n" + "=" * 63)
    print("   [3/5] LLM SAMPLING")
    print("=" * 63)
    cmd_sampling()

    print("\n" + "=" * 63)
    print("   [4/5] GENERATIVE ENGINE")
    print("=" * 63)
    cmd_generate()

    print("\n" + "=" * 63)
    print("   [5/5] CONTINUOUS BATCHING")
    print("=" * 63)
    cmd_batch()

    print("\n" + "=" * 63)
    print("   ALL SUBSYSTEMS: READY")
    print("=" * 63)


def main():
    print("=" * 63)
    print("   AI INFERENCE ENGINE — RUNNER (INT8 + LLM + Sampling)")
    print("=" * 63)
    print()

    args = sys.argv[1:]
    if not args or args[0] == "help":
        cmd_help()
    elif args[0] == "inference":
        cmd_inference(args[1:])
    elif args[0] == "sampling":
        cmd_sampling()
    elif args[0] == "kvcache":
        cmd_kvcache(args[1:])
    elif args[0] == "generate":
        cmd_generate(args[1:])
    elif args[0] == "batch":
        cmd_batch(args[1:])
    elif args[0] == "all":
        cmd_all()
    else:
        print(f"Unknown command: {args[0]}")
        cmd_help()


if __name__ == "__main__":
    sys.exit(main())
