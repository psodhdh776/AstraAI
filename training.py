#!/usr/bin/env python3
"""
Training CLI for the INT8 AI Engine.
Обучает биграмную модель на текстовом корпусе и экспортирует веса.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.ai_engine import GenerativeEngine, BigramTrainer, _RUSSIAN_CORPUS


def cmd_train(args):
    """Обучить на файле или встроенном корпусе."""
    if args and args[0] == "--builtin":
        corpus = _RUSSIAN_CORPUS
        name = "built-in Russian corpus"
    elif args:
        path = args[0]
        if not os.path.isfile(path):
            print(f"  [ERROR] Файл не найден: {path}")
            return
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            corpus = f.read()
        name = os.path.basename(path)
    else:
        corpus = _RUSSIAN_CORPUS
        name = "built-in Russian corpus"

    print(f"  Corpus: {name}")
    print(f"  Size:   {len(corpus)} chars")
    print()

    trainer = BigramTrainer()
    t0 = time.perf_counter()
    trainer.feed_corpus(corpus)
    dt = time.perf_counter() - t0

    total = sum(sum(row) for row in trainer.counts)
    nonzero = sum(1 for row in trainer.counts for c in row if c > 0)
    print(f"  Training: {dt*1000:.0f} ms")
    print(f"  Bigrams:  {total} total, {nonzero} nonzero cells")
    print()

    # Build engine with trained weights
    gen = GenerativeEngine()
    t0 = time.perf_counter()
    gen.train(corpus, temperature=0.9)
    dt = time.perf_counter() - t0
    print(f"  Engine build: {dt*1000:.0f} ms")
    print()

    # Test generation
    print("  Samples:")
    for prompt, temp in [("привет", 0.9), ("как дела", 1.0), ("расскажи", 1.1), ("что", 0.8)]:
        r = gen.generate(prompt, 80, temperature=temp, top_k=12, top_p=0.9)
        reply = r[len(prompt):].strip()[:60]
        print(f"    [{temp}] {prompt} -> {reply}")
    print()

    # Export weights
    weights = trainer.to_int8_weights(0.9)
    w_path = args[1] if len(args) > 1 and not args[0].startswith("--") else "weights.bin"
    if not w_path.startswith("--"):
        with open(w_path, "wb") as f:
            for w in weights:
                f.write(w.to_bytes(1, "big", signed=True))
        print(f"  Weights exported: {w_path} ({len(weights)} bytes)")
    else:
        print(f"  (use second arg to export weights, e.g. python training.py corpus.txt weights.bin)")


def cmd_interactive(args):
    """Интерактивная сессия с обученным движком."""
    if args and os.path.isfile(args[0]):
        with open(args[0], "r", encoding="utf-8", errors="replace") as f:
            corpus = f.read()
        name = os.path.basename(args[0])
    else:
        corpus = _RUSSIAN_CORPUS
        name = "built-in corpus"

    print(f"  Loading: {name} ({len(corpus)} chars)")
    gen = GenerativeEngine()
    gen.train(corpus, temperature=0.9)
    print("  Engine ready. Type 'quit' to exit.\n")

    while True:
        try:
            text = input("  you: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text or text.lower() in ("quit", "exit", "q"):
            break

        t0 = time.perf_counter()
        r = gen.generate(text, 80, 0.9, 12, 0.9)
        dt = (time.perf_counter() - t0) * 1000
        reply = r[len(text):].strip()
        print(f"  ai:  {reply}")
        print(f"       ({dt:.0f} ms, {len(reply)} chars)")
        print()


def cmd_export(args):
    """Экспорт весов в бинарный файл."""
    if args and os.path.isfile(args[0]):
        with open(args[0], "r", encoding="utf-8", errors="replace") as f:
            corpus = f.read()
    else:
        corpus = _RUSSIAN_CORPUS

    trainer = BigramTrainer()
    trainer.feed_corpus(corpus)
    weights = trainer.to_int8_weights(0.9)

    out_path = args[1] if len(args) > 1 else "weights.bin"
    with open(out_path, "wb") as f:
        for w in weights:
            f.write(w.to_bytes(1, "big", signed=True))
    print(f"  Exported {len(weights)} bytes -> {out_path}")


def cmd_help():
    print("Usage: python training.py <command> [options]")
    print()
    print("Commands:")
    print("  train [file|--builtin] [export_path]")
    print("        Train engine on .txt file (or built-in corpus)")
    print("  chat  [file|--builtin]")
    print("        Interactive generation session")
    print("  export [file] [output_path]")
    print("        Export INT8 weights to binary file")
    print("  help")
    print("        Show this message")
    print()
    print("Examples:")
    print("  python training.py train")
    print("  python training.py train corpus.txt")
    print("  python training.py train corpus.txt weights.bin")
    print("  python training.py chat")
    print("  python training.py chat corpus.txt")
    print("  python training.py export corpus.txt weights.bin")


def main():
    print("=" * 63)
    print("   AI ENGINE — TRAINING CLI (Bigram + INT8)")
    print("=" * 63)
    print()

    args = sys.argv[1:]
    if not args or args[0] in ("help", "--help"):
        cmd_help()
    elif args[0] == "train":
        cmd_train(args[1:])
    elif args[0] == "chat":
        cmd_interactive(args[1:])
    elif args[0] == "export":
        cmd_export(args[1:])
    else:
        print(f"Unknown command: {args[0]}")
        cmd_help()


if __name__ == "__main__":
    sys.exit(main())
