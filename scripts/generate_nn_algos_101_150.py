import os
import sys
import math
from pathlib import Path

BASE_DIR = Path("/home/btpl-lap-22/live/llm-obs-infra/policies/policy-orchestrator/src/features/code_engine/algos/nn")
TEST_DIR = Path("/home/btpl-lap-22/live/llm-obs-infra/policies/policy-orchestrator/tests/unit/algos")

categories = [
    "attention_objectives",
    "position_encodings",
    "transformer_efficiency",
    "mixture_of_experts",
    "multimodal_memory",
    "scaling_stability",
    "decoding"
]

for cat in categories:
    (BASE_DIR / cat).mkdir(parents=True, exist_ok=True)
    init_file = BASE_DIR / cat / "__init__.py"
    if not init_file.exists():
        init_file.write_text(f'"""Neural network algorithms category: {cat}."""\n')

print("Created subdirectories and __init__.py files.")
