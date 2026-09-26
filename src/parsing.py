
import structure


class ParseFile():

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.lines = []
        with open(file_path, "r") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                self.lines.append(line)
        self.start_hub = self.get_start_hub()
        self.end_hub = self.get_end_hub()
        self.hubs = self.get_all_hubs()

    def check_file(self) -> bool:
        """Check if the file is valid."""
        with open(self.file_path, "r") as f:
            for i, line in enumerate(f):
                if line.startswith("#"):
                    continue
                elif len(line) == 1:
                    continue
                elif i == 0:
                    self.check_nb_drones(line)
                elif line.startswith("start_hub:"):
                    self.check_hub(line, i+1)
                elif line.startswith("end_hub:"):
                    self.check_hub(line, i+1)
                elif line.startswith("hub:"):
                    self.check_hub(line, i+1)
                elif line.startswith("connection:"):
                    self.check_connection(line, i+1)
                else:
                    raise ValueError(f"Line {i+1} is invalid: {line.strip()}")
        return True

    @staticmethod
    def check_nb_drones(line: str) -> None:
        """Check if the line is a valid nb_drones line."""
        parts = line.split()
        if len(parts) != 2:
            raise ValueError("line '1' must be 'nb_drones <num>'")
        if parts[0] != ("nb_drones:"):
            raise ValueError("line '1' must be 'nb_drones <num>'")
        if not parts[1].isdigit():
            raise ValueError("line '1' must be 'nb_drones <num>'")
        if int(parts[1]) < 1:
            raise ValueError("line '1' 'nb_drones' must be a positive integer")

    @staticmethod
    def check_hub(line: str, line_number: int) -> bool:
        """Check if the line is a valid hub line."""
        parts = line.split()
        if len(parts) < 5:
            raise ValueError(f"parts Line {line_number} is invalid: {line[:-1]}")
        if parts[0] not in ("start_hub:", "end_hub:", "hub:"):
            raise ValueError(f"start Line {line_number} is invalid: {line[:-1]}")
        if "-" in parts[1] or "–" in parts[1] or "—" in parts[1]:
            raise ValueError(f"Line {line_number}: Name cannot contain '=': {line[:-1]}")
        x, y = ParseFile.get_coordinates(line)
        if not (isinstance(x, int) and isinstance(y, int)):
            raise ValueError(f"Line {line_number}: invalid coordinates: {line[:-1]}")
        if x < 0 or y < 0:
            raise ValueError(f"Line {line_number}: coordinates need to be positive: {line[:-1]}")
        try:
            temp = (line.split()[4:])
        except IndexError:
            return True
        temp[0] = temp[0][1:]
        temp[-1] = temp[-1][:-1]
        for data in temp:
            if data.startswith("max_drones="):
                temp2 = data.split("=")
                if not temp2[1].isdigit():
                    raise ValueError(f"Line {line_number}: max_drones must be an integer: {data}")
                if int(temp2[1]) < 1:
                    raise ValueError(f"Line {line_number}: max_drones must be a positive integer: {data}")
            elif data.startswith("color="):
                temp2 = data.split("=")
                # check if color is valid
            elif data.startswith("zone="):
                temp2 = data.split("=")
                if temp2[1] not in ("normal", "priority", "restricted", "blocked"):
                    raise ValueError(f"Line {line_number}: invalid zone_type: {data}")
            else:
                raise ValueError(f"Line {line_number}: unknown metadata: {data}")
        return True

    def check_connection(self, line: str, line_number: int) -> bool:
        con1_valid = False
        con2_valid = False
        parts = line.split()
        connections = parts[1].split("-")
        if self.start_hub.get_zone_name() == connections[0]:
            con1_valid = True
        elif self.end_hub.get_zone_name() == connections[0]:
            con1_valid = True
        else:
            for hub in self.hubs:
                if hub.get_zone_name() == connections[0]:
                    con1_valid = True
                    break
            if con1_valid == False:
                raise ValueError(f"Connection {connections[0]} on Line {line_number} does not exist")
        if self.start_hub.get_zone_name() == connections[1]:
            con2_valid = True
        elif self.end_hub.get_zone_name() == connections[1]:
            con2_valid = True
        else:
            for hub in self.hubs:
                if hub.get_zone_name() == connections[1]:
                    con2_valid = True
                    break
            if con2_valid == False:
                raise ValueError(f"Connection {connections[1]} on Line {line_number} does not exist")
        if con1_valid and con2_valid:
            return True
        return False

    def get_nb_drones(self) -> int:
        """Return the number of drones from the file."""
        if self.lines[0].startswith("nb_drones"):
            return int(self.lines[0].split()[1])
        raise ValueError("No nb_drones found at the beginning of the file.")

    def get_start_hub(self) -> structure.Zone:
        """Return the start hub zone."""
        for line in self.lines:
            if line.startswith("start_hub"):
                return structure.Zone(
                    name=self.get_name(line),
                    x=self.get_coordinates(line)[0],
                    y=self.get_coordinates(line)[1],
                    zone_type=self.get_zone_type(line),
                    max_drones=self.get_max_drones(line),
                    color=self.get_metadata_color(line),
                    is_start=True,
                )
        raise ValueError("No start_hub found in the file.")

    def get_end_hub(self) -> structure.Zone:
        """Return the end hub zone."""
        for line in self.lines:
            if line.startswith("end_hub"):
                return structure.Zone(
                    name=self.get_name(line),
                    x=self.get_coordinates(line)[0],
                    y=self.get_coordinates(line)[1],
                    zone_type=self.get_zone_type(line),
                    max_drones=self.get_max_drones(line),
                    color=self.get_metadata_color(line),
                    is_end=True,
                )
        raise ValueError("No end_hub found in the file.")

    def get_all_hubs(self) -> list[structure.Zone]:
        """Return a list of all hub zones."""
        hubs = []
        for line in self.lines:
            if line.startswith("hub"):
                hubs.append(
                    structure.Zone(
                        name=self.get_name(line),
                        x=self.get_coordinates(line)[0],
                        y=self.get_coordinates(line)[1],
                        zone_type=self.get_zone_type(line),
                        max_drones=self.get_max_drones(line),
                        color=self.get_metadata_color(line),
                    )
                )
        return hubs

    @staticmethod
    def get_name(line: str) -> str:
        """Return the name of a zone or connection from a line."""
        return line.split()[1]

    @staticmethod
    def get_coordinates(line: str) -> tuple[int, int]:
        """Return the (x, y) coordinates of a zone from a line."""
        _, _, x, y, *_ = line.split()
        return int(x), int(y)

    @staticmethod
    def get_max_drones(line: str) -> int:
        """Return the maximum number of drones for a zone from a line."""
        args = line.split()
        for arg in args:
            if arg.startswith("max_drones="):
                temp = arg.split("=")
                return temp[1]
        return -1

    @staticmethod
    def get_zone_type(line: str) -> structure.ZoneType:
        """Return the zone type from a line."""
        args = line.split()
        for arg in args:
            if arg.startswith("zone="):
                temp = arg.split("=")
                return structure.ZoneType.get_zone_type(temp[1])
        return structure.ZoneType.NORMAL

    @staticmethod
    def get_metadata_zone(line: str) -> str:
        """Return the metadata zone type from a line."""
        if not line.startswith("connection") and not line.startswith("nb_d"):
            raise ValueError("Line needs to be a hub")

    @staticmethod
    def get_metadata_color(line: str) -> str:
        """Return the metadata color from a line."""
        if not line.startswith("connection") and not line.startswith("nb_d"):
            try:
                temp = (line.split()[4:])
            except IndexError:
                return None
            temp[0] = temp[0][1:]
            temp[-1] = temp[-1][:-1]
            for data in temp:
                if data.startswith("color="):
                    temp2 = data.split("=")
                    return temp2[1]
            return None
        raise ValueError("Line needs to be a hub")

    @staticmethod
    def get_metadata_max_drones(line: str) -> str:
        """Return the metadata max drones from a line."""
        if not line.startswith("connection") and not line.startswith("nb_d"):
            try:
                temp = (line.split()[4:])
            except IndexError:
                return 1
            temp[0] = temp[0][1:]
            temp[-1] = temp[-1][:-1]
            for data in temp:
                if data.startswith("max_drones="):
                    temp2 = data.split("=")
                    return int(temp2[1])
            return 1
        raise ValueError("Line needs to be a hub")

    @staticmethod
    def get_metadata_max_link_capacity(line: str) -> str:
        """Return the metadata max link capacity from a line."""
        if line.startswith("connection"):
            try:
                temp = (line.split()[2:])
            except IndexError:
                return 1
            temp[0] = temp[0][1:]
            temp[-1] = temp[-1][:-1]
            for data in temp:
                if data.startswith("max_link_capacity="):
                    temp2 = data.split("=")
                    return int(temp2[1])
            return 1
        raise ValueError("Line needs to be a connection")


parser = ParseFile("data.txt")
try:
    parser.check_file()
    print("File is valid!")
except ValueError as e:
    print(f"Error: {e}")
