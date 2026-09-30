import heapq

from structure import Connection, Graph, Zone, ZoneType


class PathfindingError(Exception):
    """Error that is raised if pathfinding fails"""


class ReservationTable:
    """Tracks which zones and connections are used on each turn.

    zone_use[(t, zone)] counts the drones inside zone at the END of turn t.
    link_use[(t, conn)] counts the drones on conn DURING turn t.
    Turn 0 is the initial state; the first move happens during turn 1.
    """

    def __init__(self, graph: Graph) -> None:
        """Start with an empty table for the given graph."""
        self.graph = graph
        self.zone_use: dict[tuple[int, str], int] = {}
        self.link_use: dict[tuple[int, str], int] = {}

    def zone_free(self, zone: Zone, turn: int) -> bool:
        """Return whether one more drone can be in zone at the end of turn."""
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
        """Return whether one more drone can use conn during turn."""
        key = (turn, conn.name)
        if key in self.link_use:
            drones_on_link = self.link_use[key]
        else:
            drones_on_link = 0
        if drones_on_link < conn.max_link_capacity:
            return True
        return False

    def can_wait(self, zone: Zone, turn: int) -> bool:
        """Return whether a drone in zone at turn may stay there one more."""
        return self.zone_free(zone, turn + 1)

    def can_move(self, src: Zone, dst: Zone, turn: int) -> bool:
        """Return whether a drone in src at turn may start flying to dst.

        The flight uses the connection during every turn it lasts (2 turns
        for a restricted zone), and the destination must have room on the
        arrival turn, because a drone can never wait on a connection.
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
        """Return the latest turn that has any reservation (0 if none)."""
        latest = 0
        for turn, _name in self.zone_use:
            if turn > latest:
                latest = turn
        for turn, _name in self.link_use:
            if turn > latest:
                latest = turn
        return latest

    def reserve(self, path: list[tuple[int, Zone]]) -> None:
        """Record a planned path so later drones avoid it."""
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
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.dist_to_goal: dict[str, int] = dict()
        self.reservations = ReservationTable(graph)

    def get_distance_left(self) -> None:
        if self.graph.end is None or self.graph.start is None:
            raise PathfindingError("graph has no start or end zone")
        end: Zone = self.graph.end
        self.dist_to_goal = {end.name: 0}
        heap: list[tuple[int, str]] = [(0, end.name)]
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

        if self.graph.start.name not in self.dist_to_goal:
            raise PathfindingError(
                f"no path from '{self.graph.start.name}' "
                f"to '{end.name}'"
            )
