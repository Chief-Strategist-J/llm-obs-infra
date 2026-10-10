import os
import math
from pathlib import Path

BASE_DIR = Path("/home/btpl-lap-22/live/llm-obs-infra/policies/policy-orchestrator/src/features/code_engine/algos/nn")

def write_algo(category: str, algo_folder: str, impl_code: str, math_tex: str):
    folder = BASE_DIR / category / algo_folder
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "impl.py").write_text(impl_code.strip() + "\n")
    (folder / "math.tex").write_text(math_tex.strip() + "\n")
    print(f"Generated {category}/{algo_folder}")

# ==============================================================================
# 101. Scaled Dot-Product Attention (attention_objectives)
# ==============================================================================
impl_101 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class NnAlgoScaledDotProductAttention:
    """
    ---
    contract:
      algo_id: ALGO-NN-101
      name: NnAlgoScaledDotProductAttention
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - attention
        - transformer
        - scaled_dot_product
      inputs:
        type: object
        required:
          - query
          - key
          - value
        properties:
          query:
            type: array
            items:
              type: array
              items:
                type: number
            description: Query matrix Q of shape (N_q, d_k).
          key:
            type: array
            items:
              type: array
              items:
                type: number
            description: Key matrix K of shape (N_k, d_k).
          value:
            type: array
            items:
              type: array
              items:
                type: number
            description: Value matrix V of shape (N_k, d_v).
          mask:
            type: array
            items:
              type: array
              items:
                type: number
            description: Optional additive attention mask of shape (N_q, N_k).
          scale:
            type: number
            description: Optional custom scale factor (defaults to 1 / sqrt(d_k)).
      outputs:
        type: object
        required:
          - output
          - attention_weights
          - scale_factor
        properties:
          output:
            type: array
            items:
              type: array
              items:
                type: number
            description: Attention output matrix of shape (N_q, d_v).
          attention_weights:
            type: array
            items:
              type: array
              items:
                type: number
            description: Attention probability weights of shape (N_q, N_k).
          scale_factor:
            type: number
            description: Multiplicative scaling factor applied to raw logits.
      parameters: {}
      input_assumptions:
        - query is a non-empty 2D array of shape (N_q, d_k)
        - key is a non-empty 2D array of shape (N_k, d_k)
        - value is a non-empty 2D array of shape (N_k, d_v)
        - mask if provided has shape (N_q, N_k)
        - all numerical values are finite floats
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Bounded by floating point roundoff in softmax"
      uses_model: false
      complexity:
        variables:
          N_q: query sequence length
          N_k: key/value sequence length
          d_k: key dimension
          d_v: value dimension
        time_worst: O(N_q * N_k * (d_k + d_v))
        time_typical: O(N_q * N_k * (d_k + d_v))
        space: O(N_q * N_k + N_q * d_v)
      preconditions:
        - len(input.query) > 0 and len(input.key) > 0 and len(input.value) > 0
        - len(input.key) == len(input.value)
        - len(input.query[0]) == len(input.key[0])
      postconditions:
        - len(output.output) == len(input.query)
        - len(output.output[0]) == len(input.value[0])
        - len(output.attention_weights) == len(input.query)
        - len(output.attention_weights[0]) == len(input.key)
      certificate: "softmax rows sum to 1.0 within numerical tolerance"
      compatible_adapters:
        - ADAPTER-TRANSFORMER-ATTENTION
      related_algos:
        - ALGO-NN-102
        - ALGO-NN-116
      references:
        - "https://arxiv.org/abs/1706.03762"
        - "https://doi.org/10.1145/3381831"
    ---
    """

    @staticmethod
    def forward(
        query: List[List[float]],
        key: List[List[float]],
        value: List[List[float]],
        mask: Optional[List[List[float]]] = None,
        scale: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not query or len(query) == 0:
            raise ValueError("Precondition failed: query must be non-empty")
        if not key or len(key) == 0:
            raise ValueError("Precondition failed: key must be non-empty")
        if not value or len(value) == 0:
            raise ValueError("Precondition failed: value must be non-empty")

        N_q = len(query)
        N_k = len(key)
        if len(value) != N_k:
            raise ValueError("Precondition failed: len(key) == len(value)")

        d_k = len(query[0])
        if d_k == 0:
            raise ValueError("Precondition failed: query feature dimension must be > 0")
        if len(key[0]) != d_k:
            raise ValueError("Precondition failed: query and key must have same dimension d_k")
        d_v = len(value[0])
        if d_v == 0:
            raise ValueError("Precondition failed: value feature dimension must be > 0")

        for r in query:
            if len(r) != d_k or any(math.isnan(v) or math.isinf(v) for v in r):
                raise ValueError("Precondition failed: query contains invalid elements")
        for r in key:
            if len(r) != d_k or any(math.isnan(v) or math.isinf(v) for v in r):
                raise ValueError("Precondition failed: key contains invalid elements")
        for r in value:
            if len(r) != d_v or any(math.isnan(v) or math.isinf(v) for v in r):
                raise ValueError("Precondition failed: value contains invalid elements")

        if mask is not None:
            if len(mask) != N_q or any(len(r) != N_k for r in mask):
                raise ValueError("Precondition failed: mask shape must be (N_q, N_k)")

        scale_factor = scale if (scale is not None and scale > 0) else 1.0 / math.sqrt(d_k)

        attn_weights: List[List[float]] = []
        for i in range(N_q):
            q_vec = query[i]
            scores: List[float] = []
            for j in range(N_k):
                k_vec = key[j]
                dot = sum(q_vec[d] * k_vec[d] for d in range(d_k))
                score = dot * scale_factor
                if mask is not None:
                    score += mask[i][j]
                scores.append(score)

            max_score = max(scores)
            exp_scores = [math.exp(s - max_score) for s in scores]
            sum_exp = sum(exp_scores)
            if sum_exp <= 0.0 or math.isnan(sum_exp):
                row_weights = [1.0 / N_k] * N_k
            else:
                row_weights = [e / sum_exp for e in exp_scores]
            attn_weights.append(row_weights)

        output: List[List[float]] = []
        for i in range(N_q):
            row_out = [0.0] * d_v
            for j in range(N_k):
                w = attn_weights[i][j]
                v_vec = value[j]
                for d in range(d_v):
                    row_out[d] += w * v_vec[d]
            output.append(row_out)

        return {
            "output": output,
            "attention_weights": attn_weights,
            "scale_factor": scale_factor,
        }
'''

math_101 = r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb, amsthm, bm}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Scaled Dot-Product Attention Formulation}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle

\section{Mathematical Definition}
Given query matrix $\mathbf{Q} \in \mathbb{R}^{N_q \times d_k}$, key matrix $\mathbf{K} \in \mathbb{R}^{N_k \times d_k}$, and value matrix $\mathbf{V} \in \mathbb{R}^{N_k \times d_v}$, the scaled dot-product attention mapping is defined as:
\begin{equation}
\text{Attention}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{softmax}\left(\frac{\mathbf{Q}\mathbf{K}^\top}{\sqrt{d_k}} + \mathbf{M}\right)\mathbf{V}
\end{equation}
where $\mathbf{M} \in \{0, -\infty\}^{N_q \times N_k}$ is an optional masking matrix (e.g., causal or padding mask), and the softmax is computed row-wise:
\begin{equation}
\mathbf{A}_{i, j} = \frac{\exp\left(\frac{\mathbf{q}_i^\top \mathbf{k}_j}{\sqrt{d_k}} + M_{i,j} - m_i\right)}{\sum_{l=1}^{N_k} \exp\left(\frac{\mathbf{q}_i^\top \mathbf{k}_l}{\sqrt{d_k}} + M_{i,l} - m_i\right)}, \quad m_i = \max_l \left(\frac{\mathbf{q}_i^\top \mathbf{k}_l}{\sqrt{d_k}} + M_{i,l}\right)
\end{equation}

\section{Complexity and Stability}
The time complexity is $\mathcal{O}(N_q N_k d_k + N_q N_k d_v)$ and the memory footprint is $\mathcal{O}(N_q N_k + N_q d_v)$. The scale factor $\frac{1}{\sqrt{d_k}}$ preserves unit variance of the dot-products under standard normal independent components, preventing the softmax gradient from vanishing.

\end{document}
'''
write_algo("attention_objectives", "scaled_dot_product_attention", impl_101, math_101)


# ==============================================================================
# 102. Multi-Head Attention (attention_objectives)
# ==============================================================================
impl_102 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from src.features.code_engine.algos.nn.attention_objectives.scaled_dot_product_attention.impl import (
    NnAlgoScaledDotProductAttention,
)


class NnAlgoMultiHeadAttention:
    """
    ---
    contract:
      algo_id: ALGO-NN-102
      name: NnAlgoMultiHeadAttention
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - multi_head_attention
        - transformer
        - parallel_attention
      inputs:
        type: object
        required:
          - query
          - key
          - value
          - num_heads
        properties:
          query:
            type: array
            items:
              type: array
              items:
                type: number
            description: Input query sequence of shape (N_q, d_model).
          key:
            type: array
            items:
              type: array
              items:
                type: number
            description: Input key sequence of shape (N_k, d_model).
          value:
            type: array
            items:
              type: array
              items:
                type: number
            description: Input value sequence of shape (N_k, d_model).
          num_heads:
            type: integer
            minimum: 1
            description: Number of attention heads h dividing d_model.
          mask:
            type: array
            items:
              type: array
              items:
                type: number
            description: Optional mask of shape (N_q, N_k).
      outputs:
        type: object
        required:
          - output
          - head_outputs
          - head_dim
        properties:
          output:
            type: array
            items:
              type: array
              items:
                type: number
            description: Combined projected output of shape (N_q, d_model).
          head_outputs:
            type: array
            items:
              type: array
              items:
                type: array
                items:
                  type: number
            description: List of head outputs of shape (h, N_q, d_k).
          head_dim:
            type: integer
            description: Dimension of each individual attention head d_k = d_model / h.
      parameters: {}
      input_assumptions:
        - query, key, value non-empty with d_model divisible by num_heads
        - all values finite
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard floating point precision bounds"
      uses_model: false
      complexity:
        variables:
          N_q: query sequence length
          N_k: key sequence length
          d_model: model hidden dimension
          h: number of heads
        time_worst: O(N_q * N_k * d_model)
        time_typical: O(N_q * N_k * d_model)
        space: O(h * N_q * N_k + N_q * d_model)
      preconditions:
        - len(input.query) > 0 and len(input.key) > 0 and len(input.value) > 0
        - len(input.query[0]) % input.num_heads == 0
      postconditions:
        - len(output.output) == len(input.query)
        - len(output.output[0]) == len(input.query[0])
        - len(output.head_outputs) == input.num_heads
      certificate: "Concatenation of head outputs preserves exact shape (N_q, d_model)"
      compatible_adapters:
        - ADAPTER-TRANSFORMER-MHA
      related_algos:
        - ALGO-NN-101
        - ALGO-NN-114
      references:
        - "https://arxiv.org/abs/1706.03762"
        - "https://doi.org/10.1162/neco.1997.9.8.1735"
    ---
    """

    @staticmethod
    def forward(
        query: List[List[float]],
        key: List[List[float]],
        value: List[List[float]],
        num_heads: int,
        mask: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        if not query or not key or not value:
            raise ValueError("Precondition failed: query, key, value must be non-empty")
        if not isinstance(num_heads, int) or num_heads < 1:
            raise ValueError("Precondition failed: num_heads must be positive integer")

        N_q = len(query)
        N_k = len(key)
        d_model = len(query[0])
        if d_model % num_heads != 0:
            raise ValueError(f"Precondition failed: d_model ({d_model}) must be divisible by num_heads ({num_heads})")

        d_k = d_model // num_heads

        head_outputs: List[List[List[float]]] = []
        for h in range(num_heads):
            start_idx = h * d_k
            end_idx = start_idx + d_k

            q_h = [[row[c] for c in range(start_idx, end_idx)] for row in query]
            k_h = [[row[c] for c in range(start_idx, end_idx)] for row in key]
            v_h = [[row[c] for c in range(start_idx, end_idx)] for row in value]

            res = NnAlgoScaledDotProductAttention.forward(q_h, k_h, v_h, mask=mask)
            head_outputs.append(res["output"])

        output: List[List[float]] = []
        for i in range(N_q):
            row_combined: List[float] = []
            for h in range(num_heads):
                row_combined.extend(head_outputs[h][i])
            output.append(row_combined)

        return {
            "output": output,
            "head_outputs": head_outputs,
            "head_dim": d_k,
        }
'''

math_102 = r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb, amsthm, bm}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Multi-Head Attention Theory}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle

\section{Formulation}
Multi-Head Attention projects the input queries, keys, and values $h$ times with parameter matrices $\mathbf{W}_i^Q \in \mathbb{R}^{d_{\text{model}} \times d_k}$, $\mathbf{W}_i^K \in \mathbb{R}^{d_{\text{model}} \times d_k}$, $\mathbf{W}_i^V \in \mathbb{R}^{d_{\text{model}} \times d_v}$:
\begin{equation}
\text{MHA}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{Concat}(\text{head}_1, \dots, \text{head}_h)\mathbf{W}^O
\end{equation}
where:
\begin{equation}
\text{head}_i = \text{Attention}(\mathbf{Q}\mathbf{W}_i^Q, \mathbf{K}\mathbf{W}_i^K, \mathbf{V}\mathbf{W}_i^V)
\end{equation}
with $d_k = d_v = d_{\text{model}} / h$.

\end{document}
'''
write_algo("attention_objectives", "multi_head_attention", impl_102, math_102)

print("C1 algorithms initialized.")
'''

# We will execute the comprehensive script generating all batches
print("Generator batch script prepared.")
