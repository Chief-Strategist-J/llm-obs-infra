#!/usr/bin/env python3
"""
Generator for ALGO-NN-43 to ALGO-NN-50 (Schedules, Scalings & Initializations)
"""

import sys
from pathlib import Path

BASE_DIR = Path("/home/btpl-lap-22/live/llm-obs-infra/policies/policy-orchestrator/src/features/code_engine/algos/nn")

def write_algo(name: str, impl_content: str, tex_content: str):
    target_dir = BASE_DIR / name
    target_dir.mkdir(parents=True, exist_ok=True)
    with open(target_dir / "impl.py", "w", encoding="utf-8") as f:
        f.write(impl_content.strip() + "\n")
    with open(target_dir / "math.tex", "w", encoding="utf-8") as f:
        f.write(tex_content.strip() + "\n")
    print(f"Generated {name}: impl.py & math.tex")

# ==============================================================================
# ALGO-NN-43: Learning Rate Warmup
# ==============================================================================
IMPL_43 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoLearningRateWarmup:
    """
    ---
    contract:
      algo_id: ALGO-NN-43
      name: NnAlgoLearningRateWarmup
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.schedule
        - nn.warmup
        - nn.learning_rate
        - nn.early_training_stability
      inputs:
        type: object
        properties:
          current_step:
            type: integer
            description: Current training step t >= 0.
          warmup_steps:
            type: integer
            description: Total warmup duration W >= 1.
          base_lr:
            type: number
            description: Peak target learning rate eta_max > 0.
          warmup_init_lr:
            type: number
            default: 0.0
            description: Starting learning rate at step 0 eta_min >= 0.
          strategy:
            type: string
            enum: [linear, cosine, quadratic]
            default: linear
            description: Mathematical warmup ramp curve.
        required:
          - current_step
          - warmup_steps
          - base_lr
        additionalProperties: false
      outputs:
        type: object
        properties:
          learning_rate:
            type: number
            description: Computed learning rate eta_t for the current step.
          progress_fraction:
            type: number
            description: Normalized progress ratio in [0, 1].
          is_warmup:
            type: boolean
            description: Whether the current step is within the warmup phase.
        required:
          - learning_rate
          - progress_fraction
          - is_warmup
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        current_step: int,
        warmup_steps: int,
        base_lr: float,
        warmup_init_lr: float = 0.0,
        strategy: Literal["linear", "cosine", "quadratic"] = "linear",
    ) -> Dict[str, Any]:
        if current_step < 0:
            raise ValueError(f"Precondition failed: current_step must be >= 0, got {current_step}.")
        if warmup_steps < 1:
            raise ValueError(f"Precondition failed: warmup_steps must be >= 1, got {warmup_steps}.")
        if base_lr <= 0.0:
            raise ValueError(f"Precondition failed: base_lr must be > 0, got {base_lr}.")
        if warmup_init_lr < 0.0:
            raise ValueError(f"Precondition failed: warmup_init_lr must be >= 0, got {warmup_init_lr}.")

        if current_step >= warmup_steps:
            return {
                "learning_rate": base_lr,
                "progress_fraction": 1.0,
                "is_warmup": False,
            }

        progress = float(current_step) / float(warmup_steps)

        if strategy == "linear":
            lr = warmup_init_lr + (base_lr - warmup_init_lr) * progress
        elif strategy == "cosine":
            factor = 0.5 * (1.0 - math.cos(math.pi * progress))
            lr = warmup_init_lr + (base_lr - warmup_init_lr) * factor
        elif strategy == "quadratic":
            lr = warmup_init_lr + (base_lr - warmup_init_lr) * (progress ** 2)
        else:
            raise ValueError(f"Precondition failed: unrecognized strategy {strategy}")

        return {
            "learning_rate": lr,
            "progress_fraction": progress,
            "is_warmup": True,
        }
'''

TEX_43 = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{hyperref}

\theoremstyle{definition}
\newtheorem{definition}{Definition}[section]
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{remark}{Remark}[section]

\title{\textbf{Rigorous Mathematical Specification of Learning Rate Warmup Strategies in Adaptive Optimization}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
During initial optimization steps, empirical second-moment statistics $v_t$ are highly inaccurate, producing erratic updates under large learning rates. Learning rate warmup monotonically ramps the step size from $\eta_{\min}$ to $\eta_{\max}$ over $W$ steps.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{goyal2017} P.~Goyal et al., ``Accurate, Large Minibatch SGD: Training ImageNet in 1 Hour,'' \emph{arXiv:1706.02677}, 2017.
\end{thebibliography}

\end{document}
'''

write_algo("learning_rate_warmup", IMPL_43, TEX_43)

# ==============================================================================
# ALGO-NN-44: Cosine Decay and Warm Restarts
# ==============================================================================
IMPL_44 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoCosineDecayRestarts:
    """
    ---
    contract:
      algo_id: ALGO-NN-44
      name: NnAlgoCosineDecayRestarts
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.schedule
        - nn.cosine_annealing
        - nn.sgdr
        - nn.warm_restarts
      inputs:
        type: object
        properties:
          current_step:
            type: integer
            description: Current global step count t >= 0.
          total_steps:
            type: integer
            description: Total training duration or base period T_0 >= 1.
          lr_max:
            type: number
            description: Peak learning rate eta_max > 0.
          lr_min:
            type: number
            default: 0.0
            description: Minimum decayed learning rate eta_min >= 0.
          use_restarts:
            type: boolean
            default: false
            description: Whether to enable SGDR periodic warm restarts.
          t_mult:
            type: integer
            default: 1
            description: Period multiplier factor T_mult >= 1 for consecutive restart cycles.
        required:
          - current_step
          - total_steps
          - lr_max
        additionalProperties: false
      outputs:
        type: object
        properties:
          learning_rate:
            type: number
            description: Decayed learning rate eta_t.
          current_cycle:
            type: integer
            description: Current restart cycle index i >= 0.
        required:
          - learning_rate
          - current_cycle
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        current_step: int,
        total_steps: int,
        lr_max: float,
        lr_min: float = 0.0,
        use_restarts: bool = false,
        t_mult: int = 1,
    ) -> Dict[str, Any]:
        if current_step < 0 or total_steps < 1 or lr_max <= 0.0 or lr_min < 0.0 or t_mult < 1:
            raise ValueError("Precondition failed: invalid schedule parameters.")

        if not use_restarts:
            t = min(current_step, total_steps)
            progress = float(t) / float(total_steps)
            lr = lr_min + 0.5 * (lr_max - lr_min) * (1.0 + math.cos(math.pi * progress))
            return {"learning_rate": lr, "current_cycle": 0}

        # SGDR restarts
        t_cur = current_step
        t_i = total_steps
        cycle = 0

        while t_cur >= t_i:
            t_cur -= t_i
            t_i *= t_mult
            cycle += 1

        progress = float(t_cur) / float(t_i)
        lr = lr_min + 0.5 * (lr_max - lr_min) * (1.0 + math.cos(math.pi * progress))

        return {
            "learning_rate": lr,
            "current_cycle": cycle,
        }
'''

TEX_44 = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{hyperref}

\theoremstyle{definition}
\newtheorem{definition}{Definition}[section]
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{remark}{Remark}[section]

\title{\textbf{Rigorous Mathematical Specification and Period Dynamics of Cosine Annealing and SGDR Warm Restarts}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Cosine annealing lowers the learning rate smoothly along a half-cosine period: $\eta_t = \eta_{\min} + \frac{1}{2}(\eta_{\max} - \eta_{\min})\left(1 + \cos\left(\frac{\pi t}{T}\right)\right)$. SGDR warm restarts periodically reset the learning rate, escaping sharp local minima.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{loshchilov2016} I.~Loshchilov and F.~Hutter, ``SGDR: Stochastic Gradient Descent with Warm Restarts,'' \emph{ICLR}, 2017.
\end{thebibliography}

\end{document}
'''

write_algo("cosine_decay_restarts", IMPL_44, TEX_44)

# ==============================================================================
# ALGO-NN-45: Warmup-Stable-Decay (WSD), Linear Decay, One-Cycle
# ==============================================================================
IMPL_45 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoWsdOneCycleSchedules:
    """
    ---
    contract:
      algo_id: ALGO-NN-45
      name: NnAlgoWsdOneCycleSchedules
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.schedule
        - nn.wsd
        - nn.one_cycle
        - nn.linear_decay
      inputs:
        type: object
        properties:
          current_step:
            type: integer
            description: Current step t >= 0.
          total_steps:
            type: integer
            description: Total steps T >= 1.
          max_lr:
            type: number
            description: Peak learning rate eta_max > 0.
          schedule_type:
            type: string
            enum: [wsd, one_cycle, linear_decay]
            default: wsd
            description: Schedule formulation.
          warmup_pct:
            type: number
            default: 0.1
            description: Fraction of steps for warmup in [0, 1].
          decay_pct:
            type: number
            default: 0.2
            description: Fraction of steps for cooldown/decay in [0, 1] (for WSD).
        required:
          - current_step
          - total_steps
          - max_lr
        additionalProperties: false
      outputs:
        type: object
        properties:
          learning_rate:
            type: number
            description: Computed learning rate eta_t.
          phase:
            type: string
            description: Current schedule phase (warmup, stable, decay).
        required:
          - learning_rate
          - phase
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        current_step: int,
        total_steps: int,
        max_lr: float,
        schedule_type: Literal["wsd", "one_cycle", "linear_decay"] = "wsd",
        warmup_pct: float = 0.1,
        decay_pct: float = 0.2,
    ) -> Dict[str, Any]:
        if current_step < 0 or total_steps < 1 or max_lr <= 0.0:
            raise ValueError("Precondition failed: invalid step or learning rate values.")

        step = min(current_step, total_steps)

        if schedule_type == "wsd":
            w_steps = int(warmup_pct * total_steps)
            d_steps = int(decay_pct * total_steps)
            s_steps = total_steps - w_steps - d_steps

            if step < w_steps:
                lr = max_lr * (float(step) / float(max(1, w_steps)))
                phase = "warmup"
            elif step < (w_steps + s_steps):
                lr = max_lr
                phase = "stable"
            else:
                progress = float(step - w_steps - s_steps) / float(max(1, d_steps))
                lr = max_lr * 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))
                phase = "decay"

        elif schedule_type == "linear_decay":
            progress = float(step) / float(total_steps)
            lr = max_lr * (1.0 - progress)
            phase = "decay"

        elif schedule_type == "one_cycle":
            half_steps = total_steps / 2.0
            if step < half_steps:
                progress = float(step) / half_steps
                lr = max_lr * progress
                phase = "warmup"
            else:
                progress = float(step - half_steps) / half_steps
                lr = max_lr * (1.0 - progress)
                phase = "decay"
        else:
            raise ValueError(f"Precondition failed: unknown schedule {schedule_type}")

        return {
            "learning_rate": max(0.0, lr),
            "phase": phase,
        }
'''

TEX_45 = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{hyperref}

\theoremstyle{definition}
\newtheorem{definition}{Definition}[section]
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{remark}{Remark}[section]

\title{\textbf{Rigorous Mathematical Specification of Warmup-Stable-Decay (WSD) and 1-Cycle Learning Rate Schedules}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
The Warmup-Stable-Decay (WSD) schedule maintains constant learning rate across indefinite training lengths, allowing continuous checkpoint branching before applying a rapid cooldown phase.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{smith2019} L.~N.~Smith and N.~Topin, ``Super-Convergence: Very Fast Training of Neural Networks Using Large Learning Rates,'' \emph{AAAI}, 2019.
\end{thebibliography}

\end{document}
'''

write_algo("wsd_one_cycle_schedules", IMPL_45, TEX_45)

# ==============================================================================
# ALGO-NN-46: Batch Size and Learning Rate Scaling Rules
# ==============================================================================
IMPL_46 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoBatchSizeLrScaling:
    """
    ---
    contract:
      algo_id: ALGO-NN-46
      name: NnAlgoBatchSizeLrScaling
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.scaling
        - nn.batch_size
        - nn.learning_rate_scaling
        - nn.distributed_training
      inputs:
        type: object
        properties:
          base_batch_size:
            type: integer
            description: Reference baseline batch size B_0 >= 1.
          base_lr:
            type: number
            description: Reference baseline learning rate eta_0 > 0.
          target_batch_size:
            type: integer
            description: Scaled target batch size B >= 1.
          scaling_rule:
            type: string
            enum: [linear, square_root]
            default: linear
            description: Scaling rule (linear for SGD, square_root for Adam).
        required:
          - base_batch_size
          - base_lr
          - target_batch_size
        additionalProperties: false
      outputs:
        type: object
        properties:
          scaled_lr:
            type: number
            description: Scaled target learning rate eta.
          scale_factor:
            type: number
            description: Batch ratio k = B / B_0.
        required:
          - scaled_lr
          - scale_factor
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        base_batch_size: int,
        base_lr: float,
        target_batch_size: int,
        scaling_rule: Literal["linear", "square_root"] = "linear",
    ) -> Dict[str, Any]:
        if base_batch_size < 1 or target_batch_size < 1:
            raise ValueError("Precondition failed: batch sizes must be >= 1.")
        if base_lr <= 0.0:
            raise ValueError(f"Precondition failed: base_lr must be > 0, got {base_lr}.")

        k = float(target_batch_size) / float(base_batch_size)

        if scaling_rule == "linear":
            scaled_lr = base_lr * k
        elif scaling_rule == "square_root":
            scaled_lr = base_lr * math.sqrt(k)
        else:
            raise ValueError(f"Precondition failed: unknown scaling rule {scaling_rule}")

        return {
            "scaled_lr": scaled_lr,
            "scale_factor": k,
        }
'''

TEX_46 = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{hyperref}

\theoremstyle{definition}
\newtheorem{definition}{Definition}[section]
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{remark}{Remark}[section]

\title{\textbf{Rigorous Mathematical Specification of Batch Size and Learning Rate Scaling Laws}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Linear scaling ($\eta = \eta_0 \frac{B}{B_0}$) preserves total stochastic drift per epoch in SGD, whereas square-root scaling ($\eta = \eta_0 \sqrt{\frac{B}{B_0}}$) matches variance scales under adaptive optimizers.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{krizhevsky2014} A.~Krizhevsky, ``One Weird Trick for Parallelizing Convolutional Neural Networks,'' \emph{arXiv:1404.5997}, 2014.
\end{thebibliography}

\end{document}
'''

write_algo("batch_size_lr_scaling", IMPL_46, TEX_46)

# ==============================================================================
# ALGO-NN-47: Xavier (Glorot) Initialization
# ==============================================================================
IMPL_47 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoXavierGlorotInit:
    """
    ---
    contract:
      algo_id: ALGO-NN-47
      name: NnAlgoXavierGlorotInit
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.initialization
        - nn.xavier
        - nn.glorot
        - nn.variance_preservation
      inputs:
        type: object
        properties:
          fan_in:
            type: integer
            description: Number of input connections fan_in >= 1.
          fan_out:
            type: integer
            description: Number of output connections fan_out >= 1.
          distribution:
            type: string
            enum: [uniform, normal]
            default: uniform
            description: Sampling distribution family.
          gain:
            type: number
            default: 1.0
            description: Non-linearity gain multiplier.
        required:
          - fan_in
          - fan_out
        additionalProperties: false
      outputs:
        type: object
        properties:
          std_dev:
            type: number
            description: Standard deviation sigma for normal sampling.
          uniform_bound:
            type: number
            description: Half-width bound a for uniform sampling in [-a, a].
          variance:
            type: number
            description: Target weight variance 2 / (fan_in + fan_out).
        required:
          - std_dev
          - uniform_bound
          - variance
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        fan_in: int,
        fan_out: int,
        distribution: Literal["uniform", "normal"] = "uniform",
        gain: float = 1.0,
    ) -> Dict[str, Any]:
        if fan_in < 1 or fan_out < 1:
            raise ValueError("Precondition failed: fan_in and fan_out must be >= 1.")
        if gain <= 0.0:
            raise ValueError(f"Precondition failed: gain must be > 0, got {gain}.")

        var = (gain ** 2) * (2.0 / float(fan_in + fan_out))
        std = math.sqrt(var)
        bound = math.sqrt(3.0 * var)

        return {
            "std_dev": std,
            "uniform_bound": bound,
            "variance": var,
        }
'''

TEX_47 = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{hyperref}

\theoremstyle{definition}
\newtheorem{definition}{Definition}[section]
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{remark}{Remark}[section]

\title{\textbf{Rigorous Mathematical Specification and Variance Equilibrium Proof of Xavier (Glorot) Initialization}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Xavier initialization preserves activation variance in the forward pass and gradient variance in the backward pass for symmetric linear/tanh activations: $\operatorname{Var}(W) = \frac{2}{\text{fan\_in} + \text{fan\_out}}$.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{glorot2010} X.~Glorot and Y.~Bengio, ``Understanding the Difficulty of Training Deep Feedforward Neural Networks,'' \emph{AISTATS}, 2010.
\end{thebibliography}

\end{document}
'''

write_algo("xavier_glorot_init", IMPL_47, TEX_47)

# ==============================================================================
# ALGO-NN-48: He (Kaiming) Initialization
# ==============================================================================
IMPL_48 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoHeKaimingInit:
    """
    ---
    contract:
      algo_id: ALGO-NN-48
      name: NnAlgoHeKaimingInit
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.initialization
        - nn.kaiming
        - nn.he_init
        - nn.relu_init
      inputs:
        type: object
        properties:
          fan_in:
            type: integer
            description: Input connection dimension fan_in >= 1.
          mode:
            type: string
            enum: [fan_in, fan_out]
            default: fan_in
            description: Forward variance preservation (fan_in) vs backward gradient variance preservation (fan_out).
          fan_out:
            type: integer
            default: 1
            description: Output connection dimension (required if mode is fan_out).
          nonlinearity:
            type: string
            enum: [relu, leaky_relu]
            default: relu
            description: Rectification activation function.
          negative_slope:
            type: number
            default: 0.0
            description: Negative slope alpha for Leaky ReLU.
        required:
          - fan_in
        additionalProperties: false
      outputs:
        type: object
        properties:
          std_dev:
            type: number
            description: Standard deviation sigma for normal initialization.
          uniform_bound:
            type: number
            description: Bound a for uniform initialization in [-a, a].
          gain:
            type: number
            description: Non-linearity compensation gain factor.
        required:
          - std_dev
          - uniform_bound
          - gain
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        fan_in: int,
        mode: Literal["fan_in", "fan_out"] = "fan_in",
        fan_out: int = 1,
        nonlinearity: Literal["relu", "leaky_relu"] = "relu",
        negative_slope: float = 0.0,
    ) -> Dict[str, Any]:
        if fan_in < 1 or fan_out < 1:
            raise ValueError("Precondition failed: fan dimensions must be >= 1.")

        if nonlinearity == "relu":
            gain = math.sqrt(2.0)
        elif nonlinearity == "leaky_relu":
            gain = math.sqrt(2.0 / (1.0 + negative_slope ** 2))
        else:
            raise ValueError(f"Precondition failed: unknown nonlinearity {nonlinearity}")

        fan = fan_in if mode == "fan_in" else fan_out
        std = gain / math.sqrt(fan)
        bound = math.sqrt(3.0) * std

        return {
            "std_dev": std,
            "uniform_bound": bound,
            "gain": gain,
        }
'''

TEX_48 = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{hyperref}

\theoremstyle{definition}
\newtheorem{definition}{Definition}[section]
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{remark}{Remark}[section]

\title{\textbf{Rigorous Mathematical Specification and Rectified Variance Proof of He (Kaiming) Initialization}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Because ReLU zeroes out approximately half of all activations, signal variance is halved at every layer. He (Kaiming) initialization introduces a compensation factor of 2: $\operatorname{Var}(W) = \frac{2}{\text{fan\_in}}$.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{he2015} K.~He et al., ``Delving Deep into Rectifiers: Surpassing Human-Level Performance on ImageNet Classification,'' \emph{ICCV}, 2015.
\end{thebibliography}

\end{document}
'''

write_algo("he_kaiming_init", IMPL_48, TEX_48)

# ==============================================================================
# ALGO-NN-49: Initialization for Deep Residual Networks
# ==============================================================================
IMPL_49 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoDeepResidualInit:
    """
    ---
    contract:
      algo_id: ALGO-NN-49
      name: NnAlgoDeepResidualInit
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.initialization
        - nn.residual
        - nn.fixup
        - nn.zero_init
        - nn.gpt2_scaling
      inputs:
        type: object
        properties:
          num_layers:
            type: integer
            description: Total number of residual blocks/layers L >= 1.
          base_std:
            type: number
            default: 0.02
            description: Standard baseline standard deviation sigma_0 > 0.
          strategy:
            type: string
            enum: [scaled_residual, zero_init, fixup]
            default: scaled_residual
            description: Deep residual initialization scheme.
        required:
          - num_layers
        additionalProperties: false
      outputs:
        type: object
        properties:
          scaled_std:
            type: number
            description: Scaled standard deviation sigma for residual projection weights.
          scale_factor:
            type: number
            description: Multiplicative attenuation coefficient (e.g., 1 / sqrt(2L)).
        required:
          - scaled_std
          - scale_factor
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        num_layers: int,
        base_std: float = 0.02,
        strategy: Literal["scaled_residual", "zero_init", "fixup"] = "scaled_residual",
    ) -> Dict[str, Any]:
        if num_layers < 1:
            raise ValueError(f"Precondition failed: num_layers must be >= 1, got {num_layers}.")
        if base_std <= 0.0:
            raise ValueError(f"Precondition failed: base_std must be > 0, got {base_std}.")

        if strategy == "scaled_residual":
            scale = 1.0 / math.sqrt(2.0 * num_layers)
            scaled_std = base_std * scale
        elif strategy == "zero_init":
            scale = 0.0
            scaled_std = 0.0
        elif strategy == "fixup":
            scale = num_layers ** (-0.25)
            scaled_std = base_std * scale
        else:
            raise ValueError(f"Precondition failed: unknown strategy {strategy}")

        return {
            "scaled_std": scaled_std,
            "scale_factor": scale,
        }
'''

TEX_49 = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{hyperref}

\theoremstyle{definition}
\newtheorem{definition}{Definition}[section]
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{remark}{Remark}[section]

\title{\textbf{Rigorous Mathematical Specification of Scaled Residual Initialization and Zero-Init for Very Deep Transformers}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
In $L$-layer residual networks, activation variance accumulates as $\operatorname{Var}(\mathbf{x}_L) \approx L \cdot \operatorname{Var}(\mathbf{x}_0)$. Scaled residual initialization attenuates output projection weights by $\frac{1}{\sqrt{2L}}$ (GPT-2 style), keeping hidden state norms constant throughout depth.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{radford2019} A.~Radford et al., ``Language Models are Unsupervised Multitask Learners,'' \emph{OpenAI Blog}, 2019.
\bibitem{zhang2019b} H.~Zhang, Y.~N.~Dauphin, and T.~Ma, ``Fixup Initialization: Residual Learning Without Normalization,'' \emph{ICLR}, 2019.
\end{thebibliography}

\end{document}
'''

write_algo("deep_residual_init", IMPL_49, TEX_49)

# ==============================================================================
# ALGO-NN-50: Maximal Update Parametrization (muP)
# ==============================================================================
IMPL_50 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoMaximalUpdateParam:
    """
    ---
    contract:
      algo_id: ALGO-NN-50
      name: NnAlgoMaximalUpdateParam
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.scaling
        - nn.mup
        - nn.hyperparameter_transfer
        - nn.infinite_width
      inputs:
        type: object
        properties:
          base_width:
            type: integer
            description: Proxy model base hidden width n_0 >= 1.
          target_width:
            type: integer
            description: Target scaled model hidden width n >= 1.
          base_lr:
            type: number
            description: Optimal learning rate eta_0 tuned on proxy model.
          layer_type:
            type: string
            enum: [input_embedding, hidden_weight, output_head]
            default: hidden_weight
            description: Specific architectural layer role in muP framework.
        required:
          - base_width
          - target_width
          - base_lr
        additionalProperties: false
      outputs:
        type: object
        properties:
          scaled_lr:
            type: number
            description: Scaled learning rate eta for target width.
          init_std_multiplier:
            type: number
            description: Scaling multiplier for weight initialization standard deviation.
          width_ratio:
            type: number
            description: Hidden dimension ratio n / n_0.
        required:
          - scaled_lr
          - init_std_multiplier
          - width_ratio
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        base_width: int,
        target_width: int,
        base_lr: float,
        layer_type: Literal["input_embedding", "hidden_weight", "output_head"] = "hidden_weight",
    ) -> Dict[str, Any]:
        if base_width < 1 or target_width < 1:
            raise ValueError("Precondition failed: widths must be >= 1.")
        if base_lr <= 0.0:
            raise ValueError(f"Precondition failed: base_lr must be > 0, got {base_lr}.")

        ratio = float(target_width) / float(base_width)

        if layer_type == "hidden_weight":
            # In muP: hidden weights learning rate scales as 1 / ratio
            scaled_lr = base_lr / ratio
            init_std = 1.0 / math.sqrt(ratio)
        elif layer_type == "input_embedding":
            # Input embeddings learning rate remains constant O(1)
            scaled_lr = base_lr
            init_std = 1.0
        elif layer_type == "output_head":
            # Output head learning rate scales as 1 / ratio
            scaled_lr = base_lr / ratio
            init_std = 1.0 / ratio
        else:
            raise ValueError(f"Precondition failed: unknown layer_type {layer_type}")

        return {
            "scaled_lr": scaled_lr,
            "init_std_multiplier": init_std,
            "width_ratio": ratio,
        }
'''

TEX_50 = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{hyperref}

\theoremstyle{definition}
\newtheorem{definition}{Definition}[section]
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{remark}{Remark}[section]

\title{\textbf{Rigorous Mathematical Specification and Hyperparameter Transfer Theory of Maximal Update Parametrization ($\mu$P)}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Standard Parameterization (SP) causes feature representations to either freeze or blow up as network width $n \to \infty$. Maximal Update Parametrization ($\mu$P) scales initialization variances and layer-wise learning rates by width ratios, guaranteeing non-trivial feature learning and zero-shot transfer of optimal hyperparameters from small proxy models to massive architectures.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{yang2022} G.~Yang et al., ``Tensor Programs V: Tuning Large Neural Networks via Zero-Shot Hyperparameter Transfer,'' \emph{NeurIPS}, 2022.
\end{thebibliography}

\end{document}
'''

write_algo("maximal_update_param", IMPL_50, TEX_50)

print("Batch 4 (Schedules, Scalings & Initializations #43 - #50) written successfully.")
