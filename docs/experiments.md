# Q-TRANSIT NEXUS — Experimental Methodology & Protocol

This document specifies the experimental design, baseline configurations, and statistical testing methodologies employed to validate the optimization engine.

---

## 1. Experimental Protocol & Reproducibility

To ensure rigorous scientific reproducibility, all comparative experiments follow a standardized protocol:

1. **Independent Runs**: Every stochastic metaheuristic is executed across $N = 30$ independent runs per benchmark instance.
2. **Seed Determinism**: Run $i \in \{0, \dots, 29\}$ utilizes a deterministic seed $S_i = \text{base\_seed} + i$.
3. **Apples-to-Apples Evaluation**: All algorithms share the exact same:
   - Problem instance representations (`VRPProblem`).
   - Evaluation pipeline (`calculate_fitness` and constraint checkers).
   - Solution decoders and repair operators.
   - Hardware environment and timeout thresholds.

---

## 2. Compared Algorithms

| Algorithm | Type | Key Hyperparameters |
|---|---|---|
| **Greedy NN** | Deterministic Constructive | Nearest-neighbor insertion by Euclidean travel time |
| **A\*** | Deterministic Heuristic Search | Admissible Euclidean distance-to-go heuristic |
| **Classical PSO** | Continuous Swarm Metaheuristic | Swarm=50, $w=0.729$, $c_1=1.494$, $c_2=1.494$ |
| **Genetic Algorithm (GA)** | Evolutionary Metaheuristic | Pop=50, Order Crossover (OX), Swap Mutation ($p_m=0.15$) |
| **Ant Colony (ACO)** | Probabilistic Swarm | Ants=30, $\alpha=1.0$, $\beta=2.0$, $\rho=0.10$ |
| **Standard QPSO** | Quantum-inspired Metaheuristic | Swarm=50, static $\alpha=0.75$, no local search |
| **Adaptive D-QPSO (Ours)** | Adaptive Quantum-inspired Swarm | Swarm=50, $\alpha \in [0.3, 1.0]$, diversity-triggered restarts, elite local search |

---

## 3. Statistical Testing Suite

Reporting mean metrics alone is insufficient to prove algorithmic superiority. We employ non-parametric statistical hypothesis testing:

### 3.1 Wilcoxon Signed-Rank Test (Pairwise)
- Evaluates whether the median difference between paired run outcomes of Adaptive D-QPSO and a rival baseline is statistically significant.
- Null hypothesis $H_0$: There is no significant difference in solution cost between Adaptive D-QPSO and the baseline.
- Significance threshold: $\alpha = 0.05$ (reject $H_0$ if $p < 0.05$).

### 3.2 Friedman Omnibus Test (Multi-Algorithm Ranking)
- Ranks each algorithm $r_i^j$ across multiple problem instances/scenarios.
- Computes the Friedman statistic:
  $$\chi_F^2 = \frac{12 N}{k(k+1)} \left[ \sum_{j=1}^k R_j^2 - \frac{k(k+1)^2}{4} \right]$$
  where $k$ is the number of algorithms, $N$ is the number of test runs, and $R_j = \frac{1}{N} \sum_i r_i^j$.

### 3.3 Nemenyi Post-Hoc Analysis
- Conducted if the Friedman test detects significant differences ($p < 0.05$).
- Determines the Critical Difference (CD) at significance level $\alpha$:
  $$CD = q_\alpha \sqrt{\frac{k(k+1)}{6N}}$$
- Two algorithms are significantly different if their average rank difference exceeds $CD$.

---

## 4. Benchmark Instance Sets

### Category A: Standard CVRPLIB Benchmarks
- Classical instances from the literature (Augerat Set A/B/P, TSPLIB95 format).
- Used to validate constraint satisfaction and convergence against known optima.

### Category B: Bhopal Urban Transportation Suite
- Grounded in realistic Bhopal geographic coordinates:
  - Central Depot: DB City Mall / Arera Hills.
  - Landmarks: New Market, MP Nagar, Habibganj, AIIMS, TT Nagar, Govindpura, Misrod, Mandideep, Berasia Road.
- Realistic speed limits and road connectivity.
- Scalability sweep: $n \in \{10, 25, 50, 100, 200, 500\}$ customers.
- Traffic scenarios: Normal ($\times 1.0$), Morning Peak ($\times 1.6$), Evening Peak ($\times 1.8$), Severe Congestion ($\times 2.2$), Road Closure ($\times \infty$).

---

## 5. Quantum Lab Experimental Protocol

To demonstrate quantum optimization concepts without misleading claims:
- Instances are formulated as **Quadratic Unconstrained Binary Optimization (QUBO)** for $n \in \{4, 5, 6\}$ customers:
  $$H = \sum_{i,j} Q_{ij} x_i x_j$$
- Solved on:
  1. **Exact Brute-Force**: Exhaustive $2^N$ evaluation to compute the true ground-state energy.
  2. **QAOA on Qiskit Aer Statevector Simulator**: Parameterized ansatz with $p = 2$ layers.
  3. **Simulated Annealing Fallback**: Classical thermal relaxation if Qiskit is not available.
  4. **Adaptive D-QPSO**: Validating that classical quantum-inspired heuristics scale seamlessly to practical fleet sizes.
