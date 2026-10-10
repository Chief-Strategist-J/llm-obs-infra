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

# 101. Scaled dot-product attention
write_algo(
    "attention_objectives",
    "scaled_dot_product_attention",
    '''from __future__ import annotations

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
            description: Optional custom scale factor.
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
        - query, key, and value are non-empty 2D matrices
        - query and key have matching feature dimension d_k > 0
        - key and value have matching length N_k > 0
        - all values are finite floats
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard floating point roundoff"
      uses_model: false
      complexity:
        variables:
          N_q: query sequence length
          N_k: key sequence length
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
      certificate: "Row sums of attention_weights equal 1.0 within numerical precision"
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
        if not query or not key or not value:
            raise ValueError("Precondition failed: inputs must be non-empty")
        N_q = len(query)
        N_k = len(key)
        if len(value) != N_k:
            raise ValueError("Precondition failed: key and value must have equal sequence length")
        d_k = len(query[0])
        if len(key[0]) != d_k:
            raise ValueError("Precondition failed: query and key must have same dimension d_k")
        d_v = len(value[0])

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
            row_weights = [e / sum_exp for e in exp_scores] if sum_exp > 0 else [1.0 / N_k] * N_k
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
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb, amsthm, bm}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Scaled Dot-Product Attention}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\section{Formulation}
\begin{equation}
\text{Attention}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{softmax}\left(\frac{\mathbf{Q}\mathbf{K}^\top}{\sqrt{d_k}} + \mathbf{M}\right)\mathbf{V}
\end{equation}
\end{document}
'''
)

# 102. Multi-head attention
write_algo(
    "attention_objectives",
    "multi_head_attention",
    '''from __future__ import annotations

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
            description: Query matrix of shape (N_q, d_model).
          key:
            type: array
            items:
              type: array
              items:
                type: number
            description: Key matrix of shape (N_k, d_model).
          value:
            type: array
            items:
              type: array
              items:
                type: number
            description: Value matrix of shape (N_k, d_model).
          num_heads:
            type: integer
            minimum: 1
            description: Number of heads h.
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
            description: Output tensor of shape (N_q, d_model).
          head_outputs:
            type: array
            items:
              type: array
              items:
                type: array
                items:
                  type: number
            description: Per-head outputs of shape (h, N_q, d_k).
          head_dim:
            type: integer
            description: Head dimension d_k.
      parameters: {}
      input_assumptions:
        - d_model is divisible by num_heads
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard floating point bounds"
      uses_model: false
      complexity:
        variables:
          N_q: query sequence length
          N_k: key sequence length
          d_model: model dimension
          h: number of heads
        time_worst: O(N_q * N_k * d_model)
        time_typical: O(N_q * N_k * d_model)
        space: O(h * N_q * N_k + N_q * d_model)
      preconditions:
        - len(input.query) > 0 and len(input.query[0]) % input.num_heads == 0
      postconditions:
        - len(output.output) == len(input.query)
        - len(output.output[0]) == len(input.query[0])
      certificate: "Output dimension equals input dimension"
      compatible_adapters:
        - ADAPTER-MHA
      related_algos:
        - ALGO-NN-101
      references:
        - "https://arxiv.org/abs/1706.03762"
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
        d_model = len(query[0])
        if d_model % num_heads != 0:
            raise ValueError("Precondition failed: d_model must be divisible by num_heads")

        d_k = d_model // num_heads

        head_outputs: List[List[List[float]]] = []
        for h in range(num_heads):
            s = h * d_k
            e = s + d_k
            q_h = [[row[c] for c in range(s, e)] for row in query]
            k_h = [[row[c] for c in range(s, e)] for row in key]
            v_h = [[row[c] for c in range(s, e)] for row in value]

            res = NnAlgoScaledDotProductAttention.forward(q_h, k_h, v_h, mask=mask)
            head_outputs.append(res["output"])

        output: List[List[float]] = []
        for i in range(N_q):
            row: List[float] = []
            for h in range(num_heads):
                row.extend(head_outputs[h][i])
            output.append(row)

        return {
            "output": output,
            "head_outputs": head_outputs,
            "head_dim": d_k,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Multi-Head Attention}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\text{MHA}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{Concat}(\text{head}_1, \dots, \text{head}_h)\mathbf{W}^O
\end{equation}
\end{document}
'''
)

# 103. Causal language modeling
write_algo(
    "attention_objectives",
    "causal_language_modeling",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class NnAlgoCausalLanguageModeling:
    """
    ---
    contract:
      algo_id: ALGO-NN-103
      name: NnAlgoCausalLanguageModeling
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - causal_lm
        - next_token_prediction
        - cross_entropy
      inputs:
        type: object
        required:
          - logits
          - target_tokens
        properties:
          logits:
            type: array
            items:
              type: array
              items:
                type: number
            description: Logits matrix of shape (seq_len - 1, vocab_size).
          target_tokens:
            type: array
            items:
              type: integer
            description: Target token indices of shape (seq_len - 1).
          ignore_index:
            type: integer
            default: -100
            description: Target index to ignore in loss computation.
      outputs:
        type: object
        required:
          - loss
          - perplexity
          - token_losses
          - num_active_tokens
        properties:
          loss:
            type: number
            description: Average cross-entropy loss over active tokens.
          perplexity:
            type: number
            description: Perplexity exp(loss).
          token_losses:
            type: array
            items:
              type: number
            description: Per-token loss vector.
          num_active_tokens:
            type: integer
            description: Number of unmasked tokens contributing to loss.
      parameters: {}
      input_assumptions:
        - len(logits) == len(target_tokens)
        - target indices valid or equal to ignore_index
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard floating point bounds"
      uses_model: false
      complexity:
        variables:
          T: sequence length
          V: vocabulary size
        time_worst: O(T * V)
        time_typical: O(T * V)
        space: O(T)
      preconditions:
        - len(input.logits) > 0
        - len(input.logits) == len(input.target_tokens)
      postconditions:
        - output.loss >= 0.0
        - output.perplexity >= 1.0
      certificate: "perplexity == exp(loss)"
      compatible_adapters:
        - ADAPTER-CAUSAL-LM
      related_algos:
        - ALGO-NN-104
        - ALGO-NN-14
      references:
        - "https://doi.org/10.1162/neco.1997.9.8.1735"
    ---
    """

    @staticmethod
    def forward(
        logits: List[List[float]],
        target_tokens: List[int],
        ignore_index: int = -100,
    ) -> Dict[str, Any]:
        if not logits or not target_tokens:
            raise ValueError("Precondition failed: logits and target_tokens must be non-empty")
        if len(logits) != len(target_tokens):
            raise ValueError("Precondition failed: len(logits) == len(target_tokens)")

        V = len(logits[0])
        total_loss = 0.0
        active_count = 0
        token_losses: List[float] = []

        for row, target in zip(logits, target_tokens):
            if target == ignore_index:
                token_losses.append(0.0)
                continue
            if not (0 <= target < V):
                raise ValueError(f"Precondition failed: target token {target} out of range [0, {V})")

            max_l = max(row)
            exp_sum = sum(math.exp(z - max_l) for z in row)
            log_prob = (row[target] - max_l) - math.log(exp_sum)
            nll = -log_prob
            token_losses.append(nll)
            total_loss += nll
            active_count += 1

        avg_loss = (total_loss / active_count) if active_count > 0 else 0.0
        ppl = math.exp(min(avg_loss, 100.0))

        return {
            "loss": avg_loss,
            "perplexity": ppl,
            "token_losses": token_losses,
            "num_active_tokens": active_count,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Causal Language Modeling Objective}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathcal{L}_{\text{CLM}} = -\frac{1}{T}\sum_{t=1}^T \log P(x_t \mid x_{<t}; \theta)
\end{equation}
\end{document}
'''
)

# 104. Masked language modeling (MLM)
write_algo(
    "attention_objectives",
    "masked_language_modeling",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class NnAlgoMaskedLanguageModeling:
    """
    ---
    contract:
      algo_id: ALGO-NN-104
      name: NnAlgoMaskedLanguageModeling
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - masked_language_modeling
        - bert
        - encoder_pretraining
      inputs:
        type: object
        required:
          - logits
          - masked_positions
          - target_tokens
        properties:
          logits:
            type: array
            items:
              type: array
              items:
                type: number
            description: Encoder logits of shape (seq_len, vocab_size).
          masked_positions:
            type: array
            items:
              type: integer
            description: Indices of masked positions in the sequence.
          target_tokens:
            type: array
            items:
              type: integer
            description: Ground truth token indices at the masked positions.
      outputs:
        type: object
        required:
          - loss
          - accuracy
          - predictions
        properties:
          loss:
            type: number
            description: Average cross-entropy loss over masked tokens.
          accuracy:
            type: number
            description: Prediction accuracy on masked positions.
          predictions:
            type: array
            items:
              type: integer
            description: Predicted token indices for each masked position.
      parameters: {}
      input_assumptions:
        - masked_positions and target_tokens have equal length
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard numerical error"
      uses_model: false
      complexity:
        variables:
          M: number of masked tokens
          V: vocab size
        time_worst: O(M * V)
        time_typical: O(M * V)
        space: O(M)
      preconditions:
        - len(input.masked_positions) == len(input.target_tokens)
      postconditions:
        - output.loss >= 0.0
        - 0.0 <= output.accuracy <= 1.0
      certificate: "accuracy is in [0.0, 1.0]"
      compatible_adapters:
        - ADAPTER-BERT-MLM
      related_algos:
        - ALGO-NN-103
        - ALGO-NN-105
      references:
        - "https://arxiv.org/abs/1810.04805"
    ---
    """

    @staticmethod
    def forward(
        logits: List[List[float]],
        masked_positions: List[int],
        target_tokens: List[int],
    ) -> Dict[str, Any]:
        if len(masked_positions) != len(target_tokens):
            raise ValueError("Precondition failed: masked_positions and target_tokens must match length")
        if not masked_positions:
            return {"loss": 0.0, "accuracy": 1.0, "predictions": []}

        V = len(logits[0])
        total_loss = 0.0
        correct = 0
        predictions: List[int] = []

        for pos, target in zip(masked_positions, target_tokens):
            if not (0 <= pos < len(logits)):
                raise ValueError(f"Precondition failed: masked position {pos} out of sequence range")
            if not (0 <= target < V):
                raise ValueError(f"Precondition failed: target token {target} out of range [0, {V})")

            row = logits[pos]
            max_l = max(row)
            exp_sum = sum(math.exp(z - max_l) for z in row)
            log_prob = (row[target] - max_l) - math.log(exp_sum)
            total_loss += -log_prob

            pred = max(range(V), key=lambda idx: row[idx])
            predictions.append(pred)
            if pred == target:
                correct += 1

        M = len(masked_positions)
        return {
            "loss": total_loss / float(M),
            "accuracy": correct / float(M),
            "predictions": predictions,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Masked Language Modeling (MLM)}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathcal{L}_{\text{MLM}} = -\sum_{i \in \mathcal{M}} \log P(x_i \mid \tilde{\mathbf{x}}; \theta)
\end{equation}
\end{document}
'''
)

# 105. Span corruption (denoising objectives, T5)
write_algo(
    "attention_objectives",
    "span_corruption",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


class NnAlgoSpanCorruption:
    """
    ---
    contract:
      algo_id: ALGO-NN-105
      name: NnAlgoSpanCorruption
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - span_corruption
        - t5
        - denoising
      inputs:
        type: object
        required:
          - tokens
          - corruption_spans
          - sentinel_start_id
        properties:
          tokens:
            type: array
            items:
              type: integer
            description: Original token sequence.
          corruption_spans:
            type: array
            items:
              type: array
              items:
                type: integer
            description: List of (start_idx, end_idx) non-overlapping token spans to corrupt.
          sentinel_start_id:
            type: integer
            description: Starting token ID for unique sentinel tokens.
      outputs:
        type: object
        required:
          - corrupted_inputs
          - target_sequence
          - num_spans_corrupted
        properties:
          corrupted_inputs:
            type: array
            items:
              type: integer
            description: Input sequence with spans replaced by sentinel tokens.
          target_sequence:
            type: array
            items:
              type: integer
            description: Target decoder sequence containing sentinels followed by missing tokens.
          num_spans_corrupted:
            type: integer
            description: Total count of spans corrupted.
      parameters: {}
      input_assumptions:
        - corruption_spans are sorted and non-overlapping
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact deterministic span replacement"
      uses_model: false
      complexity:
        variables:
          N: sequence length
          S: number of spans
        time_worst: O(N)
        time_typical: O(N)
        space: O(N)
      preconditions:
        - len(input.tokens) > 0
      postconditions:
        - len(output.corrupted_inputs) > 0
        - len(output.target_sequence) > 0
      certificate: "Corrupted inputs contain exactly one sentinel token per corrupted span"
      compatible_adapters:
        - ADAPTER-T5-DENOISING
      related_algos:
        - ALGO-NN-104
      references:
        - "https://arxiv.org/abs/1910.10683"
    ---
    """

    @staticmethod
    def forward(
        tokens: List[int],
        corruption_spans: List[Tuple[int, int]],
        sentinel_start_id: int = 32000,
    ) -> Dict[str, Any]:
        if not tokens:
            raise ValueError("Precondition failed: tokens must be non-empty")

        corrupted_inputs: List[int] = []
        target_seq: List[int] = []

        curr_pos = 0
        sentinel_id = sentinel_start_id

        sorted_spans = sorted(corruption_spans, key=lambda s: s[0])
        for start, end in sorted_spans:
            if start < curr_pos or end > len(tokens) or start >= end:
                raise ValueError(f"Precondition failed: invalid span ({start}, {end})")

            corrupted_inputs.extend(tokens[curr_pos:start])
            corrupted_inputs.append(sentinel_id)

            target_seq.append(sentinel_id)
            target_seq.extend(tokens[start:end])

            curr_pos = end
            sentinel_id += 1

        corrupted_inputs.extend(tokens[curr_pos:])
        target_seq.append(sentinel_id)

        return {
            "corrupted_inputs": corrupted_inputs,
            "target_sequence": target_seq,
            "num_spans_corrupted": len(sorted_spans),
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Span Corruption Denoising Objective (T5)}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
Replaces spans of length $L$ with sentinel tokens $S_k$:
\begin{equation}
\mathbf{x}_{\text{corrupt}} = [x_1, \dots, S_1, x_i, \dots], \quad \mathbf{y}_{\text{target}} = [S_1, x_{\text{span}_1}, S_2, x_{\text{span}_2}, \dots]
\end{equation}
\end{document}
'''
)

# 106. Sinusoidal positional encoding
write_algo(
    "position_encodings",
    "sinusoidal_positional_encoding",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoSinusoidalPositionalEncoding:
    """
    ---
    contract:
      algo_id: ALGO-NN-106
      name: NnAlgoSinusoidalPositionalEncoding
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - positional_encoding
        - sinusoidal
        - transformer
      inputs:
        type: object
        required:
          - seq_len
          - d_model
        properties:
          seq_len:
            type: integer
            minimum: 1
            description: Maximum sequence length N.
          d_model:
            type: integer
            minimum: 2
            description: Model embedding dimension d (must be even).
          base:
            type: number
            default: 10000.0
            description: Geometric progression base frequency.
      outputs:
        type: object
        required:
          - encoding_matrix
          - seq_len
          - d_model
        properties:
          encoding_matrix:
            type: array
            items:
              type: array
              items:
                type: number
            description: Positional encoding matrix of shape (seq_len, d_model).
          seq_len:
            type: integer
            description: Sequence length.
          d_model:
            type: integer
            description: Embedding dimension.
      parameters: {}
      input_assumptions:
        - d_model is even and >= 2
        - seq_len >= 1
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard floating point bounds"
      uses_model: false
      complexity:
        variables:
          N: seq_len
          d: d_model
        time_worst: O(N * d)
        time_typical: O(N * d)
        space: O(N * d)
      preconditions:
        - input.seq_len >= 1
        - input.d_model >= 2 and input.d_model % 2 == 0
      postconditions:
        - len(output.encoding_matrix) == input.seq_len
        - len(output.encoding_matrix[0]) == input.d_model
      certificate: "Encodings bounded in [-1.0, 1.0]"
      compatible_adapters:
        - ADAPTER-POSITIONAL-ENCODING
      related_algos:
        - ALGO-NN-107
        - ALGO-NN-108
      references:
        - "https://arxiv.org/abs/1706.03762"
    ---
    """

    @staticmethod
    def forward(seq_len: int, d_model: int, base: float = 10000.0) -> Dict[str, Any]:
        if not isinstance(seq_len, int) or seq_len < 1:
            raise ValueError("Precondition failed: seq_len >= 1")
        if not isinstance(d_model, int) or d_model < 2 or d_model % 2 != 0:
            raise ValueError("Precondition failed: d_model must be an even integer >= 2")

        pe_matrix: List[List[float]] = []
        for pos in range(seq_len):
            row = [0.0] * d_model
            for i in range(0, d_model, 2):
                denom = math.pow(base, float(i) / float(d_model))
                row[i] = math.sin(float(pos) / denom)
                row[i + 1] = math.cos(float(pos) / denom)
            pe_matrix.append(row)

        return {
            "encoding_matrix": pe_matrix,
            "seq_len": seq_len,
            "d_model": d_model,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Sinusoidal Positional Encoding}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\text{PE}_{(pos, 2i)} = \sin\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right), \quad \text{PE}_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)
\end{equation}
\end{document}
'''
)

# 107. Learned absolute position embeddings
write_algo(
    "position_encodings",
    "learned_absolute_position_embeddings",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoLearnedAbsolutePositionEmbeddings:
    """
    ---
    contract:
      algo_id: ALGO-NN-107
      name: NnAlgoLearnedAbsolutePositionEmbeddings
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - learned_position_embeddings
        - transformer
        - bert
      inputs:
        type: object
        required:
          - token_embeddings
          - position_table
        properties:
          token_embeddings:
            type: array
            items:
              type: array
              items:
                type: number
            description: Input token embeddings of shape (seq_len, d_model).
          position_table:
            type: array
            items:
              type: array
              items:
                type: number
            description: Learned position table of shape (max_seq_len, d_model).
          offset:
            type: integer
            default: 0
            description: Starting position offset.
      outputs:
        type: object
        required:
          - output_embeddings
          - seq_len
          - d_model
        properties:
          output_embeddings:
            type: array
            items:
              type: array
              items:
                type: number
            description: Position-augmented embeddings of shape (seq_len, d_model).
          seq_len:
            type: integer
            description: Input sequence length.
          d_model:
            type: integer
            description: Model embedding dimension.
      parameters: {}
      input_assumptions:
        - offset + seq_len <= len(position_table)
        - dimensions match
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact summation"
      uses_model: false
      complexity:
        variables:
          N: seq_len
          d: d_model
        time_worst: O(N * d)
        time_typical: O(N * d)
        space: O(N * d)
      preconditions:
        - len(input.token_embeddings) > 0
        - input.offset + len(input.token_embeddings) <= len(input.position_table)
        - len(input.token_embeddings[0]) == len(input.position_table[0])
      postconditions:
        - len(output.output_embeddings) == len(input.token_embeddings)
        - len(output.output_embeddings[0]) == len(input.token_embeddings[0])
      certificate: "Output = token_embeddings + position_table[offset:offset+seq_len]"
      compatible_adapters:
        - ADAPTER-EMBEDDING-LOOKUP
      related_algos:
        - ALGO-NN-106
      references:
        - "https://arxiv.org/abs/1810.04805"
    ---
    """

    @staticmethod
    def forward(
        token_embeddings: List[List[float]],
        position_table: List[List[float]],
        offset: int = 0,
    ) -> Dict[str, Any]:
        if not token_embeddings or not position_table:
            raise ValueError("Precondition failed: inputs must be non-empty")

        N = len(token_embeddings)
        d = len(token_embeddings[0])

        if offset < 0 or offset + N > len(position_table):
            raise ValueError("Precondition failed: sequence exceeds position table capacity")
        if len(position_table[0]) != d:
            raise ValueError("Precondition failed: position table embedding dimension mismatch")

        out: List[List[float]] = []
        for i in range(N):
            pos_vec = position_table[offset + i]
            tok_vec = token_embeddings[i]
            out.append([tok_vec[j] + pos_vec[j] for j in range(d)])

        return {
            "output_embeddings": out,
            "seq_len": N,
            "d_model": d,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Learned Absolute Position Embeddings}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{h}_i = \mathbf{e}_{\text{tok}}(x_i) + \mathbf{W}_{\text{pos}}[i]
\end{equation}
\end{document}
'''
)

# 108. Rotary position embeddings (RoPE)
write_algo(
    "position_encodings",
    "rotary_position_embeddings",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class NnAlgoRotaryPositionEmbeddings:
    """
    ---
    contract:
      algo_id: ALGO-NN-108
      name: NnAlgoRotaryPositionEmbeddings
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - rope
        - rotary_position_embeddings
        - relative_position
      inputs:
        type: object
        required:
          - vectors
          - positions
        properties:
          vectors:
            type: array
            items:
              type: array
              items:
                type: number
            description: Query or Key tensor of shape (seq_len, dim) where dim is even.
          positions:
            type: array
            items:
              type: integer
            description: Position indices of shape (seq_len).
          base:
            type: number
            default: 10000.0
            description: Base frequency theta.
      outputs:
        type: object
        required:
          - rotated_vectors
          - dim
        properties:
          rotated_vectors:
            type: array
            items:
              type: array
              items:
                type: number
            description: Rotary-transformed vectors of shape (seq_len, dim).
          dim:
            type: integer
            description: Dimension of vectors.
      parameters: {}
      input_assumptions:
        - dim is even
        - len(vectors) == len(positions)
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard floating point rotation error"
      uses_model: false
      complexity:
        variables:
          N: seq_len
          d: dim
        time_worst: O(N * d)
        time_typical: O(N * d)
        space: O(N * d)
      preconditions:
        - len(input.vectors) > 0 and len(input.vectors) == len(input.positions)
        - len(input.vectors[0]) % 2 == 0
      postconditions:
        - len(output.rotated_vectors) == len(input.vectors)
        - len(output.rotated_vectors[0]) == len(input.vectors[0])
      certificate: "Vector norm invariant under 2D Givens rotations"
      compatible_adapters:
        - ADAPTER-ROPE
      related_algos:
        - ALGO-NN-106
        - ALGO-NN-111
      references:
        - "https://arxiv.org/abs/2104.09864"
    ---
    """

    @staticmethod
    def forward(
        vectors: List[List[float]],
        positions: List[int],
        base: float = 10000.0,
    ) -> Dict[str, Any]:
        if not vectors or not positions:
            raise ValueError("Precondition failed: vectors and positions must be non-empty")
        if len(vectors) != len(positions):
            raise ValueError("Precondition failed: len(vectors) == len(positions)")

        dim = len(vectors[0])
        if dim % 2 != 0:
            raise ValueError("Precondition failed: dim must be even")

        rotated: List[List[float]] = []
        for vec, m in zip(vectors, positions):
            row = [0.0] * dim
            for i in range(0, dim, 2):
                theta = 1.0 / math.pow(base, float(i) / float(dim))
                angle = float(m) * theta
                cos_val = math.cos(angle)
                sin_val = math.sin(angle)

                x0 = vec[i]
                x1 = vec[i + 1]

                row[i] = x0 * cos_val - x1 * sin_val
                row[i + 1] = x0 * sin_val + x1 * cos_val
            rotated.append(row)

        return {
            "rotated_vectors": rotated,
            "dim": dim,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Rotary Position Embeddings (RoPE)}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{R}_{\Theta, m}^d \mathbf{x} = \begin{pmatrix} x_0 \cos(m\theta_0) - x_1 \sin(m\theta_0) \\ x_0 \sin(m\theta_0) + x_1 \cos(m\theta_0) \\ \vdots \end{pmatrix}
\end{equation}
\end{document}
'''
)

# 109. ALiBi (attention with linear biases)
write_algo(
    "position_encodings",
    "alibi_attention_linear_biases",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoAlibiAttentionLinearBiases:
    """
    ---
    contract:
      algo_id: ALGO-NN-109
      name: NnAlgoAlibiAttentionLinearBiases
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - alibi
        - linear_bias
        - length_extrapolation
      inputs:
        type: object
        required:
          - num_heads
          - seq_len_q
          - seq_len_k
        properties:
          num_heads:
            type: integer
            minimum: 1
            description: Number of attention heads h.
          seq_len_q:
            type: integer
            minimum: 1
            description: Query sequence length N_q.
          seq_len_k:
            type: integer
            minimum: 1
            description: Key sequence length N_k.
      outputs:
        type: object
        required:
          - bias_matrices
          - slopes
        properties:
          bias_matrices:
            type: array
            items:
              type: array
              items:
                type: array
                items:
                  type: number
            description: Tensor of shape (num_heads, seq_len_q, seq_len_k).
          slopes:
            type: array
            items:
              type: number
            description: Head slope values m_h.
      parameters: {}
      input_assumptions:
        - num_heads >= 1, seq_len_q >= 1, seq_len_k >= 1
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact arithmetic"
      uses_model: false
      complexity:
        variables:
          H: num_heads
          N_q: seq_len_q
          N_k: seq_len_k
        time_worst: O(H * N_q * N_k)
        time_typical: O(H * N_q * N_k)
        space: O(H * N_q * N_k)
      preconditions:
        - input.num_heads >= 1 and input.seq_len_q >= 1 and input.seq_len_k >= 1
      postconditions:
        - len(output.bias_matrices) == input.num_heads
        - len(output.bias_matrices[0]) == input.seq_len_q
        - len(output.bias_matrices[0][0]) == input.seq_len_k
      certificate: "Diagonal entries are 0.0, off-diagonal negative penalties"
      compatible_adapters:
        - ADAPTER-ALIBI-ATTENTION
      related_algos:
        - ALGO-NN-108
        - ALGO-NN-110
      references:
        - "https://arxiv.org/abs/2108.12409"
    ---
    """

    @staticmethod
    def forward(num_heads: int, seq_len_q: int, seq_len_k: int) -> Dict[str, Any]:
        if num_heads < 1 or seq_len_q < 1 or seq_len_k < 1:
            raise ValueError("Precondition failed: dimensions must be positive integers")

        def get_slopes(n: int) -> List[float]:
            def get_slopes_power_of_2(count: int) -> List[float]:
                start = math.pow(2.0, -math.pow(2.0, -(math.log2(count) - 3)))
                ratio = start
                return [start * math.pow(ratio, i) for i in range(count)]

            if math.log2(n).is_integer():
                return get_slopes_power_of_2(n)
            closest_power = 2 ** math.floor(math.log2(n))
            base_slopes = get_slopes_power_of_2(closest_power)
            extra_slopes = get_slopes_power_of_2(2 * closest_power)[0::2][: n - closest_power]
            return base_slopes + extra_slopes

        slopes = get_slopes(num_heads)
        bias_matrices: List[List[List[float]]] = []

        for m in slopes:
            mat: List[List[float]] = []
            for i in range(seq_len_q):
                row: List[float] = []
                for j in range(seq_len_k):
                    penalty = -m * float(abs(i - j))
                    row.append(penalty)
                mat.append(row)
            bias_matrices.append(mat)

        return {
            "bias_matrices": bias_matrices,
            "slopes": slopes,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{ALiBi Linear Attention Biases}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\text{Score}_{i,j}^h = \frac{\mathbf{q}_i^\top \mathbf{k}_j}{\sqrt{d_k}} - m_h |i - j|
\end{equation}
\end{document}
'''
)

# 110. Relative position bias (T5 buckets, Transformer-XL)
write_algo(
    "position_encodings",
    "relative_position_bias",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoRelativePositionBias:
    """
    ---
    contract:
      algo_id: ALGO-NN-110
      name: NnAlgoRelativePositionBias
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - t5
        - relative_position_bias
        - bucketing
      inputs:
        type: object
        required:
          - seq_len_q
          - seq_len_k
          - num_buckets
          - max_distance
        properties:
          seq_len_q:
            type: integer
            minimum: 1
            description: Query length.
          seq_len_k:
            type: integer
            minimum: 1
            description: Key length.
          num_buckets:
            type: integer
            default: 32
            description: Number of discrete relative buckets.
          max_distance:
            type: integer
            default: 128
            description: Maximum exact relative distance before logarithmic bucketing.
      outputs:
        type: object
        required:
          - bucket_matrix
          - num_buckets
        properties:
          bucket_matrix:
            type: array
            items:
              type: array
              items:
                type: integer
            description: 2D array of bucket indices of shape (seq_len_q, seq_len_k).
          num_buckets:
            type: integer
            description: Number of buckets.
      parameters: {}
      input_assumptions:
        - num_buckets is even and >= 4
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact integer mapping"
      uses_model: false
      complexity:
        variables:
          N_q: seq_len_q
          N_k: seq_len_k
        time_worst: O(N_q * N_k)
        time_typical: O(N_q * N_k)
        space: O(N_q * N_k)
      preconditions:
        - input.seq_len_q >= 1 and input.seq_len_k >= 1
        - input.num_buckets >= 4
      postconditions:
        - len(output.bucket_matrix) == input.seq_len_q
        - len(output.bucket_matrix[0]) == input.seq_len_k
      certificate: "Bucket indices strictly bounded in [0, num_buckets)"
      compatible_adapters:
        - ADAPTER-T5-POSITION
      related_algos:
        - ALGO-NN-109
      references:
        - "https://arxiv.org/abs/1910.10683"
    ---
    """

    @staticmethod
    def forward(
        seq_len_q: int,
        seq_len_k: int,
        num_buckets: int = 32,
        max_distance: int = 128,
    ) -> Dict[str, Any]:
        if seq_len_q < 1 or seq_len_k < 1 or num_buckets < 4:
            raise ValueError("Precondition failed: invalid parameters")

        def compute_bucket(relative_position: int) -> int:
            ret = 0
            n = -relative_position
            if n > 0:
                ret += num_buckets // 2
                n = -n
            else:
                n = abs(n)

            max_exact = num_buckets // 4
            is_small = n < max_exact
            if is_small:
                val_if_large = max_exact + int(
                    math.log(float(n) / float(max_exact) + 1e-6)
                    / math.log(float(max_distance) / float(max_exact))
                    * float(num_buckets // 4)
                )
                val_if_large = min(val_if_large, num_buckets // 2 - 1)
                ret += n
            else:
                val_if_large = max_exact + int(
                    math.log(float(n) / float(max_exact) + 1e-6)
                    / math.log(float(max_distance) / float(max_exact))
                    * float(num_buckets // 4)
                )
                val_if_large = min(val_if_large, num_buckets // 2 - 1)
                ret += val_if_large
            return min(ret, num_buckets - 1)

        bucket_mat: List[List[int]] = []
        for i in range(seq_len_q):
            row: List[int] = []
            for j in range(seq_len_k):
                row.append(compute_bucket(j - i))
            bucket_mat.append(row)

        return {
            "bucket_matrix": bucket_mat,
            "num_buckets": num_buckets,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{T5 Relative Position Bucketing}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
b(d) = \begin{cases} d & \text{if } |d| < d_{\text{exact}} \\ d_{\text{exact}} + \left\lfloor \frac{\log(|d|/d_{\text{exact}})}{\log(d_{\max}/d_{\text{exact}})} (B - d_{\text{exact}}) \right\rfloor & \text{otherwise} \end{cases}
\end{equation}
\end{document}
'''
)

# 111. Context window extension (position interpolation, NTK-aware scaling, YaRN)
write_algo(
    "position_encodings",
    "context_window_extension",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoContextWindowExtension:
    """
    ---
    contract:
      algo_id: ALGO-NN-111
      name: NnAlgoContextWindowExtension
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - context_extension
        - position_interpolation
        - ntk_scaling
        - yarn
      inputs:
        type: object
        required:
          - scale_factor
          - method
          - original_max_len
        properties:
          scale_factor:
            type: number
            minimum: 1.0
            description: Context expansion scale factor s >= 1.0.
          method:
            type: string
            enum: ["linear_interpolation", "ntk_aware", "yarn"]
            description: Scaling methodology.
          original_max_len:
            type: integer
            minimum: 1
            description: Pretrained context length L_orig.
          d_model:
            type: integer
            default: 128
            description: Head dimension.
          base:
            type: number
            default: 10000.0
            description: RoPE base frequency.
      outputs:
        type: object
        required:
          - extended_max_len
          - scaled_frequencies
          - effective_scale
        properties:
          extended_max_len:
            type: integer
            description: Extended context window size.
          scaled_frequencies:
            type: array
            items:
              type: number
            description: Scaled theta frequencies per dimension pair.
          effective_scale:
            type: number
            description: Final scaling ratio.
      parameters: {}
      input_assumptions:
        - scale_factor >= 1.0
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact scaling formulas"
      uses_model: false
      complexity:
        variables:
          d: d_model
        time_worst: O(d)
        time_typical: O(d)
        space: O(d)
      preconditions:
        - input.scale_factor >= 1.0
        - input.original_max_len >= 1
      postconditions:
        - output.extended_max_len >= input.original_max_len
      certificate: "extended_max_len == int(scale_factor * original_max_len)"
      compatible_adapters:
        - ADAPTER-ROPE-SCALING
      related_algos:
        - ALGO-NN-108
      references:
        - "https://arxiv.org/abs/2306.15595"
        - "https://arxiv.org/abs/2309.00071"
    ---
    """

    @staticmethod
    def forward(
        scale_factor: float,
        method: str,
        original_max_len: int,
        d_model: int = 128,
        base: float = 10000.0,
    ) -> Dict[str, Any]:
        if scale_factor < 1.0 or original_max_len < 1:
            raise ValueError("Precondition failed: invalid scaling parameters")

        half_d = d_model // 2
        extended_len = int(scale_factor * original_max_len)

        if method == "linear_interpolation":
            scaled_freqs = [1.0 / (scale_factor * math.pow(base, (2.0 * i) / float(d_model))) for i in range(half_d)]
        elif method == "ntk_aware":
            base_new = base * math.pow(scale_factor, float(d_model) / float(d_model - 2))
            scaled_freqs = [1.0 / math.pow(base_new, (2.0 * i) / float(d_model)) for i in range(half_d)]
        elif method == "yarn":
            scaled_freqs = []
            for i in range(half_d):
                freq = 1.0 / math.pow(base, (2.0 * i) / float(d_model))
                wavelength = 2.0 * math.pi / freq
                if wavelength < original_max_len / 4.0:
                    scaled_freqs.append(freq)
                elif wavelength > original_max_len:
                    scaled_freqs.append(freq / scale_factor)
                else:
                    alpha = (original_max_len - wavelength) / (3.0 * original_max_len / 4.0)
                    interpolated = (1.0 - alpha) * (freq / scale_factor) + alpha * freq
                    scaled_freqs.append(interpolated)
        else:
            raise ValueError(f"Unknown method {method}")

        return {
            "extended_max_len": extended_len,
            "scaled_frequencies": scaled_freqs,
            "effective_scale": float(scale_factor),
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Context Window Extension Formulations}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
b_{\text{NTK}} = b \cdot s^{d / (d-2)}, \quad \theta_i^{\text{interp}} = \frac{\theta_i}{s}
\end{equation}
\end{document}
'''
)

print("Chunk 1 (101-111) successfully written!")
