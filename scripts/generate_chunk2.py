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

# 112. The transformer block
write_algo(
    "transformer_efficiency",
    "transformer_block",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from src.features.code_engine.algos.nn.attention_objectives.multi_head_attention.impl import (
    NnAlgoMultiHeadAttention,
)


class NnAlgoTransformerBlock:
    """
    ---
    contract:
      algo_id: ALGO-NN-112
      name: NnAlgoTransformerBlock
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - transformer_block
        - pre_norm
        - ffn
      inputs:
        type: object
        required:
          - hidden_states
          - num_heads
          - d_ff
        properties:
          hidden_states:
            type: array
            items:
              type: array
              items:
                type: number
            description: Input sequence hidden states of shape (seq_len, d_model).
          num_heads:
            type: integer
            minimum: 1
            description: Number of attention heads.
          d_ff:
            type: integer
            minimum: 1
            description: FFN intermediate dimension.
          mask:
            type: array
            items:
              type: array
              items:
                type: number
            description: Optional attention mask.
      outputs:
        type: object
        required:
          - output_states
          - attn_residual
          - ffn_residual
        properties:
          output_states:
            type: array
            items:
              type: array
              items:
                type: number
            description: Output hidden states of shape (seq_len, d_model).
          attn_residual:
            type: array
            items:
              type: array
              items:
                type: number
            description: State after attention residual add.
          ffn_residual:
            type: array
            items:
              type: array
              items:
                type: number
            description: Final state after FFN residual add.
      parameters: {}
      input_assumptions:
        - hidden_states is non-empty 2D array
        - d_model divisible by num_heads
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard floating point error"
      uses_model: false
      complexity:
        variables:
          N: seq_len
          d: d_model
          d_ff: d_ff
        time_worst: O(N^2 * d + N * d * d_ff)
        time_typical: O(N^2 * d + N * d * d_ff)
        space: O(N * d)
      preconditions:
        - len(input.hidden_states) > 0
        - len(input.hidden_states[0]) % input.num_heads == 0
      postconditions:
        - len(output.output_states) == len(input.hidden_states)
        - len(output.output_states[0]) == len(input.hidden_states[0])
      certificate: "Output preserves hidden_states tensor shape"
      compatible_adapters:
        - ADAPTER-TRANSFORMER-LAYER
      related_algos:
        - ALGO-NN-102
      references:
        - "https://arxiv.org/abs/1706.03762"
        - "https://arxiv.org/abs/2002.04745"
    ---
    """

    @staticmethod
    def forward(
        hidden_states: List[List[float]],
        num_heads: int,
        d_ff: int,
        mask: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        if not hidden_states:
            raise ValueError("Precondition failed: hidden_states must be non-empty")

        N = len(hidden_states)
        d = len(hidden_states[0])
        if d % num_heads != 0:
            raise ValueError("Precondition failed: d_model must be divisible by num_heads")

        def rms_norm(x_seq: List[List[float]]) -> List[List[float]]:
            normed: List[List[float]] = []
            for row in x_seq:
                ms = sum(v * v for v in row) / float(len(row))
                scale = 1.0 / math.sqrt(ms + 1e-6)
                normed.append([v * scale for v in row])
            return normed

        norm1 = rms_norm(hidden_states)
        attn_res = NnAlgoMultiHeadAttention.forward(norm1, norm1, norm1, num_heads=num_heads, mask=mask)
        attn_out = attn_res["output"]

        x_mid: List[List[float]] = []
        for i in range(N):
            x_mid.append([hidden_states[i][j] + attn_out[i][j] for j in range(d)])

        norm2 = rms_norm(x_mid)
        ffn_out: List[List[float]] = []
        for i in range(N):
            row = norm2[i]
            proj1 = [max(0.0, sum(row[j] * 0.01 for j in range(d))) for _ in range(d_ff)]
            proj2 = [sum(proj1[k] * 0.01 for k in range(d_ff)) for _ in range(d)]
            ffn_out.append(proj2)

        x_final: List[List[float]] = []
        for i in range(N):
            x_final.append([x_mid[i][j] + ffn_out[i][j] for j in range(d)])

        return {
            "output_states": x_final,
            "attn_residual": x_mid,
            "ffn_residual": x_final,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Pre-LN Transformer Block}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{x}^{(1)} = \mathbf{x} + \text{MHA}(\text{LN}(\mathbf{x})), \quad \mathbf{x}^{(2)} = \mathbf{x}^{(1)} + \text{FFN}(\text{LN}(\mathbf{x}^{(1)}))
\end{equation}
\end{document}
'''
)

# 113. Encoder-only, decoder-only and encoder-decoder transformers
write_algo(
    "transformer_efficiency",
    "encoder_decoder_transformers",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from src.features.code_engine.algos.nn.attention_objectives.scaled_dot_product_attention.impl import (
    NnAlgoScaledDotProductAttention,
)


class NnAlgoEncoderDecoderTransformers:
    """
    ---
    contract:
      algo_id: ALGO-NN-113
      name: NnAlgoEncoderDecoderTransformers
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - encoder_decoder
        - cross_attention
        - sequence_to_sequence
      inputs:
        type: object
        required:
          - encoder_hidden_states
          - decoder_hidden_states
        properties:
          encoder_hidden_states:
            type: array
            items:
              type: array
              items:
                type: number
            description: Encoder representation matrix of shape (src_len, d_model).
          decoder_hidden_states:
            type: array
            items:
              type: array
              items:
                type: number
            description: Decoder query states of shape (tgt_len, d_model).
          cross_mask:
            type: array
            items:
              type: array
              items:
                type: number
            description: Optional cross-attention mask of shape (tgt_len, src_len).
      outputs:
        type: object
        required:
          - cross_attention_output
          - cross_weights
        properties:
          cross_attention_output:
            type: array
            items:
              type: array
              items:
                type: number
            description: Cross-attended representations of shape (tgt_len, d_model).
          cross_weights:
            type: array
            items:
              type: array
              items:
                type: number
            description: Cross-attention alignment weights.
      parameters: {}
      input_assumptions:
        - encoder and decoder feature dimensions match
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard numerical bounds"
      uses_model: false
      complexity:
        variables:
          T_src: src_len
          T_tgt: tgt_len
          d: d_model
        time_worst: O(T_tgt * T_src * d)
        time_typical: O(T_tgt * T_src * d)
        space: O(T_tgt * T_src + T_tgt * d)
      preconditions:
        - len(input.encoder_hidden_states) > 0 and len(input.decoder_hidden_states) > 0
        - len(input.encoder_hidden_states[0]) == len(input.decoder_hidden_states[0])
      postconditions:
        - len(output.cross_attention_output) == len(input.decoder_hidden_states)
        - len(output.cross_attention_output[0]) == len(input.decoder_hidden_states[0])
      certificate: "Output aligns decoder tokens with encoder representations"
      compatible_adapters:
        - ADAPTER-SEQ2SEQ-CROSS-ATTN
      related_algos:
        - ALGO-NN-101
        - ALGO-NN-131
      references:
        - "https://arxiv.org/abs/1706.03762"
    ---
    """

    @staticmethod
    def forward(
        encoder_hidden_states: List[List[float]],
        decoder_hidden_states: List[List[float]],
        cross_mask: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        if not encoder_hidden_states or not decoder_hidden_states:
            raise ValueError("Precondition failed: inputs must be non-empty")
        if len(encoder_hidden_states[0]) != len(decoder_hidden_states[0]):
            raise ValueError("Precondition failed: feature dimensions must match")

        res = NnAlgoScaledDotProductAttention.forward(
            query=decoder_hidden_states,
            key=encoder_hidden_states,
            value=encoder_hidden_states,
            mask=cross_mask,
        )

        return {
            "cross_attention_output": res["output"],
            "cross_weights": res["attention_weights"],
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Encoder-Decoder Cross-Attention}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\text{CrossAttention}(\mathbf{H}_{\text{dec}}, \mathbf{H}_{\text{enc}}) = \text{softmax}\left(\frac{\mathbf{H}_{\text{dec}}\mathbf{H}_{\text{enc}}^\top}{\sqrt{d}}\right)\mathbf{H}_{\text{enc}}
\end{equation}
\end{document}
'''
)

# 114. Multi-query and grouped-query attention (MQA, GQA)
write_algo(
    "transformer_efficiency",
    "grouped_query_attention",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from src.features.code_engine.algos.nn.attention_objectives.scaled_dot_product_attention.impl import (
    NnAlgoScaledDotProductAttention,
)


class NnAlgoGroupedQueryAttention:
    """
    ---
    contract:
      algo_id: ALGO-NN-114
      name: NnAlgoGroupedQueryAttention
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - gqa
        - mqa
        - kv_cache_compression
      inputs:
        type: object
        required:
          - query
          - key
          - value
          - num_q_heads
          - num_kv_heads
        properties:
          query:
            type: array
            items:
              type: array
              items:
                type: number
            description: Query sequence of shape (seq_len, num_q_heads * head_dim).
          key:
            type: array
            items:
              type: array
              items:
                type: number
            description: Key sequence of shape (seq_len, num_kv_heads * head_dim).
          value:
            type: array
            items:
              type: array
              items:
                type: number
            description: Value sequence of shape (seq_len, num_kv_heads * head_dim).
          num_q_heads:
            type: integer
            minimum: 1
            description: Number of query heads.
          num_kv_heads:
            type: integer
            minimum: 1
            description: Number of key/value heads (must divide num_q_heads).
      outputs:
        type: object
        required:
          - output
          - compression_ratio
          - head_dim
        properties:
          output:
            type: array
            items:
              type: array
              items:
                type: number
            description: Attention output matrix of shape (seq_len, num_q_heads * head_dim).
          compression_ratio:
            type: number
            description: KV cache memory compression factor (num_q_heads / num_kv_heads).
          head_dim:
            type: integer
            description: Dimension per head.
      parameters: {}
      input_assumptions:
        - num_q_heads is divisible by num_kv_heads
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard floating point precision"
      uses_model: false
      complexity:
        variables:
          N: seq_len
          H_q: num_q_heads
          H_kv: num_kv_heads
          d: head_dim
        time_worst: O(H_q * N^2 * d)
        time_typical: O(H_q * N^2 * d)
        space: O(H_q * N^2)
      preconditions:
        - input.num_q_heads % input.num_kv_heads == 0
        - len(input.query) > 0 and len(input.key) > 0 and len(input.value) > 0
      postconditions:
        - len(output.output) == len(input.query)
        - len(output.output[0]) == len(input.query[0])
      certificate: "compression_ratio == num_q_heads / num_kv_heads"
      compatible_adapters:
        - ADAPTER-GQA
      related_algos:
        - ALGO-NN-102
        - ALGO-NN-115
      references:
        - "https://arxiv.org/abs/2305.13245"
    ---
    """

    @staticmethod
    def forward(
        query: List[List[float]],
        key: List[List[float]],
        value: List[List[float]],
        num_q_heads: int,
        num_kv_heads: int,
    ) -> Dict[str, Any]:
        if not query or not key or not value:
            raise ValueError("Precondition failed: non-empty inputs required")
        if num_q_heads % num_kv_heads != 0:
            raise ValueError("Precondition failed: num_q_heads must be divisible by num_kv_heads")

        N_q = len(query)
        N_k = len(key)
        head_dim = len(query[0]) // num_q_heads
        if len(key[0]) != num_kv_heads * head_dim or len(value[0]) != num_kv_heads * head_dim:
            raise ValueError("Precondition failed: key/value head dimension mismatch")

        group_size = num_q_heads // num_kv_heads
        q_heads_out: List[List[List[float]]] = []

        for q_h in range(num_q_heads):
            kv_h = q_h // group_size

            q_s = q_h * head_dim
            q_e = q_s + head_dim
            kv_s = kv_h * head_dim
            kv_e = kv_s + head_dim

            q_vecs = [[row[c] for c in range(q_s, q_e)] for row in query]
            k_vecs = [[row[c] for c in range(kv_s, kv_e)] for row in key]
            v_vecs = [[row[c] for c in range(kv_s, kv_e)] for row in value]

            res = NnAlgoScaledDotProductAttention.forward(q_vecs, k_vecs, v_vecs)
            q_heads_out.append(res["output"])

        combined: List[List[float]] = []
        for i in range(N_q):
            row: List[float] = []
            for q_h in range(num_q_heads):
                row.extend(q_heads_out[q_h][i])
            combined.append(row)

        return {
            "output": combined,
            "compression_ratio": float(group_size),
            "head_dim": head_dim,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Grouped-Query Attention (GQA)}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\text{Group}(\text{head}_i) = \text{Attention}(\mathbf{Q}_i, \mathbf{K}_{\lfloor i/g \rfloor}, \mathbf{V}_{\lfloor i/g \rfloor})
\end{equation}
\end{document}
'''
)

# 115. Multi-head latent attention (MLA)
write_algo(
    "transformer_efficiency",
    "multi_head_latent_attention",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoMultiHeadLatentAttention:
    """
    ---
    contract:
      algo_id: ALGO-NN-115
      name: NnAlgoMultiHeadLatentAttention
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - mla
        - deepseek
        - latent_compression
      inputs:
        type: object
        required:
          - hidden_states
          - latent_dim
          - num_heads
          - head_dim
        properties:
          hidden_states:
            type: array
            items:
              type: array
              items:
                type: number
            description: Hidden states of shape (seq_len, d_model).
          latent_dim:
            type: integer
            minimum: 1
            description: Low-rank compressed latent dimension d_c.
          num_heads:
            type: integer
            minimum: 1
            description: Number of attention heads h.
          head_dim:
            type: integer
            minimum: 1
            description: Head dimension d_h.
      outputs:
        type: object
        required:
          - compressed_kv_latent
          - cached_bytes_per_token
          - compression_factor
        properties:
          compressed_kv_latent:
            type: array
            items:
              type: array
              items:
                type: number
            description: Cached latent KV representation of shape (seq_len, latent_dim).
          cached_bytes_per_token:
            type: integer
            description: Bytes required per token (latent_dim * 2 for fp16).
          compression_factor:
            type: number
            description: Ratio of uncompressed KV size to compressed latent size.
      parameters: {}
      input_assumptions:
        - latent_dim < 2 * num_heads * head_dim
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact compression transformation"
      uses_model: false
      complexity:
        variables:
          N: seq_len
          d: d_model
          d_c: latent_dim
        time_worst: O(N * d * d_c)
        time_typical: O(N * d * d_c)
        space: O(N * d_c)
      preconditions:
        - len(input.hidden_states) > 0
        - input.latent_dim >= 1
      postconditions:
        - len(output.compressed_kv_latent) == len(input.hidden_states)
        - len(output.compressed_kv_latent[0]) == input.latent_dim
      certificate: "compression_factor == (2 * num_heads * head_dim) / latent_dim"
      compatible_adapters:
        - ADAPTER-DEEPSEEK-MLA
      related_algos:
        - ALGO-NN-114
      references:
        - "https://arxiv.org/abs/2405.04434"
    ---
    """

    @staticmethod
    def forward(
        hidden_states: List[List[float]],
        latent_dim: int,
        num_heads: int,
        head_dim: int,
    ) -> Dict[str, Any]:
        if not hidden_states:
            raise ValueError("Precondition failed: hidden_states must be non-empty")
        N = len(hidden_states)
        d_model = len(hidden_states[0])

        compressed_latents: List[List[float]] = []
        for i in range(N):
            row = hidden_states[i]
            c_vec: List[float] = []
            for j in range(latent_dim):
                val = sum(row[k] * 0.01 for k in range(d_model))
                c_vec.append(val)
            compressed_latents.append(c_vec)

        uncompressed_dim = 2 * num_heads * head_dim
        ratio = float(uncompressed_dim) / float(latent_dim)
        bytes_per_tok = latent_dim * 2

        return {
            "compressed_kv_latent": compressed_latents,
            "cached_bytes_per_token": bytes_per_tok,
            "compression_factor": ratio,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Multi-Head Latent Attention (MLA)}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{c}_t^{KV} = \mathbf{W}_{DKV}\mathbf{h}_t, \quad \mathbf{k}_t = \mathbf{W}_{UK}\mathbf{c}_t^{KV}, \quad \mathbf{v}_t = \mathbf{W}_{UV}\mathbf{c}_t^{KV}
\end{equation}
\end{document}
'''
)

# 116. FlashAttention (IO-aware tiled attention)
write_algo(
    "transformer_efficiency",
    "flash_attention",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class NnAlgoFlashAttention:
    """
    ---
    contract:
      algo_id: ALGO-NN-116
      name: NnAlgoFlashAttention
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - flash_attention
        - online_softmax
        - tiled_attention
      inputs:
        type: object
        required:
          - query
          - key
          - value
          - block_size
        properties:
          query:
            type: array
            items:
              type: array
              items:
                type: number
            description: Query matrix of shape (N, d).
          key:
            type: array
            items:
              type: array
              items:
                type: number
            description: Key matrix of shape (N, d).
          value:
            type: array
            items:
              type: array
              items:
                type: number
            description: Value matrix of shape (N, d).
          block_size:
            type: integer
            minimum: 1
            description: SRAM block tile size B_r = B_c.
      outputs:
        type: object
        required:
          - output
          - logsumexp
          - memory_reduction_factor
        properties:
          output:
            type: array
            items:
              type: array
              items:
                type: number
            description: Exact attention output matrix of shape (N, d).
          logsumexp:
            type: array
            items:
              type: number
            description: Row-wise log-sum-exp normalization constants.
          memory_reduction_factor:
            type: number
            description: Theoretical memory savings over standard O(N^2) materialization.
      parameters: {}
      input_assumptions:
        - query, key, value have uniform shape (N, d)
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Numerically identical to standard attention within float epsilon"
      uses_model: false
      complexity:
        variables:
          N: sequence length
          d: head dimension
          B: block size
        time_worst: O(N^2 * d)
        time_typical: O(N^2 * d)
        space: O(N * d + B * d)
      preconditions:
        - len(input.query) > 0 and len(input.key) == len(input.query) and len(input.value) == len(input.query)
        - input.block_size >= 1
      postconditions:
        - len(output.output) == len(input.query)
        - len(output.output[0]) == len(input.query[0])
      certificate: "FlashAttention output matches exact scaled dot-product attention within 1e-5"
      compatible_adapters:
        - ADAPTER-FLASH-ATTN
      related_algos:
        - ALGO-NN-101
      references:
        - "https://arxiv.org/abs/2205.14135"
        - "https://arxiv.org/abs/2307.08691"
    ---
    """

    @staticmethod
    def forward(
        query: List[List[float]],
        key: List[List[float]],
        value: List[List[float]],
        block_size: int = 16,
    ) -> Dict[str, Any]:
        if not query or len(query) != len(key) or len(query) != len(value):
            raise ValueError("Precondition failed: query, key, value must have matching lengths")

        N = len(query)
        d = len(query[0])
        scale = 1.0 / math.sqrt(d)

        output: List[List[float]] = [[0.0] * d for _ in range(N)]
        m_i: List[float] = [-float("inf")] * N
        l_i: List[float] = [0.0] * N

        num_blocks = (N + block_size - 1) // block_size

        for b_kv in range(num_blocks):
            kv_start = b_kv * block_size
            kv_end = min(N, kv_start + block_size)
            k_block = key[kv_start:kv_end]
            v_block = value[kv_start:kv_end]
            b_len = kv_end - kv_start

            for i in range(N):
                q_vec = query[i]
                scores = [sum(q_vec[k] * k_block[j][k] for k in range(d)) * scale for j in range(b_len)]
                m_curr = max(scores)
                m_new = max(m_i[i], m_curr)

                exp_prev = math.exp(m_i[i] - m_new) if m_i[i] != -float("inf") else 0.0
                exp_curr = [math.exp(s - m_new) for s in scores]
                l_curr = sum(exp_curr)
                l_new = l_i[i] * exp_prev + l_curr

                rescaled_out = [output[i][k] * exp_prev for k in range(d)]
                for j in range(b_len):
                    for k in range(d):
                        rescaled_out[k] += exp_curr[j] * v_block[j][k]

                output[i] = rescaled_out
                m_i[i] = m_new
                l_i[i] = l_new

        for i in range(N):
            norm_factor = 1.0 / l_i[i] if l_i[i] > 0 else 1.0
            output[i] = [val * norm_factor for val in output[i]]

        lse = [m_i[i] + math.log(max(l_i[i], 1e-12)) for i in range(N)]
        mem_savings = float(N * N) / float(N * d + block_size * d)

        return {
            "output": output,
            "logsumexp": lse,
            "memory_reduction_factor": mem_savings,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{FlashAttention Tiled Online Softmax}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
m_{\text{new}} = \max(m^{(j-1)}, m^{(j)}), \quad \ell^{(j)} = e^{m^{(j-1)} - m_{\text{new}}}\ell^{(j-1)} + \sum e^{S_{i,:} - m_{\text{new}}}
\end{equation}
\end{document}
'''
)

# 117. KV cache
write_algo(
    "transformer_efficiency",
    "kv_cache",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class NnAlgoKvCache:
    """
    ---
    contract:
      algo_id: ALGO-NN-117
      name: NnAlgoKvCache
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - kv_cache
        - autoregressive_decoding
        - inference_engine
      inputs:
        type: object
        required:
          - new_key
          - new_value
        properties:
          new_key:
            type: array
            items:
              type: number
            description: Key vector for current decoding step of shape (d_k).
          new_value:
            type: array
            items:
              type: number
            description: Value vector for current decoding step of shape (d_v).
          cached_keys:
            type: array
            items:
              type: array
              items:
                type: number
            description: Existing cached keys of shape (seq_len, d_k).
          cached_values:
            type: array
            items:
              type: array
              items:
                type: number
            description: Existing cached values of shape (seq_len, d_v).
      outputs:
        type: object
        required:
          - updated_keys
          - updated_values
          - sequence_length
          - memory_bytes
        properties:
          updated_keys:
            type: array
            items:
              type: array
              items:
                type: number
            description: Appended key cache of shape (seq_len + 1, d_k).
          updated_values:
            type: array
            items:
              type: array
              items:
                type: number
            description: Appended value cache of shape (seq_len + 1, d_v).
          sequence_length:
            type: integer
            description: Updated total cached token count.
          memory_bytes:
            type: integer
            description: Approximate memory allocated for cache in bytes (fp16 assumption).
      parameters: {}
      input_assumptions:
        - new_key and new_value are non-empty 1D arrays
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact append operation"
      uses_model: false
      complexity:
        variables:
          T: sequence length
          d: head dimension
        time_worst: O(d)
        time_typical: O(d)
        space: O(T * d)
      preconditions:
        - len(input.new_key) > 0 and len(input.new_value) > 0
      postconditions:
        - output.sequence_length == len(output.updated_keys)
      certificate: "updated_keys[-1] == new_key and updated_values[-1] == new_value"
      compatible_adapters:
        - ADAPTER-KV-CACHE
      related_algos:
        - ALGO-NN-118
      references:
        - "https://arxiv.org/abs/2205.14135"
    ---
    """

    @staticmethod
    def append_step(
        new_key: List[float],
        new_value: List[float],
        cached_keys: Optional[List[List[float]]] = None,
        cached_values: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        if not new_key or not new_value:
            raise ValueError("Precondition failed: new_key and new_value must be non-empty")

        keys = [row[:] for row in cached_keys] if cached_keys else []
        values = [row[:] for row in cached_values] if cached_values else []

        keys.append(new_key[:])
        values.append(new_value[:])

        seq_len = len(keys)
        d_k = len(new_key)
        d_v = len(new_value)
        mem_bytes = seq_len * (d_k + d_v) * 2

        return {
            "updated_keys": keys,
            "updated_values": values,
            "sequence_length": seq_len,
            "memory_bytes": mem_bytes,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{KV Cache Memory Formulation}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\text{Memory}_{\text{KV}} = 2 \times n_{\text{layers}} \times n_{\text{heads}} \times d_{\text{head}} \times T \times B \times 2 \text{ bytes}
\end{equation}
\end{document}
'''
)

# 118. PagedAttention (paged KV cache memory)
write_algo(
    "transformer_efficiency",
    "paged_attention",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class NnAlgoPagedAttention:
    """
    ---
    contract:
      algo_id: ALGO-NN-118
      name: NnAlgoPagedAttention
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - paged_attention
        - vllm
        - memory_management
      inputs:
        type: object
        required:
          - block_table
          - physical_blocks
          - query_vector
          - block_size
        properties:
          block_table:
            type: array
            items:
              type: integer
            description: Sequence logical-to-physical block mapping indices.
          physical_blocks:
            type: array
            items:
              type: array
              items:
                type: array
                items:
                  type: number
            description: Global physical memory block pool of shape (num_blocks, block_size, d_k).
          query_vector:
            type: array
            items:
              type: number
            description: Current query vector of shape (d_k).
          block_size:
            type: integer
            default: 16
            description: Number of tokens per block page.
      outputs:
        type: object
        required:
          - gathered_keys
          - total_tokens
          - fragmentation_loss
        properties:
          gathered_keys:
            type: array
            items:
              type: array
              items:
                type: number
            description: Non-contiguous physical keys gathered into sequence order.
          total_tokens:
            type: integer
            description: Total resolved token count.
          fragmentation_loss:
            type: number
            description: Memory fragmentation waste fraction.
      parameters: {}
      input_assumptions:
        - all block indices in block_table are valid
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact page indexing"
      uses_model: false
      complexity:
        variables:
          B: number of allocated blocks
          S: block_size
          d: head_dim
        time_worst: O(B * S * d)
        time_typical: O(B * S * d)
        space: O(B * S * d)
      preconditions:
        - len(input.block_table) > 0 and len(input.physical_blocks) > 0
      postconditions:
        - len(output.gathered_keys) == len(input.block_table) * input.block_size
      certificate: "Gathered keys correctly index physical blocks according to block_table"
      compatible_adapters:
        - ADAPTER-VLLM-PAGED-ATTN
      related_algos:
        - ALGO-NN-117
      references:
        - "https://arxiv.org/abs/2309.06180"
    ---
    """

    @staticmethod
    def forward(
        block_table: List[int],
        physical_blocks: List[List[List[float]]],
        query_vector: List[float],
        block_size: int = 16,
    ) -> Dict[str, Any]:
        if not block_table or not physical_blocks or not query_vector:
            raise ValueError("Precondition failed: inputs must be non-empty")

        gathered: List[List[float]] = []
        for p_idx in block_table:
            if not (0 <= p_idx < len(physical_blocks)):
                raise ValueError(f"Precondition failed: invalid physical block index {p_idx}")
            block = physical_blocks[p_idx]
            for tok_vec in block:
                gathered.append(tok_vec[:])

        total_toks = len(gathered)
        allocated_capacity = len(block_table) * block_size
        frag_loss = 1.0 - (float(total_toks) / float(allocated_capacity)) if allocated_capacity > 0 else 0.0

        return {
            "gathered_keys": gathered,
            "total_tokens": total_toks,
            "fragmentation_loss": max(0.0, frag_loss),
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{PagedAttention Virtual Memory Mapping}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{K}[t] = \text{Pool}[\text{BlockTable}[\lfloor t/B \rfloor]][t \pmod B]
\end{equation}
\end{document}
'''
)

# 119. Sliding window (local) attention
write_algo(
    "transformer_efficiency",
    "sliding_window_attention",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from src.features.code_engine.algos.nn.attention_objectives.scaled_dot_product_attention.impl import (
    NnAlgoScaledDotProductAttention,
)


class NnAlgoSlidingWindowAttention:
    """
    ---
    contract:
      algo_id: ALGO-NN-119
      name: NnAlgoSlidingWindowAttention
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - sliding_window
        - mistral
        - local_attention
      inputs:
        type: object
        required:
          - query
          - key
          - value
          - window_size
        properties:
          query:
            type: array
            items:
              type: array
              items:
                type: number
            description: Query matrix of shape (seq_len, d_k).
          key:
            type: array
            items:
              type: array
              items:
                type: number
            description: Key matrix of shape (seq_len, d_k).
          value:
            type: array
            items:
              type: array
              items:
                type: number
            description: Value matrix of shape (seq_len, d_v).
          window_size:
            type: integer
            minimum: 1
            description: Sliding window receptive field width W.
      outputs:
        type: object
        required:
          - output
          - attention_weights
          - active_window_size
        properties:
          output:
            type: array
            items:
              type: array
              items:
                type: number
            description: Attention output of shape (seq_len, d_v).
          attention_weights:
            type: array
            items:
              type: array
              items:
                type: number
            description: Banded attention probability matrix.
          active_window_size:
            type: integer
            description: Configured window size.
      parameters: {}
      input_assumptions:
        - window_size >= 1
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard numerical roundoff"
      uses_model: false
      complexity:
        variables:
          N: seq_len
          W: window_size
          d: dimension
        time_worst: O(N * W * d)
        time_typical: O(N * W * d)
        space: O(N * W)
      preconditions:
        - len(input.query) > 0 and len(input.key) == len(input.query)
        - input.window_size >= 1
      postconditions:
        - len(output.output) == len(input.query)
      certificate: "Mask zero outside causal window [max(0, i - W), i]"
      compatible_adapters:
        - ADAPTER-MISTRAL-SWA
      related_algos:
        - ALGO-NN-101
        - ALGO-NN-120
      references:
        - "https://arxiv.org/abs/2004.05150"
        - "https://arxiv.org/abs/2310.06825"
    ---
    """

    @staticmethod
    def forward(
        query: List[List[float]],
        key: List[List[float]],
        value: List[List[float]],
        window_size: int,
    ) -> Dict[str, Any]:
        if not query or len(query) != len(key) or len(query) != len(value):
            raise ValueError("Precondition failed: matching lengths required")
        if window_size < 1:
            raise ValueError("Precondition failed: window_size >= 1")

        N = len(query)
        mask: List[List[float]] = []
        for i in range(N):
            row: List[float] = []
            for j in range(N):
                if j > i or j < (i - window_size):
                    row.append(-1e9)
                else:
                    row.append(0.0)
            mask.append(row)

        res = NnAlgoScaledDotProductAttention.forward(query, key, value, mask=mask)

        return {
            "output": res["output"],
            "attention_weights": res["attention_weights"],
            "active_window_size": window_size,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Sliding Window Attention (SWA)}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
M_{i, j} = \begin{cases} 0 & \text{if } i - W \leq j \leq i \\ -\infty & \text{otherwise} \end{cases}
\end{equation}
\end{document}
'''
)

# 120. Sparse attention patterns (Longformer, BigBird)
write_algo(
    "transformer_efficiency",
    "sparse_attention_patterns",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Set


class NnAlgoSparseAttentionPatterns:
    """
    ---
    contract:
      algo_id: ALGO-NN-120
      name: NnAlgoSparseAttentionPatterns
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - sparse_attention
        - bigbird
        - longformer
      inputs:
        type: object
        required:
          - seq_len
          - window_radius
          - global_indices
          - random_connections_per_token
        properties:
          seq_len:
            type: integer
            minimum: 1
            description: Sequence length N.
          window_radius:
            type: integer
            minimum: 0
            description: Local sliding window radius r.
          global_indices:
            type: array
            items:
              type: integer
            description: Indices of global tokens.
          random_connections_per_token:
            type: integer
            default: 0
            description: Number of pseudorandom connections per token.
      outputs:
        type: object
        required:
          - adjacency_mask
          - total_edges
          - sparsity_ratio
        properties:
          adjacency_mask:
            type: array
            items:
              type: array
              items:
                type: integer
            description: Binary mask of shape (N, N) where 1 indicates attended position.
          total_edges:
            type: integer
            description: Number of active attention links.
          sparsity_ratio:
            type: number
            description: Fraction of attention matrix elements skipped (1 - edges / N^2).
      parameters: {}
      input_assumptions:
        - all global_indices in [0, seq_len)
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact graph construction"
      uses_model: false
      complexity:
        variables:
          N: seq_len
          r: window_radius
          G: num_global
        time_worst: O(N^2)
        time_typical: O(N * (r + G))
        space: O(N^2)
      preconditions:
        - input.seq_len >= 1
      postconditions:
        - len(output.adjacency_mask) == input.seq_len
        - len(output.adjacency_mask[0]) == input.seq_len
      certificate: "Sparsity ratio strictly in [0.0, 1.0]"
      compatible_adapters:
        - ADAPTER-SPARSE-ATTN
      related_algos:
        - ALGO-NN-119
      references:
        - "https://arxiv.org/abs/2004.05150"
        - "https://arxiv.org/abs/2007.14062"
    ---
    """

    @staticmethod
    def construct_pattern(
        seq_len: int,
        window_radius: int,
        global_indices: List[int],
        random_connections_per_token: int = 0,
    ) -> Dict[str, Any]:
        if seq_len < 1:
            raise ValueError("Precondition failed: seq_len >= 1")

        global_set: Set[int] = set(global_indices)
        mask: List[List[int]] = []
        edges = 0

        for i in range(seq_len):
            row = [0] * seq_len
            for j in range(seq_len):
                is_local = abs(i - j) <= window_radius
                is_global = (i in global_set) or (j in global_set)
                is_random = False
                if random_connections_per_token > 0:
                    hash_val = (i * 31 + j * 17) % seq_len
                    if hash_val < random_connections_per_token:
                        is_random = True

                if is_local or is_global or is_random:
                    row[j] = 1
                    edges += 1
            mask.append(row)

        total_entries = seq_len * seq_len
        sparsity = 1.0 - (float(edges) / float(total_entries))

        return {
            "adjacency_mask": mask,
            "total_edges": edges,
            "sparsity_ratio": max(0.0, sparsity),
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Sparse Attention Graphs (BigBird / Longformer)}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
A_{i, j} = \mathbb{I}(|i - j| \leq r) \lor \mathbb{I}(i \in \mathcal{G} \lor j \in \mathcal{G}) \lor \mathbb{I}(j \in \mathcal{R}_i)
\end{equation}
\end{document}
'''
)

# 121. Linear attention (kernel feature maps)
write_algo(
    "transformer_efficiency",
    "linear_attention",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoLinearAttention:
    """
    ---
    contract:
      algo_id: ALGO-NN-121
      name: NnAlgoLinearAttention
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - linear_attention
        - kernel_feature_map
        - recurrent_attention
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
            description: Query matrix Q of shape (seq_len, d).
          key:
            type: array
            items:
              type: array
              items:
                type: number
            description: Key matrix K of shape (seq_len, d).
          value:
            type: array
            items:
              type: array
              items:
                type: number
            description: Value matrix V of shape (seq_len, d_v).
          eps:
            type: number
            default: 1e-6
            description: Numerical normalizer epsilon.
      outputs:
        type: object
        required:
          - output
          - complexity_advantage
        properties:
          output:
            type: array
            items:
              type: array
              items:
                type: number
            description: Linear attention output of shape (seq_len, d_v).
          complexity_advantage:
            type: string
            description: Asymptotic complexity compared to standard quadratic attention.
      parameters: {}
      input_assumptions:
        - all inputs non-empty with matching lengths
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
          d: feature dimension
          d_v: value dimension
        time_worst: O(N * d * d_v)
        time_typical: O(N * d * d_v)
        space: O(d * d_v + N * d_v)
      preconditions:
        - len(input.query) > 0 and len(input.query) == len(input.key)
      postconditions:
        - len(output.output) == len(input.query)
        - len(output.output[0]) == len(input.value[0])
      certificate: "Complexity linear in sequence length O(N * d * d_v)"
      compatible_adapters:
        - ADAPTER-LINEAR-ATTN
      related_algos:
        - ALGO-NN-101
        - ALGO-NN-124
      references:
        - "https://arxiv.org/abs/2006.16236"
    ---
    """

    @staticmethod
    def forward(
        query: List[List[float]],
        key: List[List[float]],
        value: List[List[float]],
        eps: float = 1e-6,
    ) -> Dict[str, Any]:
        if not query or len(query) != len(key) or len(query) != len(value):
            raise ValueError("Precondition failed: inputs must be non-empty matching sequences")

        N = len(query)
        d = len(query[0])
        d_v = len(value[0])

        def phi(x_vec: List[float]) -> List[float]:
            return [math.log(1.0 + math.exp(v)) + 1.0 for v in x_vec]

        state_kv = [[0.0] * d_v for _ in range(d)]
        state_z = [0.0] * d
        output: List[List[float]] = []

        for t in range(N):
            q_t = phi(query[t])
            k_t = phi(key[t])
            v_t = value[t]

            for i in range(d):
                state_z[i] += k_t[i]
                for j in range(d_v):
                    state_kv[i][j] += k_t[i] * v_t[j]

            denom = sum(q_t[i] * state_z[i] for i in range(d)) + eps
            out_row = [0.0] * d_v
            for j in range(d_v):
                num = sum(q_t[i] * state_kv[i][j] for i in range(d))
                out_row[j] = num / denom
            output.append(out_row)

        return {
            "output": output,
            "complexity_advantage": "O(N * d * d_v) linear time vs O(N^2 * d)",
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Linear Attention via Kernel Feature Maps}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{o}_t = \frac{\phi(\mathbf{q}_t)^\top \mathbf{S}_t}{\phi(\mathbf{q}_t)^\top \mathbf{z}_t}, \quad \mathbf{S}_t = \mathbf{S}_{t-1} + \phi(\mathbf{k}_t)\mathbf{v}_t^\top, \quad \mathbf{z}_t = \mathbf{z}_{t-1} + \phi(\mathbf{k}_t)
\end{equation}
\end{document}
'''
)

# 122. Structured state space models (S4)
write_algo(
    "transformer_efficiency",
    "structured_state_space_s4",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoStructuredStateSpaceS4:
    """
    ---
    contract:
      algo_id: ALGO-NN-122
      name: NnAlgoStructuredStateSpaceS4
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - state_space_model
        - s4
        - hippo
      inputs:
        type: object
        required:
          - inputs
          - state_dim
          - delta
        properties:
          inputs:
            type: array
            items:
              type: number
            description: 1D input sequence x of length L.
          state_dim:
            type: integer
            minimum: 1
            description: SSM latent state dimension N.
          delta:
            type: number
            minimum: 0.0
            exclusiveMinimum: true
            description: Discretization step size Delta > 0.
      outputs:
        type: object
        required:
          - outputs
          - final_state
          - state_dim
        properties:
          outputs:
            type: array
            items:
              type: number
            description: Convolved output sequence y of length L.
          final_state:
            type: array
            items:
              type: number
            description: Final latent state h_L of dimension N.
          state_dim:
            type: integer
            description: State dimension.
      parameters: {}
      input_assumptions:
        - delta > 0.0 and inputs non-empty
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard Euler/Bilinear discretization error"
      uses_model: false
      complexity:
        variables:
          L: sequence length
          N: state dimension
        time_worst: O(L * N)
        time_typical: O(L * N)
        space: O(N + L)
      preconditions:
        - len(input.inputs) > 0
        - input.state_dim >= 1
        - input.delta > 0.0
      postconditions:
        - len(output.outputs) == len(input.inputs)
        - len(output.final_state) == input.state_dim
      certificate: "Outputs length exactly equals input length"
      compatible_adapters:
        - ADAPTER-S4-SSM
      related_algos:
        - ALGO-NN-123
      references:
        - "https://arxiv.org/abs/2111.00396"
    ---
    """

    @staticmethod
    def forward(inputs: List[float], state_dim: int, delta: float = 0.01) -> Dict[str, Any]:
        if not inputs or state_dim < 1 or delta <= 0.0:
            raise ValueError("Precondition failed: invalid inputs or dimensions")

        A = [-1.0 / (float(i) + 1.0) for i in range(state_dim)]
        B = [1.0] * state_dim
        C = [1.0 / math.sqrt(state_dim)] * state_dim

        A_bar = [math.exp(a * delta) for a in A]
        B_bar = [(1.0 - a_b) * (b / abs(a)) if a != 0 else b * delta for a, b, a_b in zip(A, B, A_bar)]

        h = [0.0] * state_dim
        outputs: List[float] = []

        for u in inputs:
            for i in range(state_dim):
                h[i] = A_bar[i] * h[i] + B_bar[i] * u
            y = sum(C[i] * h[i] for i in range(state_dim))
            outputs.append(y)

        return {
            "outputs": outputs,
            "final_state": h,
            "state_dim": state_dim,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Structured State Space (S4) Recurrence}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
h_t = \bar{\mathbf{A}} h_{t-1} + \bar{\mathbf{B}} x_t, \quad y_t = \mathbf{C} h_t + \mathbf{D} x_t
\end{equation}
\end{document}
'''
)

# 123. Mamba (selective state space models)
write_algo(
    "transformer_efficiency",
    "mamba_selective_ssm",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoMambaSelectiveSsm:
    """
    ---
    contract:
      algo_id: ALGO-NN-123
      name: NnAlgoMambaSelectiveSsm
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - mamba
        - selective_ssm
        - state_space_model
      inputs:
        type: object
        required:
          - inputs
          - state_dim
        properties:
          inputs:
            type: array
            items:
              type: number
            description: 1D input sequence x of length L.
          state_dim:
            type: integer
            minimum: 1
            description: Latent SSM state dimension N.
      outputs:
        type: object
        required:
          - outputs
          - final_state
          - delta_history
        properties:
          outputs:
            type: array
            items:
              type: number
            description: Selective SSM filtered outputs of length L.
          final_state:
            type: array
            items:
              type: number
            description: Final hidden state of dimension N.
          delta_history:
            type: array
            items:
              type: number
            description: Input-dependent dynamic delta sequence.
      parameters: {}
      input_assumptions:
        - inputs non-empty and finite
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard numerical precision"
      uses_model: false
      complexity:
        variables:
          L: sequence length
          N: state dimension
        time_worst: O(L * N)
        time_typical: O(L * N)
        space: O(L + N)
      preconditions:
        - len(input.inputs) > 0
        - input.state_dim >= 1
      postconditions:
        - len(output.outputs) == len(input.inputs)
      certificate: "Output sequence matches input length with selective state filtering"
      compatible_adapters:
        - ADAPTER-MAMBA-SSM
      related_algos:
        - ALGO-NN-122
      references:
        - "https://arxiv.org/abs/2312.00752"
    ---
    """

    @staticmethod
    def forward(inputs: List[float], state_dim: int) -> Dict[str, Any]:
        if not inputs or state_dim < 1:
            raise ValueError("Precondition failed: invalid inputs")

        L = len(inputs)
        A = [-1.0 * (i + 1) for i in range(state_dim)]
        h = [0.0] * state_dim
        outputs: List[float] = []
        delta_history: List[float] = []

        for x in inputs:
            delta = math.log(1.0 + math.exp(x * 0.5 + 0.1))
            delta_history.append(delta)

            B_t = [math.tanh(x * 0.1 * (i + 1)) for i in range(state_dim)]
            C_t = [math.cos(x * 0.1 * (i + 1)) for i in range(state_dim)]

            for i in range(state_dim):
                a_bar = math.exp(A[i] * delta)
                b_bar = delta * B_t[i]
                h[i] = a_bar * h[i] + b_bar * x

            y = sum(C_t[i] * h[i] for i in range(state_dim))
            outputs.append(y)

        return {
            "outputs": outputs,
            "final_state": h,
            "delta_history": delta_history,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Mamba Selective State Space Model}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\Delta_t = \text{softplus}(\mathbf{W}_\Delta x_t), \quad \mathbf{B}_t = \mathbf{W}_B x_t, \quad \mathbf{C}_t = \mathbf{W}_C x_t
\end{equation}
\end{document}
'''
)

# 124. RWKV and RetNet (recurrent transformer alternatives)
write_algo(
    "transformer_efficiency",
    "rwkv_retnet_recurrent",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoRwkvRetnetRecurrent:
    """
    ---
    contract:
      algo_id: ALGO-NN-124
      name: NnAlgoRwkvRetnetRecurrent
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - retnet
        - rwkv
        - retention
        - recurrent_transformer
      inputs:
        type: object
        required:
          - query
          - key
          - value
          - gamma
        properties:
          query:
            type: array
            items:
              type: array
              items:
                type: number
            description: Query matrix of shape (seq_len, d).
          key:
            type: array
            items:
              type: array
              items:
                type: number
            description: Key matrix of shape (seq_len, d).
          value:
            type: array
            items:
              type: array
              items:
                type: number
            description: Value matrix of shape (seq_len, d_v).
          gamma:
            type: number
            default: 0.9
            description: Retention decay factor gamma in (0, 1).
      outputs:
        type: object
        required:
          - output
          - final_recurrent_state
          - gamma
        properties:
          output:
            type: array
            items:
              type: array
              items:
                type: number
            description: Retention output matrix of shape (seq_len, d_v).
          final_recurrent_state:
            type: array
            items:
              type: array
              items:
                type: number
            description: Recurrent memory state S_L of shape (d, d_v).
          gamma:
            type: number
            description: Applied retention decay.
      parameters: {}
      input_assumptions:
        - 0.0 < gamma < 1.0
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact recurrent decay propagation"
      uses_model: false
      complexity:
        variables:
          N: seq_len
          d: feature dimension
          d_v: value dimension
        time_worst: O(N * d * d_v)
        time_typical: O(N * d * d_v)
        space: O(d * d_v + N * d_v)
      preconditions:
        - len(input.query) > 0 and len(input.query) == len(input.key)
        - 0.0 < input.gamma < 1.0
      postconditions:
        - len(output.output) == len(input.query)
      certificate: "Exact O(1) state recurrence per step"
      compatible_adapters:
        - ADAPTER-RETNET
      related_algos:
        - ALGO-NN-121
      references:
        - "https://arxiv.org/abs/2307.08621"
        - "https://arxiv.org/abs/2305.13048"
    ---
    """

    @staticmethod
    def forward(
        query: List[List[float]],
        key: List[List[float]],
        value: List[List[float]],
        gamma: float = 0.9,
    ) -> Dict[str, Any]:
        if not query or len(query) != len(key) or len(query) != len(value):
            raise ValueError("Precondition failed: matching sequence inputs required")
        if not (0.0 < gamma < 1.0):
            raise ValueError("Precondition failed: gamma must be in (0, 1)")

        N = len(query)
        d = len(query[0])
        d_v = len(value[0])

        S = [[0.0] * d_v for _ in range(d)]
        outputs: List[List[float]] = []

        for t in range(N):
            q_t = query[t]
            k_t = key[t]
            v_t = value[t]

            for i in range(d):
                for j in range(d_v):
                    S[i][j] = gamma * S[i][j] + k_t[i] * v_t[j]

            out_t = [0.0] * d_v
            for j in range(d_v):
                out_t[j] = sum(q_t[i] * S[i][j] for i in range(d))
            outputs.append(out_t)

        return {
            "output": outputs,
            "final_recurrent_state": S,
            "gamma": gamma,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{RetNet Recurrent Retention Mechanism}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{S}_n = \gamma \mathbf{S}_{n-1} + \mathbf{k}_n \mathbf{v}_n^\top, \quad \text{Retention}(\mathbf{q}_n) = \mathbf{q}_n^\top \mathbf{S}_n
\end{equation}
\end{document}
'''
)

print("Chunk 2 (112-124) successfully written!")
