#!/usr/bin/env python3

import sys

from visualizer import Visualizer
from parsing import ParseError, ParseFile
from pathfinding import Pathfinding, PathfindingError


def main() -> None:
    """Parse the map given on the command line, plan and print the moves."""
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python3 main.py <map_file> [--simple]", file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) == 3 and "--simple" not in sys.argv:
        print("Usage: python3 main.py <map_file> [--simple]", file=sys.stderr)
        sys.exit(1)
    simple = False
    if "--simple" in sys.argv:
        simple = True
    if "--simple" == sys.argv[1]:
        parser = ParseFile(sys.argv[2])
    else:
        parser = ParseFile(sys.argv[1])
    try:
        graph = parser.parse()
    except ParseError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        pathfinder = Pathfinding(graph)
        paths = pathfinder.plan_all_drones(parser.nb_drones)
    except PathfindingError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    visualizer = Visualizer(graph)
    visualizer.run_visualization(paths, simple)


if __name__ == "__main__":
    main()
