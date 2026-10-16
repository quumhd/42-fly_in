*This project has been created as part of the 42 curriculum by jdreissi*

# Fly-in

## Description

Fly-in is a drone routing simulator. A map file describes a network of zones
(nodes) linked by connections (edges). All drones start in a single start zone
and must reach a single end zone. The goal is to deliver **every** drone in as
few simulation turns as possible while respecting the rules of the network:

- **Zone capacity** – a zone holds at most `max_drones` drones at the end of a
  turn (default 1). The start and end zones have no limit.
- **Connection capacity** – a connection carries at most `max_link_capacity`
  drones during a turn (default 1).
- **Zone types** – entering a `normal` or `priority` zone takes 1 turn,
  entering a `restricted` zone takes 2 turns (the drone stays on the
  connection in between and may not wait there), and `blocked` zones can never
  be entered.

The program reads a map, plans a conflict-free route for every drone, and
prints the simulation turn by turn in the format required by the subject,
with colors taken from the map.

The project is written in Python 3.10+, fully object-oriented, type-hinted
(checked with mypy), flake8-compliant, and uses no graph library.

## Instructions

### Requirements

- Python 3.10 or later
- `flake8` and `mypy` (only needed for linting)

### Installation

```sh
make install
```

### Running

```sh
make run MAP=maps/easy/01_linear_path.txt
# or directly
python3 src/main.py --visualizer maps/easy/01_linear_path.txt
```

`make run` starts the program with the `--visualizer` flag, which shows the
drone counts behind every move and a summary at the end. Without the flag the
program prints only the moves, in exactly the format of the subject:

```sh
make no_visualizer MAP=maps/easy/01_linear_path.txt
# or directly
python3 src/main.py maps/easy/01_linear_path.txt
```

The flag can be placed before or after the map file.

Other Makefile rules:

| Rule                   | Effect                                                   |
|------------------------|----------------------------------------------------------|
| `make no_visualizer`   | Run the program without `--visualizer` (moves only)      |
| `make debug`           | Run the program under the Python debugger (`pdb`)        |
| `make clean`           | Remove `__pycache__` and `.mypy_cache`                   |
| `make lint`            | Run `flake8` and `mypy` with the flags from the subject  |

### Map format

```
nb_drones: 2

start_hub: start 0 0
end_hub: goal 4 0
hub: R 2 1 [zone=restricted color=red]
hub: A 1 -1
hub: B 3 -1
connection: start-R
connection: R-goal
connection: start-A
connection: A-B
connection: B-goal
```

- The first line must be `nb_drones: <positive integer>`.
- Zones: `start_hub:`, `end_hub:` or `hub:` followed by `<name> <x> <y>` and an
  optional `[zone=... color=... max_drones=...]` block.
- Connections: `connection: <zone1>-<zone2>` with an optional
  `[max_link_capacity=...]` block. Both zones must already be defined.
- Lines starting with `#` are comments.

Any invalid line stops the program with an error message giving the line
number and the cause.

### Output

One line per turn, listing every drone that moved during that turn. By default
the output is exactly the format of the subject:

```
D1-A D2-start-R
D1-B D2-R
D1-goal D2-goal
```

- `D<ID>-<zone>` – the drone is in `<zone>` at the end of the turn.
- `D<ID>-<connection>` – the drone is on its way to a restricted zone and is
  still on the connection.
- Drones that wait are not listed. Delivered drones disappear from the output.

With `--visualizer` every move is followed by the state of the zone or
connection it refers to, and a summary is printed at the end:

```
D1-A[1/1, normal] D2-start-R[1/1]
D1-B[1/1, normal] D2-R[1/1, restricted]
D1-goal[2] D2-goal[2]

Summary
  Drones:               2
  Total turns:          3
  Avg. arrival turn:    3.00
```

See [Visual representation](#visual-representation) for the meaning of the
brackets.

## Algorithm

The routing is done in three stages, in `src/pathfinding.py`.

### 1. Distance to the goal (Dijkstra, run once)

`get_distance_left` runs Dijkstra **backwards from the end zone** and stores,
for every reachable zone, the minimum number of turns needed to reach the goal
on an empty map. Restricted zones count as 2 turns, blocked zones are skipped.
If the start zone is not reached, the map has no solution and the program
stops with an error.

This table is computed once and reused for every drone (cached).

### 2. Planning one drone (A* in space and time)

`find_path` searches for the earliest possible arrival of a single drone.
A search state is a pair `(turn, zone)`: being in a zone at turn 3 is a
different state from being in the same zone at turn 5, because the zones that
are free differ between turns. From every state the drone can:

- **wait** – go to `(turn + 1, same zone)` if the zone still has room;
- **move** – go to `(turn + cost, neighbour)` if the connection is free during
  every turn of the flight and the neighbour has room on the arrival turn.

States are expanded with a binary heap (`heapq`) ordered by
`f = turn + distance_to_goal(zone)`. When two states have the same `f` and the
same turn, a state in a `priority` zone is expanded first, so priority zones
are preferred without ever costing extra turns. The distance from stage 1 never
overestimates the real remaining time (other drones can only slow a drone
down), so the first time the end zone is popped from the heap its turn is the
earliest possible arrival. A `seen` set prevents exploring the same
`(turn, zone)` twice, and a `last_steps` dictionary (the state each state
was reached from) is used to rebuild the route once the goal is reached.

The search is bounded: after the last reserved turn the network is empty, so a
drone can always wait at the start and then fly straight to the goal. No useful
path is therefore longer than `last reserved turn + distance(start)`.

### 3. Planning all drones (prioritized / cooperative planning)

`plan_all_drones` plans the drones one after another. After each drone is
planned, its whole route is written to a **reservation table**
(`ReservationTable`):

- `zone_use[(turn, zone)]` – how many drones are inside a zone at the end of a
  turn;
- `link_use[(turn, connection)]` – how many drones use a connection during a
  turn.

Every following drone plans around the drones already reserved. This gives,
without any special case:

- **distribution over several paths** – when the best path is full, the next
  drone takes the next-best one if it arrives earlier than waiting would;
- **strategic waiting** – waiting is an ordinary action of the search;
- **no conflicts or deadlocks** – a drone is only allowed to move where the
  table says there is room, including the arrival turn of a restricted move.

### Complexity

With `V` zones, `E` connections, `D` drones and `T` the length of the
simulation:

| Step                        | Time                         | Memory        |
|-----------------------------|------------------------------|---------------|
| Distance table (once)       | `O((V + E) log V)`           | `O(V)`        |
| One drone (A*)              | `O(V·T·log(V·T))` worst case | `O(V·T)`      |
| All drones                  | `D ×` one drone              | reservations: `O(D·T)` |

In practice the heuristic keeps the number of explored states far below
`V·T`: the search goes almost straight to the goal and only spreads out where
other drones block the way. Paths are not recomputed during the simulation;
they are planned once and then printed.

### Limitations

Drones are planned in a fixed order and each one takes the best route
available *for itself*. This is fast and always produces a valid simulation,
but it is not guaranteed to give the globally minimal number of turns: in some
maps letting an earlier drone take a slightly worse route would let several
later drones arrive sooner.

## Visual representation

The simulation is printed in the terminal using 24-bit ANSI colors, one line
per turn (`src/visualizer.py`).

**Colors**

- every move onto a zone (`D<ID>-<zone>`) is printed in the **color of that
  zone** as defined by `color=` in the map, so drones heading for the same
  zone share a color and routes are easy to follow line by line;
- zones without a color, or with a color name the program does not know, are
  shown in light gray;
- a move onto the connection of a restricted zone (`D<ID>-<connection>`) has
  no color of its own and is shown in light gray, so the 2-turn flights stand
  out from the arrivals.

**Zone states (`--visualizer`)**

Behind every move, in brackets, the program shows how many drones are in the
zone or on the connection at the end of that turn:

| Move | Brackets | Meaning |
|------|----------|---------|
| arrival in a normal zone | `[1/2, priority]` | 1 drone in the zone, capacity 2, zone type `priority` |
| arrival in the start or end zone | `[3]` | 3 drones in the zone (no capacity limit) |
| flight on a connection | `[1/1]` | 1 drone on the connection, `max_link_capacity` 1 |

This makes it easy to see where drones queue up and which zones or links are
full.

**Summary (`--visualizer`)**

After the last turn the program prints the number of drones, the total number
of turns and the average turn at which a drone arrives.

**Default mode**

Without `--visualizer` the program prints only the colored moves, in the exact
format of the subject, so the output can be compared or checked line by line.

## Resources

- P. E. Hart, N. J. Nilsson, B. Raphael, *A Formal Basis for the Heuristic
  Determination of Minimum Cost Paths* (1968) – the original A* paper.
- E. W. Dijkstra, *A Note on Two Problems in Connexion with Graphs* (1959).
- D. Silver, *Cooperative Pathfinding* (AIIDE 2005) – cooperative A* and
  reservation tables for multi-agent pathfinding.
- [Red Blob Games – Introduction to A*](https://www.redblobgames.com/pathfinding/a-star/introduction.html)
- [Python documentation – `heapq`](https://docs.python.org/3/library/heapq.html)
- [ANSI escape codes (Wikipedia)](https://en.wikipedia.org/wiki/ANSI_escape_code)
- [mypy documentation](https://mypy.readthedocs.io/) and
  [flake8 documentation](https://flake8.pycqa.org/)

### Use of AI

An AI assistant (Claude, through Claude Code) was used for:

- reading the subject and listing which requirements were still missing;
- explaining concepts (A*, why the heap and the heuristic give the earliest
  arrival, the role of the `seen` and `last_steps` structures, mypy type
  narrowing);
- planning and guiding the visualizer (the `--visualizer` flag, the per-zone drone
  counts and the summary): I was given step-by-step instructions and wrote
  the code, which I then had checked;
- reviewing the code for bugs (a multi-agent code review) and fixing the
  findings: priority zones were not preferred in the pathfinding, and the
  summary counted the in-flight movements twice;
- drafting this README, which I reviewed and adapted.
