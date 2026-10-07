import heapq

from structure import Connection, Graph, Zone, ZoneType


Path = list[tuple[int, Zone]]
State = tuple[int, str]


class PathfindingError(Exception):
    """Raised when no valid route can be planned."""


class ReservationTable:
    """Track which zones and connections are used on each turn.

    zone_use[(t, zone)] counts the drones inside zone at the END of turn t.
    link_use[(t, conn)] counts the drones on conn DURING turn t.
    Turn 0 is the initial state; the first move happens during turn 1.

    Attributes:
        graph: The network the reservations refer to.
        zone_use: Number of drones per (turn, zone name).
        link_use: Number of drones per (turn, connection name).
    """

    def __init__(self, graph: Graph) -> None:
        """Start with an empty table for the given graph.

        Args:
            graph: The network the reservations refer to.
        """
        self.graph = graph
        self.zone_use: dict[tuple[int, str], int] = {}
        self.link_use: dict[tuple[int, str], int] = {}

    def zone_free(self, zone: Zone, turn: int) -> bool:
        """Check whether one more drone can be in a zone at the end of a turn.

        Args:
            zone: The zone to check.
            turn: The turn to check.

        Returns:
            True if the zone has room left, always True for start and end.
        """
        if zone.is_start or zone.is_end:
            return True
        key = (turn, zone.name)
        if key in self.zone_use:
            drones_there = self.zone_use[key]
        else:
            drones_there = 0
        if drones_there < zone.max_drones:
            return True
        return False

    def link_free(self, conn: Connection, turn: int) -> bool:
        """Check whether one more drone can use a connection during a turn.

        Args:
            conn: The connection to check.
            turn: The turn to check.

        Returns:
            True if the connection has capacity left.
        """
        key = (turn, conn.name)
        if key in self.link_use:
            drones_on_link = self.link_use[key]
        else:
            drones_on_link = 0
        if drones_on_link < conn.max_link_capacity:
            return True
        return False

    def can_wait(self, zone: Zone, turn: int) -> bool:
        """Check whether a drone in a zone may stay there one more turn.

        Args:
            zone: The zone the drone is in.
            turn: The current turn.

        Returns:
            True if the zone still has room at the end of the next turn.
        """
        return self.zone_free(zone, turn + 1)

    def can_move(self, src: Zone, dst: Zone, turn: int) -> bool:
        """Check whether a drone in src at turn may start flying to dst.

        The flight uses the connection during every turn it lasts (2 turns
        for a restricted zone), and the destination must have room on the
        arrival turn, because a drone can never wait on a connection.

        Args:
            src: The zone the drone leaves.
            dst: The zone the drone flies to.
            turn: The turn before the move starts.

        Returns:
            True if the move respects all zone and connection capacities.
        """
        if dst.zone_type is ZoneType.BLOCKED:
            return False
        conn = self.graph.get_connection(src, dst)
        if conn is None:
            return False
        arrival = turn + dst.zone_type.move_cost()
        for flight_turn in range(turn + 1, arrival + 1):
            if not self.link_free(conn, flight_turn):
                return False
        if not self.zone_free(dst, arrival):
            return False
        return True

    def last_turn(self) -> int:
        """Return the latest turn that has any reservation.

        Returns:
            The highest reserved turn, or 0 if nothing is reserved.
        """
        latest = 0
        for turn, _name in self.zone_use:
            if turn > latest:
                latest = turn
        for turn, _name in self.link_use:
            if turn > latest:
                latest = turn
        return latest

    def reserve(self, path: Path) -> None:
        """Record a planned path so later drones avoid it.

        Args:
            path: The (turn, zone) steps of one drone, one entry per turn
                spent in a zone.

        Raises:
            PathfindingError: If two consecutive zones are not connected.
        """
        for turn, zone in path:
            key = (turn, zone.name)
            if key in self.zone_use:
                self.zone_use[key] += 1
            else:
                self.zone_use[key] = 1

        for index in range(len(path) - 1):
            start_turn, from_zone = path[index]
            end_turn, to_zone = path[index + 1]
            if from_zone is to_zone:
                continue
            conn = self.graph.get_connection(from_zone, to_zone)
            if conn is None:
                raise PathfindingError(
                    f"no connection {from_zone.name}-{to_zone.name}"
                )
            for flight_turn in range(start_turn + 1, end_turn + 1):
                key = (flight_turn, conn.name)
                if key in self.link_use:
                    self.link_use[key] += 1
                else:
                    self.link_use[key] = 1


class Pathfinding:
    """Plan conflict-free routes for all drones, one drone at a time.

    Attributes:
        graph: The network to plan in.
        start: The start zone of the graph.
        end: The end zone of the graph.
        paths: The planned path of each drone, keyed by drone id ("D1").
        dist_to_goal: Minimum number of turns from each zone to the end
            zone on an empty map.
        reservations: The zones and connections used by planned drones.
    """

    def __init__(self, graph: Graph) -> None:
        """Prepare pathfinding for an already-parsed graph.

        Args:
            graph: The network to plan in.

        Raises:
            PathfindingError: If the graph has no start or end zone.
        """
        if graph.start is None or graph.end is None:
            raise PathfindingError("graph has no start or end zone")
        self.graph = graph
        self.start: Zone = graph.start
        self.end: Zone = graph.end
        self.paths: dict[str, Path] = {}
        self.dist_to_goal: dict[str, int] = {}
        self.reservations = ReservationTable(graph)

    def plan_all_drones(self, nb_drones: int) -> dict[str, Path]:
        """Plan and reserve a path for every drone, in order.

        Args:
            nb_drones: The number of drones to plan.

        Returns:
            The path of each drone, keyed by drone id ("D1", "D2", ...).

        Raises:
            PathfindingError: If the end zone cannot be reached.
        """
        self.get_distance_left()
        for i in range(1, nb_drones + 1):
            path = self.find_path()
            self.reservations.reserve(path)
            self.paths[f"D{i}"] = path
        return self.paths

    def get_distance_left(self) -> None:
        """Compute dist_to_goal with Dijkstra, starting from the end zone.

        Raises:
            PathfindingError: If the start zone cannot reach the end zone.
        """
        self.dist_to_goal = {self.end.name: 0}
        heap: list[tuple[int, str]] = [(0, self.end.name)]
        while heap:
            dist, name = heapq.heappop(heap)
            if dist > self.dist_to_goal[name]:
                continue
            current = self.graph.zones[name]
            step_cost = current.zone_type.move_cost()
            for neighbour in self.graph.neighbors(current):
                if neighbour.zone_type is ZoneType.BLOCKED:
                    continue
                new_dist = dist + step_cost
                old_dist = self.dist_to_goal.get(neighbour.name)
                if old_dist is None or new_dist < old_dist:
                    self.dist_to_goal[neighbour.name] = new_dist
                    heapq.heappush(heap, (new_dist, neighbour.name))

        if self.start.name not in self.dist_to_goal:
            raise PathfindingError(
                f"no path from '{self.start.name}' "
                f"to '{self.end.name}'"
            )

    def find_path(self) -> Path:
        """Find the earliest conflict-free path from start to end.

        Runs A* over (turn, zone) states. A drone can either wait in its
        zone or move to a neighbour, as long as the reservation table allows
        it. dist_to_goal is used as the heuristic.

        Returns:
            The (turn, zone) steps of the path, starting at (0, start).

        Raises:
            PathfindingError: If no path exists within the turn limit.
        """
        max_turns = (self.reservations.last_turn()
                     + self.dist_to_goal[self.start.name] + 1)

        heap: list[tuple[int, int, str]] = [
            (self.dist_to_goal[self.start.name], 0, self.start.name)
        ]
        last_steps: dict[State, State] = {}
        seen: set[State] = set()

        while heap:
            _estimation, turn, name = heapq.heappop(heap)
            zone = self.graph.zones[name]
            if zone is self.end:
                return self.rebuild(last_steps, (turn, name))
            for neighbour in self.graph.neighbors(zone):
                if not self.reservations.can_move(zone, neighbour, turn):
                    continue
                new_turn = turn + neighbour.zone_type.move_cost()
                new_state = (new_turn, neighbour.name)
                if new_state in seen:
                    continue
                if new_turn > max_turns:
                    continue
                seen.add(new_state)
                last_steps[new_state] = (turn, name)
                estimation = new_turn + self.dist_to_goal[neighbour.name]
                heapq.heappush(heap, (estimation, new_turn, neighbour.name))
            if self.reservations.can_wait(zone, turn):
                new_state = (turn + 1, zone.name)
                if new_state in seen:
                    continue
                if turn + 1 > max_turns:
                    continue
                seen.add(new_state)
                last_steps[new_state] = (turn, name)
                estimation = turn + 1 + self.dist_to_goal[zone.name]
                heapq.heappush(heap, (estimation, turn + 1, zone.name))
        raise PathfindingError(
            f"no route within {max_turns} turns from start to end"
        )

    def rebuild(self, last_steps: dict[State, State], last: State) -> Path:
        """Rebuild a path by following last_steps back from the goal.

        Args:
            last_steps: Maps every reached state to the state it came from.
            last: The goal state the search reached.

        Returns:
            The (turn, zone) steps from the start state to last.
        """
        path: list[State] = []

        current = last
        path.append(current)
        while current in last_steps:
            current = last_steps[current]
            path.append(current)
        path.reverse()
        result: Path = []
        for turn, name in path:
            result.append((turn, self.graph.zones[name]))
        return result
