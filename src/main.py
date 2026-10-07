#!/usr/bin/env python3

import sys

from visualizer import Visualizer
from parsing import ParseError, ParseFile
from pathfinding import Pathfinding, PathfindingError


def main() -> None:
    """Parse the map given on the command line, plan and print the moves."""
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
    try:
        pathfinder = Pathfinding(graph)
        paths = pathfinder.plan_all_drones(parser.nb_drones)
    except PathfindingError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    visualizer = Visualizer(graph)
    visualizer.run_visualization(paths)


if __name__ == "__main__":
    main()
