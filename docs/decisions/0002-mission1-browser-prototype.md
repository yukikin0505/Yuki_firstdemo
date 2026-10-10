# 0002: Mission 1 as a browser prototype first, Gazebo / ROS 2 later

- **Status:** proposed
- **Date:** 2026-10-10
- **Deciders:** Yuki Kin (proposed), team to confirm

## Context

Mission 1 (search and guided evacuation from a damaged building) needs four heterogeneous drones,
an unknown interior, blocked exits, unreliable GPS and comms, drone failures and survivors who move.
We want to agree on the architecture (state vector, task list, messages, allocation rule) before we
invest in a full simulator. Gazebo with ROS 2, possibly with PX4 SITL or a Python UAV library, was
suggested as the target environment.

A Gazebo + ROS 2 stack takes days to set up for everyone, needs a Linux machine or VM, and mixes
vehicle dynamics into questions that are about coordination. Advisor guidance says to stay above
low-level control.

## Decision

1. Build Mission 1 first as a standalone HTML demo (`tools/mission1_evacuation.html`), in the same
   style as `tools/consensus_lab.html`. It is 2D, grid-based, with no vehicle dynamics and no
   consensus algorithm. Allocation is a per-drone greedy assignment over local knowledge.
2. Keep every rule in the demo written so that it maps 1:1 onto the planned Python modules:
   - `world.py`: truth grid, survivors, no-go and no-GPS zones, aftershock
   - `agent.py`: knowledge (map, searched cells, teammate states, survivor reports), allocation, behaviours
   - `comms.py`: unit-disk links with a per-wall range factor, packet loss, hop-by-hop merge
   - `operator.py`: objective and task priorities
3. Treat Gazebo / ROS 2 as the later integration step, after the Python version exists:
   - one ROS 2 node per drone, running the same `agent.py` logic
   - topics per message type: `state` (the broadcast state vector), `map_delta`, `survivor`, `claim`
   - a comms-emulation node that drops or delays messages by distance and walls, so the
     decentralization is real, not assumed
   - Gazebo for the building and sensors. PX4 SITL only if we need flight dynamics, which the
     project scope says we do not.

## Alternatives considered

- **Go straight to Gazebo + ROS 2:** most realistic, but slow to iterate on coordination logic and
  heavy to run for the whole team. Better as the final demonstrator.
- **Python + matplotlib only:** matches the current code base, but interactive failure injection
  and dragging zones are awkward. We will still port the logic there, with tests.
- **A UAV library such as gym-pybullet-drones:** good for control and RL, but too low-level for
  our questions.

## Consequences

- Teammates and advisors can try the scenario in a browser today, with no install.
- The demo's JavaScript is not tested like the Python package. Only static checks run
  (`tests/test_tools_html.py`). Numbers from the demo are illustrations, not results.
- Logic now lives in two places until the Python port is done. Port it soon, then make the HTML a
  viewer for Python output, or keep it as a sketchpad.
- Revisit this decision when the Python `agent.py` exists.
