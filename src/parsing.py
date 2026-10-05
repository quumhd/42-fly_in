import re

import structure


class ParseError(Exception):
    """Raised when the map file is invalid."""


class ParseFile:
    """Parse a map file and build the drone network from it."""

    ZONE_PREFIXES: tuple[str, ...] = ("start_hub", "end_hub", "hub")
    ZONE_KEYS: tuple[str, ...] = ("zone", "color", "max_drones")
    CONNECTION_KEYS: tuple[str, ...] = ("max_link_capacity",)
    FORBIDDEN_NAME_CHARS: tuple[str, ...] = ("-", "–", "—")

    def __init__(self, file_path: str) -> None:
        """Store the file path; call parse() to read the file."""
        self.file_path = file_path
        self.nb_drones: int = 0
        self.graph = structure.Graph()

    def parse(self) -> structure.Graph:
        """Read, validate and build the graph described by the file."""
        try:
            with open(self.file_path, "r") as f:
                lines: list[str] = f.readlines()
        except OSError as e:
            raise ParseError(f"cannot read '{self.file_path}': {e.strerror}")

        seen_nb_drones = False
        for i, raw_line in enumerate(lines):
            line_number = i + 1
            parts = raw_line.split("#", 1)
            before_comment = parts[0]
            content = before_comment.strip()
            if not content:
                continue
            key, sep, rest = content.partition(":")
            key = key.strip()
            if not sep:
                raise ParseError(f"missing ':' in '{content}'", line_number)
            if not seen_nb_drones:
                if key != "nb_drones":
                    raise ParseError(
                        "the first line must be 'nb_drones: <number>'",
                        line_number,
                    )
                self.nb_drones = self.parse_nb_drones(rest, line_number)
                seen_nb_drones = True
            elif key == "nb_drones":
                raise ParseError("'nb_drones' defined twice", line_number)
            elif key in self.ZONE_PREFIXES:
                self.parse_zone(key, rest, line_number)
            elif key == "connection":
                self.parse_connection(rest, line_number)
            else:
                raise ParseError(f"unknown line type '{key}'", line_number)

        if not seen_nb_drones:
            raise ParseError("the file does not define 'nb_drones'")
        if self.graph.start is None:
            raise ParseError("the file does not define a 'start_hub'")
        if self.graph.end is None:
            raise ParseError("the file does not define an 'end_hub'")
        return self.graph

    @staticmethod
    def parse_positive_int(value: str, what: str, line_number: int) -> int:
        """Convert value to an int, requiring it to be a positive integer."""
        if not re.fullmatch(r"[0-9]+", value) or int(value) < 1:
            raise ParseError(
                f"{what} must be a positive integer, got '{value}'",
                line_number,
            )
        return int(value)

    @staticmethod
    def parse_int(value: str, what: str, line_number: int) -> int:
        """Convert value to an int, requiring it to be an integer."""
        if not re.fullmatch(r"-?[0-9]+", value):
            raise ParseError(
                f"{what} must be an integer, got '{value}'", line_number
            )
        return int(value)

    def parse_nb_drones(self, rest: str, line_number: int) -> int:
        """Return the number of drones from the text after 'nb_drones:'."""
        parts = rest.split()
        if len(parts) != 1:
            raise ParseError(
                "the first line must be 'nb_drones: <number>'", line_number
            )
        return self.parse_positive_int(parts[0], "nb_drones", line_number)

    @staticmethod
    def split_metadata(
        rest: str, allowed_keys: tuple[str, ...], line_number: int
    ) -> tuple[str, dict[str, str]]:
        """Split 'body [k=v ...]' into the body and a metadata dict."""
        if "[" not in rest:
            if "]" in rest:
                raise ParseError("unmatched ']' in metadata", line_number)
            return rest, {}
        start = rest.index("[")
        if not rest.endswith("]"):
            raise ParseError(
                "metadata must be enclosed in '[...]' at the end of the line",
                line_number,
            )
        inside = rest[start + 1:-1]
        if "[" in inside or "]" in inside:
            raise ParseError("only one metadata block is allowed", line_number)
        metadata: dict[str, str] = {}
        for item in inside.split():
            key, sep, value = item.partition("=")
            if not sep or not key or not value or "=" in value:
                raise ParseError(
                    f"invalid metadata '{item}', expected 'key=value'",
                    line_number,
                )
            if key not in allowed_keys:
                raise ParseError(f"unknown metadata '{key}'", line_number)
            if key in metadata:
                raise ParseError(f"duplicate metadata '{key}'", line_number)
            metadata[key] = value
        return rest[:start], metadata

    def check_name(self, name: str, line_number: int) -> None:
        """Check that name is a legal zone name."""
        for char in self.FORBIDDEN_NAME_CHARS:
            if char in name:
                raise ParseError(
                    f"zone name '{name}' cannot contain dashes", line_number
                )

    def parse_zone(self, kind: str, rest: str, line_number: int) -> None:
        """Parse a start_hub, end_hub or hub line and add it to the graph."""
        body, metadata = self.split_metadata(
            rest, self.ZONE_KEYS, line_number
        )
        parts = body.split()
        if len(parts) != 3:
            raise ParseError(
                f"expected '{kind}: <name> <x> <y> [metadata]'", line_number
            )
        name, x_str, y_str = parts
        self.check_name(name, line_number)
        if name in self.graph.zones:
            raise ParseError(f"zone '{name}' is already defined", line_number)
        x = self.parse_int(x_str, "x coordinate", line_number)
        y = self.parse_int(y_str, "y coordinate", line_number)

        zone_type = structure.ZoneType.NORMAL
        if "zone" in metadata:
            try:
                zone_type = structure.ZoneType(metadata["zone"])
            except ValueError:
                raise ParseError(
                    f"invalid zone type '{metadata['zone']}' (expected "
                    "normal, blocked, restricted or priority)",
                    line_number,
                )
        max_drones = 1
        if "max_drones" in metadata:
            max_drones = self.parse_positive_int(
                metadata["max_drones"], "max_drones", line_number
            )

        if kind == "start_hub":
            is_start = True
        else:
            is_start = False

        if kind == "end_hub":
            is_end = True
        else:
            is_end = False

        if is_start and self.graph.start is not None:
            raise ParseError("there can only be one start_hub", line_number)
        if is_end and self.graph.end is not None:
            raise ParseError("there can only be one end_hub", line_number)
        if (is_start or is_end) and zone_type is structure.ZoneType.BLOCKED:
            raise ParseError(f"{kind} cannot be a blocked zone", line_number)

        self.graph.add_zone(
            structure.Zone(
                name=name,
                x=x,
                y=y,
                zone_type=zone_type,
                max_drones=max_drones,
                color=metadata.get("color"),
                is_start=is_start,
                is_end=is_end,
            )
        )

    def parse_connection(self, rest: str, line_number: int) -> None:
        """Parse a connection line and add it to the graph."""
        body, metadata = self.split_metadata(
            rest, self.CONNECTION_KEYS, line_number
        )
        parts = body.split()
        if len(parts) != 1:
            raise ParseError(
                "expected 'connection: <zone1>-<zone2> [metadata]'",
                line_number,
            )
        names = parts[0].split("-")
        if len(names) != 2 or not names[0] or not names[1]:
            raise ParseError(
                f"invalid connection '{parts[0]}', expected '<zone1>-<zone2>'",
                line_number,
            )
        for name in names:
            if name not in self.graph.zones:
                raise ParseError(
                    f"zone '{name}' is not defined before this connection",
                    line_number,
                )
        if names[0] == names[1]:
            raise ParseError(
                f"zone '{names[0]}' cannot connect to itself", line_number
            )
        zone1 = self.graph.zones[names[0]]
        zone2 = self.graph.zones[names[1]]
        if self.graph.get_connection(zone1, zone2) is not None:
            raise ParseError(
                f"connection '{parts[0]}' is already defined", line_number
            )
        capacity = 1
        if "max_link_capacity" in metadata:
            capacity = self.parse_positive_int(
                metadata["max_link_capacity"], "max_link_capacity",
                line_number,
            )
        self.graph.add_connection(
            structure.Connection(zone1, zone2, max_link_capacity=capacity)
        )
