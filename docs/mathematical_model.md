# Q-TRANSIT NEXUS — Mathematical Formulation & Optimization Model

This document outlines the formal mathematical model governing the optimization engine of **Q-TRANSIT NEXUS**.

---

## 1. Problem Notation

Let $G = (V, E)$ be a complete directed graph where:
- $V = \{0\} \cup C$ represents the set of nodes, with node $0$ denoting the central depot and $C = \{1, 2, \dots, n\}$ denoting the set of customer locations.
- $E = \{(i, j) : i, j \in V, i \neq j\}$ is the set of directed edges (arcs) connecting nodes.
- $K = \{1, 2, \dots, m\}$ is the fleet of available vehicles.

### Parameters
| Symbol | Description | Domain |
|---|---|---|
| $Q_k$ | Maximum cargo load capacity of vehicle $k \in K$ | $\mathbb{R}^+$ |
| $d_i$ | Demand of customer $i \in C$ ($d_0 = 0$) | $\mathbb{R}^+$ |
| $s_i$ | Service duration at customer $i \in C$ ($s_0 = 0$) | $\mathbb{R}^+$ |
| $[e_i, l_i]$ | Earliest and latest allowed arrival time window for customer $i$ | $\mathbb{R}^+ \times \mathbb{R}^+$ |
| $p_i$ | Priority ranking of customer $i$ | $\{1, 2, 3, 4, 5\}$ |
| $c_{ij}^d$ | Distance between nodes $i$ and $j$ | $\mathbb{R}^+$ |
| $c_{ij}^t(\tau)$ | Time-dependent travel time departing node $i$ at time $\tau$ | $\mathbb{R}^+$ |
| $\mu_{ij}$ | Traffic congestion multiplier on arc $(i, j)$ | $[1.0, \infty]$ |

### Decision Variables
- $x_{ijk} \in \{0, 1\}$: Binary variable equal to $1$ if vehicle $k$ traverses arc $(i, j)$, and $0$ otherwise.
- $t_{ik} \ge 0$: Continuous variable representing arrival time of vehicle $k$ at node $i$.
- $u_{ik} \ge 0$: Cumulative load carried by vehicle $k$ after visiting node $i$.

---

## 2. Multi-Objective Function

The optimization engine evaluates candidate route solutions via a weighted composite fitness function:

$$\min \quad F = w_t \cdot C_t + w_d \cdot C_d + w_c \cdot C_c + w_r \cdot C_r + P$$

Subject to $\sum_{m \in \{t, d, c, r\}} w_m = 1.0$ and $w_m \ge 0$.

### Component Definitions

1. **Travel Time Cost ($C_t$)**:
   $$C_t = \sum_{k \in K} \sum_{(i,j) \in E} x_{ijk} \cdot c_{ij}^t(t_{ik})$$

2. **Distance Cost ($C_d$)**:
   $$C_d = \sum_{k \in K} \sum_{(i,j) \in E} x_{ijk} \cdot c_{ij}^d$$

3. **Congestion Exposure Cost ($C_c$)**:
   $$C_c = \sum_{k \in K} \sum_{(i,j) \in E} x_{ijk} \cdot \left(\mu_{ij} - 1.0\right) \cdot c_{ij}^t$$

4. **Risk and Reliability Cost ($C_r$)**:
   Penalizes delivery lateness weighted by customer priority:
   $$C_r = \sum_{k \in K} \sum_{i \in C} p_i \cdot \max\left(0, t_{ik} - l_i\right)$$

5. **Constraint Violation Penalty ($P$)**:
   $$P = M \cdot \left( \sum \text{Capacity Overload} + \sum \text{Unvisited Customers} + \sum \text{Closure Traversals} \right)$$
   where $M = 10^6$ is the large-$M$ penalty coefficient.

---

## 3. Constraints

### 3.1 Routing & Flow Conservation
Each customer is served exactly once by one vehicle:
$$\sum_{k \in K} \sum_{j \in V, j \neq i} x_{ijk} = 1 \quad \forall i \in C$$

Flow conservation at every customer node:
$$\sum_{i \in V, i \neq j} x_{ijk} - \sum_{l \in V, l \neq j} x_{jlk} = 0 \quad \forall j \in C, \forall k \in K$$

Every vehicle departs from and returns to the central depot:
$$\sum_{j \in C} x_{0jk} \le 1 \quad \forall k \in K$$
$$\sum_{i \in C} x_{i0k} = \sum_{j \in C} x_{0jk} \quad \forall k \in K$$

### 3.2 Vehicle Capacity
Vehicle load accumulates along the tour and must not exceed vehicle capacity:
$$u_{jk} \ge u_{ik} + d_j - Q_k (1 - x_{ijk}) \quad \forall (i, j) \in E, i \neq 0, \forall k \in K$$
$$d_i \le u_{ik} \le Q_k \quad \forall i \in C, \forall k \in K$$

### 3.3 Subtour Elimination & Time Windows
Arrival time propagation:
$$t_{jk} \ge t_{ik} + s_i + c_{ij}^t(t_{ik}) - M' (1 - x_{ijk}) \quad \forall (i, j) \in E, \forall k \in K$$

Time window constraints (with optional early waiting):
$$e_i \le t_{ik} \le l_i \quad \forall i \in C, \forall k \in K$$

### 3.4 Road Availability & Dynamic Closure
If edge $(i, j)$ is closed by the traffic module ($\mu_{ij} = \infty$):
$$x_{ijk} = 0 \quad \forall k \in K$$

---

## 4. Multi-Objective Weight Profiles

The platform supports 5 operational profiles:
- **Fastest** ($w_t=0.60, w_d=0.15, w_c=0.20, w_r=0.05$): Minimizes time during high-urgency operations.
- **Balanced** ($w_t=0.35, w_d=0.35, w_c=0.20, w_r=0.10$): Standard logistics compromise.
- **Green** ($w_t=0.20, w_d=0.55, w_c=0.15, w_r=0.10$): Minimizes fuel consumption and emissions.
- **Reliable** ($w_t=0.30, w_d=0.20, w_c=0.15, w_r=0.35$): Guarantees strict on-time arrival for high-priority stops.
- **Emergency** ($w_t=0.70, w_d=0.10, w_c=0.10, w_r=0.10$): Maximum priority dispatch.

---

## 5. Algorithmic Formulation: Adaptive D-QPSO with Quantum Tunneling

### 5.1 Quantum Delta-Potential Well Dynamics
In continuous random-key space $[0, 1]^n$, particle position $x_i$ evolves under a delta potential well centered at local attractor $p_i$:

$$p_{ij}(t) = \phi_j \cdot \text{pbest}_{ij}(t) + (1 - \phi_j) \cdot \text{gbest}_j(t), \quad \phi_j \sim U(0, 1)$$

Position update:
$$x_{ij}(t+1) = p_{ij}(t) \pm \alpha(t) \cdot |m_{\text{best}, j}(t) - x_{ij}(t)| \cdot \ln\left(\frac{1}{u}\right), \quad u \sim U(0, 1)$$

Where mean best position:
$$m_{\text{best}}(t) = \frac{1}{N} \sum_{i=1}^N \text{pbest}_i(t)$$

### 5.2 Multi-Feedback Alpha Annealing
$$\alpha(t) = \text{clip}\left( \alpha_{\max} - (\alpha_{\max} - \alpha_{\min}) \cdot \frac{t}{T} + \Delta\alpha_{\text{stag}} + \Delta\alpha_{\text{div}}, \quad \alpha_{\min}, \alpha_{\max} \right)$$
- $\Delta\alpha_{\text{stag}} = c_{\text{stag}} \cdot \text{stagnation\_counter}$
- $\Delta\alpha_{\text{div}} = c_{\text{div}} \cdot \max\left(0, 1 - \frac{D(t)}{D_{\text{threshold}}}\right)$

### 5.3 Quantum Tunneling via Cauchy Perturbation
To escape deep local potential wells, stagnant particles undergo heavy-tailed Cauchy mutations:
$$x_{\text{tunnel}} = \text{clip}\left(x_i + \text{Cauchy}(0, \sigma) \odot |g^* - x_i|, \quad 0, 1\right)$$
Simultaneously, Opposition-Based Learning (OBL) evaluates dual states:
$$\tilde{x}_j = 1.0 - x_j$$

---

## 6. Elite Variable Neighborhood Descent (VND)

The discrete solution space is polished through a systematic Variable Neighborhood Descent:

$$N_1 (\text{2-opt}) \longrightarrow N_2 (\text{Or-opt}_{1,2,3}) \longrightarrow N_3 (\text{Relocate}) \longrightarrow N_4 (\text{Swap}) \longrightarrow N_5 (\text{2-opt}^*) \longrightarrow N_6 (\text{CROSS-exchange})$$

- **Or-opt**: Contiguous blocks of length $L \in \{1, 2, 3\}$ relocated within or between routes.
- **2-opt\***: Route tails swapped across vehicles: $(0..a_i) + (b_{j+1}..0)$ and $(0..b_j) + (a_{i+1}..0)$.
- **CROSS-exchange**: Sub-segments of lengths up to $L=2$ swapped between two routes with capacity checks.

---

## 7. Quantum Lab: Exact QUBO & Statevector QAOA

### 7.1 QUBO Formulation
$$\min_{x \in \{0, 1\}^N} \quad x^T Q x$$
Where $x_{i, j} = 1$ if customer $i$ is placed at sequence position $j$.

### 7.2 Ising Hamiltonian Mapping
$$x_i = \frac{1 - s_i}{2}, \quad s_i \in \{-1, +1\}$$
$$H = \sum_{i < j} J_{ij} Z_i Z_j + \sum_i h_i Z_i + C_{\text{offset}}$$
where $J_{ij} = \frac{Q_{ij} + Q_{ji}}{8}$, $h_i = -\frac{Q_{ii}}{2} - \sum_{j \neq i} \frac{Q_{ij} + Q_{ji}}{4}$.

### 7.3 QAOA Quantum State Evolution
$$|\psi(\boldsymbol{\gamma}, \boldsymbol{\beta})\rangle = \prod_{l=1}^p e^{-i \beta_l \sum_k X_k} e^{-i \gamma_l H_C} |+\rangle^{\otimes n}$$
Ground state fidelity: $F = \sum_{z \in Z^*} |\langle z | \psi^* \rangle|^2$.
Approximation ratio: $r = \frac{E_{\max} - \langle H_C \rangle}{E_{\max} - E_{\min}}$.
