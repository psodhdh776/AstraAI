import glob, py_compile, sys

errors = []
for f in sorted(glob.glob("**/*.py", recursive=True)):
    if "\\." in f or f.startswith("."):
        continue
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"{f}: {e}")

if errors:
    for e in errors:
        print(e, file=sys.stderr)
    sys.exit(1)
else:
    print(f"OK: {len(list(glob.glob('**/*.py', recursive=True)))} files checked")
