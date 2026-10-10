# Mission 1: decentralized multi-UAV search and guided evacuation

Interactive demo: open [`tools/mission1_evacuation.html`](../tools/mission1_evacuation.html) in a
browser. It runs entirely in the page (no server, no build step).

<p align="center"><img src="figures/mission1_map.png" width="60%" alt="Mission 1 demo map at about 3 minutes"></p>

This is a **visual architecture prototype**. Coordination is deliberately simple: no consensus
algorithm, no learning. The point is to show the pieces of Mission 1 working together under
decentralization, partial observability and failures, so we can decide what the Python and
Gazebo/ROS 2 versions need to contain. See [ADR 0002](decisions/0002-mission1-browser-prototype.md).

## Setting

A multi-story building has been damaged by an earthquake. Its interior layout is unknown, some
corridors and exits are blocked, and GPS and radio are unreliable. The demo models one floor in 2D.

| Element | In the demo |
|---|---|
| Area | 200 m x 200 m, occupancy grid of 2 m cells |
| Building | 98 m x 90 m frame in the middle, 8 rooms, two 8 m corridors, seeded rubble piles |
| Drone entry | window in the south wall, bottom left (drones only, too high for people) |
| Exits | **Exit A** top right (designated, open). **Exit B** east (open inside, facade collapse outside). **Exit C** north (rubble inside) |
| Launch / charging pad | bottom-left corner |
| Safe assembly point | top-right corner |
| No-go zone | circle in the bottom-right corner (fire / collapse). A known geofence; a drone that enters is lost |
| No-GPS zone | draggable circle, default over the NE part of the building |
| Survivors | 1 to 4, one per room, seeded. Optionally one is injured and cannot walk |
| Aftershock | at a set time, drops rubble on the route a guide is using (only if another way out still exists) |

## Swarm

Four heterogeneous drones. All carry the same kit (onboard GPU, obstacle avoidance, light, speaker,
optical + thermal + lidar), but at different quality levels. The capabilities partly overlap, so
the first allocation follows capability matching, and any task can still be picked up by a second
drone after a failure.

| Drone | Role | thermal | optical | lidar | beacon (light + speaker) | radio | GPU | v<sub>max</sub> | Start |
|---|---|---|---|---|---|---|---|---|---|
| D0 Scout | lidar mapper | 0.35 | 0.6 | **1.0** | 0.35 | 0.5 | 0.6 | 4.5 m/s | inside |
| D1 Seeker | thermal searcher | **1.0** | 0.8 | 0.5 | 0.5 | 0.5 | **1.0** | 3.5 m/s | inside |
| D2 Herald | guide | 0.6 | 0.6 | 0.45 | **1.0** | 0.6 | 0.7 | 3.0 m/s | outside |
| D3 Relay | long-range radio | 0.3 | 0.9 | 0.7 | 0.4 | **1.0** | 0.5 | 5.0 m/s | outside, 48 % battery |

Sensor ranges follow from the capability: lidar 6 + 14·lidar m, thermal 5 + 13·thermal m, optical
4 + 8·optical m, radio r<sub>c</sub>·(0.6 + 0.6·radio).

### State vector

Each drone broadcasts its own state, and it is the only thing other drones know about it:

| Field | Meaning |
|---|---|
| node ID | i |
| r | heading (yaw) |
| p̂, σ | estimated position and its uncertainty (true p is used only by the simulator) |
| v | velocity |
| battery | percent |
| health | ok / charging / lost (plus faults: lidar, radio, navigation) |
| N<sub>i</sub> | current neighbours (links that are up) |
| task, goal | current claim and where it is heading |
| caps | capability vector (changes when a sensor fails) |

## Tasks (objective -> tasks -> metrics)

Operator objective: **locate survivors and assist them in reaching safe exits.** The operator only
sets four priorities w (sliders). No per-drone commands.

| Task family | Tasks in the demo | Required capabilities | Success metric |
|---|---|---|---|
| Search and tracking | `SEARCH`, `SEARCH2` | thermal 0.5, optical 0.2, GPU 0.3 | % of interior floor thermal-searched, survivors found |
| Mapping and route assessment | `MAP_IN` (lidar frontiers), `MAP_EXT` (look at each exit from outside) | lidar 0.7, optical 0.15, GPU 0.15 / optical 0.5, lidar 0.3, radio 0.2 | % mapped, exits assessed from both sides |
| Active guidance | `GUIDE:s`, one per walking survivor found | beacon 0.7, thermal 0.15, optical 0.15 | survivors at the assembly point |
| Communication and coordination | `RELAY` (hold the link through the entry window) | radio 0.85, optical 0.15 | connectivity, mean information age |

An exit is assessed when its inner apron (seen by inside drones) and its outer apron (seen by an
outside drone) are both observed. Exit B looks fine from inside and is only found blocked from the
street. This is the "match interior to exterior exits" part of the mission.

## How a drone decides (same algorithm on every drone)

Once per second, each drone builds the task list from **its own knowledge** and solves a small
assignment over the teammates it has heard from in the last few seconds:

    u(j, task) = w_task * (req_task . caps_j) * battery_factor_j - 0.35 * dist / 200 + bonus

The bonus is +0.12 for the task j already claims, or +0.62 while j is actively leading that
survivor. The search is exhaustive (4 drones, about 10 tasks): each task gets at most one drone and
the total utility is maximised. The drone acts on its own row only. There is no consensus step. If
two drones heard different things, both can claim the same task for a while. The demo shows this
as a *task conflict*. It resolves once their knowledge agrees again, and the lower ID keeps a
contested guidance task. A drone keeps a task for at least 6 s while the task still exists, so
stale information cannot make it flip back and forth.

Behaviour per task: Dijkstra/A* on the drone's own map (unknown cells allowed at a higher cost,
known obstacles and the geofence blocked). Guides walk through approach, then contact (light and
speaker on), then lead. While leading they re-plan the walking route every 3 s and report when new
debris or a blocked exit forces a different route. A guide notices a survivor who leaves the route
by more than 4.5 m and goes back to them. The survivor follows the guide when they can see the
light (11 m, line of sight) or hear the speaker (6 m, around corners).

A drone below 20 % battery returns to the pad, charges and rejoins. When a drone's own knowledge
says the mission is over (floor searched, every known survivor safe or reported, all exits
assessed), it returns and lands.

## Communication

- Unit-disk digraph as in step 1: a link exists iff d<sub>ij</sub> ≤ min(r<sub>i</sub>, r<sub>j</sub>) · k<sup>w</sup>,
  where w is the number of walls the straight line crosses and k is the range kept per wall.
  Weights a<sub>ij</sub> = exp(−d²/σ²), drawn as arrow thickness. Each link is two directed lanes.
- Packet loss: each link is a two-state Markov chain (mean outage 1 s).
- Every τ seconds, each drone merges the snapshot of each neighbour's knowledge: drone states
  (newest stamp wins), map cells (newest stamp wins), searched cells (OR), survivor reports
  (newest sighting wins, status only moves forward found -> guiding -> evacuated). Information
  therefore moves exactly one hop per τ.
- Heartbeat: a teammate not heard from for `hb` seconds is left out of the allocation.
- At t = 0 every drone knows the roster, the outer walls (seen from the street) and the entry
  window. Nothing else.

## Localization

Outside the no-GPS zone, σ = 1 m. Inside it, the drone dead-reckons: dσ/dt = 0.03 + 0.04 |v|, and
the estimate drifts by a random walk of that size. Every 0.5 s it tries a cooperative fix: one
neighbour with σ ≤ 2 m and line of sight (range + bearing), or two such neighbours (range-only
trilateration, no line of sight needed). While σ > 3 m the drone stops adding to its map.

## Failure injection

| Type | Effect | What to look for |
|---|---|---|
| Crash | drone stops, silent | teammates notice after the heartbeat timeout and re-allocate its task |
| Into no-go | navigation fault, flies into the no-go zone | lost on entry; same as a crash for the others |
| Lidar | lidar capability 1.0 -> 0.05 | capability match changes in its next broadcast; mapping goes to someone else |
| Radio | radio off | it keeps working on what it knows; the others re-plan without it; duplicate work shows up |
| Battery | battery drops to 19 % | returns to the pad, charges, rejoins |

Scheduled by default: D1 (the best searcher) crashes at 150 s.

## What it does not model (yet)

Vehicle dynamics and control, 3D and stairs, realistic radio propagation (only a per-wall factor),
sensor noise beyond detection probability and position error, survivors who talk back, and
human operators in the loop after the objective. Moving this into Python (`world.py`, `agent.py`,
`operator.py`) and later Gazebo/ROS 2 is in ADR 0002.
