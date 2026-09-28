from __future__ import annotations

from enum import Enum
from typing import Optional


class ZoneCapacityError(Exception):
    """Raised when a drone tries to enter a zone or connection that is full."""


class EmptyOccupantError(Exception):
    """Raised when a drone is removed from an empty zone or connection."""


class UnknownZoneError(Exception):
    """Raised when a zone name is referenced but not present in the graph."""


class ZoneType(Enum):
    """The four zone kinds allowed by the input format."""

    NORMAL = "normal"
    PRIORITY = "priority"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"

    def move_cost(self) -> int:
        """Return the number of turns required to move into this zone type."""
        costs = {
            ZoneType.NORMAL: 1,
            ZoneType.PRIORITY: 1,
            ZoneType.RESTRICTED: 2,
        }
        if self not in costs:
            raise ValueError(f"{self.name} zones cannot be entered.")
        return costs[self]

    @staticmethod
    def get_zone_type(zone_type_str: str) -> ZoneType:
        """Return the ZoneType corresponding to a string."""
        if zone_type_str == "normal":
            return ZoneType.NORMAL
        elif zone_type_str == "priority":
            return ZoneType.PRIORITY
        elif zone_type_str == "restricted":
            return ZoneType.RESTRICTED
        elif zone_type_str == "blocked":
            return ZoneType.BLOCKED
        else:
            raise ValueError(f"Unknown zone type: {zone_type_str}")


class Zone:
    """A single node in the drone network."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        max_drones: int = 1,
        color: Optional[str] = None,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Initialize a Zone."""
        self.name = name
        self.zone_type = zone_type
        self.x = x
        self.y = y
        self.max_drones = max_drones
        self.color = color
        self.is_start = is_start
        self.is_end = is_end
        self.current_drones = 0

    def has_capacity(self) -> bool:
        """Return whether one more drone may currently enter this zone."""
        if self.is_start or self.is_end:
            return True
        return self.current_drones < self.max_drones

    def add_drone(self) -> None:
        """Register one more drone as occupying this zone."""
        if not self.has_capacity():
            raise ZoneCapacityError(
                f"Zone {self.name} has reached its maximum capacity "
                f"of {self.max_drones} drones."
            )
        self.current_drones += 1

    def remove_drone(self) -> None:
        """Remove one drone from this zone's occupancy count."""
        if self.current_drones <= 0:
            raise EmptyOccupantError(
                f"Zone {self.name} has no drones to remove."
            )
        self.current_drones -= 1

    def get_zone_name(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Zone({self.name}, type={self.zone_type.value})"


class Connection:
    """A bidirectional edge between two zones."""

    def __init__(
        self, zone1: Zone, zone2: Zone, max_link_capacity: int = 1
    ) -> None:
        """Initialize a Connection."""
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity
        self.current_drones = 0

    @property
    def name(self) -> str:
        """Return a printable identifier for this connection, e.g. a-b."""
        return f"{self.zone1.name}-{self.zone2.name}"

    def other_end(self, zone: Zone) -> Zone:
        """Return the endpoint of this connection opposite zone."""
        if zone is self.zone1:
            return self.zone2
        if zone is self.zone2:
            return self.zone1
        raise ValueError(
            f"Zone {zone.name} is not an endpoint of {self.name}."
        )

    def has_capacity(self) -> bool:
        """Return whether one more drone may traverse this connection now."""
        return self.current_drones < self.max_link_capacity

    def add_drone(self) -> None:
        """Register one more drone as traversing this connection."""
        if not self.has_capacity():
            raise ZoneCapacityError(
                f"Connection {self.name} has reached its maximum capacity "
                f"of {self.max_link_capacity} drones."
            )
        self.current_drones += 1

    def remove_drone(self) -> None:
        """Remove one drone from this connection's occupancy count."""
        if self.current_drones <= 0:
            raise EmptyOccupantError(
                f"Connection {self.name} has no drones to remove."
            )
        self.current_drones -= 1

    def __repr__(self) -> str:
        return f"Connection({self.name}, capacity={self.max_link_capacity})"


class Graph:
    """Owns all zones and connections and exposes lookup helpers."""

    def __init__(self) -> None:
        """Initialize an empty graph."""
        self.zones: dict[str, Zone] = {}
        self.connections: dict[tuple[str, str], Connection] = {}
        self.adjacency: dict[str, list[Connection]] = {}
        self.start: Optional[Zone] = None
        self.end: Optional[Zone] = None

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph, tracking start/end if flagged."""
        self.zones[zone.name] = zone
        self.adjacency.setdefault(zone.name, [])
        if zone.is_start:
            self.start = zone
        if zone.is_end:
            self.end = zone

    def get_zone(self, name: str) -> Zone:
        """Look up a zone by name."""
        if name not in self.zones:
            raise UnknownZoneError(f"No zone named {name} in the graph.")
        return self.zones[name]

    @staticmethod
    def _key(name1: str, name2: str) -> tuple[str, str]:
        """Return an order-independent key for a pair of zone names."""
        return (name1, name2) if name1 <= name2 else (name2, name1)

    def add_connection(self, connection: Connection) -> None:
        """Add a connection, indexed for lookup in either direction."""
        key = self._key(connection.zone1.name, connection.zone2.name)
        self.connections[key] = connection
        self.adjacency.setdefault(connection.zone1.name, []).append(connection)
        self.adjacency.setdefault(connection.zone2.name, []).append(connection)

    def get_connection(self, zone1: Zone, zone2: Zone) -> Optional[Connection]:
        """Look up the connection between two zones, in either direction."""
        key = self._key(zone1.name, zone2.name)
        return self.connections.get(key)

    def neighbors(self, zone: Zone) -> list[Zone]:
        """Return all zones directly connected to zone."""
        return [
            connection.other_end(zone)
            for connection in self.adjacency.get(zone.name, [])
        ]


class Drone:
    """A single drone's identity, position, and in-transit state."""

    def __init__(self, drone_id: str, current_zone: Zone) -> None:
        """Initialize a drone sitting at its starting zone."""
        self.drone_id = drone_id
        self.current_zone: Optional[Zone] = current_zone
        self.assigned_path: list[Zone] = []
        self.in_transit_connection: Optional[Connection] = None
        self.turns_remaining: Optional[int] = None
        self.finished = False

    def is_in_transit(self) -> bool:
        """Return whether the drone is mid-flight on a connection."""
        return self.in_transit_connection is not None

    def start_transit(self, connection: Connection, turns: int) -> None:
        """Commit the drone to crossing a connection over several turns."""
        if self.is_in_transit():
            raise ValueError(f"Drone {self.drone_id} is already in transit.")
        self.current_zone = None
        self.in_transit_connection = connection
        self.turns_remaining = turns

    def tick_transit(self) -> None:
        """Advance the in-transit countdown by one turn."""
        if self.turns_remaining is None:
            raise ValueError(f"Drone {self.drone_id} is not in transit.")
        self.turns_remaining -= 1

    def arrive(self, zone: Zone) -> None:
        """Land the drone at ``zone``, clearing any in-transit state."""
        self.current_zone = zone
        self.in_transit_connection = None
        self.turns_remaining = None
        if zone.is_end:
            self.finished = True

    def __repr__(self) -> str:
        where = (
            self.current_zone.name
            if self.current_zone
            else self.in_transit_connection
        )
        return f"Drone({self.drone_id}, at={where})"


class Simulation:
    """Orchestrates the turn-by-turn movement of all drones."""

    def __init__(self, graph: Graph) -> None:
        """Initialize a simulation over an already-built graph."""
        self.graph = graph
        self.drones: dict[str, Drone] = {}
        self.turn = 0
        self.log: list[str] = []

    def add_drone(self, drone: Drone) -> None:
        """Register a drone with the simulation."""
        self.drones[drone.drone_id] = drone

    def all_delivered(self) -> bool:
        """Return whether every registered drone has reached the end zone."""
        return all(drone.finished for drone in self.drones.values())

    def record_turn(self, moves: dict[str, str]) -> None:
        """Append one formatted line to the simulation log."""
        line = " ".join(
            f"{drone_id}-{dest}" for drone_id, dest in moves.items()
        )
        self.log.append(line)
        self.turn += 1
