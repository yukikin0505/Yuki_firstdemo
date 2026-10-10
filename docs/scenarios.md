# Scenarios

## S0: static scalar consensus (implemented)

`configs/consensus_static.yaml`, `configs/consensus_weighted.yaml`

Eight static drones in a 100 m x 100 m area agree on one scalar with comms delay. This tests the
consensus building block that the search scenario will use for belief fusion. Details and results are
in [consensus_step1.md](consensus_step1.md).

## S1: 2D post-disaster search (planned, reference scenario)

A person is missing somewhere in a sector.

- **Operator:** gives one objective, a search region plus a priority. No per-drone commands.
- **World:** 2D grid. The target is in one cell (static at first).
- **Drones:** limited sensor footprint with detection and false-alarm probabilities, and limited
  radio range r_c.
- **Belief:** each drone keeps a map b(c) = P(person in cell c). It updates the map from its own
  observations (Bayes) and fuses it with its neighbours via graph-Laplacian consensus.
- **Decisions:** each drone moves to reduce uncertainty, using only local information. There is no
  leader or judging node.
- **Metrics:** time to detection, coverage, belief error vs ground truth, messages sent, and
  operator actions needed.

## M1: search and guided evacuation from a damaged building (browser prototype)

[`tools/mission1_evacuation.html`](../tools/mission1_evacuation.html), details in
[mission1_evacuation.md](mission1_evacuation.md).

After an earthquake, four heterogeneous drones (two start inside, two outside) explore a building
with an unknown layout. They find survivors and lead them to the designated exit and then to a safe
assembly point. Exits and corridors may be blocked, and some of this is only visible from outside.
GPS is missing in a draggable zone, comms are attenuated by walls, a no-go zone kills any drone that
enters, and failures can be injected. Each drone allocates tasks (search, map, check exits, relay,
guide) from its own knowledge only. There is no consensus algorithm yet.

## S2: stress tests (planned)

The same as S1 with injected events: drone failures, communication blackouts (a region or a time
window), packet loss, GPS loss.
- **Question:** does the swarm keep pursuing the objective, and how much do the metrics degrade?
