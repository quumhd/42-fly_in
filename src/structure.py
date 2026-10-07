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
        """Return the number of turns required to move into this zone type.

        Returns:
            1 for normal and priority zones, 2 for restricted zones.

        Raises:
            ValueError: If the zone is blocked and cannot be entered.
        """
        costs = {
            ZoneType.NORMAL: 1,
            ZoneType.PRIORITY: 1,
            ZoneType.RESTRICTED: 2,
        }
        if self not in costs:
            raise ValueError(f"{self.name} zones cannot be entered.")
        return costs[self]


class Zone:
    """A single node in the drone network.

    Attributes:
        name: Unique name of the zone.
        zone_type: The type of the zone, which sets the cost to enter it.
        x: Horizontal coordinate.
        y: Vertical coordinate.
        max_drones: Maximum number of drones in the zone at once.
        color: Color name used for display, or None.
        is_start: Whether this is the start zone.
        is_end: Whether this is the end zone.
    """

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
        """Initialize a Zone.

        Args:
            name: Unique name of the zone.
            x: Horizontal coordinate.
            y: Vertical coordinate.
            zone_type: The type of the zone.
            max_drones: Maximum number of drones in the zone at once.
            color: Color name used for display, or None.
            is_start: Whether this is the start zone.
            is_end: Whether this is the end zone.
        """
        self.name = name
        self.zone_type = zone_type
        self.x = x
        self.y = y
        self.max_drones = max_drones
        self.color = color
        self.is_start = is_start
        self.is_end = is_end

    def get_zone_name(self) -> str:
        """Return the name of the zone."""
        return self.name


class Connection:
    """A bidirectional edge between two zones.

    Attributes:
        zone1: The first endpoint.
        zone2: The second endpoint.
        max_link_capacity: Maximum number of drones on the connection
            during one turn.
    """

    def __init__(
        self, zone1: Zone, zone2: Zone, max_link_capacity: int = 1
    ) -> None:
        """Initialize a Connection.

        Args:
            zone1: The first endpoint.
            zone2: The second endpoint.
            max_link_capacity: Maximum number of drones on the connection
                during one turn.
        """
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity

    @property
    def name(self) -> str:
        """Return a printable identifier for this connection, e.g. a-b."""
        return f"{self.zone1.name}-{self.zone2.name}"

    def other_end(self, zone: Zone) -> Zone:
        """Return the endpoint of this connection opposite zone.

        Args:
            zone: One endpoint of the connection.

        Returns:
            The other endpoint.

        Raises:
            ValueError: If zone is not an endpoint of this connection.
        """
        if zone is self.zone1:
            return self.zone2
        if zone is self.zone2:
            return self.zone1
        raise ValueError(
            f"Zone {zone.name} is not an endpoint of {self.name}."
        )


class Graph:
    """Own all zones and connections and provide lookup helpers.

    Attributes:
        zones: All zones, keyed by name.
        connections: All connections, keyed by their sorted zone names.
        adjacency: The connections of each zone, keyed by zone name.
        start: The start zone, or None until it is added.
        end: The end zone, or None until it is added.
    """

    def __init__(self) -> None:
        """Initialize an empty graph."""
        self.zones: dict[str, Zone] = {}
        self.connections: dict[tuple[str, str], Connection] = {}
        self.adjacency: dict[str, list[Connection]] = {}
        self.start: Optional[Zone] = None
        self.end: Optional[Zone] = None

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph, tracking start/end if flagged.

        Args:
            zone: The zone to add.
        """
        self.zones[zone.name] = zone
        self.adjacency.setdefault(zone.name, [])
        if zone.is_start:
            self.start = zone
        if zone.is_end:
            self.end = zone

    def get_zone(self, name: str) -> Zone:
        """Look up a zone by name.

        Args:
            name: The name of the zone.

        Returns:
            The zone with that name.

        Raises:
            UnknownZoneError: If no zone has that name.
        """
        if name not in self.zones:
            raise UnknownZoneError(f"No zone named {name} in the graph.")
        return self.zones[name]

    @staticmethod
    def _key(name1: str, name2: str) -> tuple[str, str]:
        """Return an order-independent key for a pair of zone names.

        Args:
            name1: The first zone name.
            name2: The second zone name.

        Returns:
            The two names in sorted order.
        """
        if name1 <= name2:
            return (name1, name2)
        else:
            return (name2, name1)

    def add_connection(self, connection: Connection) -> None:
        """Add a connection, indexed for lookup in either direction.

        Args:
            connection: The connection to add.
        """
        key = self._key(connection.zone1.name, connection.zone2.name)
        self.connections[key] = connection
        for zone in (connection.zone1, connection.zone2):
            if zone.name not in self.adjacency:
                self.adjacency[zone.name] = []
            self.adjacency[zone.name].append(connection)

    def get_connection(
        self, zone1: Zone, zone2: Zone
    ) -> Optional[Connection]:
        """Look up the connection between two zones, in either direction.

        Args:
            zone1: One endpoint.
            zone2: The other endpoint.

        Returns:
            The connection, or None if the zones are not connected.
        """
        key = self._key(zone1.name, zone2.name)
        return self.connections.get(key)

    def neighbors(self, zone: Zone) -> list[Zone]:
        """Return all zones directly connected to zone.

        Args:
            zone: The zone whose neighbours are wanted.

        Returns:
            The neighbouring zones, including blocked ones.
        """
        result: list[Zone] = []
        if zone.name not in self.adjacency:
            return result
        for connection in self.adjacency[zone.name]:
            other_zone = connection.other_end(zone)
            result.append(other_zone)
        return result
