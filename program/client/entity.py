import pygame
from dataclasses import dataclass, field
from typing import Dict, Tuple

@dataclass
class PlayerInfo:
    player_id: int
    username: str
    color: Tuple[int, int, int]
    x: float = 400.0
    y: float = 300.0
    target_x: float = 400.0
    target_y: float = 300.0

class ClientState:
    def __init__(self):
        self.network_players: Dict[int, PlayerInfo] = {}

    def updatePosition(self, pid: int, x: float, y: float):
        if pid in self.network_players:
            self.network_players[pid].target_x = x
            self.network_players[pid].target_y = y

    def update_network_players(self, dt: float):
        lerp_speed = 10.0
        for p in self.network_players.values():
            p.x += (p.target_x - p.x) * lerp_speed * dt
            p.y += (p.target_y - p.y) * lerp_speed * dt

class NetworkState:
    def __init__(self):
        self.mode = "Offline"
        self.room = ""
        
    def reset(self):
        self.mode = "Offline"
        self.room = ""
        
    def toDict(self):
        return {"Mode": self.mode, "Room": self.room}

def update_local_player(screen: pygame.Surface, pos: pygame.Vector2, dt: float):
    speed = 300.0
    keys = pygame.key.get_pressed()
    
    if keys[pygame.K_w] or keys[pygame.K_UP]: pos.y -= speed * dt
    if keys[pygame.K_s] or keys[pygame.K_DOWN]: pos.y += speed * dt
    if keys[pygame.K_a] or keys[pygame.K_LEFT]: pos.x -= speed * dt
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]: pos.x += speed * dt
    
    # Boundary check
    pos.x = max(20, min(screen.get_width() - 20, pos.x))
    pos.y = max(20, min(screen.get_height() - 20, pos.y))

def draw_all_players(screen, local_pos, local_name, local_color, client_state, font):
    # Draw network players
    for p in client_state.network_players.values():
        pygame.draw.circle(screen, p.color, (int(p.x), int(p.y)), 20)
        pygame.draw.circle(screen, (255, 255, 255), (int(p.x), int(p.y)), 20, 2)
        name_surf = font.render(p.username, True, (255, 255, 255))
        screen.blit(name_surf, (p.x - name_surf.get_width()/2, p.y - 25 - name_surf.get_height()))
        
    # Draw local player on top
    pygame.draw.circle(screen, local_color, (int(local_pos.x), int(local_pos.y)), 20)
    pygame.draw.circle(screen, (255, 255, 255), (int(local_pos.x), int(local_pos.y)), 20, 2)
    name_surf = font.render(local_name, True, (255, 255, 0)) # Highlight local name
    screen.blit(name_surf, (local_pos.x - name_surf.get_width()/2, local_pos.y - 25 - name_surf.get_height()))
