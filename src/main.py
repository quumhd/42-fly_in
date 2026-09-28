#!/usr/bin/env python3

import sys

from parsing import ParseError, ParseFile


def main() -> None:
    """Parse the map file given on the command line."""
    if len(sys.argv) != 2:
        print("Usage: python3 main.py <map_file>", file=sys.stderr)
        sys.exit(1)
    parser = ParseFile(sys.argv[1])
    try:
        graph = parser.parse()
    except ParseError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Parsed {parser.nb_drones} drones, {len(graph.zones)} zones, "
          f"{len(graph.connections)} connections.")


if __name__ == "__main__":
    main()
