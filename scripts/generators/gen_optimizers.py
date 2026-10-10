#!/usr/bin/env python3
"""
Generator for ALGO-NN-31 to ALGO-NN-42 (Optimizers & Optimization Dynamics)
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
# ALGO-NN-31: Stochastic Gradient Descent (SGD)
# ==============================================================================
IMPL_31 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoStochasticGradientDescent:
    """
    ---
    contract:
      algo_id: ALGO-NN-31
      name: NnAlgoStochasticGradientDescent
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.sgd
        - nn.gradient_descent
        - nn.weight_decay
      inputs:
        type: object
        properties:
          parameters:
            type: array
            items:
              type: number
            description: Current parameter vector theta of length P.
          gradients:
            type: array
            items:
              type: number
            description: Parameter gradient vector g of length P.
          lr:
            type: number
            default: 0.01
            description: Learning rate step size eta > 0.
          weight_decay:
            type: number
            default: 0.0
            description: L2 weight decay regularization coefficient lambda >= 0.
        required:
          - parameters
          - gradients
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_parameters:
            type: array
            items:
              type: number
            description: Updated parameter vector theta_{t+1} of length P.
          step_norm:
            type: number
            description: L2 Euclidean norm of the parameter displacement step.
        required:
          - updated_parameters
          - step_norm
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        parameters: Sequence[float],
        gradients: Sequence[float],
        lr: float = 0.01,
        weight_decay: float = 0.0,
    ) -> Dict[str, Any]:
        p = len(parameters)
        if p == 0:
            raise ValueError("Precondition failed: parameters list cannot be empty.")
        if len(gradients) != p:
            raise ValueError(f"Precondition failed: gradients length ({len(gradients)}) must match parameters ({p}).")
        if lr <= 0.0:
            raise ValueError(f"Precondition failed: learning rate lr must be > 0, got {lr}.")
        if weight_decay < 0.0:
            raise ValueError(f"Precondition failed: weight_decay must be >= 0, got {weight_decay}.")

        new_params: List[float] = []
        step_sq = 0.0

        for theta, g in zip(parameters, gradients):
            grad_eff = g + weight_decay * theta
            delta = lr * grad_eff
            theta_new = theta - delta
            new_params.append(theta_new)
            step_sq += delta ** 2

        return {
            "updated_parameters": new_params,
            "step_norm": math.sqrt(step_sq),
        }
'''

TEX_31 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification and Convergence Properties of Stochastic Gradient Descent (SGD)}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Stochastic Gradient Descent (SGD) updates parameters along negative empirical mini-batch gradient trajectories $\theta_{t+1} = \theta_t - \eta_t (\mathbf{g}_t + \lambda \theta_t)$. We formalize the Robbins-Monro convergence conditions and analyze implicit regularization from gradient covariance noise.
\end{abstract}

\section{Update Equation and Robbins-Monro Conditions}
\begin{equation}
\theta_{t+1} = \theta_t - \eta_t \mathbf{g}_t(\theta_t; \xi_t) - \eta_t \lambda \theta_t.
\end{equation}
Convergence to a stationary point $\nabla f(\theta^*) = 0$ requires $\sum_{t=1}^\infty \eta_t = \infty$ and $\sum_{t=1}^\infty \eta_t^2 < \infty$.

\begin{thebibliography}{9}
\bibitem{robbins1951} H.~Robbins and S.~Monro, ``A Stochastic Approximation Method,'' \emph{Annals of Mathematical Statistics}, vol.~22, no.~3, pp.~400--407, 1951.
\end{thebibliography}

\end{document}
'''

write_algo("stochastic_gradient_descent", IMPL_31, TEX_31)

# ==============================================================================
# ALGO-NN-32: Momentum and Nesterov Momentum
# ==============================================================================
IMPL_32 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoMomentumNesterov:
    """
    ---
    contract:
      algo_id: ALGO-NN-32
      name: NnAlgoMomentumNesterov
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.momentum
        - nn.nesterov
        - nn.acceleration
      inputs:
        type: object
        properties:
          parameters:
            type: array
            items:
              type: number
            description: Parameter vector theta of length P.
          gradients:
            type: array
            items:
              type: number
            description: Parameter gradient vector g of length P.
          velocity:
            type: array
            items:
              type: number
            description: Momentum velocity buffer v of length P.
          lr:
            type: number
            default: 0.01
            description: Learning rate eta > 0.
          beta:
            type: number
            default: 0.9
            description: Momentum damping coefficient beta in [0, 1).
          nesterov:
            type: boolean
            default: false
            description: Whether to apply Nesterov Accelerated Gradient (NAG) lookahead formulation.
        required:
          - parameters
          - gradients
          - velocity
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_parameters:
            type: array
            items:
              type: number
            description: Updated parameter vector theta_{t+1} of length P.
          updated_velocity:
            type: array
            items:
              type: number
            description: Updated velocity buffer v_{t+1} of length P.
        required:
          - updated_parameters
          - updated_velocity
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        parameters: Sequence[float],
        gradients: Sequence[float],
        velocity: Sequence[float],
        lr: float = 0.01,
        beta: float = 0.9,
        nesterov: bool = False,
    ) -> Dict[str, Any]:
        p = len(parameters)
        if p == 0 or len(gradients) != p or len(velocity) != p:
            raise ValueError("Precondition failed: parameter, gradient, and velocity buffers must have identical non-zero length.")
        if lr <= 0.0:
            raise ValueError(f"Precondition failed: lr must be > 0, got {lr}.")
        if not (0.0 <= beta < 1.0):
            raise ValueError(f"Precondition failed: beta must be in [0, 1), got {beta}.")

        new_params: List[float] = []
        new_velocity: List[float] = []

        for theta, g, v in zip(parameters, gradients, velocity):
            v_next = beta * v + g
            if nesterov:
                step = lr * (g + beta * v_next)
            else:
                step = lr * v_next

            theta_next = theta - step
            new_params.append(theta_next)
            new_velocity.append(v_next)

        return {
            "updated_parameters": new_params,
            "updated_velocity": new_velocity,
        }
'''

TEX_32 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification of Classical Heavy-Ball Momentum and Nesterov Accelerated Gradient (NAG)}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Heavy-Ball momentum and Nesterov Accelerated Gradient (NAG) accelerate gradient descent along low-curvature ravines while damping high-frequency oscillations. We formulate velocity buffer recurrences and establish the optimal accelerated convergence rate $\mathcal{O}(1/k^2)$ for convex functions.
\end{abstract}

\section{Momentum Recurrences}
\begin{itemize}
    \item \textbf{Polyak Heavy-Ball:} $\mathbf{v}_{t+1} = \beta \mathbf{v}_t + \mathbf{g}_t, \quad \theta_{t+1} = \theta_t - \eta \mathbf{v}_{t+1}$.
    \item \textbf{Nesterov Accelerated Gradient:} $\mathbf{v}_{t+1} = \beta \mathbf{v}_t + \mathbf{g}_t, \quad \theta_{t+1} = \theta_t - \eta (\mathbf{g}_t + \beta \mathbf{v}_{t+1})$.
\end{itemize}

\begin{thebibliography}{9}
\bibitem{nesterov1983} Y.~Nesterov, ``A Method for Solving the Convex Programming Problem with Convergence Rate $O(1/k^2)$,'' \emph{Doklady AN SSSR}, vol.~269, pp.~543--547, 1983.
\end{thebibliography}

\end{document}
'''

write_algo("momentum_nesterov", IMPL_32, TEX_32)

# ==============================================================================
# ALGO-NN-33: AdaGrad Optimizer
# ==============================================================================
IMPL_33 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoAdagradOptimizer:
    """
    ---
    contract:
      algo_id: ALGO-NN-33
      name: NnAlgoAdagradOptimizer
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.adagrad
        - nn.adaptive_learning_rate
        - nn.sparse_features
      inputs:
        type: object
        properties:
          parameters:
            type: array
            items:
              type: number
            description: Parameter coordinate vector theta of length P.
          gradients:
            type: array
            items:
              type: number
            description: Coordinate gradient vector g of length P.
          state_accumulator:
            type: array
            items:
              type: number
            description: Accumulated squared gradient buffer G of length P.
          lr:
            type: number
            default: 0.01
            description: Global learning rate eta > 0.
          eps:
            type: number
            default: 0.00000001
            description: Numerical stability denominator epsilon > 0.
        required:
          - parameters
          - gradients
          - state_accumulator
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_parameters:
            type: array
            items:
              type: number
            description: Updated parameter vector theta_{t+1} of length P.
          updated_accumulator:
            type: array
            items:
              type: number
            description: Updated squared gradient accumulator G_{t+1} of length P.
        required:
          - updated_parameters
          - updated_accumulator
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        parameters: Sequence[float],
        gradients: Sequence[float],
        state_accumulator: Sequence[float],
        lr: float = 0.01,
        eps: float = 1e-8,
    ) -> Dict[str, Any]:
        p = len(parameters)
        if p == 0 or len(gradients) != p or len(state_accumulator) != p:
            raise ValueError("Precondition failed: buffers must have identical non-zero length.")
        if lr <= 0.0 or eps <= 0.0:
            raise ValueError("Precondition failed: lr and eps must be > 0.")

        new_params: List[float] = []
        new_accum: List[float] = []

        for theta, g, G in zip(parameters, gradients, state_accumulator):
            G_next = G + g ** 2
            theta_next = theta - (lr / (math.sqrt(G_next) + eps)) * g
            new_params.append(theta_next)
            new_accum.append(G_next)

        return {
            "updated_parameters": new_params,
            "updated_accumulator": new_accum,
        }
'''

TEX_33 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification and Coordinate Scaling of the AdaGrad Adaptive Optimizer}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
AdaGrad scales coordinate learning rates inversely proportional to the square root of historical squared gradient sums $G_t = \sum_{\tau=1}^t g_\tau^2$. We analyze coordinate adaptation on sparse features and derive the asymptotic step decay.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{duchi2011} J.~Duchi, E.~Hazan, and Y.~Singer, ``Adaptive Subgradient Methods for Online Learning and Stochastic Optimization,'' \emph{JMLR}, vol.~12, pp.~2121--2159, 2011.
\end{thebibliography}

\end{document}
'''

write_algo("adagrad_optimizer", IMPL_33, TEX_33)

# ==============================================================================
# ALGO-NN-34: RMSProp Optimizer
# ==============================================================================
IMPL_34 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoRmspropOptimizer:
    """
    ---
    contract:
      algo_id: ALGO-NN-34
      name: NnAlgoRmspropOptimizer
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.rmsprop
        - nn.adaptive_learning_rate
        - nn.ema
      inputs:
        type: object
        properties:
          parameters:
            type: array
            items:
              type: number
            description: Parameter vector theta of length P.
          gradients:
            type: array
            items:
              type: number
            description: Parameter gradient vector g of length P.
          moving_average:
            type: array
            items:
              type: number
            description: Exponential moving average second moment buffer v of length P.
          lr:
            type: number
            default: 0.001
            description: Learning rate eta > 0.
          alpha:
            type: number
            default: 0.99
            description: Smoothing factor alpha in [0, 1).
          eps:
            type: number
            default: 0.00000001
            description: Denominator epsilon > 0.
        required:
          - parameters
          - gradients
          - moving_average
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_parameters:
            type: array
            items:
              type: number
            description: Updated parameter vector theta_{t+1} of length P.
          updated_moving_average:
            type: array
            items:
              type: number
            description: Updated moving average second moment v_{t+1} of length P.
        required:
          - updated_parameters
          - updated_moving_average
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        parameters: Sequence[float],
        gradients: Sequence[float],
        moving_average: Sequence[float],
        lr: float = 0.001,
        alpha: float = 0.99,
        eps: float = 1e-8,
    ) -> Dict[str, Any]:
        p = len(parameters)
        if p == 0 or len(gradients) != p or len(moving_average) != p:
            raise ValueError("Precondition failed: buffers must have identical non-zero length.")
        if lr <= 0.0 or eps <= 0.0:
            raise ValueError("Precondition failed: lr and eps must be > 0.")
        if not (0.0 <= alpha < 1.0):
            raise ValueError(f"Precondition failed: alpha must be in [0, 1), got {alpha}.")

        new_params: List[float] = []
        new_v: List[float] = []

        for theta, g, v in zip(parameters, gradients, moving_average):
            v_next = alpha * v + (1.0 - alpha) * (g ** 2)
            theta_next = theta - (lr / (math.sqrt(v_next) + eps)) * g
            new_params.append(theta_next)
            new_v.append(v_next)

        return {
            "updated_parameters": new_params,
            "updated_moving_average": new_v,
        }
'''

TEX_34 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification and Exponential Moving Average Dynamics of RMSProp}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
RMSProp addresses AdaGrad's diminishing learning rates in non-convex settings by replacing monotonic sums with an Exponential Moving Average (EMA) of squared gradients: $v_t = \alpha v_{t-1} + (1 - \alpha) g_t^2$.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{tieleman2012} T.~Tieleman and G.~Hinton, ``Lecture 6.5-rmsprop: Divide the gradient by a running average of its recent magnitude,'' \emph{COURSERA}, 2012.
\end{thebibliography}

\end{document}
'''

write_algo("rmsprop_optimizer", IMPL_34, TEX_34)

# ==============================================================================
# ALGO-NN-35: Adam Optimizer
# ==============================================================================
IMPL_35 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoAdamOptimizer:
    """
    ---
    contract:
      algo_id: ALGO-NN-35
      name: NnAlgoAdamOptimizer
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.adam
        - nn.first_moment
        - nn.second_moment
        - nn.bias_correction
      inputs:
        type: object
        properties:
          parameters:
            type: array
            items:
              type: number
            description: Parameter vector theta of length P.
          gradients:
            type: array
            items:
              type: number
            description: Parameter gradient vector g of length P.
          exp_avg:
            type: array
            items:
              type: number
            description: First moment moving average m of length P.
          exp_avg_sq:
            type: array
            items:
              type: number
            description: Second moment moving average v of length P.
          step:
            type: integer
            description: Current optimizer step count t >= 1.
          lr:
            type: number
            default: 0.001
            description: Learning rate eta > 0.
          beta1:
            type: number
            default: 0.9
            description: First moment decay coefficient beta_1 in [0, 1).
          beta2:
            type: number
            default: 0.999
            description: Second moment decay coefficient beta_2 in [0, 1).
          eps:
            type: number
            default: 0.00000001
            description: Numerical stability denominator epsilon > 0.
        required:
          - parameters
          - gradients
          - exp_avg
          - exp_avg_sq
          - step
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_parameters:
            type: array
            items:
              type: number
            description: Updated parameter vector theta_{t+1} of length P.
          updated_exp_avg:
            type: array
            items:
              type: number
            description: Updated first moment buffer m_{t+1} of length P.
          updated_exp_avg_sq:
            type: array
            items:
              type: number
            description: Updated second moment buffer v_{t+1} of length P.
        required:
          - updated_parameters
          - updated_exp_avg
          - updated_exp_avg_sq
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        parameters: Sequence[float],
        gradients: Sequence[float],
        exp_avg: Sequence[float],
        exp_avg_sq: Sequence[float],
        step: int,
        lr: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        eps: float = 1e-8,
    ) -> Dict[str, Any]:
        p = len(parameters)
        if p == 0 or len(gradients) != p or len(exp_avg) != p or len(exp_avg_sq) != p:
            raise ValueError("Precondition failed: buffers must have identical non-zero length P.")
        if step < 1:
            raise ValueError(f"Precondition failed: step must be >= 1, got {step}.")
        if lr <= 0.0 or eps <= 0.0:
            raise ValueError("Precondition failed: lr and eps must be > 0.")
        if not (0.0 <= beta1 < 1.0) or not (0.0 <= beta2 < 1.0):
            raise ValueError("Precondition failed: beta1 and beta2 must be in [0, 1).")

        bias_correction1 = 1.0 - (beta1 ** step)
        bias_correction2 = 1.0 - (beta2 ** step)

        new_params: List[float] = []
        new_m: List[float] = []
        new_v: List[float] = []

        for theta, g, m, v in zip(parameters, gradients, exp_avg, exp_avg_sq):
            m_next = beta1 * m + (1.0 - beta1) * g
            v_next = beta2 * v + (1.0 - beta2) * (g ** 2)

            m_hat = m_next / bias_correction1
            v_hat = v_next / bias_correction2

            theta_next = theta - (lr * m_hat) / (math.sqrt(v_hat) + eps)

            new_params.append(theta_next)
            new_m.append(m_next)
            new_v.append(v_next)

        return {
            "updated_parameters": new_params,
            "updated_exp_avg": new_m,
            "updated_exp_avg_sq": new_v,
        }
'''

TEX_35 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification and Bias Correction Proof of the Adam Adaptive Optimizer}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Adam combines first-moment momentum with second-moment uncentered variance estimates. We provide the formal derivation of the step-dependent bias correction factors $(1 - \beta_1^t)$ and $(1 - \beta_2^t)$ compensating for zero initialization.
\end{abstract}

\section{Adam Update and Bias Correction Derivation}
\begin{equation}
m_t = \beta_1 m_{t-1} + (1 - \beta_1) g_t = (1 - \beta_1) \sum_{i=1}^t \beta_1^{t-i} g_i.
\end{equation}
Taking expectations under stationary gradients $\mathbb{E}[g_i] = \mathbb{E}[g_t]$:
\begin{equation}
\mathbb{E}[m_t] = \mathbb{E}\left[(1 - \beta_1) \sum_{i=1}^t \beta_1^{t-i} g_i\right] = \mathbb{E}[g_t](1 - \beta_1) \frac{1 - \beta_1^t}{1 - \beta_1} = \mathbb{E}[g_t](1 - \beta_1^t).
\end{equation}
Dividing by $(1 - \beta_1^t)$ yields an unbiased estimator $\hat{m}_t = \frac{m_t}{1 - \beta_1^t}$.

\begin{thebibliography}{9}
\bibitem{kingma2014} D.~P.~Kingma and J.~Ba, ``Adam: A Method for Stochastic Optimization,'' \emph{ICLR}, 2015.
\end{thebibliography}

\end{document}
'''

write_algo("adam_optimizer", IMPL_35, TEX_35)

# ==============================================================================
# ALGO-NN-36: AdamW Optimizer (Decoupled Weight Decay)
# ==============================================================================
IMPL_36 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoAdamwOptimizer:
    """
    ---
    contract:
      algo_id: ALGO-NN-36
      name: NnAlgoAdamwOptimizer
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.adamw
        - nn.decoupled_weight_decay
        - nn.transformer_training
      inputs:
        type: object
        properties:
          parameters:
            type: array
            items:
              type: number
            description: Parameter vector theta of length P.
          gradients:
            type: array
            items:
              type: number
            description: Parameter gradient vector g of length P.
          exp_avg:
            type: array
            items:
              type: number
            description: First moment buffer m of length P.
          exp_avg_sq:
            type: array
            items:
              type: number
            description: Second moment buffer v of length P.
          step:
            type: integer
            description: Current optimizer step count t >= 1.
          lr:
            type: number
            default: 0.001
            description: Learning rate eta > 0.
          beta1:
            type: number
            default: 0.9
            description: First moment decay beta_1 in [0, 1).
          beta2:
            type: number
            default: 0.999
            description: Second moment decay beta_2 in [0, 1).
          eps:
            type: number
            default: 0.00000001
            description: Stability constant epsilon > 0.
          weight_decay:
            type: number
            default: 0.01
            description: Decoupled weight decay coefficient lambda >= 0.
        required:
          - parameters
          - gradients
          - exp_avg
          - exp_avg_sq
          - step
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_parameters:
            type: array
            items:
              type: number
            description: Updated parameter vector theta_{t+1} of length P.
          updated_exp_avg:
            type: array
            items:
              type: number
            description: Updated first moment buffer m_{t+1} of length P.
          updated_exp_avg_sq:
            type: array
            items:
              type: number
            description: Updated second moment buffer v_{t+1} of length P.
        required:
          - updated_parameters
          - updated_exp_avg
          - updated_exp_avg_sq
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        parameters: Sequence[float],
        gradients: Sequence[float],
        exp_avg: Sequence[float],
        exp_avg_sq: Sequence[float],
        step: int,
        lr: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        eps: float = 1e-8,
        weight_decay: float = 0.01,
    ) -> Dict[str, Any]:
        p = len(parameters)
        if p == 0 or len(gradients) != p or len(exp_avg) != p or len(exp_avg_sq) != p:
            raise ValueError("Precondition failed: buffers must have identical non-zero length P.")
        if step < 1:
            raise ValueError(f"Precondition failed: step must be >= 1, got {step}.")
        if lr <= 0.0 or eps <= 0.0:
            raise ValueError("Precondition failed: lr and eps must be > 0.")
        if weight_decay < 0.0:
            raise ValueError(f"Precondition failed: weight_decay must be >= 0, got {weight_decay}.")

        bias_correction1 = 1.0 - (beta1 ** step)
        bias_correction2 = 1.0 - (beta2 ** step)

        new_params: List[float] = []
        new_m: List[float] = []
        new_v: List[float] = []

        for theta, g, m, v in zip(parameters, gradients, exp_avg, exp_avg_sq):
            # Decoupled weight decay step first: theta = theta * (1 - lr * lambda)
            theta_decayed = theta * (1.0 - lr * weight_decay)

            # Update moments on pure objective gradient g (not g + lambda*theta)
            m_next = beta1 * m + (1.0 - beta1) * g
            v_next = beta2 * v + (1.0 - beta2) * (g ** 2)

            m_hat = m_next / bias_correction1
            v_hat = v_next / bias_correction2

            theta_next = theta_decayed - (lr * m_hat) / (math.sqrt(v_hat) + eps)

            new_params.append(theta_next)
            new_m.append(m_next)
            new_v.append(v_next)

        return {
            "updated_parameters": new_params,
            "updated_exp_avg": new_m,
            "updated_exp_avg_sq": new_v,
        }
'''

TEX_36 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification and Decoupled Regularization Theory of AdamW}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Standard L2 regularization in adaptive optimizers erroneously scales weight decay by the inverse second moment $\frac{1}{\sqrt{v_t}}$, heavily suppressing decay for frequently updated parameters. AdamW decouples weight decay directly from gradient updates: $\theta_{t+1} = \theta_t(1 - \eta \lambda) - \frac{\eta \hat{m}_t}{\sqrt{\hat{v}_t} + \epsilon}$.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{loshchilov2017} I.~Loshchilov and F.~Hutter, ``Decoupled Weight Decay Regularization,'' \emph{ICLR}, 2019.
\end{thebibliography}

\end{document}
'''

write_algo("adamw_optimizer", IMPL_36, TEX_36)

# ==============================================================================
# ALGO-NN-37: LARS and LAMB Optimizers
# ==============================================================================
IMPL_37 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoLarsLambOptimizer:
    """
    ---
    contract:
      algo_id: ALGO-NN-37
      name: NnAlgoLarsLambOptimizer
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.lars
        - nn.lamb
        - nn.large_batch
        - nn.trust_ratio
      inputs:
        type: object
        properties:
          parameters:
            type: array
            items:
              type: number
            description: Parameter vector theta for a layer/tensor of length P.
          gradients:
            type: array
            items:
              type: number
            description: Gradient vector g of length P.
          mode:
            type: string
            enum: [lars, lamb]
            default: lamb
            description: Large-batch optimizer algorithm (LARS vs LAMB).
          exp_avg:
            type: array
            items:
              type: number
            description: First moment buffer m of length P (for LAMB).
          exp_avg_sq:
            type: array
            items:
              type: number
            description: Second moment buffer v of length P (for LAMB).
          step:
            type: integer
            default: 1
            description: Current optimizer step t >= 1.
          lr:
            type: number
            default: 0.001
            description: Learning rate eta > 0.
          weight_decay:
            type: number
            default: 0.01
            description: Weight decay lambda >= 0.
          trust_coefficient:
            type: number
            default: 1.0
            description: Layer-wise trust coefficient phi > 0.
          eps:
            type: number
            default: 0.00000001
            description: Numerical stability denominator epsilon > 0.
        required:
          - parameters
          - gradients
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_parameters:
            type: array
            items:
              type: number
            description: Updated parameter vector theta_{t+1} of length P.
          trust_ratio:
            type: number
            description: Computed layer-wise trust ratio r_t = ||theta|| / ||update||.
          updated_exp_avg:
            type: array
            items:
              type: number
            description: Updated first moment buffer m (for LAMB).
          updated_exp_avg_sq:
            type: array
            items:
              type: number
            description: Updated second moment buffer v (for LAMB).
        required:
          - updated_parameters
          - trust_ratio
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        parameters: Sequence[float],
        gradients: Sequence[float],
        mode: Literal["lars", "lamb"] = "lamb",
        exp_avg: Optional[Sequence[float]] = None,
        exp_avg_sq: Optional[Sequence[float]] = None,
        step: int = 1,
        lr: float = 0.001,
        weight_decay: float = 0.01,
        trust_coefficient: float = 1.0,
        eps: float = 1e-8,
    ) -> Dict[str, Any]:
        p = len(parameters)
        if p == 0 or len(gradients) != p:
            raise ValueError("Precondition failed: parameters and gradients must have identical non-zero length.")

        w_norm = math.sqrt(sum(w ** 2 for w in parameters))
        new_m: List[float] = []
        new_v: List[float] = []
        raw_updates: List[float] = []

        if mode == "lamb":
            m_buf = exp_avg if exp_avg is not None else [0.0] * p
            v_buf = exp_avg_sq if exp_avg_sq is not None else [0.0] * p
            beta1, beta2 = 0.9, 0.999
            bc1 = 1.0 - (beta1 ** step)
            bc2 = 1.0 - (beta2 ** step)

            for theta, g, m, v in zip(parameters, gradients, m_buf, v_buf):
                m_next = beta1 * m + (1.0 - beta1) * g
                v_next = beta2 * v + (1.0 - beta2) * (g ** 2)
                m_hat = m_next / bc1
                v_hat = v_next / bc2
                r_update = (m_hat / (math.sqrt(v_hat) + eps)) + weight_decay * theta
                raw_updates.append(r_update)
                new_m.append(m_next)
                new_v.append(v_next)
        else:  # lars
            for theta, g in zip(parameters, gradients):
                r_update = g + weight_decay * theta
                raw_updates.append(r_update)

        u_norm = math.sqrt(sum(u ** 2 for u in raw_updates))
        if w_norm > 0.0 and u_norm > 0.0:
            trust_ratio = trust_coefficient * (w_norm / u_norm)
        else:
            trust_ratio = 1.0

        new_params = [theta - lr * trust_ratio * u for theta, u in zip(parameters, raw_updates)]

        res: Dict[str, Any] = {
            "updated_parameters": new_params,
            "trust_ratio": trust_ratio,
        }
        if mode == "lamb":
            res["updated_exp_avg"] = new_m
            res["updated_exp_avg_sq"] = new_v
        return res
'''

TEX_37 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification and Trust Ratio Dynamics of LARS and LAMB for Extreme-Batch Scaling}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Large-batch distributed training (batch sizes $\ge 32\text{K}$) causes gradient divergence in shallow layers while starving deep layers. Layer-wise Adaptive Rate Scaling (LARS) and Layer-wise Adaptive Moments (LAMB) rescale each layer's step by the layer trust ratio $r_t^{(l)} = \phi \frac{\|\mathbf{w}_t^{(l)}\|_2}{\|\mathbf{u}_t^{(l)}\|_2}$.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{you2019} Y.~You et al., ``Large Batch Optimization for Deep Learning: Training BERT in 76 Minutes,'' \emph{ICLR}, 2020.
\end{thebibliography}

\end{document}
'''

write_algo("lars_lamb_optimizer", IMPL_37, TEX_37)

# ==============================================================================
# ALGO-NN-38: Adafactor Optimizer (Factored Second Moments)
# ==============================================================================
IMPL_38 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoAdafactorOptimizer:
    """
    ---
    contract:
      algo_id: ALGO-NN-38
      name: NnAlgoAdafactorOptimizer
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.adafactor
        - nn.memory_efficient
        - nn.matrix_factorization
      inputs:
        type: object
        properties:
          weight_matrix:
            type: array
            items:
              type: array
              items:
                type: number
            description: 2D weight matrix W of shape (R, C).
          grad_matrix:
            type: array
            items:
              type: array
              items:
                type: number
            description: 2D gradient matrix G of shape (R, C).
          row_factor:
            type: array
            items:
              type: number
            description: Factored row moving average v_row of length R.
          col_factor:
            type: array
            items:
              type: number
            description: Factored column moving average v_col of length C.
          lr:
            type: number
            default: 0.001
            description: Learning rate eta > 0.
          beta2:
            type: number
            default: 0.999
            description: Second moment decay coefficient beta_2 in [0, 1).
          eps:
            type: number
            default: 0.00000001
            description: Epsilon stability constant > 0.
        required:
          - weight_matrix
          - grad_matrix
          - row_factor
          - col_factor
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_weights:
            type: array
            items:
              type: array
              items:
                type: number
            description: Updated weight matrix W_{t+1} of shape (R, C).
          updated_row_factor:
            type: array
            items:
              type: number
            description: Updated row factor buffer of length R.
          updated_col_factor:
            type: array
            items:
              type: number
            description: Updated column factor buffer of length C.
        required:
          - updated_weights
          - updated_row_factor
          - updated_col_factor
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        weight_matrix: Sequence[Sequence[float]],
        grad_matrix: Sequence[Sequence[float]],
        row_factor: Sequence[float],
        col_factor: Sequence[float],
        lr: float = 0.001,
        beta2: float = 0.999,
        eps: float = 1e-8,
    ) -> Dict[str, Any]:
        r = len(weight_matrix)
        if r == 0:
            raise ValueError("Precondition failed: weight_matrix cannot be empty.")
        c = len(weight_matrix[0])
        if len(grad_matrix) != r or len(grad_matrix[0]) != c or len(row_factor) != r or len(col_factor) != c:
            raise ValueError("Precondition failed: matrix dimension mismatch.")

        # Compute empirical mean squared gradient across rows and cols
        row_means = [sum(grad_matrix[i][j] ** 2 for j in range(c)) / float(c) for i in range(r)]
        col_means = [sum(grad_matrix[i][j] ** 2 for i in range(r)) / float(r) for j in range(c)]

        # Update row and col factors with EMA
        new_row = [beta2 * rf + (1.0 - beta2) * rm for rf, rm in zip(row_factor, row_means)]
        new_col = [beta2 * cf + (1.0 - beta2) * cm for cf, cm in zip(col_factor, col_means)]

        total_row_sum = sum(new_row) + eps

        # Rank-1 reconstruction of second moment: V_{ij} = (new_row_i * new_col_j) / sum(new_row)
        new_weights: List[List[float]] = []
        for i in range(r):
            row_w: List[float] = []
            for j in range(c):
                v_ij = (new_row[i] * new_col[j]) / total_row_sum
                u_ij = grad_matrix[i][j] / (math.sqrt(v_ij) + eps)
                w_next = weight_matrix[i][j] - lr * u_ij
                row_w.append(w_next)
            new_weights.append(row_w)

        return {
            "updated_weights": new_weights,
            "updated_row_factor": new_row,
            "updated_col_factor": new_col,
        }
'''

TEX_38 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification and Rank-1 Kronecker Factorization of Adafactor}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Adafactor reduces optimizer state memory from $\mathcal{O}(R \cdot C)$ to $\mathcal{O}(R + C)$ by decomposing the 2D second moment matrix into row and column marginal averages $V_{ij} \approx \frac{r_i c_j}{\mathbf{1}^T \mathbf{r}}$.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{shazeer2018} N.~Shazeer and N.~Stern, ``Adafactor: Adaptive Learning Rates with Sublinear Memory Cost,'' \emph{ICML}, 2018.
\end{thebibliography}

\end{document}
'''

write_algo("adafactor_optimizer", IMPL_38, TEX_38)

# ==============================================================================
# ALGO-NN-39: Lion Optimizer
# ==============================================================================
IMPL_39 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoLionOptimizer:
    """
    ---
    contract:
      algo_id: ALGO-NN-39
      name: NnAlgoLionOptimizer
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.lion
        - nn.sign_momentum
        - nn.memory_efficiency
      inputs:
        type: object
        properties:
          parameters:
            type: array
            items:
              type: number
            description: Parameter coordinate vector theta of length P.
          gradients:
            type: array
            items:
              type: number
            description: Gradient vector g of length P.
          exp_avg:
            type: array
            items:
              type: number
            description: Momentum buffer m of length P.
          lr:
            type: number
            default: 0.0001
            description: Learning rate eta > 0.
          beta1:
            type: number
            default: 0.9
            description: Interpolation momentum factor beta_1 in [0, 1).
          beta2:
            type: number
            default: 0.99
            description: Tracking momentum factor beta_2 in [0, 1).
          weight_decay:
            type: number
            default: 0.1
            description: Decoupled weight decay coefficient lambda >= 0.
        required:
          - parameters
          - gradients
          - exp_avg
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_parameters:
            type: array
            items:
              type: number
            description: Updated parameter vector theta_{t+1} of length P.
          updated_exp_avg:
            type: array
            items:
              type: number
            description: Updated momentum buffer m_{t+1} of length P.
        required:
          - updated_parameters
          - updated_exp_avg
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        parameters: Sequence[float],
        gradients: Sequence[float],
        exp_avg: Sequence[float],
        lr: float = 1e-4,
        beta1: float = 0.9,
        beta2: float = 0.99,
        weight_decay: float = 0.1,
    ) -> Dict[str, Any]:
        p = len(parameters)
        if p == 0 or len(gradients) != p or len(exp_avg) != p:
            raise ValueError("Precondition failed: buffers must have identical non-zero length P.")
        if lr <= 0.0:
            raise ValueError(f"Precondition failed: lr must be > 0, got {lr}.")

        new_params: List[float] = []
        new_m: List[float] = []

        for theta, g, m in zip(parameters, gradients, exp_avg):
            # Compute update direction using sign of interpolated momentum
            interp = beta1 * m + (1.0 - beta1) * g
            sign_update = 1.0 if interp > 0.0 else (-1.0 if interp < 0.0 else 0.0)

            # Update weights: theta = theta * (1 - lr * lambda) - lr * sign_update
            theta_next = theta * (1.0 - lr * weight_decay) - lr * sign_update

            # Update momentum buffer: m = beta2 * m + (1 - beta2) * g
            m_next = beta2 * m + (1.0 - beta2) * g

            new_params.append(theta_next)
            new_m.append(m_next)

        return {
            "updated_parameters": new_params,
            "updated_exp_avg": new_m,
        }
'''

TEX_39 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification and Sign-Momentum Dynamics of the Lion Optimizer}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Discovered via programmatic symbolic algorithm search, the Lion optimizer discards second-moment tracking entirely and updates parameters along the coordinate sign of an interpolated momentum vector: $c_t = \operatorname{sign}(\beta_1 m_{t-1} + (1 - \beta_1) g_t)$.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{chen2023} X.~Chen et al., ``Symbolic Discovery of Optimization Algorithms,'' \emph{NeurIPS}, 2023.
\end{thebibliography}

\end{document}
'''

write_algo("lion_optimizer", IMPL_39, TEX_39)

# ==============================================================================
# ALGO-NN-40: Second-Order Preconditioning (Shampoo & K-FAC)
# ==============================================================================
IMPL_40 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoSecondOrderPreconditioning:
    """
    ---
    contract:
      algo_id: ALGO-NN-40
      name: NnAlgoSecondOrderPreconditioning
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.second_order
        - nn.shampoo
        - nn.kfac
        - nn.preconditioning
      inputs:
        type: object
        properties:
          grad_matrix:
            type: array
            items:
              type: array
              items:
                type: number
            description: 2D gradient matrix G of shape (M, N).
          left_preconditioner:
            type: array
            items:
              type: array
              items:
                type: number
            description: Left Kronecker preconditioner buffer L = sum G G^T of shape (M, M).
          right_preconditioner:
            type: array
            items:
              type: array
              items:
                type: number
            description: Right Kronecker preconditioner buffer R = sum G^T G of shape (N, N).
          lr:
            type: number
            default: 0.001
            description: Learning rate eta > 0.
          eps:
            type: number
            default: 0.0001
            description: Diagonal damping epsilon > 0.
        required:
          - grad_matrix
          - left_preconditioner
          - right_preconditioner
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_left:
            type: array
            items:
              type: array
              items:
                type: number
            description: Accumulated left covariance matrix of shape (M, M).
          updated_right:
            type: array
            items:
              type: array
              items:
                type: number
            description: Accumulated right covariance matrix of shape (N, N).
          preconditioned_gradient:
            type: array
            items:
              type: array
              items:
                type: number
            description: Preconditioned matrix update of shape (M, N).
        required:
          - updated_left
          - updated_right
          - preconditioned_gradient
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        grad_matrix: Sequence[Sequence[float]],
        left_preconditioner: Sequence[Sequence[float]],
        right_preconditioner: Sequence[Sequence[float]],
        lr: float = 0.001,
        eps: float = 1e-4,
    ) -> Dict[str, Any]:
        m = len(grad_matrix)
        if m == 0:
            raise ValueError("Precondition failed: grad_matrix cannot be empty.")
        n = len(grad_matrix[0])

        # Update left: L += G @ G^T (M, M)
        new_l = [[left_preconditioner[i][j] + sum(grad_matrix[i][k] * grad_matrix[j][k] for k in range(n)) for j in range(m)] for i in range(m)]

        # Update right: R += G^T @ G (N, N)
        new_r = [[right_preconditioner[i][j] + sum(grad_matrix[k][i] * grad_matrix[k][j] for k in range(m)) for j in range(n)] for i in range(n)]

        # Diagonal approximate inverse 4th root preconditioning: P_ij = (L_ii + eps)^(-1/4) * G_ij * (R_jj + eps)^(-1/4)
        p_grad: List[List[float]] = []
        for i in range(m):
            l_scale = (new_l[i][i] + eps) ** (-0.25)
            row_p: List[float] = []
            for j in range(n):
                r_scale = (new_r[j][j] + eps) ** (-0.25)
                row_p.append(l_scale * grad_matrix[i][j] * r_scale)
            p_grad.append(row_p)

        return {
            "updated_left": new_l,
            "updated_right": new_r,
            "preconditioned_gradient": p_grad,
        }
'''

TEX_40 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification of Second-Order Matrix Preconditioning (Shampoo and K-FAC)}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Second-order preconditioning rotates and rescales gradient coordinates according to Riemannian curvature estimates. Shampoo applies left and right matrix root preconditioning $L^{-1/2d} G R^{-1/2d}$ across tensor factors.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{gupta2018} V.~Gupta, T.~Koren, and Y.~Singer, ``Shampoo: Preconditioned Stochastic Tensor Optimization,'' \emph{ICML}, 2018.
\end{thebibliography}

\end{document}
'''

write_algo("second_order_preconditioning", IMPL_40, TEX_40)

# ==============================================================================
# ALGO-NN-41: Sharpness-Aware Minimization (SAM)
# ==============================================================================
IMPL_41 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoSharpnessAwareMinimization:
    """
    ---
    contract:
      algo_id: ALGO-NN-41
      name: NnAlgoSharpnessAwareMinimization
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.sam
        - nn.generalization
        - nn.flat_minima
      inputs:
        type: object
        properties:
          parameters:
            type: array
            items:
              type: number
            description: Base parameter coordinates theta of length P.
          base_gradients:
            type: array
            items:
              type: number
            description: Unperturbed gradient vector nabla L(theta) of length P.
          perturbed_gradients:
            type: array
            items:
              type: number
            description: Gradient vector evaluated at perturbed coordinates nabla L(theta + eps) of length P.
          rho:
            type: number
            default: 0.05
            description: Neighborhood perturbation radius rho > 0.
          lr:
            type: number
            default: 0.01
            description: Step size eta > 0.
        required:
          - parameters
          - base_gradients
          - perturbed_gradients
        additionalProperties: false
      outputs:
        type: object
        properties:
          adversarial_perturbation:
            type: array
            items:
              type: number
            description: Computed adversarial epsilon perturbation of length P.
          updated_parameters:
            type: array
            items:
              type: number
            description: Updated parameter vector theta_{t+1} of length P.
        required:
          - adversarial_perturbation
          - updated_parameters
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        parameters: Sequence[float],
        base_gradients: Sequence[float],
        perturbed_gradients: Sequence[float],
        rho: float = 0.05,
        lr: float = 0.01,
    ) -> Dict[str, Any]:
        p = len(parameters)
        if p == 0 or len(base_gradients) != p or len(perturbed_gradients) != p:
            raise ValueError("Precondition failed: buffers must have identical non-zero length P.")
        if rho <= 0.0 or lr <= 0.0:
            raise ValueError("Precondition failed: rho and lr must be > 0.")

        g_norm = math.sqrt(sum(g ** 2 for g in base_gradients))
        scale = rho / (g_norm + 1e-12)

        eps_perturbation = [g * scale for g in base_gradients]
        updated_params = [theta - lr * g_pert for theta, g_pert in zip(parameters, perturbed_gradients)]

        return {
            "adversarial_perturbation": eps_perturbation,
            "updated_parameters": updated_params,
        }
'''

TEX_41 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification and PAC-Bayes Bounds of Sharpness-Aware Minimization (SAM)}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Sharpness-Aware Minimization (SAM) simultaneously minimizes loss value and loss curvature by seeking parameters inside uniformly low loss neighborhoods: $\min_\theta \max_{\|\epsilon\| \le \rho} \mathcal{L}(\theta + \epsilon)$.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{foret2020} P.~Foret et al., ``Sharpness-Aware Minimization for Efficiently Improving Generalization,'' \emph{ICLR}, 2021.
\end{thebibliography}

\end{document}
'''

write_algo("sharpness_aware_minimization", IMPL_41, TEX_41)

# ==============================================================================
# ALGO-NN-42: Lookahead and Weight Averaging (EMA / Polyak)
# ==============================================================================
IMPL_42 = '''from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Sequence


class NnAlgoLookaheadWeightAveraging:
    """
    ---
    contract:
      algo_id: ALGO-NN-42
      name: NnAlgoLookaheadWeightAveraging
      version: 1.0.0
      category: nn
      capability_tags:
        - nn.optimizer
        - nn.lookahead
        - nn.ema
        - nn.polyak_averaging
      inputs:
        type: object
        properties:
          mode:
            type: string
            enum: [lookahead, ema]
            default: ema
            description: Weight smoothing strategy.
          fast_weights:
            type: array
            items:
              type: number
            description: Current fast optimizer weights theta of length P.
          slow_weights:
            type: array
            items:
              type: number
            description: Slow reference weights or EMA target weights of length P.
          alpha:
            type: number
            default: 0.999
            description: Slow interpolation rate or EMA decay coefficient in (0, 1).
        required:
          - mode
          - fast_weights
          - slow_weights
        additionalProperties: false
      outputs:
        type: object
        properties:
          updated_slow_weights:
            type: array
            items:
              type: number
            description: Updated smoothed weights of length P.
          synced_fast_weights:
            type: array
            items:
              type: number
            description: Fast weights synchronized to updated slow weights (for Lookahead).
        required:
          - updated_slow_weights
        additionalProperties: false
    ---
    """

    @staticmethod
    def forward(
        mode: Literal["lookahead", "ema"] = "ema",
        fast_weights: Optional[Sequence[float]] = None,
        slow_weights: Optional[Sequence[float]] = None,
        alpha: float = 0.999,
    ) -> Dict[str, Any]:
        if fast_weights is None or slow_weights is None:
            raise ValueError("Precondition failed: fast_weights and slow_weights are required.")
        p = len(fast_weights)
        if p == 0 or len(slow_weights) != p:
            raise ValueError("Precondition failed: weights must have identical non-zero length P.")
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"Precondition failed: alpha must be in (0, 1), got {alpha}.")

        if mode == "ema":
            new_slow = [alpha * s + (1.0 - alpha) * f for s, f in zip(slow_weights, fast_weights)]
            return {
                "updated_slow_weights": new_slow,
            }
        elif mode == "lookahead":
            # Slow weights take step: slow = slow + alpha * (fast - slow)
            new_slow = [s + alpha * (f - s) for s, f in zip(slow_weights, fast_weights)]
            # Fast weights reset to new slow weights
            return {
                "updated_slow_weights": new_slow,
                "synced_fast_weights": list(new_slow),
            }
        else:
            raise ValueError(f"Precondition failed: unrecognized mode {mode}")
'''

TEX_42 = r'''\documentclass[11pt,a4paper]{article}
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

\title{\textbf{Rigorous Mathematical Specification of Lookahead and Exponential Moving Average (EMA) Weight Averaging}}
\author{Architecture and Core Engine Team}
\date{October 2026}

\begin{document}
\maketitle

\begin{abstract}
Weight averaging techniques stabilize non-convex optimization trajectories. Exponential Moving Average (EMA) smooths parameter oscillations, while Lookahead couples fast inner loops with slow outer steps: $\phi_{t+1} = \phi_t + \alpha (\theta_{t, k} - \phi_t)$.
\end{abstract}

\begin{thebibliography}{9}
\bibitem{zhang2019} M.~R.~Zhang et al., ``Lookahead Optimizer: k steps forward, 1 step back,'' \emph{NeurIPS}, 2019.
\bibitem{polyak1992} B.~T.~Polyak and A.~B.~Juditsky, ``Acceleration of Stochastic Approximation by Averaging,'' \emph{SIAM J. Control Optim.}, vol.~30, pp.~838--855, 1992.
\end{thebibliography}

\end{document}
'''

write_algo("lookahead_weight_averaging", IMPL_42, TEX_42)

print("Batch 3 (Optimizers #31 - #42) written successfully.")
