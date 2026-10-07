from typing import Optional

from structure import Graph, Zone


class Visualizer:
    """Print the simulation turn by turn in colored terminal output.

    Attributes:
        graph: The network the drones fly through.
    """

    DEFAULT_RGB: tuple[int, int, int] = (200, 200, 200)
    COLORS: dict[str, tuple[int, int, int]] = {
        "black": (60, 60, 60),
        "white": (240, 240, 240),
        "gray": (150, 150, 150),
        "grey": (150, 150, 150),
        "red": (230, 60, 60),
        "darkred": (160, 30, 30),
        "crimson": (220, 20, 60),
        "maroon": (140, 30, 50),
        "orange": (255, 150, 40),
        "gold": (255, 200, 40),
        "yellow": (245, 225, 60),
        "lime": (150, 230, 60),
        "green": (70, 190, 90),
        "cyan": (60, 210, 220),
        "blue": (70, 120, 235),
        "purple": (160, 80, 200),
        "violet": (190, 120, 230),
        "magenta": (225, 70, 200),
        "pink": (245, 150, 190),
        "brown": (150, 100, 60),
    }

    def __init__(self, graph: Graph) -> None:
        """Store the graph the drones fly through.

        Args:
            graph: The network the drones fly through.
        """
        self.graph = graph

    @staticmethod
    def add_color(text: str, color: Optional[str]) -> str:
        """Return text in the RGB color matching a color name from the map.

        Args:
            text: The text to color.
            color: A color name from the map, or None.

        Returns:
            The text wrapped in ANSI color codes. Unknown colors and None
            use DEFAULT_RGB.
        """
        if color is None:
            r, g, b = Visualizer.DEFAULT_RGB
        else:
            r, g, b = Visualizer.COLORS.get(color.lower(),
                                            Visualizer.DEFAULT_RGB)
        return f"\033[38;2;{r};{g};{b}m{text}\033[0m"

    def run_visualization(
        self, paths: dict[str, list[tuple[int, Zone]]]
    ) -> None:
        """Print one colored line of drone moves per turn.

        Args:
            paths: The planned path of each drone, keyed by drone id.
        """
        turns = self.create_turns(paths)
        for t in range(1, max(turns) + 1):
            try:
                moves = turns[t]
            except KeyError:
                moves = []
            words: list[str] = []
            for move in moves:
                text = move[0]
                zone = move[1]
                colored = self.add_color(text, zone.color)
                words.append(colored)
            print(" ".join(words))

    def create_turns(
        self, paths: dict[str, list[tuple[int, Zone]]]
    ) -> dict[int, list[tuple[str, Zone]]]:
        """Group every drone move by the turn it happens on.

        Args:
            paths: The planned path of each drone, keyed by drone id.

        Returns:
            For each turn, the move texts (e.g. "D1-roof1") together with
            the zone that gives them their color.

        Raises:
            ValueError: If a 2-turn move uses zones that are not connected.
        """
        turns: dict[int, list[tuple[str, Zone]]] = {}
        for drone_id, path in paths.items():
            for (t_start, src), (t_end, dst) in zip(path, path[1:]):
                if src == dst:
                    continue
                if t_end - t_start == 2:
                    con = self.graph.get_connection(src, dst)
                    if con is None:
                        raise ValueError(
                            f"no connection {src.name}-{dst.name}"
                        )
                    if t_start + 1 not in turns:
                        turns[t_start + 1] = []
                    turns[t_start + 1].append((f"{drone_id}-{con.name}", dst))
                if t_end not in turns:
                    turns[t_end] = []
                turns[t_end].append((f"{drone_id}-{dst.name}", dst))
        return turns
