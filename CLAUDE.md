# CLAUDE.md

Context for Claude Code (and any other AI assistant) working in this repo.

## What this project is

UC Berkeley MEng capstone (Project 212, sponsor: U.S. Army Research Laboratory, Sep 2026 to May 2027): a **minimal simulation proof of concept** for objective-driven shared autonomy in UAS swarms. An operator states an objective; agents coordinate in a fully decentralized way to achieve it. Emphasis is on **architecture**, not on optimal algorithms or real hardware.

Advisors: Mark Mueller, Christian Brommer. Team: Yuki Kin (multi-agent autonomy / consensus), Maria Vlahos (autonomy hierarchy: goal -> tasks -> success metrics), Leonard "Leo" Wang (communications).

## Advisor guidance (keep this in mind when proposing changes)

- Start from a concrete scenario (current ones: 2D search for a missing person after a disaster, and Mission 1: search and guided evacuation from an earthquake-damaged building).
- Stay at the right level of abstraction: not low-level control (no MPC, no vehicle dynamics), not high-level LLM agents chatting with each other.
- Prefer no "judge" or leader nodes. Prefer probabilistic, gradient-based or learning-based coordination.
- Aim for fully decentralized operation with information propagating through the comms graph. Agents only observe the world partially.

## Core principles

- No leader drone, central node, judging node or ground station in the decision loop.
- Every drone runs the same algorithm and uses only its neighbours N_i, never the whole network.
- Decisions propagate hop by hop. Continuous-time model, simulated with a consistent discretization.

## Code conventions

- Python >= 3.10, dependencies kept minimal: `numpy`, `pyyaml`, optional `matplotlib`.
- Package lives in `src/swarm/`. Each module owns one layer:
  - `config.py`: scenario parameters (one dataclass), loaded from YAML
  - `comms.py`: who can talk to whom at each step, and message delivery
  - `consensus.py`: pure math functions, no side effects
  - `sim.py`: loop, events, metrics, scenario runners (`SCENARIOS` registry)
  - `viz.py`: figures, only module that imports matplotlib
  - `tools/*.html`: standalone browser demos (see Status below); `docs/mission1_explainer.html` is a doc page
  - planned: `operator.py` (objectives to initial priors), `world.py` (ground truth, sensor model), `agent.py` (one agent's belief and decisions, using only local info plus messages)
- An agent must never read another agent's state directly. Everything goes through the comms graph (`comms.deliver()`).
- All randomness goes through a seeded `numpy.random.Generator` passed in from the sim. Runs must be reproducible from the config seed.
- Scenarios are YAML in `configs/`. New behavior should be switchable from config, not hard-coded. Unknown config keys are an error.
- Type hints and short docstrings on public functions. Comment code with the equation each block implements; keep it readable for teammates.

## Consensus model (step 1, implemented; reference: Olfati-Saber, Fax, Murray, Proc. IEEE 2007)

- Drones = nodes, comms links = edges. Unit-disk graph: link iff ||p_i - p_j|| <= r_c (later: plus line-of-sight, buildings).
- Adjacency A = [a_ij], degree D = diag(sum_j a_ij), Laplacian L = D - A. Undirected for now (a_ij = a_ji), but each link is stored as two directed edges so asymmetric links can be added later.
- Edge weights: a_ij = exp(-d_ij^2 / sigma^2) inside r_c, 0 outside.
- Law, with information weight gamma_i, normalization by neighbour count and comms delay tau:
    gamma_i * dx_i/dt = (1/|N_i|) * sum_{j in N_i} a_ij * ( x_j(t - tau) - x_i(t - tau) )
  Matrix form: dx/dt = -Lhat x(t - tau), Lhat = Gamma^{-1} DeltaN^{-1} L, DeltaN = diag(|N_i|).
- Known results, all checked in `tests/test_sim.py`:
  * Undirected + connected => consensus on alpha = sum_i w_i x_i(0) / sum_i w_i, w_i = gamma_i * |N_i|.
  * Rate set by mu_2 of Lhat. Lhat is similar to symmetric W^{-1/2} L W^{-1/2}, W = Gamma*DeltaN, so its eigenvalues are real and >= 0.
  * Delay stability: consensus iff tau < pi / (2 * mu_n). A moderate delay (mu_2 tau < 1/e) speeds up the slow mode.
  * Euler: dt must be << 2 / mu_n.
- Isolated drones (|N_i| = 0) hold their value.
- Next stages: vector states x_i in R^m, switching/dynamic topology, sensor inputs that change x over time, temporal weighting of old info (x e^(-age/T)), link dropouts, node capacity limits, minimum separation d_min, 2D search-and-rescue with belief maps b(c) = P(person in cell).

## Status: what exists so far (Oct 2026)

| Piece | Where | State |
|---|---|---|
| Step 1 scalar consensus (delay, weights, normalization) | `src/swarm/`, `configs/consensus_*.yaml`, `docs/consensus_step1.md`, ADR 0001 | done, tested |
| Consensus Lab (browser) | `tools/consensus_lab.html` | done |
| Mission 1 evacuation demo (browser) | `tools/mission1_evacuation.html`, `docs/mission1_evacuation.md`, ADR 0002 | done (prototype) |
| Mission 1 explainer page | `docs/mission1_explainer.html` | done |
| Python port of Mission 1 (`world.py`, `agent.py`, `operator.py`) | planned | not started |
| ROS 2 / Gazebo integration | ADR 0002 | later |

Browser demos are single HTML files with inline JS and CSS, no build step and no server. Open them directly in a browser. They follow the same rules as the Python code (agents use only their own sensing and messages, seeded RNG via mulberry32), but they are not built on the Python package. Their numbers are illustrations, not results. `tests/test_tools_html.py` statically checks every `tools/*.html`: every `$("id")` has an element, the page has a `<title>`, and there are no external `<script src>`.

### Consensus Lab (`tools/consensus_lab.html`)

An interactive version of the step 1 law, extended past the Python code:
- Up to 15 drones (a third are grey backups, so 5 at 15), sensor types, min separation d_min (non-overlapping d_min/2 safety circles), comms radius r_c, falloff σ, per-drone link capacity K, delay τ, packet loss, age fading T, information weight γ, solver dt and playback speed.
- Roles: Task 1, Task 2 (a linked pair), backups, out of service. Failure injection (malfunction or comms lost) at a set time; the nearest backup takes over after 2 s.
- Continuous-time comms: links fail and recover, messages stream along both directions of each link (balanced digraph, drawn as two arrows). There is an option to highlight links used in the last 5 s (jointly connected).
- Live views: swarm diagram, fleet status boxes, x_i(t) with predicted α, disagreement on a log scale with the e^(−μ₂t) slope, the per-drone equation with a row per neighbour, live A / D / L matrices, and a comms transcript.

### Mission 1: search and guided evacuation (`tools/mission1_evacuation.html`)

Full description: `docs/mission1_evacuation.md`. Plain-language walkthrough: `docs/mission1_explainer.html`. This is a visual architecture prototype. It has no averaging consensus; "consensus" means every drone's copy of the task tree reaches root done.

- **World.** 200 m × 200 m, 2 m occupancy grid. A 78 m building with 4 rooms (one cross wall, a door in each half) and seeded rubble. There are 4 outer openings, none known in advance: S and N are usable, W is blocked by rubble inside, and E is blocked by a facade collapse outside. Launch pad A (every drone starts here), charging pad B, a designated safe area, a known no-go geofence (a drone that enters is lost), a draggable no-GPS zone, and an optional aftershock that drops debris on an active route. People wander off route. Scenario A has one person; scenario B has three.
- **Swarm.** 4 to 10 drones (default 6). Four leaves are open at the start (2 outside, 2 inside), so 4 drones launch and the rest wait docked as backups. Types: Scout (lidar mapper), Seeker (thermal searcher), Watcher (outside inspector), Herald (guide: light + speaker), Relay (long-range radio). All carry every sensor at different quality levels, so capabilities overlap. Broadcast state vector: ID, heading, p̂ ± σ, v, battery, health, N_i, leaf, capabilities, root hash, network flags.
- **Task tree.** A binary Merkle tree (BLAKE3 256-bit hashes, implemented inline and checked against the reference test vectors), one copy per drone, built only from neighbours' messages. Root "Everyone in the safe area" → Find people (Search inside; Track P_k per find) / Get them out (Escape routes: Map inside + routes, Inspect outside SW / NE; Guide P_k per find). Neighbours compare root hashes and send only the branches that differ, at most N neighbours per hop, best-connected first.
- **Merge rule** (the same everywhere): the newer claim wins for the same drone; release and claim are ordered by time. When two live claims collide, the better-suited drone keeps the leaf, with the lower ID winning a tie. A stale claimant (silent for 2 × the heartbeat timeout) loses, and "done" never reverts.
- **Claiming.** score = priority × capability fit × battery factor − distance cost. A free drone runs a greedy assignment over the open leaves and the free teammates it has heard from recently, and claims its own pick if score ≥ the claim threshold. It keeps the leaf until the leaf's success criteria hold. The exceptions are a swap in radio range (summed score gain ≥ 0.15), priority preemption (a leaf open for 30 s with priority higher by ≥ 0.15), and low battery (release the leaf and fly to the nearest pad). The operator sets only the leaf-family priorities (search, mapping, inspection, guidance, comms/localization).
- **Edge cases → local sub-leaves.** Relay for D_k, Localize D_k (σ > 2.5 m) and Re-map route P_k. For 15 s only drones within 2 hops may claim them; after that the sub-leaf escalates to everyone.
- **Connectivity.** Unit-disk digraph plus walls: a link exists iff d ≤ min(r_i, r_j) · k^walls, with hysteresis to 112 %, and a_ij = e^(−d²/σ²). Critical links come from the reported neighbour graph, and a drone never leaves a critical neighbour's range. A drone held back sends `pull` and its neighbour follows. Backups and drones flying home stay as bridges. A lost drone flies to a teammate's position, predicted from the stored message history (last H messages per teammate). Measured: 20 headless runs all completed; the flying net was split about 5 % of flight time.
- **Localization.** σ = 1 m with GPS; dead reckoning in the no-GPS zone (dσ/dt = 0.03 + 0.04|v|). A range fix needs 2 neighbours; range + bearing needs 1 in line of sight. No mapping while σ > 3 m.
- **Abort.** Forwarded hop by hop to the uninformed neighbour with the most neighbours. Every drone drops its leaf, cancels its root and returns to pad A.
- **Failures.** Crash, navigation fault into the no-go zone, lidar, radio or battery. Each is scheduled or injected now on any drone.
- **Views.** Map layers (selected drone / swarm union / ground truth), fleet state vectors, root hashes, the tree, the claim matrix (who each drone thinks holds each leaf), leaf scores, knowledge of teammates, the comms graph, mission-brief success metrics (search & tracking, mapping & routes, guidance, comms & coordination, overall), the event log and the comms transcript.
- **Module mapping for the Python port** (ADR 0002): ground truth, people and zones → `world.py`; knowledge, tree, claiming and behaviours → `agent.py`; links, critical links, hop-by-hop merge and abort → `comms.py`; root goal and leaf priorities → `operator.py`. After that, ROS 2: one node per drone, topics `state`, `map_delta`, `person`, `tree_delta`, `abort`, plus a comms-emulation node.

## Next steps

1. Port Mission 1 to Python with tests (`world.py`, `agent.py`, `operator.py`, extend `comms.py`), configurable from YAML; then the HTML becomes a viewer or a sketchpad.
2. Python consensus roadmap: moving drones with switching topology, vector states and belief maps, age weighting and packet loss (see `docs/roadmap.md`).
3. Baselines for comparison (fixed roles, centralized), and stress-test configs.
4. Later: ROS 2 / Gazebo (ADR 0002).

## Commands

```bash
pip install -e ".[dev,viz]"
pytest                                   # run tests
ruff check src tests                     # lint
python -m swarm --config configs/consensus_static.yaml --plot
# browser demos: open tools/consensus_lab.html or tools/mission1_evacuation.html directly
# planned: configs/search_rescue_2d.yaml, configs/stress_failures.yaml
```

## When making changes

- Add or update a test in `tests/` for any new behavior.
- Significant design choices go in `docs/decisions/` as a short ADR (copy `0000-template.md`).
- Keep `README.md` and `docs/architecture.md` in sync with the code layout.
- Generated output goes to `outputs/` (git-ignored). Figures meant for docs go in `docs/figures/`.
