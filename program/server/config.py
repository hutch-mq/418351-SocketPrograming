MAGIC_NUMBER = 0x8750
DEFAULT_PORT = 42512

class PacketType:
    CREATE_ROOM = 0x01
    JOIN_ROOM = 0x02
    LEAVE_ROOM = 0x0B
    MOVE = 0x08
    STATE_UPDATE = 0x09
    ERROR = 0x0A
    LIST_ROOMS = 0x0C

class TargetType:
    SERVER = 0x00
    ROOM = 0x01

class StatusCode:
    OK = 0x00
    ROOM_NOT_FOUND = 0x01
    ROOM_FULL = 0x02
    ERROR = 0x03
    NAME_TAKEN = 0x04
    COLOR_TAKEN = 0x05
    MAX_ROOMS_REACHED = 0x06
