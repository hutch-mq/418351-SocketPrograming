import pygame

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

class GameConfig:
    TITLE = "Game Network Project"
    SERVER_IP = "ต้องทำการใส่ IPของ SERVER ก่อนจึงจะใช้งานได้" #ต้องทำการใส่ IPของ SERVER ก่อนจึงจะใช้งานได้    
    SCREEN_WIDTH = 1024
    SCREEN_HEIGHT = 768
    FPS = 60
    NET_TICK_RATE = 20
    SERVER_TIMEOUT = 5.0
    DEFAULT_COLOR = (255, 255, 255)
    
    try:
        pygame.font.init()
        FONT_PATH = pygame.font.match_font('tahoma', bold=True) or pygame.font.get_default_font()
    except:
        FONT_PATH = None
