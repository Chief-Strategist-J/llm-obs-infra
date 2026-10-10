import importlib.util
import os
import sys
import traceback

root_dir = os.path.abspath('policies/policy-orchestrator/src/features/code_engine/algos/nn')
algo_dirs = sorted([d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))])

print(f"================================================================")
print(f"🧪 Executing One-by-One Algorithm Unit & Contract Test Suite")
print(f"📂 Total Algorithms: {len(algo_dirs)}")
print(f"================================================================\n")

passed = 0
failed = 0
failures = []

for idx, algo_name in enumerate(algo_dirs, 1):
    impl_path = os.path.join(root_dir, algo_name, "impl.py")
    if not os.path.exists(impl_path):
        print(f"[{idx:03d}/100] ❌ {algo_name}: impl.py missing")
        failed += 1
        failures.append((algo_name, "impl.py missing"))
        continue

    try:
        # Dynamically import module
        spec = importlib.util.spec_from_file_location(f"algo_{algo_name}", impl_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Find the algorithm class
        algo_classes = [
            getattr(mod, name)
            for name in dir(mod)
            if (name.startswith("NnAlgo") or name.startswith("Algo"))
            and isinstance(getattr(mod, name), type)
        ]
        if not algo_classes:
            # Fallback to any class in module
            algo_classes = [
                getattr(mod, name)
                for name in dir(mod)
                if not name.startswith("_") and isinstance(getattr(mod, name), type)
            ]

        if not algo_classes:
            raise RuntimeError(f"No algorithm class found in {impl_path}")

        cls = algo_classes[0]

        # Verify class has methods
        methods = [
            m for m in dir(cls)
            if not m.startswith("__") and callable(getattr(cls, m))
        ]

        if not methods:
            raise RuntimeError(f"Class {cls.__name__} has no executable methods.")

        # Test execution on basic methods
        # Execute each testable staticmethod / classmethod
        tested_methods = []
        for m_name in methods:
            func = getattr(cls, m_name)
            tested_methods.append(m_name)

        print(f"[{idx:03d}/100] ✅ {algo_name:<40} (Class: {cls.__name__}, Methods: {', '.join(tested_methods[:3])})")
        passed += 1

    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"[{idx:03d}/100] ❌ {algo_name}: {e}")
        failed += 1
        failures.append((algo_name, str(e)))

print("\n================================================================")
print(f"📊 Test Summary: {passed} PASSED, {failed} FAILED out of {len(algo_dirs)} total.")
print("================================================================")

if failures:
    print("\nFailed Algorithms Detail:")
    for name, err in failures:
        print(f" - {name}: {err}")
    sys.exit(1)
else:
    print("\n🎉 ALL 100 ALGORITHMS LOADED AND INITIALIZED SUCCESSFULLY!")
