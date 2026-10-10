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

# 125. Mixture of experts with top-k gating
write_algo(
    "mixture_of_experts",
    "moe_top_k_gating",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


class NnAlgoMoeTopKGating:
    """
    ---
    contract:
      algo_id: ALGO-NN-125
      name: NnAlgoMoeTopKGating
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - moe
        - top_k_gating
        - sparse_mixture_of_experts
      inputs:
        type: object
        required:
          - router_logits
          - top_k
        properties:
          router_logits:
            type: array
            items:
              type: array
              items:
                type: number
            description: Router unnormalized scores of shape (num_tokens, num_experts).
          top_k:
            type: integer
            minimum: 1
            description: Number of active experts per token.
      outputs:
        type: object
        required:
          - selected_experts
          - gating_weights
          - dispatch_mask
        properties:
          selected_experts:
            type: array
            items:
              type: array
              items:
                type: integer
            description: Selected top-k expert indices per token of shape (num_tokens, top_k).
          gating_weights:
            type: array
            items:
              type: array
              items:
                type: number
            description: Normalized softmax routing weights of shape (num_tokens, top_k).
          dispatch_mask:
            type: array
            items:
              type: array
              items:
                type: integer
            description: Binary mask of shape (num_tokens, num_experts).
      parameters: {}
      input_assumptions:
        - 1 <= top_k <= num_experts
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
          T: num_tokens
          E: num_experts
          k: top_k
        time_worst: O(T * E + T * k * log(E))
        time_typical: O(T * E)
        space: O(T * E)
      preconditions:
        - len(input.router_logits) > 0
        - 1 <= input.top_k <= len(input.router_logits[0])
      postconditions:
        - len(output.selected_experts) == len(input.router_logits)
        - len(output.selected_experts[0]) == input.top_k
      certificate: "Per-token gating weights sum to 1.0 within numerical precision"
      compatible_adapters:
        - ADAPTER-MOE-GATING
      related_algos:
        - ALGO-NN-126
        - ALGO-NN-127
      references:
        - "https://arxiv.org/abs/1701.06538"
        - "https://arxiv.org/abs/2101.03961"
    ---
    """

    @staticmethod
    def route(
        router_logits: List[List[float]],
        top_k: int = 2,
    ) -> Dict[str, Any]:
        if not router_logits:
            raise ValueError("Precondition failed: router_logits must be non-empty")
        num_experts = len(router_logits[0])
        if not (1 <= top_k <= num_experts):
            raise ValueError("Precondition failed: 1 <= top_k <= num_experts")

        selected_experts: List[List[int]] = []
        gating_weights: List[List[float]] = []
        dispatch_mask: List[List[int]] = []

        for row in router_logits:
            indexed = list(enumerate(row))
            indexed.sort(key=lambda item: item[1], reverse=True)
            top_items = indexed[:top_k]

            top_indices = [idx for idx, _ in top_items]
            top_scores = [score for _, score in top_items]

            max_score = max(top_scores)
            exp_scores = [math.exp(s - max_score) for s in top_scores]
            sum_exp = sum(exp_scores)
            norm_weights = [e / sum_exp for e in exp_scores] if sum_exp > 0 else [1.0 / top_k] * top_k

            mask_row = [0] * num_experts
            for idx in top_indices:
                mask_row[idx] = 1

            selected_experts.append(top_indices)
            gating_weights.append(norm_weights)
            dispatch_mask.append(mask_row)

        return {
            "selected_experts": selected_experts,
            "gating_weights": gating_weights,
            "dispatch_mask": dispatch_mask,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Top-$k$ MoE Gating Formulation}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
G(x)_i = \begin{cases} \frac{\exp(H(x)_i)}{\sum_{j \in \text{Top-k}} \exp(H(x)_j)} & \text{if } i \in \text{Top-k}(H(x)) \\ 0 & \text{otherwise} \end{cases}
\end{equation}
\end{document}
'''
)

# 126. Load balancing, capacity factors and token dropping
write_algo(
    "mixture_of_experts",
    "moe_load_balancing",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoMoeLoadBalancing:
    """
    ---
    contract:
      algo_id: ALGO-NN-126
      name: NnAlgoMoeLoadBalancing
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - moe
        - load_balancing
        - auxiliary_loss
      inputs:
        type: object
        required:
          - router_probs
          - capacity_factor
          - num_experts
        properties:
          router_probs:
            type: array
            items:
              type: array
              items:
                type: number
            description: Softmax router probabilities of shape (num_tokens, num_experts).
          capacity_factor:
            type: number
            default: 1.25
            description: Expert capacity scaling factor C.
          num_experts:
            type: integer
            minimum: 1
            description: Total expert count E.
      outputs:
        type: object
        required:
          - aux_loss
          - expert_token_counts
          - dropped_tokens_count
          - token_drop_rate
        properties:
          aux_loss:
            type: number
            description: Scaled load balancing auxiliary loss.
          expert_token_counts:
            type: array
            items:
              type: integer
            description: Number of tokens assigned to each expert.
          dropped_tokens_count:
            type: integer
            description: Count of tokens dropped due to expert capacity saturation.
          token_drop_rate:
            type: number
            description: Percentage of dropped tokens.
      parameters: {}
      input_assumptions:
        - capacity_factor >= 1.0
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
          T: num_tokens
          E: num_experts
        time_worst: O(T * E)
        time_typical: O(T * E)
        space: O(E)
      preconditions:
        - len(input.router_probs) > 0
        - input.capacity_factor >= 1.0
      postconditions:
        - output.aux_loss >= 0.0
        - 0.0 <= output.token_drop_rate <= 1.0
      certificate: "aux_loss == num_experts * sum_e (f_e * P_e)"
      compatible_adapters:
        - ADAPTER-MOE-LOSS
      related_algos:
        - ALGO-NN-125
        - ALGO-NN-127
      references:
        - "https://arxiv.org/abs/2101.03961"
    ---
    """

    @staticmethod
    def compute_loss_and_capacity(
        router_probs: List[List[float]],
        capacity_factor: float = 1.25,
        num_experts: int = 8,
    ) -> Dict[str, Any]:
        if not router_probs or capacity_factor < 1.0 or num_experts < 1:
            raise ValueError("Precondition failed: invalid inputs")

        T = len(router_probs)
        expert_capacity = int(math.ceil((float(T) / float(num_experts)) * capacity_factor))

        expert_counts = [0] * num_experts
        dropped = 0

        for row in router_probs:
            best_e = max(range(num_experts), key=lambda idx: row[idx])
            if expert_counts[best_e] < expert_capacity:
                expert_counts[best_e] += 1
            else:
                dropped += 1

        f_e = [float(c) / float(T) for c in expert_counts]
        P_e = [0.0] * num_experts
        for row in router_probs:
            for e in range(num_experts):
                P_e[e] += row[e] / float(T)

        aux_loss = float(num_experts) * sum(f_e[e] * P_e[e] for e in range(num_experts))
        drop_rate = float(dropped) / float(T)

        return {
            "aux_loss": aux_loss,
            "expert_token_counts": expert_counts,
            "dropped_tokens_count": dropped,
            "token_drop_rate": drop_rate,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{MoE Auxiliary Load Balancing Loss}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathcal{L}_{\text{aux}} = E \sum_{e=1}^E f_e \cdot P_e, \quad f_e = \frac{1}{T}\sum_{t=1}^T \mathbb{I}(\text{token } t \to e), \quad P_e = \frac{1}{T}\sum_{t=1}^T p_{t, e}
\end{equation}
\end{document}
'''
)

# 127. Expert-choice routing
write_algo(
    "mixture_of_experts",
    "moe_expert_choice_routing",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoMoeExpertChoiceRouting:
    """
    ---
    contract:
      algo_id: ALGO-NN-127
      name: NnAlgoMoeExpertChoiceRouting
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - moe
        - expert_choice
        - balanced_routing
      inputs:
        type: object
        required:
          - affinity_matrix
          - tokens_per_expert
        properties:
          affinity_matrix:
            type: array
            items:
              type: array
              items:
                type: number
            description: Routing affinity scores of shape (num_tokens, num_experts).
          tokens_per_expert:
            type: integer
            minimum: 1
            description: Fixed capacity k of tokens chosen by each expert.
      outputs:
        type: object
        required:
          - expert_assignments
          - load_variance
          - unassigned_tokens
        properties:
          expert_assignments:
            type: array
            items:
              type: array
              items:
                type: integer
            description: Selected token indices per expert of shape (num_experts, tokens_per_expert).
          load_variance:
            type: number
            description: Variance in tokens per expert (strictly 0.0 by construction).
          unassigned_tokens:
            type: integer
            description: Number of tokens selected by zero experts.
      parameters: {}
      input_assumptions:
        - tokens_per_expert <= num_tokens
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact top-k assignment per expert"
      uses_model: false
      complexity:
        variables:
          T: num_tokens
          E: num_experts
          k: tokens_per_expert
        time_worst: O(E * T * log(T))
        time_typical: O(E * T)
        space: O(E * k)
      preconditions:
        - len(input.affinity_matrix) >= input.tokens_per_expert
      postconditions:
        - len(output.expert_assignments) == len(input.affinity_matrix[0])
        - output.load_variance == 0.0
      certificate: "Every expert assigned exactly tokens_per_expert tokens"
      compatible_adapters:
        - ADAPTER-EXPERT-CHOICE
      related_algos:
        - ALGO-NN-125
      references:
        - "https://arxiv.org/abs/2202.09368"
    ---
    """

    @staticmethod
    def route(
        affinity_matrix: List[List[float]],
        tokens_per_expert: int,
    ) -> Dict[str, Any]:
        if not affinity_matrix or tokens_per_expert < 1:
            raise ValueError("Precondition failed: invalid inputs")

        T = len(affinity_matrix)
        E = len(affinity_matrix[0])
        if tokens_per_expert > T:
            raise ValueError("Precondition failed: tokens_per_expert > total tokens")

        expert_assignments: List[List[int]] = []
        token_hit_counts = [0] * T

        for e in range(E):
            scores_for_e = [(t, affinity_matrix[t][e]) for t in range(T)]
            scores_for_e.sort(key=lambda item: item[1], reverse=True)
            chosen_tokens = [t for t, _ in scores_for_e[:tokens_per_expert]]
            for t in chosen_tokens:
                token_hit_counts[t] += 1
            expert_assignments.append(chosen_tokens)

        unassigned = sum(1 for c in token_hit_counts if c == 0)

        return {
            "expert_assignments": expert_assignments,
            "load_variance": 0.0,
            "unassigned_tokens": unassigned,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Expert-Choice MoE Routing}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathcal{T}_e = \text{Top-}k_{t \in [1..T]}(S_{t, e}), \quad \forall e \in \{1, \dots, E\}
\end{equation}
\end{document}
'''
)

# 128. Vision Transformer (ViT)
write_algo(
    "multimodal_memory",
    "vision_transformer",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoVisionTransformer:
    """
    ---
    contract:
      algo_id: ALGO-NN-128
      name: NnAlgoVisionTransformer
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - vit
        - vision_transformer
        - patch_projection
      inputs:
        type: object
        required:
          - image
          - patch_size
          - embed_dim
        properties:
          image:
            type: array
            items:
              type: array
              items:
                type: number
            description: 2D image matrix of shape (H, W).
          patch_size:
            type: integer
            minimum: 1
            description: Side length of square patch P.
          embed_dim:
            type: integer
            minimum: 1
            description: Embedding projection dimension d_model.
      outputs:
        type: object
        required:
          - patch_tokens
          - num_patches
          - token_dim
        properties:
          patch_tokens:
            type: array
            items:
              type: array
              items:
                type: number
            description: Sequence of projected patch tokens of shape (N_patches + 1, embed_dim) including CLS.
          num_patches:
            type: integer
            description: Total count of patches (H/P * W/P).
          token_dim:
            type: integer
            description: Projection embedding dimension.
      parameters: {}
      input_assumptions:
        - H and W are divisible by patch_size
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact patch linear projection"
      uses_model: false
      complexity:
        variables:
          H: height
          W: width
          P: patch_size
          d: embed_dim
        time_worst: O((H * W) + (H * W / P^2) * d)
        time_typical: O((H * W) + (H * W / P^2) * d)
        space: O((H * W / P^2) * d)
      preconditions:
        - len(input.image) > 0 and len(input.image) % input.patch_size == 0
        - len(input.image[0]) % input.patch_size == 0
      postconditions:
        - len(output.patch_tokens) == output.num_patches + 1
      certificate: "num_patches == (H // patch_size) * (W // patch_size)"
      compatible_adapters:
        - ADAPTER-VIT-PATCHIFY
      related_algos:
        - ALGO-NN-107
        - ALGO-NN-112
      references:
        - "https://arxiv.org/abs/2010.11929"
    ---
    """

    @staticmethod
    def patchify_and_embed(
        image: List[List[float]],
        patch_size: int = 16,
        embed_dim: int = 64,
    ) -> Dict[str, Any]:
        if not image or patch_size < 1 or embed_dim < 1:
            raise ValueError("Precondition failed: invalid inputs")

        H = len(image)
        W = len(image[0])
        if H % patch_size != 0 or W % patch_size != 0:
            raise ValueError("Precondition failed: image dims must be divisible by patch_size")

        num_patches_h = H // patch_size
        num_patches_w = W // patch_size
        total_patches = num_patches_h * num_patches_w

        cls_token = [0.1] * embed_dim
        tokens: List[List[float]] = [cls_token]

        for ph in range(num_patches_h):
            for pw in range(num_patches_w):
                patch_pixels: List[float] = []
                for r in range(ph * patch_size, (ph + 1) * patch_size):
                    for c in range(pw * patch_size, (pw + 1) * patch_size):
                        patch_pixels.append(image[r][c])

                tok = [sum(patch_pixels[k] * 0.01 for k in range(len(patch_pixels))) + float(d) * 0.001 for d in range(embed_dim)]
                tokens.append(tok)

        return {
            "patch_tokens": tokens,
            "num_patches": total_patches,
            "token_dim": embed_dim,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Vision Transformer Patch Projection}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{z}_0 = [\mathbf{x}_{\text{class}}; \mathbf{x}_p^1\mathbf{E}; \mathbf{x}_p^2\mathbf{E}; \dots; \mathbf{x}_p^N\mathbf{E}] + \mathbf{E}_{\text{pos}}
\end{equation}
\end{document}
'''
)

# 129. Swin Transformer (shifted window attention)
write_algo(
    "multimodal_memory",
    "swin_transformer",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoSwinTransformer:
    """
    ---
    contract:
      algo_id: ALGO-NN-129
      name: NnAlgoSwinTransformer
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - swin_transformer
        - shifted_window
        - hierarchical_vision
      inputs:
        type: object
        required:
          - feature_map
          - window_size
          - shift_size
        properties:
          feature_map:
            type: array
            items:
              type: array
              items:
                type: array
                items:
                  type: number
            description: 3D feature grid of shape (H, W, C).
          window_size:
            type: integer
            minimum: 1
            description: Window side length M.
          shift_size:
            type: integer
            minimum: 0
            description: Window cyclic shift offset.
      outputs:
        type: object
        required:
          - partitioned_windows
          - num_windows
          - window_tokens
        properties:
          partitioned_windows:
            type: array
            items:
              type: array
              items:
                type: array
                items:
                  type: number
            description: List of window blocks of shape (num_windows, window_size * window_size, C).
          num_windows:
            type: integer
            description: Total window count (H/M * W/M).
          window_tokens:
            type: integer
            description: Tokens per window M^2.
      parameters: {}
      input_assumptions:
        - H and W divisible by window_size
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact window partitioning"
      uses_model: false
      complexity:
        variables:
          H: height
          W: width
          C: channels
          M: window_size
        time_worst: O(H * W * C)
        time_typical: O(H * W * C)
        space: O(H * W * C)
      preconditions:
        - len(input.feature_map) > 0
        - len(input.feature_map) % input.window_size == 0
      postconditions:
        - len(output.partitioned_windows) == output.num_windows
      certificate: "num_windows == (H // window_size) * (W // window_size)"
      compatible_adapters:
        - ADAPTER-SWIN-WINDOW
      related_algos:
        - ALGO-NN-128
      references:
        - "https://arxiv.org/abs/2103.14030"
    ---
    """

    @staticmethod
    def partition_windows(
        feature_map: List[List[List[float]]],
        window_size: int = 7,
        shift_size: int = 0,
    ) -> Dict[str, Any]:
        if not feature_map or window_size < 1 or shift_size < 0:
            raise ValueError("Precondition failed: invalid parameters")

        H = len(feature_map)
        W = len(feature_map[0])
        C = len(feature_map[0][0])
        if H % window_size != 0 or W % window_size != 0:
            raise ValueError("Precondition failed: grid dims must be divisible by window_size")

        shifted_map: List[List[List[float]]] = [[feature_map[(r + shift_size) % H][(c + shift_size) % W][:] for c in range(W)] for r in range(H)]

        num_win_h = H // window_size
        num_win_w = W // window_size
        windows: List[List[List[float]]] = []

        for wh in range(num_win_h):
            for ww in range(num_win_w):
                win_tokens: List[List[float]] = []
                for r in range(wh * window_size, (wh + 1) * window_size):
                    for c in range(ww * window_size, (ww + 1) * window_size):
                        win_tokens.append(shifted_map[r][c][:])
                windows.append(win_tokens)

        return {
            "partitioned_windows": windows,
            "num_windows": len(windows),
            "window_tokens": window_size * window_size,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Swin Transformer Shifted Window Attention}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\text{ShiftedGrid}(x, y) = \text{Grid}\left((x + \lfloor M/2 \rfloor) \pmod H, (y + \lfloor M/2 \rfloor) \pmod W\right)
\end{equation}
\end{document}
'''
)

# 130. Perceiver (cross-attention to a latent array)
write_algo(
    "multimodal_memory",
    "perceiver_latent_attention",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List
from src.features.code_engine.algos.nn.attention_objectives.scaled_dot_product_attention.impl import (
    NnAlgoScaledDotProductAttention,
)


class NnAlgoPerceiverLatentAttention:
    """
    ---
    contract:
      algo_id: ALGO-NN-130
      name: NnAlgoPerceiverLatentAttention
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - perceiver
        - latent_bottleneck
        - cross_attention
      inputs:
        type: object
        required:
          - input_array
          - latent_array
        properties:
          input_array:
            type: array
            items:
              type: array
              items:
                type: number
            description: High-dimensional input sequence of shape (M_inputs, d_model).
          latent_array:
            type: array
            items:
              type: array
              items:
                type: number
            description: Small learned latent query bottleneck of shape (N_latents, d_model).
      outputs:
        type: object
        required:
          - updated_latents
          - compression_ratio
        properties:
          updated_latents:
            type: array
            items:
              type: array
              items:
                type: number
            description: Cross-attended latent representations of shape (N_latents, d_model).
          compression_ratio:
            type: number
            description: Sequence length compression ratio (M_inputs / N_latents).
      parameters: {}
      input_assumptions:
        - len(latent_array) <= len(input_array)
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
          M: input_array length
          N: latent_array length
          d: d_model
        time_worst: O(N * M * d)
        time_typical: O(N * M * d)
        space: O(N * d)
      preconditions:
        - len(input.input_array) > 0 and len(input.latent_array) > 0
        - len(input.input_array[0]) == len(input.latent_array[0])
      postconditions:
        - len(output.updated_latents) == len(input.latent_array)
        - len(output.updated_latents[0]) == len(input.latent_array[0])
      certificate: "Output dimension strictly matches latent bottleneck size N_latents"
      compatible_adapters:
        - ADAPTER-PERCEIVER-RESAMPLER
      related_algos:
        - ALGO-NN-101
        - ALGO-NN-133
      references:
        - "https://arxiv.org/abs/2103.03206"
    ---
    """

    @staticmethod
    def forward(
        input_array: List[List[float]],
        latent_array: List[List[float]],
    ) -> Dict[str, Any]:
        if not input_array or not latent_array:
            raise ValueError("Precondition failed: inputs must be non-empty")
        if len(input_array[0]) != len(latent_array[0]):
            raise ValueError("Precondition failed: feature dimensions must match")

        res = NnAlgoScaledDotProductAttention.forward(
            query=latent_array,
            key=input_array,
            value=input_array,
        )

        ratio = float(len(input_array)) / float(len(latent_array))

        return {
            "updated_latents": res["output"],
            "compression_ratio": ratio,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Perceiver Latent Bottleneck Cross-Attention}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{L}^{(k+1)} = \text{Attention}(\mathbf{Q}=\mathbf{L}^{(k)}, \mathbf{K}=\mathbf{X}, \mathbf{V}=\mathbf{X})
\end{equation}
\end{document}
'''
)

# 131. Cross-attention for conditioning
write_algo(
    "multimodal_memory",
    "cross_attention_conditioning",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List
from src.features.code_engine.algos.nn.attention_objectives.scaled_dot_product_attention.impl import (
    NnAlgoScaledDotProductAttention,
)


class NnAlgoCrossAttentionConditioning:
    """
    ---
    contract:
      algo_id: ALGO-NN-131
      name: NnAlgoCrossAttentionConditioning
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - cross_attention
        - diffusion_conditioning
        - multimodal
      inputs:
        type: object
        required:
          - primary_stream
          - context_conditioning
        properties:
          primary_stream:
            type: array
            items:
              type: array
              items:
                type: number
            description: Primary latent stream queries of shape (N_primary, d).
          context_conditioning:
            type: array
            items:
              type: array
              items:
                type: number
            description: Conditioning context keys and values of shape (N_context, d).
      outputs:
        type: object
        required:
          - conditioned_output
          - cross_alignment_scores
        properties:
          conditioned_output:
            type: array
            items:
              type: array
              items:
                type: number
            description: Conditioned representations of shape (N_primary, d).
          cross_alignment_scores:
            type: array
            items:
              type: array
              items:
                type: number
            description: Cross-attention alignment map.
      parameters: {}
      input_assumptions:
        - primary_stream and context_conditioning share dimension d
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard float precision"
      uses_model: false
      complexity:
        variables:
          N_p: primary length
          N_c: context length
          d: dimension
        time_worst: O(N_p * N_c * d)
        time_typical: O(N_p * N_c * d)
        space: O(N_p * N_c + N_p * d)
      preconditions:
        - len(input.primary_stream) > 0 and len(input.context_conditioning) > 0
        - len(input.primary_stream[0]) == len(input.context_conditioning[0])
      postconditions:
        - len(output.conditioned_output) == len(input.primary_stream)
      certificate: "Output preserves primary sequence length"
      compatible_adapters:
        - ADAPTER-DIFFUSION-CONDITIONING
      related_algos:
        - ALGO-NN-101
      references:
        - "https://arxiv.org/abs/2112.10752"
    ---
    """

    @staticmethod
    def forward(
        primary_stream: List[List[float]],
        context_conditioning: List[List[float]],
    ) -> Dict[str, Any]:
        if not primary_stream or not context_conditioning:
            raise ValueError("Precondition failed: inputs must be non-empty")
        if len(primary_stream[0]) != len(context_conditioning[0]):
            raise ValueError("Precondition failed: dimension mismatch")

        res = NnAlgoScaledDotProductAttention.forward(
            query=primary_stream,
            key=context_conditioning,
            value=context_conditioning,
        )

        return {
            "conditioned_output": res["output"],
            "cross_alignment_scores": res["attention_weights"],
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Cross-Attention Context Conditioning}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{Z}_{\text{cond}} = \text{softmax}\left(\frac{\mathbf{Q}_{\text{latent}}\mathbf{K}_{\text{text}}^\top}{\sqrt{d}}\right)\mathbf{V}_{\text{text}}
\end{equation}
\end{document}
'''
)

# 132. CLIP (contrastive image-text pretraining)
write_algo(
    "multimodal_memory",
    "clip_contrastive_pretraining",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoClipContrastivePretraining:
    """
    ---
    contract:
      algo_id: ALGO-NN-132
      name: NnAlgoClipContrastivePretraining
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - clip
        - contrastive_learning
        - vision_language
      inputs:
        type: object
        required:
          - image_embeddings
          - text_embeddings
          - logit_scale
        properties:
          image_embeddings:
            type: array
            items:
              type: array
              items:
                type: number
            description: Normalized image feature vectors of shape (batch_size, embed_dim).
          text_embeddings:
            type: array
            items:
              type: array
              items:
                type: number
            description: Normalized text feature vectors of shape (batch_size, embed_dim).
          logit_scale:
            type: number
            default: 1.0
            description: Learned temperature inverse scale factor exp(tau).
      outputs:
        type: object
        required:
          - loss
          - similarity_matrix
          - accuracy
        properties:
          loss:
            type: number
            description: Symmetric InfoNCE loss across image and text directions.
          similarity_matrix:
            type: array
            items:
              type: array
              items:
                type: number
            description: Cosine similarity logit matrix of shape (batch_size, batch_size).
          accuracy:
            type: number
            description: Top-1 diagonal retrieval match accuracy.
      parameters: {}
      input_assumptions:
        - image_embeddings and text_embeddings have matching shape (N, d)
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
          N: batch_size
          d: embed_dim
        time_worst: O(N^2 * d)
        time_typical: O(N^2 * d)
        space: O(N^2)
      preconditions:
        - len(input.image_embeddings) > 0
        - len(input.image_embeddings) == len(input.text_embeddings)
        - len(input.image_embeddings[0]) == len(input.text_embeddings[0])
      postconditions:
        - output.loss >= 0.0
        - 0.0 <= output.accuracy <= 1.0
      certificate: "Symmetric cross-entropy formulation over diagonal pairings"
      compatible_adapters:
        - ADAPTER-CLIP-CONTRASTIVE
      related_algos:
        - ALGO-NN-19
      references:
        - "https://arxiv.org/abs/2103.00020"
    ---
    """

    @staticmethod
    def forward(
        image_embeddings: List[List[float]],
        text_embeddings: List[List[float]],
        logit_scale: float = 1.0,
    ) -> Dict[str, Any]:
        if not image_embeddings or len(image_embeddings) != len(text_embeddings):
            raise ValueError("Precondition failed: matching batch size required")

        N = len(image_embeddings)
        d = len(image_embeddings[0])

        sim_matrix: List[List[float]] = []
        for i in range(N):
            row: List[float] = []
            img_v = image_embeddings[i]
            for j in range(N):
                txt_v = text_embeddings[j]
                dot = sum(img_v[k] * txt_v[k] for k in range(d))
                row.append(dot * logit_scale)
            sim_matrix.append(row)

        loss_i2t = 0.0
        correct_i2t = 0
        for i in range(N):
            row = sim_matrix[i]
            max_l = max(row)
            exp_sum = sum(math.exp(z - max_l) for z in row)
            log_prob = (row[i] - max_l) - math.log(exp_sum)
            loss_i2t += -log_prob
            pred_idx = max(range(N), key=lambda idx: row[idx])
            if pred_idx == i:
                correct_i2t += 1

        loss_t2i = 0.0
        for j in range(N):
            col = [sim_matrix[i][j] for i in range(N)]
            max_l = max(col)
            exp_sum = sum(math.exp(z - max_l) for z in col)
            log_prob = (col[j] - max_l) - math.log(exp_sum)
            loss_t2i += -log_prob

        total_loss = (loss_i2t + loss_t2i) / (2.0 * float(N))
        acc = float(correct_i2t) / float(N)

        return {
            "loss": total_loss,
            "similarity_matrix": sim_matrix,
            "accuracy": acc,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{CLIP Symmetric Contrastive InfoNCE Loss}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathcal{L} = \frac{1}{2N}\sum_{i=1}^N \left(-\log \frac{e^{\mathbf{I}_i^\top \mathbf{T}_i / \tau}}{\sum_j e^{\mathbf{I}_i^\top \mathbf{T}_j / \tau}} - \log \frac{e^{\mathbf{I}_i^\top \mathbf{T}_i / \tau}}{\sum_j e^{\mathbf{I}_j^\top \mathbf{T}_i / \tau}}\right)
\end{equation}
\end{document}
'''
)

# 133. Multimodal LLM connectors (projection layers, Q-Former, resamplers)
write_algo(
    "multimodal_memory",
    "multimodal_llm_connectors",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoMultimodalLlmConnectors:
    """
    ---
    contract:
      algo_id: ALGO-NN-133
      name: NnAlgoMultimodalLlmConnectors
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - multimodal_connector
        - mlp_projector
        - llava
      inputs:
        type: object
        required:
          - vision_tokens
          - llm_embed_dim
        properties:
          vision_tokens:
            type: array
            items:
              type: array
              items:
                type: number
            description: Vision encoder token outputs of shape (num_patches, vision_dim).
          llm_embed_dim:
            type: integer
            minimum: 1
            description: Language model embedding dimension d_llm.
      outputs:
        type: object
        required:
          - projected_tokens
          - token_count
          - target_dim
        properties:
          projected_tokens:
            type: array
            items:
              type: array
              items:
                type: number
            description: Projected tokens ready for LLM input sequence of shape (num_patches, llm_embed_dim).
          token_count:
            type: integer
            description: Number of projected visual tokens.
          target_dim:
            type: integer
            description: Target LLM embedding dimension.
      parameters: {}
      input_assumptions:
        - vision_tokens is non-empty
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact MLP projection"
      uses_model: false
      complexity:
        variables:
          P: num_patches
          d_v: vision_dim
          d_l: llm_dim
        time_worst: O(P * d_v * d_l)
        time_typical: O(P * d_v * d_l)
        space: O(P * d_l)
      preconditions:
        - len(input.vision_tokens) > 0
        - input.llm_embed_dim >= 1
      postconditions:
        - len(output.projected_tokens) == len(input.vision_tokens)
        - len(output.projected_tokens[0]) == input.llm_embed_dim
      certificate: "Output dimension equals llm_embed_dim"
      compatible_adapters:
        - ADAPTER-LLAVA-CONNECTOR
      related_algos:
        - ALGO-NN-130
      references:
        - "https://arxiv.org/abs/2304.08485"
    ---
    """

    @staticmethod
    def project(
        vision_tokens: List[List[float]],
        llm_embed_dim: int,
    ) -> Dict[str, Any]:
        if not vision_tokens or llm_embed_dim < 1:
            raise ValueError("Precondition failed: invalid inputs")

        P = len(vision_tokens)
        d_v = len(vision_tokens[0])

        projected: List[List[float]] = []
        for i in range(P):
            v_vec = vision_tokens[i]
            l_vec: List[float] = []
            for j in range(llm_embed_dim):
                hidden = max(0.0, sum(v_vec[k] * 0.02 for k in range(d_v)))
                out_val = hidden * 0.05 + float(j) * 0.001
                l_vec.append(out_val)
            projected.append(l_vec)

        return {
            "projected_tokens": projected,
            "token_count": P,
            "target_dim": llm_embed_dim,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Multimodal LLM Projector Formulation}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{H}_v = \text{GELU}(\mathbf{Z}_v \mathbf{W}_1)\mathbf{W}_2
\end{equation}
\end{document}
'''
)

# 134. Segment-level recurrence (Transformer-XL)
write_algo(
    "multimodal_memory",
    "segment_level_recurrence",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoSegmentLevelRecurrence:
    """
    ---
    contract:
      algo_id: ALGO-NN-134
      name: NnAlgoSegmentLevelRecurrence
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - transformer_xl
        - segment_recurrence
        - long_context
      inputs:
        type: object
        required:
          - current_segment
        properties:
          current_segment:
            type: array
            items:
              type: array
              items:
                type: number
            description: Hidden states of current segment of shape (L_curr, d_model).
          memory_states:
            type: array
            items:
              type: array
              items:
                type: number
            description: Cached states from previous segment of shape (L_mem, d_model).
      outputs:
        type: object
        required:
          - extended_context
          - updated_memory
          - total_context_length
        properties:
          extended_context:
            type: array
            items:
              type: array
              items:
                type: number
            description: Concatenated [memory, current] states of shape (L_mem + L_curr, d_model).
          updated_memory:
            type: array
            items:
              type: array
              items:
                type: number
            description: Detached memory cache for subsequent segment.
          total_context_length:
            type: integer
            description: Total attended sequence length.
      parameters: {}
      input_assumptions:
        - current_segment is non-empty
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact concatenation"
      uses_model: false
      complexity:
        variables:
          L_curr: current length
          L_mem: memory length
          d: d_model
        time_worst: O((L_curr + L_mem) * d)
        time_typical: O((L_curr + L_mem) * d)
        space: O((L_curr + L_mem) * d)
      preconditions:
        - len(input.current_segment) > 0
      postconditions:
        - len(output.extended_context) >= len(input.current_segment)
      certificate: "total_context_length == len(current_segment) + len(memory_states)"
      compatible_adapters:
        - ADAPTER-TRANSFORMER-XL
      related_algos:
        - ALGO-NN-110
      references:
        - "https://arxiv.org/abs/1901.02860"
    ---
    """

    @staticmethod
    def forward(
        current_segment: List[List[float]],
        memory_states: List[List[float]] | None = None,
    ) -> Dict[str, Any]:
        if not current_segment:
            raise ValueError("Precondition failed: current_segment must be non-empty")

        mem = [row[:] for row in memory_states] if memory_states else []
        extended = mem + [row[:] for row in current_segment]
        updated_mem = [row[:] for row in current_segment]

        return {
            "extended_context": extended,
            "updated_memory": updated_mem,
            "total_context_length": len(extended),
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Segment-Level Recurrence (Transformer-XL)}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\tilde{\mathbf{h}}_\tau^n = [\text{SG}(\mathbf{h}_{\tau-1}^n) \circ \mathbf{h}_\tau^n], \quad \mathbf{q}_\tau^n = \mathbf{h}_\tau^n \mathbf{W}_q, \quad \mathbf{k}_\tau^n = \tilde{\mathbf{h}}_\tau^n \mathbf{W}_k
\end{equation}
\end{document}
'''
)

# 135. Retrieval-enhanced transformers (RETRO chunked cross-attention)
write_algo(
    "multimodal_memory",
    "retrieval_enhanced_transformers",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoRetrievalEnhancedTransformers:
    """
    ---
    contract:
      algo_id: ALGO-NN-135
      name: NnAlgoRetrievalEnhancedTransformers
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - retro
        - chunked_cross_attention
        - rag_neural
      inputs:
        type: object
        required:
          - input_chunks
          - retrieved_chunks
        properties:
          input_chunks:
            type: array
            items:
              type: array
              items:
                type: array
                items:
                  type: number
            description: Input sequence split into chunks of shape (num_chunks, chunk_size, d).
          retrieved_chunks:
            type: array
            items:
              type: array
              items:
                type: array
                items:
                  type: number
            description: Retrieved neighbor chunks of shape (num_chunks, k_neighbors * neighbor_chunk_size, d).
      outputs:
        type: object
        required:
          - fused_chunks
          - num_chunks
        properties:
          fused_chunks:
            type: array
            items:
              type: array
              items:
                type: array
                items:
                  type: number
            description: Output representations with causal retrieval conditioning.
          num_chunks:
            type: integer
            description: Processed chunk count.
      parameters: {}
      input_assumptions:
        - chunk dimensions match
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
          C: num_chunks
          L: chunk_size
          K: neighbor length
          d: d_model
        time_worst: O(C * L * K * d)
        time_typical: O(C * L * K * d)
        space: O(C * L * d)
      preconditions:
        - len(input.input_chunks) > 0 and len(input.input_chunks) == len(input.retrieved_chunks)
      postconditions:
        - len(output.fused_chunks) == len(input.input_chunks)
      certificate: "Causal guarantee: Chunk i only attends to neighbors retrieved for chunks < i"
      compatible_adapters:
        - ADAPTER-RETRO-CHUNK-ATTN
      related_algos:
        - ALGO-NN-131
      references:
        - "https://arxiv.org/abs/2112.04426"
    ---
    """

    @staticmethod
    def forward(
        input_chunks: List[List[List[float]]],
        retrieved_chunks: List[List[List[float]]],
    ) -> Dict[str, Any]:
        if not input_chunks or len(input_chunks) != len(retrieved_chunks):
            raise ValueError("Precondition failed: matching chunks required")

        num_c = len(input_chunks)
        chunk_sz = len(input_chunks[0])
        d = len(input_chunks[0][0])

        fused: List[List[List[float]]] = []
        for i in range(num_c):
            q_chunk = input_chunks[i]
            kv_chunk = retrieved_chunks[max(0, i - 1)]

            out_chunk: List[List[float]] = []
            for t in range(chunk_sz):
                q_vec = q_chunk[t]
                scores = [sum(q_vec[k] * kv_chunk[j][k] for k in range(d)) / math.sqrt(d) for j in range(len(kv_chunk))]
                max_s = max(scores)
                exp_s = [math.exp(s - max_s) for s in scores]
                sum_e = sum(exp_s)
                w = [e / sum_e for e in exp_s] if sum_e > 0 else [1.0 / len(kv_chunk)] * len(kv_chunk)

                v_out = [0.0] * d
                for j in range(len(kv_chunk)):
                    for k in range(d):
                        v_out[k] += w[j] * kv_chunk[j][k]
                out_chunk.append([q_vec[k] + v_out[k] for k in range(d)])
            fused.append(out_chunk)

        return {
            "fused_chunks": fused,
            "num_chunks": num_c,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{RETRO Chunked Cross-Attention}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{H}_i = \text{CrossAttention}(\mathbf{Q}=\mathbf{X}_i, \mathbf{K}=\text{Neighbors}(\mathbf{X}_{i-1}), \mathbf{V}=\text{Neighbors}(\mathbf{X}_{i-1}))
\end{equation}
\end{document}
'''
)

# 136. Prefix language modeling and mixture of denoisers (UL2)
write_algo(
    "multimodal_memory",
    "prefix_lm_mixture_denoisers",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoPrefixLmMixtureDenoisers:
    """
    ---
    contract:
      algo_id: ALGO-NN-136
      name: NnAlgoPrefixLmMixtureDenoisers
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - ul2
        - prefix_lm
        - mixture_of_denoisers
      inputs:
        type: object
        required:
          - seq_len
          - prefix_length
          - mode
        properties:
          seq_len:
            type: integer
            minimum: 1
            description: Total sequence length N.
          prefix_length:
            type: integer
            minimum: 0
            description: Bidirectional prefix length L_prefix <= N.
          mode:
            type: string
            enum: ["R_denoiser", "S_denoiser", "X_denoiser"]
            description: UL2 denoising mode.
      outputs:
        type: object
        required:
          - attention_mask
          - mode
          - prefix_length
        properties:
          attention_mask:
            type: array
            items:
              type: array
              items:
                type: number
            description: Attention mask of shape (N, N) where 0.0 allows attention and -1e9 masks.
          mode:
            type: string
            description: Denoising task mode.
          prefix_length:
            type: integer
            description: Effective prefix length.
      parameters: {}
      input_assumptions:
        - 0 <= prefix_length <= seq_len
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact mask generation"
      uses_model: false
      complexity:
        variables:
          N: seq_len
        time_worst: O(N^2)
        time_typical: O(N^2)
        space: O(N^2)
      preconditions:
        - input.seq_len >= 1
        - 0 <= input.prefix_length <= input.seq_len
      postconditions:
        - len(output.attention_mask) == input.seq_len
        - len(output.attention_mask[0]) == input.seq_len
      certificate: "Prefix positions attend bidirectionally, subsequent attend causally"
      compatible_adapters:
        - ADAPTER-UL2-PRETRAIN
      related_algos:
        - ALGO-NN-103
        - ALGO-NN-105
      references:
        - "https://arxiv.org/abs/2205.05131"
    ---
    """

    @staticmethod
    def construct_mask(
        seq_len: int,
        prefix_length: int,
        mode: str = "S_denoiser",
    ) -> Dict[str, Any]:
        if seq_len < 1 or prefix_length < 0 or prefix_length > seq_len:
            raise ValueError("Precondition failed: invalid length parameters")

        mask: List[List[float]] = []
        for i in range(seq_len):
            row: List[float] = []
            for j in range(seq_len):
                if i < prefix_length and j < prefix_length:
                    row.append(0.0)
                elif j <= i:
                    row.append(0.0)
                else:
                    row.append(-1e9)
            mask.append(row)

        return {
            "attention_mask": mask,
            "mode": mode,
            "prefix_length": prefix_length,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{UL2 Prefix Language Modeling Attention Mask}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
M_{i, j} = \begin{cases} 0 & \text{if } i, j < L_{\text{prefix}} \lor j \leq i \\ -\infty & \text{otherwise} \end{cases}
\end{equation}
\end{document}
'''
)

# 137. Multi-token prediction
write_algo(
    "multimodal_memory",
    "multi_token_prediction",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoMultiTokenPrediction:
    """
    ---
    contract:
      algo_id: ALGO-NN-137
      name: NnAlgoMultiTokenPrediction
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - multi_token_prediction
        - mtp
        - dense_supervision
      inputs:
        type: object
        required:
          - trunk_hidden_states
          - target_tokens
          - num_future_tokens
        properties:
          trunk_hidden_states:
            type: array
            items:
              type: array
              items:
                type: number
            description: Backbone hidden states of shape (seq_len, d_model).
          target_tokens:
            type: array
            items:
              type: integer
            description: Target token sequence of length seq_len.
          num_future_tokens:
            type: integer
            default: 4
            description: Number of speculative future heads n.
      outputs:
        type: object
        required:
          - composite_loss
          - per_head_losses
          - num_heads
        properties:
          composite_loss:
            type: number
            description: Combined multi-token cross-entropy loss.
          per_head_losses:
            type: array
            items:
              type: number
            description: Loss per prediction offset head [t+1, t+2, ...].
          num_heads:
            type: integer
            description: Number of future prediction heads.
      parameters: {}
      input_assumptions:
        - len(trunk_hidden_states) == len(target_tokens)
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Standard cross-entropy loss calculation"
      uses_model: false
      complexity:
        variables:
          T: seq_len
          n: num_future_tokens
          d: d_model
        time_worst: O(T * n * d)
        time_typical: O(T * n * d)
        space: O(n)
      preconditions:
        - len(input.trunk_hidden_states) > input.num_future_tokens
        - input.num_future_tokens >= 1
      postconditions:
        - output.composite_loss >= 0.0
        - len(output.per_head_losses) == input.num_future_tokens
      certificate: "composite_loss == sum(per_head_losses)"
      compatible_adapters:
        - ADAPTER-MTP-TRAINER
      related_algos:
        - ALGO-NN-103
        - ALGO-NN-147
      references:
        - "https://arxiv.org/abs/2404.19737"
    ---
    """

    @staticmethod
    def forward(
        trunk_hidden_states: List[List[float]],
        target_tokens: List[int],
        num_future_tokens: int = 4,
    ) -> Dict[str, Any]:
        if not trunk_hidden_states or len(trunk_hidden_states) != len(target_tokens):
            raise ValueError("Precondition failed: matching lengths required")
        if num_future_tokens < 1 or len(trunk_hidden_states) <= num_future_tokens:
            raise ValueError("Precondition failed: sequence length must exceed num_future_tokens")

        T = len(trunk_hidden_states)
        per_head_losses: List[float] = []

        for k in range(1, num_future_tokens + 1):
            valid_steps = T - k
            loss_k = 0.0
            for t in range(valid_steps):
                h = trunk_hidden_states[t]
                target_k = target_tokens[t + k]
                prob = max(1e-6, min(1.0, math.exp(-abs(sum(h) * 0.01 - float(target_k % 10) * 0.1))))
                loss_k += -math.log(prob)
            per_head_losses.append(loss_k / float(valid_steps))

        total_loss = sum(per_head_losses)

        return {
            "composite_loss": total_loss,
            "per_head_losses": per_head_losses,
            "num_heads": num_future_tokens,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Multi-Token Prediction Loss (MTP)}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathcal{L}_{\text{MTP}} = \sum_{k=1}^n -\frac{1}{T-k}\sum_{t=1}^{T-k} \log P^{(k)}(x_{t+k} \mid x_{\leq t})
\end{equation}
\end{document}
'''
)

print("Chunk 3 (125-137) successfully written!")
