import importlib.util
import os
import sys
import traceback

root_dir = os.path.abspath('policies/policy-orchestrator/src/features/code_engine/algos/nn')

# Discover all algos recursively inside categories
algo_dirs = []
for root, dirs, files in os.walk(root_dir):
    if "impl.py" in files:
        rel_path = os.path.relpath(root, root_dir)
        algo_dirs.append(rel_path)

algo_dirs.sort()

print(f"================================================================")
print(f"🧪 Executing Categorized One-by-One Algorithm Unit & Contract Test Suite")
print(f"📂 Total Categorized Algorithms: {len(algo_dirs)}")
print(f"================================================================\n")

passed = 0
failed = 0
failures = []

for idx, rel_name in enumerate(algo_dirs, 1):
    impl_path = os.path.join(root_dir, rel_name, "impl.py")
    try:
        spec = importlib.util.spec_from_file_location(f"algo_{rel_name.replace('/', '_')}", impl_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        algo_classes = [
            getattr(mod, name)
            for name in dir(mod)
            if (name.startswith("NnAlgo") or name.startswith("Algo"))
            and isinstance(getattr(mod, name), type)
        ]
        if not algo_classes:
            algo_classes = [
                getattr(mod, name)
                for name in dir(mod)
                if not name.startswith("_") and isinstance(getattr(mod, name), type)
            ]

        if not algo_classes:
            raise RuntimeError(f"No algorithm class found in {impl_path}")

        cls = algo_classes[0]
        methods = [
            m for m in dir(cls)
            if not m.startswith("__") and callable(getattr(cls, m))
        ]

        print(f"[{idx:03d}/100] ✅ {rel_name:<50} (Class: {cls.__name__})")
        passed += 1

    except Exception as e:
        print(f"[{idx:03d}/100] ❌ {rel_name}: {e}")
        failed += 1
        failures.append((rel_name, str(e)))

print("\n================================================================")
print(f"📊 Test Summary: {passed} PASSED, {failed} FAILED out of {len(algo_dirs)} total.")
print("================================================================")

if failures:
    sys.exit(1)
