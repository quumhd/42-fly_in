import heapq

from structure import Graph, Zone, ZoneType

class PathfindingError(Exception):
    """Error that is raised if pathfinding fails"""


class Pathfinding:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.dist_to_goal: dict[str, int] = dict()

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
       