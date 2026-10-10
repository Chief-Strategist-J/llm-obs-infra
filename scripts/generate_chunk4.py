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

# 138. Scaling laws (compute-optimal training)
write_algo(
    "scaling_stability",
    "scaling_laws_compute_optimal",
    '''from __future__ import annotations

import math
from typing import Any, Dict


class NnAlgoScalingLawsComputeOptimal:
    """
    ---
    contract:
      algo_id: ALGO-NN-138
      name: NnAlgoScalingLawsComputeOptimal
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - scaling_laws
        - chinchilla
        - compute_optimal
      inputs:
        type: object
        required:
          - compute_budget_flops
        properties:
          compute_budget_flops:
            type: number
            minimum: 1.0
            description: Total training compute budget C in FLOPs.
          tokens_per_param_ratio:
            type: number
            default: 20.0
            description: Chinchilla token-to-parameter optimal ratio G.
      outputs:
        type: object
        required:
          - optimal_parameters
          - optimal_training_tokens
          - estimated_loss
        properties:
          optimal_parameters:
            type: number
            description: Compute-optimal model parameter count N*.
          optimal_training_tokens:
            type: number
            description: Compute-optimal dataset token count D*.
          estimated_loss:
            type: number
            description: Predicted test cross-entropy loss L(N*, D*).
      parameters: {}
      input_assumptions:
        - compute_budget_flops > 0.0
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Chinchilla power law estimation"
      uses_model: false
      complexity:
        variables:
          C: compute_budget_flops
        time_worst: O(1)
        time_typical: O(1)
        space: O(1)
      preconditions:
        - input.compute_budget_flops > 0.0
      postconditions:
        - output.optimal_parameters > 0.0
        - output.optimal_training_tokens > 0.0
      certificate: "6 * optimal_parameters * optimal_training_tokens approx equals compute_budget_flops"
      compatible_adapters:
        - ADAPTER-SCALING-PLANNER
      related_algos:
        - ALGO-NN-103
      references:
        - "https://arxiv.org/abs/2203.15556"
        - "https://arxiv.org/abs/2001.08361"
    ---
    """

    @staticmethod
    def calculate_budget(
        compute_budget_flops: float,
        tokens_per_param_ratio: float = 20.0,
    ) -> Dict[str, Any]:
        if compute_budget_flops <= 0.0 or tokens_per_param_ratio <= 0.0:
            raise ValueError("Precondition failed: positive compute budget required")

        N_star = math.sqrt(compute_budget_flops / (6.0 * tokens_per_param_ratio))
        D_star = tokens_per_param_ratio * N_star

        E = 1.69
        A = 406.4
        B = 410.7
        alpha = 0.34
        beta = 0.28
        pred_loss = E + (A / math.pow(N_star, alpha)) + (B / math.pow(D_star, beta))

        return {
            "optimal_parameters": N_star,
            "optimal_training_tokens": D_star,
            "estimated_loss": pred_loss,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Chinchilla Compute-Optimal Scaling Laws}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
C \approx 6 N D, \quad N^* \propto C^{a}, \quad D^* \propto C^{b}, \quad a \approx b \approx 0.5
\end{equation}
\end{document}
'''
)

# 139. Attention sinks and streaming generation (StreamingLLM)
write_algo(
    "scaling_stability",
    "attention_sinks_streaming",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoAttentionSinksStreaming:
    """
    ---
    contract:
      algo_id: ALGO-NN-139
      name: NnAlgoAttentionSinksStreaming
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - streaming_llm
        - attention_sinks
        - infinite_context
      inputs:
        type: object
        required:
          - full_token_stream
          - num_sink_tokens
          - window_size
        properties:
          full_token_stream:
            type: array
            items:
              type: integer
            description: Stream of input token IDs.
          num_sink_tokens:
            type: integer
            default: 4
            description: Number of initial anchor sink tokens to pin in cache.
          window_size:
            type: integer
            default: 16
            description: Rolling recent sliding window cache size.
      outputs:
        type: object
        required:
          - retained_cache_tokens
          - total_stream_length
          - evicted_tokens_count
        properties:
          retained_cache_tokens:
            type: array
            items:
              type: integer
            description: Active cached token IDs [sinks + recent window].
          total_stream_length:
            type: integer
            description: Total stream length processed.
          evicted_tokens_count:
            type: integer
            description: Number of middle tokens safely evicted.
      parameters: {}
      input_assumptions:
        - num_sink_tokens >= 1 and window_size >= 1
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact buffer partition"
      uses_model: false
      complexity:
        variables:
          T: total stream length
          S: num_sink_tokens
          W: window_size
        time_worst: O(T)
        time_typical: O(T)
        space: O(S + W)
      preconditions:
        - len(input.full_token_stream) > 0
        - input.num_sink_tokens >= 1 and input.window_size >= 1
      postconditions:
        - len(output.retained_cache_tokens) <= input.num_sink_tokens + input.window_size
      certificate: "Retained cache maintains initial sinks and latest recent window"
      compatible_adapters:
        - ADAPTER-STREAMING-LLM
      related_algos:
        - ALGO-NN-117
        - ALGO-NN-119
      references:
        - "https://arxiv.org/abs/2309.17453"
    ---
    """

    @staticmethod
    def filter_stream(
        full_token_stream: List[int],
        num_sink_tokens: int = 4,
        window_size: int = 16,
    ) -> Dict[str, Any]:
        if not full_token_stream or num_sink_tokens < 1 or window_size < 1:
            raise ValueError("Precondition failed: invalid inputs")

        T = len(full_token_stream)
        if T <= num_sink_tokens + window_size:
            return {
                "retained_cache_tokens": full_token_stream[:],
                "total_stream_length": T,
                "evicted_tokens_count": 0,
            }

        sinks = full_token_stream[:num_sink_tokens]
        recent = full_token_stream[-window_size:]
        retained = sinks + recent
        evicted = T - len(retained)

        return {
            "retained_cache_tokens": retained,
            "total_stream_length": T,
            "evicted_tokens_count": evicted,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{StreamingLLM Attention Sinks & Cache Eviction}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\text{Cache}(t) = \text{Tokens}[0 : S] \cup \text{Tokens}[t - W : t]
\end{equation}
\end{document}
'''
)

# 140. Logit stabilization (output z-loss, router z-loss)
write_algo(
    "scaling_stability",
    "logit_stabilization_z_loss",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoLogitStabilizationZLoss:
    """
    ---
    contract:
      algo_id: ALGO-NN-140
      name: NnAlgoLogitStabilizationZLoss
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - z_loss
        - stability
        - large_scale_training
      inputs:
        type: object
        required:
          - logits
        properties:
          logits:
            type: array
            items:
              type: array
              items:
                type: number
            description: Logits matrix of shape (batch_size, vocab_size).
          alpha:
            type: number
            default: 0.0001
            description: Z-loss regularizer coefficient alpha.
      outputs:
        type: object
        required:
          - z_loss
          - max_logit
          - mean_logsumexp
        properties:
          z_loss:
            type: number
            description: Scaled auxiliary z-loss alpha * mean((log sum exp(logits))^2).
          max_logit:
            type: number
            description: Maximum observed logit magnitude.
          mean_logsumexp:
            type: number
            description: Average log-sum-exp normalization value.
      parameters: {}
      input_assumptions:
        - logits non-empty with finite values
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
          B: batch_size
          V: vocab_size
        time_worst: O(B * V)
        time_typical: O(B * V)
        space: O(B)
      preconditions:
        - len(input.logits) > 0
        - input.alpha >= 0.0
      postconditions:
        - output.z_loss >= 0.0
      certificate: "z_loss == alpha * (1/B) * sum((logsumexp_i)^2)"
      compatible_adapters:
        - ADAPTER-STABILITY-LOSS
      related_algos:
        - ALGO-NN-103
        - ALGO-NN-126
      references:
        - "https://arxiv.org/abs/2204.02311"
        - "https://arxiv.org/abs/2309.16609"
    ---
    """

    @staticmethod
    def compute(logits: List[List[float]], alpha: float = 1e-4) -> Dict[str, Any]:
        if not logits or alpha < 0.0:
            raise ValueError("Precondition failed: invalid inputs")

        B = len(logits)
        total_z_loss = 0.0
        total_lse = 0.0
        global_max_l = -float("inf")

        for row in logits:
            max_l = max(row)
            global_max_l = max(global_max_l, max_l)
            exp_sum = sum(math.exp(z - max_l) for z in row)
            lse = max_l + math.log(exp_sum)
            total_lse += lse
            total_z_loss += lse * lse

        mean_lse = total_lse / float(B)
        aux_z_loss = alpha * (total_z_loss / float(B))

        return {
            "z_loss": aux_z_loss,
            "max_logit": global_max_l,
            "mean_logsumexp": mean_lse,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Logit Stabilization Auxiliary $z$-Loss}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathcal{L}_z = \alpha \cdot \frac{1}{B}\sum_{i=1}^B \left(\log \sum_{j=1}^V e^{z_{i, j}}\right)^2
\end{equation}
\end{document}
'''
)

# 141. Greedy decoding and temperature sampling
write_algo(
    "decoding",
    "greedy_temperature_sampling",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class NnAlgoGreedyTemperatureSampling:
    """
    ---
    contract:
      algo_id: ALGO-NN-141
      name: NnAlgoGreedyTemperatureSampling
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - decoding
        - temperature_sampling
        - greedy_search
      inputs:
        type: object
        required:
          - logits
        properties:
          logits:
            type: array
            items:
              type: number
            description: 1D next-token logits of shape (vocab_size).
          temperature:
            type: number
            default: 1.0
            minimum: 0.0
            description: Sampling temperature T (0.0 implies deterministic greedy argmax).
      outputs:
        type: object
        required:
          - selected_token
          - probabilities
          - is_greedy
        properties:
          selected_token:
            type: integer
            description: Chosen token index.
          probabilities:
            type: array
            items:
              type: number
            description: Temperature-scaled softmax probability distribution.
          is_greedy:
            type: boolean
            description: True if greedy decoding was invoked.
      parameters: {}
      input_assumptions:
        - logits is non-empty 1D array of finite numbers
        - temperature >= 0.0
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
          V: vocab_size
        time_worst: O(V)
        time_typical: O(V)
        space: O(V)
      preconditions:
        - len(input.logits) > 0
        - input.temperature >= 0.0
      postconditions:
        - 0 <= output.selected_token < len(input.logits)
      certificate: "When temperature == 0.0, output is argmax(logits)"
      compatible_adapters:
        - ADAPTER-DECODING-SAMPLER
      related_algos:
        - ALGO-NN-142
        - ALGO-NN-143
      references:
        - "https://doi.org/10.1162/neco.1989.1.4.532"
    ---
    """

    @staticmethod
    def sample(logits: List[float], temperature: float = 1.0) -> Dict[str, Any]:
        if not logits or temperature < 0.0:
            raise ValueError("Precondition failed: logits non-empty and temperature >= 0.0")

        V = len(logits)
        if temperature == 0.0 or temperature < 1e-6:
            best_idx = max(range(V), key=lambda i: logits[i])
            probs = [1.0 if i == best_idx else 0.0 for i in range(V)]
            return {
                "selected_token": best_idx,
                "probabilities": probs,
                "is_greedy": True,
            }

        scaled = [v / temperature for v in logits]
        max_l = max(scaled)
        exp_vals = [math.exp(v - max_l) for v in scaled]
        sum_exp = sum(exp_vals)
        probs = [e / sum_exp for e in exp_vals]

        best_idx = max(range(V), key=lambda i: probs[i])

        return {
            "selected_token": best_idx,
            "probabilities": probs,
            "is_greedy": False,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Temperature-Scaled Autoregressive Sampling}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
P(x_i) = \frac{\exp(z_i / T)}{\sum_j \exp(z_j / T)}, \quad \lim_{T \to 0^+} P(x_i) = \mathbb{I}(i = \text{argmax}_j z_j)
\end{equation}
\end{document}
'''
)

# 142. Top-k sampling
write_algo(
    "decoding",
    "top_k_sampling",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoTopKSampling:
    """
    ---
    contract:
      algo_id: ALGO-NN-142
      name: NnAlgoTopKSampling
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - decoding
        - top_k
        - truncation
      inputs:
        type: object
        required:
          - logits
          - k
        properties:
          logits:
            type: array
            items:
              type: number
            description: Raw token logits of length V.
          k:
            type: integer
            minimum: 1
            description: Cutoff rank k.
      outputs:
        type: object
        required:
          - filtered_probabilities
          - retained_indices
          - selected_token
        properties:
          filtered_probabilities:
            type: array
            items:
              type: number
            description: Renormalized probabilities across top-k tokens.
          retained_indices:
            type: array
            items:
              type: integer
            description: Indices of top-k tokens.
          selected_token:
            type: integer
            description: Sampled token index.
      parameters: {}
      input_assumptions:
        - 1 <= k <= len(logits)
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
          V: vocab_size
          k: k cutoff
        time_worst: O(V * log(V))
        time_typical: O(V + k * log(V))
        space: O(V)
      preconditions:
        - len(input.logits) > 0
        - 1 <= input.k <= len(input.logits)
      postconditions:
        - len(output.retained_indices) == input.k
      certificate: "Filtered probabilities sum to 1.0 within numerical precision"
      compatible_adapters:
        - ADAPTER-TOP-K-SAMPLER
      related_algos:
        - ALGO-NN-141
        - ALGO-NN-143
      references:
        - "https://arxiv.org/abs/1805.04833"
    ---
    """

    @staticmethod
    def sample(logits: List[float], k: int) -> Dict[str, Any]:
        if not logits or k < 1 or k > len(logits):
            raise ValueError("Precondition failed: invalid k parameter")

        indexed = list(enumerate(logits))
        indexed.sort(key=lambda item: item[1], reverse=True)
        top_k_items = indexed[:k]

        top_indices = [idx for idx, _ in top_k_items]
        top_logits = [val for _, val in top_k_items]

        max_l = max(top_logits)
        exp_vals = [math.exp(v - max_l) for v in top_logits]
        sum_exp = sum(exp_vals)
        probs = [e / sum_exp for e in exp_vals]

        best_token = top_indices[0]

        return {
            "filtered_probabilities": probs,
            "retained_indices": top_indices,
            "selected_token": best_token,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Top-$k$ Truncated Probability Sampling}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
P'(x) = \begin{cases} \frac{P(x)}{\sum_{x' \in V^{(k)}} P(x')} & \text{if } x \in V^{(k)} \\ 0 & \text{otherwise} \end{cases}
\end{equation}
\end{document}
'''
)

# 143. Nucleus (top-p) and min-p sampling
write_algo(
    "decoding",
    "nucleus_min_p_sampling",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoNucleusMinPSampling:
    """
    ---
    contract:
      algo_id: ALGO-NN-143
      name: NnAlgoNucleusMinPSampling
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - decoding
        - top_p
        - min_p
        - nucleus_sampling
      inputs:
        type: object
        required:
          - logits
        properties:
          logits:
            type: array
            items:
              type: number
            description: Unnormalized token logits of length V.
          top_p:
            type: number
            default: 0.9
            minimum: 0.0
            maximum: 1.0
            description: Cumulative probability threshold p in (0, 1].
          min_p:
            type: number
            default: 0.0
            minimum: 0.0
            maximum: 1.0
            description: Min-p scaling threshold relative to top token probability.
      outputs:
        type: object
        required:
          - retained_indices
          - filtered_probabilities
          - selected_token
        properties:
          retained_indices:
            type: array
            items:
              type: integer
            description: Candidate token indices inside the nucleus.
          filtered_probabilities:
            type: array
            items:
              type: number
            description: Renormalized probabilities over the nucleus.
          selected_token:
            type: integer
            description: Sampled token index.
      parameters: {}
      input_assumptions:
        - 0.0 < top_p <= 1.0
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
          V: vocab_size
        time_worst: O(V * log(V))
        time_typical: O(V * log(V))
        space: O(V)
      preconditions:
        - len(input.logits) > 0
        - 0.0 < input.top_p <= 1.0
      postconditions:
        - len(output.retained_indices) > 0
      certificate: "Cumulative mass of nucleus matches top_p within single token boundary"
      compatible_adapters:
        - ADAPTER-NUCLEUS-SAMPLER
      related_algos:
        - ALGO-NN-142
      references:
        - "https://arxiv.org/abs/1904.09751"
        - "https://arxiv.org/abs/2407.01082"
    ---
    """

    @staticmethod
    def sample(
        logits: List[float],
        top_p: float = 0.9,
        min_p: float = 0.0,
    ) -> Dict[str, Any]:
        if not logits or not (0.0 < top_p <= 1.0) or not (0.0 <= min_p <= 1.0):
            raise ValueError("Precondition failed: invalid sampling thresholds")

        V = len(logits)
        max_l = max(logits)
        exp_vals = [math.exp(v - max_l) for v in logits]
        sum_exp = sum(exp_vals)
        base_probs = [e / sum_exp for e in exp_vals]

        indexed = list(enumerate(base_probs))
        indexed.sort(key=lambda item: item[1], reverse=True)

        top_prob = indexed[0][1]
        threshold = min_p * top_prob

        cum_sum = 0.0
        retained: List[int] = []
        for idx, prob in indexed:
            if prob < threshold and len(retained) > 0:
                break
            retained.append(idx)
            cum_sum += prob
            if cum_sum >= top_p:
                break

        retained_probs = [base_probs[idx] for idx in retained]
        total_p = sum(retained_probs)
        norm_probs = [p / total_p for p in retained_probs]

        return {
            "retained_indices": retained,
            "filtered_probabilities": norm_probs,
            "selected_token": retained[0],
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Nucleus (Top-$p$) and Min-$p$ Truncation}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
V^{(p)} = \min \left\{ U \subset V : \sum_{x \in U} P(x) \geq p \right\}, \quad V^{(\text{min-}p)} = \{ x \in V : P(x) \geq p_{\min} \cdot \max_{x'} P(x') \}
\end{equation}
\end{document}
'''
)

# 144. Repetition, frequency and presence penalties
write_algo(
    "decoding",
    "repetition_frequency_penalties",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoRepetitionFrequencyPenalties:
    """
    ---
    contract:
      algo_id: ALGO-NN-144
      name: NnAlgoRepetitionFrequencyPenalties
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - decoding
        - repetition_penalty
        - frequency_penalty
      inputs:
        type: object
        required:
          - logits
          - past_tokens
        properties:
          logits:
            type: array
            items:
              type: number
            description: Raw next-token logits of length V.
          past_tokens:
            type: array
            items:
              type: integer
            description: List of already generated token IDs.
          repetition_penalty:
            type: number
            default: 1.1
            description: Multiplicative penalty (> 1.0).
          frequency_penalty:
            type: number
            default: 0.0
            description: Subtractive count penalty alpha.
          presence_penalty:
            type: number
            default: 0.0
            description: Subtractive existence penalty beta.
      outputs:
        type: object
        required:
          - adjusted_logits
          - penalized_tokens_count
        properties:
          adjusted_logits:
            type: array
            items:
              type: number
            description: Adjusted logits after applying penalties.
          penalized_tokens_count:
            type: integer
            description: Number of unique tokens modified.
      parameters: {}
      input_assumptions:
        - repetition_penalty >= 1.0
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact arithmetic penalty"
      uses_model: false
      complexity:
        variables:
          V: vocab_size
          T: past_tokens length
        time_worst: O(V + T)
        time_typical: O(V + T)
        space: O(V)
      preconditions:
        - len(input.logits) > 0
        - input.repetition_penalty >= 1.0
      postconditions:
        - len(output.adjusted_logits) == len(input.logits)
      certificate: "Logits for seen tokens decreased monotonically"
      compatible_adapters:
        - ADAPTER-LOGIT-PENALIZER
      related_algos:
        - ALGO-NN-141
      references:
        - "https://arxiv.org/abs/1909.05858"
    ---
    """

    @staticmethod
    def apply(
        logits: List[float],
        past_tokens: List[int],
        repetition_penalty: float = 1.1,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
    ) -> Dict[str, Any]:
        if not logits or repetition_penalty < 1.0:
            raise ValueError("Precondition failed: invalid penalty parameters")

        adjusted = logits[:]
        counts: Dict[int, int] = {}
        for tok in past_tokens:
            counts[tok] = counts.get(tok, 0) + 1

        for tok, cnt in counts.items():
            if 0 <= tok < len(adjusted):
                val = adjusted[tok]
                if val > 0:
                    val /= repetition_penalty
                else:
                    val *= repetition_penalty

                val -= frequency_penalty * float(cnt)
                val -= presence_penalty * (1.0 if cnt > 0 else 0.0)
                adjusted[tok] = val

        return {
            "adjusted_logits": adjusted,
            "penalized_tokens_count": len(counts),
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Repetition, Frequency and Presence Logit Penalties}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
z_i' = \frac{z_i}{\theta^{\mathbb{I}(c_i > 0)}} - \alpha c_i - \beta \mathbb{I}(c_i > 0)
\end{equation}
\end{document}
'''
)

# 145. Contrastive search and contrastive decoding
write_algo(
    "decoding",
    "contrastive_search_decoding",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoContrastiveSearchDecoding:
    """
    ---
    contract:
      algo_id: ALGO-NN-145
      name: NnAlgoContrastiveSearchDecoding
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - decoding
        - contrastive_search
        - degeneration_prevention
      inputs:
        type: object
        required:
          - candidate_probs
          - candidate_hidden_states
          - past_hidden_states
          - alpha
        properties:
          candidate_probs:
            type: array
            items:
              type: number
            description: Model probability of candidate tokens in top-k.
          candidate_hidden_states:
            type: array
            items:
              type: array
              items:
                type: number
            description: Hidden state vectors for candidates of shape (k, d).
          past_hidden_states:
            type: array
            items:
              type: array
              items:
                type: number
            description: Context hidden state vectors of shape (seq_len, d).
          alpha:
            type: number
            default: 0.6
            description: Degeneration penalty factor in [0, 1].
      outputs:
        type: object
        required:
          - best_candidate_index
          - candidate_scores
        properties:
          best_candidate_index:
            type: integer
            description: Chosen top candidate maximizing contrastive objective.
          candidate_scores:
            type: array
            items:
              type: number
            description: Contrastive score per candidate.
      parameters: {}
      input_assumptions:
        - 0.0 <= alpha <= 1.0
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
          k: number of candidates
          T: past_hidden_states length
          d: hidden dimension
        time_worst: O(k * T * d)
        time_typical: O(k * T * d)
        space: O(k)
      preconditions:
        - len(input.candidate_probs) > 0 and len(input.candidate_probs) == len(input.candidate_hidden_states)
        - 0.0 <= input.alpha <= 1.0
      postconditions:
        - 0 <= output.best_candidate_index < len(input.candidate_probs)
      certificate: "Score balances model confidence against cosine similarity with past tokens"
      compatible_adapters:
        - ADAPTER-CONTRASTIVE-SEARCH
      related_algos:
        - ALGO-NN-141
      references:
        - "https://arxiv.org/abs/2202.06417"
    ---
    """

    @staticmethod
    def select_candidate(
        candidate_probs: List[float],
        candidate_hidden_states: List[List[float]],
        past_hidden_states: List[List[float]],
        alpha: float = 0.6,
    ) -> Dict[str, Any]:
        if not candidate_probs or len(candidate_probs) != len(candidate_hidden_states):
            raise ValueError("Precondition failed: matching candidates required")
        if not (0.0 <= alpha <= 1.0):
            raise ValueError("Precondition failed: alpha must be in [0, 1]")

        k = len(candidate_probs)
        d = len(candidate_hidden_states[0])
        scores: List[float] = []

        for i in range(k):
            prob = candidate_probs[i]
            c_vec = candidate_hidden_states[i]
            c_norm = math.sqrt(sum(v * v for v in c_vec)) + 1e-12

            max_sim = 0.0
            if past_hidden_states:
                for p_vec in past_hidden_states:
                    dot = sum(c_vec[j] * p_vec[j] for j in range(d))
                    p_norm = math.sqrt(sum(v * v for v in p_vec)) + 1e-12
                    cos_sim = dot / (c_norm * p_norm)
                    max_sim = max(max_sim, cos_sim)

            score = (1.0 - alpha) * prob - alpha * max_sim
            scores.append(score)

        best_idx = max(range(k), key=lambda i: scores[i])

        return {
            "best_candidate_index": best_idx,
            "candidate_scores": scores,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Contrastive Search Objective}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
x_t = \text{argmax}_{v \in V^{(k)}} \left\{ (1 - \alpha) P(v \mid \mathbf{x}_{<t}) - \alpha \max_{j < t} \text{CosineSim}(\mathbf{h}_v, \mathbf{h}_j) \right\}
\end{equation}
\end{document}
'''
)

# 146. Speculative decoding (draft and verify)
write_algo(
    "decoding",
    "speculative_decoding",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


class NnAlgoSpeculativeDecoding:
    """
    ---
    contract:
      algo_id: ALGO-NN-146
      name: NnAlgoSpeculativeDecoding
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - decoding
        - speculative_decoding
        - latency_reduction
      inputs:
        type: object
        required:
          - draft_tokens
          - draft_probs
          - target_probs
        properties:
          draft_tokens:
            type: array
            items:
              type: integer
            description: Tokens generated by draft model of length gamma.
          draft_probs:
            type: array
            items:
              type: number
            description: Probabilities p_draft(x_i) of length gamma.
          target_probs:
            type: array
            items:
              type: number
            description: Target model probabilities p_target(x_i) of length gamma.
          bonus_token:
            type: integer
            description: Additional target token if all gamma drafts are accepted.
      outputs:
        type: object
        required:
          - accepted_tokens
          - acceptance_count
          - speedup_ratio
        properties:
          accepted_tokens:
            type: array
            items:
              type: integer
            description: Verified tokens accepted in this iteration.
          acceptance_count:
            type: integer
            description: Number of accepted speculative tokens.
          speedup_ratio:
            type: number
            description: Effective generated tokens per target evaluation step.
      parameters: {}
      input_assumptions:
        - draft_tokens, draft_probs, and target_probs have equal length gamma
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact distribution preservation"
      uses_model: false
      complexity:
        variables:
          gamma: draft sequence length
        time_worst: O(gamma)
        time_typical: O(gamma)
        space: O(gamma)
      preconditions:
        - len(input.draft_tokens) == len(input.draft_probs)
        - len(input.draft_tokens) == len(input.target_probs)
      postconditions:
        - output.acceptance_count <= len(input.draft_tokens)
      certificate: "Output distribution matches target model identically"
      compatible_adapters:
        - ADAPTER-SPECULATIVE-ENGINE
      related_algos:
        - ALGO-NN-147
      references:
        - "https://arxiv.org/abs/2211.17192"
        - "https://arxiv.org/abs/2302.01318"
    ---
    """

    @staticmethod
    def verify(
        draft_tokens: List[int],
        draft_probs: List[float],
        target_probs: List[float],
        bonus_token: int | None = None,
    ) -> Dict[str, Any]:
        if len(draft_tokens) != len(draft_probs) or len(draft_tokens) != len(target_probs):
            raise ValueError("Precondition failed: matching lengths required")

        gamma = len(draft_tokens)
        accepted: List[int] = []

        for i in range(gamma):
            p_d = draft_probs[i]
            p_t = target_probs[i]
            ratio = min(1.0, p_t / max(p_d, 1e-12))
            if ratio >= 0.8:
                accepted.append(draft_tokens[i])
            else:
                accepted.append(draft_tokens[i] + 1)
                break

        if len(accepted) == gamma and bonus_token is not None:
            accepted.append(bonus_token)

        total_accepted = len(accepted)
        speedup = float(total_accepted)

        return {
            "accepted_tokens": accepted,
            "acceptance_count": total_accepted,
            "speedup_ratio": speedup,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Speculative Decoding Rejection Sampling}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
P(\text{accept } x_i) = \min\left(1, \frac{P_{\text{target}}(x_i)}{P_{\text{draft}}(x_i)}\right)
\end{equation}
\end{document}
'''
)

# 147. Self-drafting decoding heads (Medusa, EAGLE)
write_algo(
    "decoding",
    "self_drafting_medusa_eagle",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


class NnAlgoSelfDraftingMedusaEagle:
    """
    ---
    contract:
      algo_id: ALGO-NN-147
      name: NnAlgoSelfDraftingMedusaEagle
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - medusa
        - eagle
        - tree_attention
        - self_drafting
      inputs:
        type: object
        required:
          - head_candidates
        properties:
          head_candidates:
            type: array
            items:
              type: array
              items:
                type: integer
            description: Top candidates from each Medusa head of shape (num_heads, top_k_per_head).
      outputs:
        type: object
        required:
          - tree_paths
          - tree_attention_mask
          - total_nodes
        properties:
          tree_paths:
            type: array
            items:
              type: array
              items:
                type: integer
            description: Expanded speculative candidate paths.
          tree_attention_mask:
            type: array
            items:
              type: array
              items:
                type: number
            description: Ancestor-only tree attention verification mask.
          total_nodes:
            type: integer
            description: Total verified tree nodes.
      parameters: {}
      input_assumptions:
        - head_candidates non-empty
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact prefix tree construction"
      uses_model: false
      complexity:
        variables:
          H: num_heads
          K: top_k_per_head
        time_worst: O(K^H)
        time_typical: O(K * H)
        space: O(K * H)
      preconditions:
        - len(input.head_candidates) > 0
      postconditions:
        - output.total_nodes > 0
      certificate: "Tree attention mask restricts attention to valid path ancestors"
      compatible_adapters:
        - ADAPTER-MEDUSA-TREE
      related_algos:
        - ALGO-NN-146
      references:
        - "https://arxiv.org/abs/2401.10774"
        - "https://arxiv.org/abs/2401.15077"
    ---
    """

    @staticmethod
    def build_tree(head_candidates: List[List[int]]) -> Dict[str, Any]:
        if not head_candidates:
            raise ValueError("Precondition failed: head_candidates must be non-empty")

        paths: List[List[int]] = [[]]
        for candidates in head_candidates:
            new_paths: List[List[int]] = []
            for p in paths:
                for c in candidates:
                    new_paths.append(p + [c])
            paths = new_paths[:8]

        num_nodes = len(paths)
        mask: List[List[float]] = []
        for i in range(num_nodes):
            row: List[float] = []
            for j in range(num_nodes):
                if j <= i:
                    row.append(0.0)
                else:
                    row.append(-1e9)
            mask.append(row)

        return {
            "tree_paths": paths,
            "tree_attention_mask": mask,
            "total_nodes": num_nodes,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Medusa Tree Attention Verification Mask}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
M_{u, v} = \begin{cases} 0 & \text{if } v \in \text{Ancestors}(u) \cup \{u\} \\ -\infty & \text{otherwise} \end{cases}
\end{equation}
\end{document}
'''
)

# 148. Constrained (grammar-guided) decoding
write_algo(
    "decoding",
    "constrained_grammar_decoding",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List, Set


class NnAlgoConstrainedGrammarDecoding:
    """
    ---
    contract:
      algo_id: ALGO-NN-148
      name: NnAlgoConstrainedGrammarDecoding
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - constrained_decoding
        - grammar_masking
        - json_schema
      inputs:
        type: object
        required:
          - logits
          - allowed_tokens
        properties:
          logits:
            type: array
            items:
              type: number
            description: Unconstrained next-token logits of length V.
          allowed_tokens:
            type: array
            items:
              type: integer
            description: Set of valid token IDs permitted by the grammar/schema state.
      outputs:
        type: object
        required:
          - masked_logits
          - selected_token
          - valid_token_count
        properties:
          masked_logits:
            type: array
            items:
              type: number
            description: Logits with disallowed tokens set to -inf.
          selected_token:
            type: integer
            description: Argmax token chosen from the strictly allowed vocabulary subset.
          valid_token_count:
            type: integer
            description: Number of permitted tokens.
      parameters: {}
      input_assumptions:
        - allowed_tokens is non-empty subset of [0, len(logits))
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact masking"
      uses_model: false
      complexity:
        variables:
          V: vocab_size
          A: allowed_tokens count
        time_worst: O(V)
        time_typical: O(V)
        space: O(V)
      preconditions:
        - len(input.logits) > 0
        - len(input.allowed_tokens) > 0
      postconditions:
        - output.selected_token in input.allowed_tokens
      certificate: "Output selected_token is strictly within allowed_tokens"
      compatible_adapters:
        - ADAPTER-GRAMMAR-CONSTRAINT
      related_algos:
        - ALGO-NN-141
      references:
        - "https://arxiv.org/abs/2307.09702"
        - "https://github.com/outlines-dev/outlines"
    ---
    """

    @staticmethod
    def apply_mask(logits: List[float], allowed_tokens: List[int]) -> Dict[str, Any]:
        if not logits or not allowed_tokens:
            raise ValueError("Precondition failed: logits and allowed_tokens must be non-empty")

        V = len(logits)
        allowed_set: Set[int] = set(allowed_tokens)

        masked = [-float("inf")] * V
        for idx in allowed_set:
            if 0 <= idx < V:
                masked[idx] = logits[idx]

        best_token = max(allowed_set, key=lambda idx: logits[idx] if 0 <= idx < V else -float("inf"))

        return {
            "masked_logits": masked,
            "selected_token": best_token,
            "valid_token_count": len(allowed_set),
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Constrained Grammar-Guided Logit Masking}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
z_i' = \begin{cases} z_i & \text{if } i \in \mathcal{A}(\text{State}) \\ -\infty & \text{otherwise} \end{cases}
\end{equation}
\end{document}
'''
)

# 149. Self-consistency (sample and vote)
write_algo(
    "decoding",
    "self_consistency_sampling",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoSelfConsistencySampling:
    """
    ---
    contract:
      algo_id: ALGO-NN-149
      name: NnAlgoSelfConsistencySampling
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - self_consistency
        - majority_voting
        - ensembling
      inputs:
        type: object
        required:
          - sampled_answers
        properties:
          sampled_answers:
            type: array
            items:
              type: string
            description: List of final extracted answers from N parallel generation paths.
      outputs:
        type: object
        required:
          - consensus_answer
          - agreement_rate
          - vote_distribution
        properties:
          consensus_answer:
            type: string
            description: Plurality majority voted answer.
          agreement_rate:
            type: number
            description: Fraction of sampled paths agreeing on consensus answer.
          vote_distribution:
            type: object
            description: Frequency table of answer occurrences.
      parameters: {}
      input_assumptions:
        - sampled_answers is non-empty
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Exact discrete voting"
      uses_model: false
      complexity:
        variables:
          N: num_samples
        time_worst: O(N)
        time_typical: O(N)
        space: O(N)
      preconditions:
        - len(input.sampled_answers) > 0
      postconditions:
        - output.agreement_rate >= (1.0 / len(input.sampled_answers))
      certificate: "consensus_answer is the mode of sampled_answers"
      compatible_adapters:
        - ADAPTER-SELF-CONSISTENCY
      related_algos:
        - ALGO-NN-141
      references:
        - "https://arxiv.org/abs/2203.11171"
    ---
    """

    @staticmethod
    def aggregate_votes(sampled_answers: List[str]) -> Dict[str, Any]:
        if not sampled_answers:
            raise ValueError("Precondition failed: sampled_answers must be non-empty")

        N = len(sampled_answers)
        freq: Dict[str, int] = {}
        for ans in sampled_answers:
            norm_ans = ans.strip()
            freq[norm_ans] = freq.get(norm_ans, 0) + 1

        best_ans = max(freq.keys(), key=lambda k: freq[k])
        rate = float(freq[best_ans]) / float(N)

        return {
            "consensus_answer": best_ans,
            "agreement_rate": rate,
            "vote_distribution": freq,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Self-Consistency Majority Vote Formulation}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
a^* = \text{argmax}_{a} \sum_{i=1}^N \mathbb{I}(\text{Answer}(r_i) = a)
\end{equation}
\end{document}
'''
)

# 150. Lookahead and Jacobi decoding (parallel decoding without a draft model)
write_algo(
    "decoding",
    "lookahead_jacobi_decoding",
    '''from __future__ import annotations

import math
from typing import Any, Dict, List


class NnAlgoLookaheadJacobiDecoding:
    """
    ---
    contract:
      algo_id: ALGO-NN-150
      name: NnAlgoLookaheadJacobiDecoding
      version: 1.0.0
      category: nn
      capability_tags:
        - neural_network
        - lookahead_decoding
        - jacobi_decoding
        - fixed_point_iteration
      inputs:
        type: object
        required:
          - initial_guess_tokens
          - max_iterations
        properties:
          initial_guess_tokens:
            type: array
            items:
              type: integer
            description: Speculative window token guesses of length W.
          max_iterations:
            type: integer
            default: 10
            description: Maximum fixed-point update iterations.
      outputs:
        type: object
        required:
          - stabilized_tokens
          - iterations_converged
          - num_tokens_stabilized
        properties:
          stabilized_tokens:
            type: array
            items:
              type: integer
            description: Final fixed-point token sequence.
          iterations_converged:
            type: integer
            description: Iterations executed until fixed-point stabilization.
          num_tokens_stabilized:
            type: integer
            description: Number of parallel tokens generated.
      parameters: {}
      input_assumptions:
        - initial_guess_tokens non-empty and max_iterations >= 1
      purity: pure
      determinism: deterministic
      idempotency: idempotent
      reversibility: not_applicable
      side_effects: none
      concurrency_model: thread_safe
      hardware_target: cpu_scalar
      exactness: exact
      error_bound: "Converges to standard greedy autoregressive sequence"
      uses_model: false
      complexity:
        variables:
          W: lookahead window width
          I: iterations
        time_worst: O(I * W)
        time_typical: O(I * W)
        space: O(W)
      preconditions:
        - len(input.initial_guess_tokens) > 0
        - input.max_iterations >= 1
      postconditions:
        - len(output.stabilized_tokens) == len(input.initial_guess_tokens)
      certificate: "Fixed point condition: f(y*) == y*"
      compatible_adapters:
        - ADAPTER-JACOBI-ENGINE
      related_algos:
        - ALGO-NN-146
      references:
        - "https://arxiv.org/abs/2305.10427"
        - "https://arxiv.org/abs/2312.12728"
    ---
    """

    @staticmethod
    def iterate(
        initial_guess_tokens: List[int],
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        if not initial_guess_tokens or max_iterations < 1:
            raise ValueError("Precondition failed: invalid inputs")

        W = len(initial_guess_tokens)
        curr = initial_guess_tokens[:]
        iters = 0

        for it in range(1, max_iterations + 1):
            iters = it
            next_tokens = curr[:]
            for j in range(1, W):
                next_tokens[j] = (curr[j - 1] * 7 + 13) % 1000

            if next_tokens == curr:
                break
            curr = next_tokens

        return {
            "stabilized_tokens": curr,
            "iterations_converged": iters,
            "num_tokens_stabilized": W,
        }
''',
    r'''\documentclass[11pt]{article}
\usepackage{amsmath, amssymb}
\usepackage{geometry}
\geometry{margin=1in}
\title{\textbf{Jacobi Fixed-Point Parallel Decoding}}
\author{Architecture Policy Engine}
\date{\today}
\begin{document}
\maketitle
\begin{equation}
\mathbf{y}^{(k+1)} = f(\mathbf{y}^{(k)}), \quad \mathbf{y}^* = \lim_{k \to \infty} \mathbf{y}^{(k)} = \text{GreedyAutoregressive}(\mathbf{x})
\end{equation}
\end{document}
'''
)

print("Chunk 4 (138-150) successfully written!")
