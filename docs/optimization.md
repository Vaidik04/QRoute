# Q-TRANSIT NEXUS — Optimization Algorithms & Architecture

This document describes the design, implementation, and theoretical foundations of the optimization algorithms implemented in **Q-TRANSIT NEXUS**.

---

## 1. Solution Representation: Random-Key Encoding

To bridge continuous metaheuristic search with combinatorial Vehicle Routing, we employ **random-key encoding**:

1. **Continuous Particle Space**: A particle position is a continuous vector $X_i \in [0, 1]^n$, where $n$ is the number of customer deliveries.
2. **Discrete Permutation Decoding**: The discrete permutation $\pi = (\pi_1, \pi_2, \dots, \pi_n)$ is obtained by sorting the indices in ascending order of their continuous values:
   $$\pi = \text{argsort}(X_i)$$
3. **Route Construction (Greedy Split)**: A greedy vehicle decoder sequentially packs customers from $\pi$ into vehicle tours respecting vehicle capacity $Q_k$ and time windows. When capacity is reached, a return arc to the depot is inserted and the next vehicle is dispatched.

---

## 2. Quantum-Behaved Particle Swarm Optimization (QPSO)

### Theoretical Foundation
In classical PSO, particles follow Newton's second law with position and velocity vectors. In **Quantum-behaved PSO (QPSO)** (Sun et al., 2004), particles move in quantum space with a delta-potential well centered at a local attractor point $P_{ij}$.

The particle state is described by a wave function $\psi(X)$. Upon measurement (collapse), the particle position updates as:

$$X_{ij}(t+1) = P_{ij}(t) \pm \alpha \cdot |mbest_j(t) - X_{ij}(t)| \cdot \ln(1/u)$$

Where:
- $u \sim U(0, 1)$ is a uniform random variable.
- The sign $\pm$ is chosen with equal probability ($0.5$).
- **Mean Best Position ($mbest$)**:
  $$mbest(t) = \frac{1}{N} \sum_{i=1}^{N} P_i(t)$$
- **Local Attractor ($P_{ij}$)**:
  $$P_{ij}(t) = \phi \cdot P_{i,\text{pbest},j}(t) + (1 - \phi) \cdot G_{\text{gbest},j}(t), \quad \phi \sim U(0, 1)$$
- **Contraction-Expansion Coefficient ($\alpha$)**: Controls the quantum tunneling radius and convergence rate.

---

## 3. The Proposed Contribution: Adaptive Discrete QPSO (Adaptive D-QPSO)

Standard QPSO with fixed $\alpha$ suffers from two classical pitfalls in discrete VRP spaces:
1. **Premature Convergence**: Rapid collapse into local optima during early iterations.
2. **Stagnation in Deep Basins**: Loss of exploration capability in later iterations.

To resolve these, **Adaptive D-QPSO** introduces four synchronized mechanisms:

### 3.1 Adaptive $\alpha$ Annealing
Rather than a static parameter, $\alpha$ decays linearly with iteration progress, supplemented by a dynamic feedback loop:

$$\alpha(t) = \alpha_{\max} - (\alpha_{\max} - \alpha_{\min}) \cdot \frac{t}{T_{\max}} + \Delta\alpha(t)$$

During exploration ($t \ll T_{\max}$), large $\alpha \approx 1.0$ enables broad quantum jumps. During exploitation ($t \to T_{\max}$), smaller $\alpha \approx 0.3$ performs fine-grained local tuning.

### 3.2 Population Diversity Monitoring
Population diversity $D(t)$ is measured in normalized continuous space:

$$D(t) = \frac{1}{N \cdot \sqrt{n}} \sum_{i=1}^{N} \|X_i(t) - \bar{X}(t)\|_2, \quad \bar{X}(t) = \frac{1}{N} \sum_{i=1}^N X_i(t)$$

### 3.3 Multi-Tier Stagnation & Diversification
- If no improvement occurs for $W_{\text{stag}} = 15$ iterations:
  - **Severe Stagnation**: Restart the worst $\mu_{\text{restart}} = 20\%$ of particles with hybrid random-key initialization.
  - **Low Diversity ($D(t) < 0.05$)**: Apply Gaussian noise perturbation ($\sigma = 0.3$) to the bottom 50% of the population.

### 3.4 Interleaved Elite Local Search
Every $K = 10$ iterations, local search operators (intra-route 2-opt, Or-opt relocation, and inter-route cross-exchange) are executed on the top elite particles to refine routing topology.

---

## 4. Constraint Handling & Route Repair

When decoded permutations yield over-capacity tours or orphaned customers:
1. **Violation Detection**: Capacity overloads, missing customer visits, and road-closure crossings are identified.
2. **Customer Extraction**: Offending visits are removed into an unserved pool.
3. **Cheapest Feasible Insertion**: Customers from the pool are re-inserted into routes at positions minimizing incremental travel time while maintaining feasibility.
4. **Large-$M$ Penalty Fallback**: If an instance cannot be repaired, a prohibitive penalty $M = 10^6$ is assigned to guide the swarm away from infeasible space.

---

## 5. Rolling-Horizon Dynamic Re-Optimization

In dynamic urban traffic environments, real-time disturbances (accidents, congestion spikes, road closures) disrupt scheduled routes:

```
[Customer 1 (Served)] -> [Customer 2 (Served)] | [Customer 3] -> [Customer 4] -> [Depot]
|<--------- FROZEN PREFIX --------->|          |<------- RE-OPTIMIZED SUFFIX ------->|
```

1. **Prefix Freezing**: All stops already completed by a vehicle are locked invariant.
2. **Dynamic Sub-Problem Construction**: Unvisited stops are extracted into a reduced VRP sub-problem, updating vehicle locations and residual capacities.
3. **Matrix Update**: Multipliers received from Member 2 (Traffic Module) are injected into the cost matrix.
4. **Route Stability Objective**:
   $$F' = F + w_s \cdot C_{\text{stability}}$$
   Minimizes disruption to drivers by penalizing deviations from the reference plan.
5. **Real-time Recovery**: Re-optimization executes in $< 100\text{ ms}$, ensuring instant response for telematics systems.
