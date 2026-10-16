#!/usr/bin/env python3

import sys

from visualizer import Visualizer
from parsing import ParseError, ParseFile
from pathfinding import Pathfinding, PathfindingError


def main() -> None:
    """Parse the map given on the command line, plan and print the moves.

    With the --visualizer flag, the drone counts and a summary are added.
    """
    args = [arg for arg in sys.argv[1:] if arg != "--visualizer"]
    if len(args) != 1:
        print("Usage: python3 main.py [--visualizer] <map_file>",
              file=sys.stderr)
        sys.exit(1)
    detailed = "--visualizer" in sys.argv
    parser = ParseFile(args[0])
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
    visualizer.run_visualization(paths, detailed)


if __name__ == "__main__":
    main()
