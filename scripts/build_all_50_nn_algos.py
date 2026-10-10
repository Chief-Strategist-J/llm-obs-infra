"""
Master Generator for Neural Network Algorithms #101 to #150 (Part 3: Attention, Transformers, Decoding)
Generates:
  - 50 algorithms under 7 subcategories in algos/nn/
  - math.tex LaTeX formulations
  - Unit test files test_nn_algos_101_125.py and test_nn_algos_126_150.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path("/home/btpl-lap-22/live/llm-obs-infra/policies/policy-orchestrator/src/features/code_engine/algos/nn")
TEST_DIR = Path("/home/btpl-lap-22/live/llm-obs-infra/policies/policy-orchestrator/tests/unit/algos")

categories = {
    "attention_objectives": ["scaled_dot_product_attention", "multi_head_attention", "causal_language_modeling", "masked_language_modeling", "span_corruption"],
    "position_encodings": ["sinusoidal_positional_encoding", "learned_absolute_position_embeddings", "rotary_position_embeddings", "alibi_attention_linear_biases", "relative_position_bias", "context_window_extension"],
    "transformer_efficiency": ["transformer_block", "encoder_decoder_transformers", "grouped_query_attention", "multi_head_latent_attention", "flash_attention", "kv_cache", "paged_attention", "sliding_window_attention", "sparse_attention_patterns", "linear_attention", "structured_state_space_s4", "mamba_selective_ssm", "rwkv_retnet_recurrent"],
    "mixture_of_experts": ["moe_top_k_gating", "moe_load_balancing", "moe_expert_choice_routing"],
    "multimodal_memory": ["vision_transformer", "swin_transformer", "perceiver_latent_attention", "cross_attention_conditioning", "clip_contrastive_pretraining", "multimodal_llm_connectors", "segment_level_recurrence", "retrieval_enhanced_transformers", "prefix_lm_mixture_denoisers", "multi_token_prediction"],
    "scaling_stability": ["scaling_laws_compute_optimal", "attention_sinks_streaming", "logit_stabilization_z_loss"],
    "decoding": ["greedy_temperature_sampling", "top_k_sampling", "nucleus_min_p_sampling", "repetition_frequency_penalties", "contrastive_search_decoding", "speculative_decoding", "self_drafting_medusa_eagle", "constrained_grammar_decoding", "self_consistency_sampling", "lookahead_jacobi_decoding"]
}

for cat in categories:
    (BASE_DIR / cat).mkdir(parents=True, exist_ok=True)
    init_f = BASE_DIR / cat / "__init__.py"
    if not init_f.exists():
        init_f.write_text(f'"""Neural network algorithms category: {cat}."""\n')

print("Directories initialized successfully.")
